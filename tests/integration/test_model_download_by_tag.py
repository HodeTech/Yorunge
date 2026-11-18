"""``models download --model OWNER/SLUG --version-tag TAG`` on a loopback TLS provider (P02-4f).

The catalog resolves the one version (two GETs, nothing guessed) and the download then runs on
the same state store, lock and engine as the version path. Each journey is judged on the wire
(which requests, in which order, with which credential), on disk (the target and its leftovers)
and in the result (the resolved identity, the warning of a dropped partial, the closed error).
"""

import json

import pytest

from tests.fixtures.http_server import Reply
from tests.fixtures.model_network import loopback_models
from tests.integration.test_download_engine import CUT, DATA, ORIGIN, TAG, credential, sha
from tests.integration.test_model_download import (
    BASE,
    JSON_PATH,
    NAME,
    SECRET,
    SIGNED,
    VERSION,
    Rig,
    json_route,
)
from tests.integration.test_model_download import certificates as certificates
from tests.integration.test_model_download import loopback_only as loopback_only
from tests.integration.test_model_download import workspace as workspace
from yorunge import api
from yorunge.adapters import catalog_http
from yorunge.adapters.download_engine import REPLACED_PARTIAL_WARNING
from yorunge.adapters.download_sink import open_held_sink
from yorunge.adapters.http_session import HttpSession
from yorunge.adapters.http_transport import HttpxTransport
from yorunge.domain.download import download_names
from yorunge.domain.errors import YorungeError

OWNER = "owner-1"
SLUG = "model-a"
MODEL_ID = "model-uuid-1"
STAMP = "2026-01-01T00:00:00Z"
VERSION_TAG = "1.1"
OTHER = "00000000-0000-4000-8000-0000000000aa"
DETAIL = f"{BASE}/models/{OWNER}/{SLUG}"
VERSIONS = f"{BASE}/models/{MODEL_ID}/versions"
JSON_QUERY = f"{JSON_PATH}?format=onnx"
KEY = "a" * 64


def model_record(**overrides):
    record = {
        "id": MODEL_ID,
        "owner_username": OWNER,
        "slug": SLUG,
        "name": "Model A",
        "description": "Synthetic",
        "license": "mit",
        "modality": "VISION",
        "stage": "EXPERIMENTAL",
        "visibility": "PRIVATE",
        "versions_count": 1,
        "architecture": "yolov8n",
        "created_at": STAMP,
        "updated_at": STAMP,
    }
    record.update(overrides)
    return record


def version_record(version_id=VERSION, tag=VERSION_TAG):
    return {
        "id": version_id,
        "version_tag": tag,
        "framework": "pytorch",
        "file_size_bytes": len(DATA),
        "created_at": STAMP,
        "weights_url": "https://example.invalid/private/signed?sig=synthetic",
        "onnx_url": None,
        "tflite_url": None,
    }


def reply(value):
    return Reply(body=json.dumps(value).encode("utf-8"))


def code_of(action):
    try:
        action()
    except YorungeError as error:
        return error.code
    raise AssertionError("a closed error was expected")


class TagRig(Rig):
    """The provider behind TLS, for the catalog as well as for the download (both reach it)."""

    def __init__(
        self, certificates, workspace, monkeypatch, provider=None, *, route=None, **routes
    ):
        super().__init__(certificates, workspace, provider, route=route, **routes)
        self._monkeypatch = monkeypatch

    def __enter__(self):
        super().__enter__()
        server = self.server
        self._monkeypatch.setattr(
            catalog_http,
            "HttpSession",
            lambda: HttpSession(
                transport_factory=lambda: HttpxTransport(
                    transport=server.transport(hostname="localhost")
                )
            ),
        )
        return self

    def values(self, changes):
        values = {
            "artifact_format": "onnx",
            "weights_out": self.target,
            "config": self.config,
            "state_dir": self.state,
        }
        values.update(changes)
        return values

    def call_tag(self, model=f"{OWNER}/{SLUG}", tag=VERSION_TAG, **changes):
        with loopback_models(self.certificates[0], self.server.port):
            return api.download_model_weights_by_tag(model, tag, **self.values(changes))

    def run_cli(self, capsys, *argv):
        from yorunge.cli import main

        with loopback_models(self.certificates[0], self.server.port):
            code = main(list(argv))
        out, err = capsys.readouterr()
        return code, out, err


def tag_rig(certificates, workspace, monkeypatch, *, detail=None, listing=None, **routes):
    catalog = {
        DETAIL: detail or reply(model_record()),
        VERSIONS: listing or reply([version_record()]),
    }
    return TagRig(certificates, workspace, monkeypatch, **catalog, **routes)


def leave_partial_of_another_version(certificates, workspace):
    """A download of ``OTHER`` cut in the middle: its stage and sidecar stay, resumable."""
    other = {f"{BASE}/models/versions/{OTHER}/download?format=onnx": json_route()}
    with Rig(certificates, workspace, **other) as rig:
        rig.provider.script = [Reply(body=DATA, headers=(("ETag", TAG),), truncate_at=CUT)]
        with loopback_models(rig.certificates[0], rig.server.port):
            assert (
                code_of(
                    lambda: api.download_model_weights(
                        OTHER,
                        artifact_format="onnx",
                        weights_out=rig.target,
                        config=rig.config,
                        state_dir=rig.state,
                    )
                )
                == "download_incomplete"
            )
    names = download_names(NAME)
    assert sorted(p.name for p in rig.directory.iterdir()) == sorted([names.stage, names.sidecar])


# --- resolution and the download ----------------------------------------------------------------


def test_a_tag_resolves_to_one_version_and_that_version_is_downloaded(
    workspace, certificates, monkeypatch
):
    with tag_rig(certificates, workspace, monkeypatch) as rig:
        result = rig.call_tag()
    summary = result.data
    assert (summary.bytes, summary.sha256) == (len(DATA), sha(DATA))
    assert summary.source.version_id == VERSION
    resolved = summary.resolution
    assert resolved is not None
    assert (resolved.model_id, resolved.owner, resolved.slug) == (MODEL_ID, OWNER, SLUG)
    assert (resolved.version_tag, resolved.version_id) == (VERSION_TAG, VERSION)
    assert result.warnings == ()
    assert [record.path for record in rig.server.requests] == [DETAIL, VERSIONS, JSON_QUERY, SIGNED]
    assert rig.server.requests[0].header("X-API-Key") == SECRET
    assert rig.signed()[0].header("X-API-Key") is None
    assert rig.signed()[0].header("Authorization") is None
    assert rig.target.read_bytes() == DATA
    assert rig.names() == [NAME]


def test_a_cut_version_id_download_resumes_when_the_same_version_is_asked_by_its_tag(
    workspace, certificates, monkeypatch
):
    with Rig(certificates, workspace) as rig:
        rig.provider.script = [Reply(body=DATA, headers=(("ETag", TAG),), truncate_at=CUT)]
        assert code_of(rig.call) == "download_incomplete"
    with tag_rig(certificates, workspace, monkeypatch) as rig:
        summary = rig.call_tag().data
    assert (summary.resumed, summary.resumed_from_bytes, summary.bytes) == (True, CUT, len(DATA))
    assert rig.provider.seen == [(f"bytes={CUT}-", TAG)]
    assert rig.target.read_bytes() == DATA


def test_a_partial_of_another_version_is_dropped_and_the_result_says_so(
    workspace, certificates, monkeypatch
):
    leave_partial_of_another_version(certificates, workspace)
    with tag_rig(certificates, workspace, monkeypatch) as rig:
        result = rig.call_tag()
    assert result.warnings == (REPLACED_PARTIAL_WARNING,)
    assert result.data.resumed is False
    assert result.data.source.version_id == VERSION
    assert rig.target.read_bytes() == DATA
    assert rig.names() == [NAME]


# --- refusals: no request, no file -----------------------------------------------------------


def test_a_missing_tag_is_not_visible_and_nothing_is_downloaded(
    workspace, certificates, monkeypatch
):
    with tag_rig(
        certificates, workspace, monkeypatch, listing=reply([version_record(tag="2.0")])
    ) as rig:
        assert code_of(lambda: rig.call_tag()) == "model_not_visible"
    assert rig.json_calls() == [] and rig.signed() == [] and rig.names() == []


def test_an_ambiguous_tag_stops_before_any_choice(workspace, certificates, monkeypatch):
    listing = reply([version_record(version_id=VERSION), version_record(version_id=OTHER)])
    with tag_rig(
        certificates,
        workspace,
        monkeypatch,
        detail=reply(model_record(versions_count=2)),
        listing=listing,
    ) as rig:
        assert code_of(lambda: rig.call_tag()) == "model_ambiguous"
    assert rig.json_calls() == [] and rig.signed() == [] and rig.names() == []


def test_an_owner_less_model_is_not_addressable_by_owner_and_slug(
    workspace, certificates, monkeypatch
):
    with tag_rig(
        certificates, workspace, monkeypatch, detail=reply(model_record(owner_username=None))
    ) as rig:
        assert code_of(lambda: rig.call_tag()) == "model_not_addressable"
    assert rig.json_calls() == [] and rig.names() == []


def test_a_version_list_that_disagrees_with_the_detail_count_is_an_invalid_response(
    workspace, certificates, monkeypatch
):
    with tag_rig(
        certificates, workspace, monkeypatch, detail=reply(model_record(versions_count=2))
    ) as rig:
        assert code_of(lambda: rig.call_tag()) == "invalid_response"
    assert rig.json_calls() == [] and rig.names() == []


@pytest.mark.parametrize(
    "model,tag",
    [
        ("no-slash", VERSION_TAG),
        ("a/b/c", VERSION_TAG),
        ("/slug", VERSION_TAG),
        (f"{OWNER}/..", VERSION_TAG),
        (f"{OWNER}/{SLUG}", ""),
        (f"{OWNER}/{SLUG}", "x" * 129),
    ],
)
def test_a_bad_reference_is_refused_before_any_file_or_request(
    workspace, certificates, monkeypatch, model, tag
):
    with tag_rig(certificates, workspace, monkeypatch) as rig:
        assert code_of(lambda: rig.call_tag(model=model, tag=tag)) == "invalid_request"
    assert rig.server.requests == [] and rig.names() == []


def test_an_existing_target_is_refused_before_any_catalog_request(
    workspace, certificates, monkeypatch
):
    with tag_rig(certificates, workspace, monkeypatch) as rig:
        rig.target.write_bytes(b"keep me")
        assert code_of(lambda: rig.call_tag()) == "download_output_exists"
    assert rig.server.requests == []
    assert rig.target.read_bytes() == b"keep me"


def test_a_busy_target_is_refused_before_any_catalog_request(workspace, certificates, monkeypatch):
    with tag_rig(certificates, workspace, monkeypatch) as rig:
        with open_held_sink(rig.target):
            assert code_of(lambda: rig.call_tag()) == "download_busy"
    assert rig.server.requests == []


def test_a_foreign_stage_is_refused_before_any_catalog_request(
    workspace, certificates, monkeypatch
):
    with tag_rig(certificates, workspace, monkeypatch) as rig:
        (rig.directory / download_names(NAME).stage).write_bytes(b"not ours")
        assert code_of(lambda: rig.call_tag()) == "download_partial_unverified"
    assert rig.server.requests == []


def test_the_lock_is_held_while_the_catalog_answers(workspace, certificates, monkeypatch):
    raced = []
    resolve = catalog_http.resolve_platform_version
    rig = tag_rig(certificates, workspace, monkeypatch)

    def resolve_while_racing(loader, owner, slug, tag):
        try:
            api.download_model_weights_by_tag(f"{OWNER}/{SLUG}", VERSION_TAG, **rig.values({}))
        except YorungeError as error:
            raced.append(error.code)
        return resolve(loader, owner, slug, tag)

    monkeypatch.setattr(catalog_http, "resolve_platform_version", resolve_while_racing)
    with rig:
        result = rig.call_tag()
    assert raced == ["download_busy"]
    assert result.data.bytes == len(DATA)


# --- the command line ---------------------------------------------------------------------------


def test_the_cli_names_the_resolved_version_in_text(workspace, certificates, monkeypatch, capsys):
    with tag_rig(certificates, workspace, monkeypatch) as rig:
        code, out, err = rig.run_cli(
            capsys,
            "models",
            "download",
            "--model",
            f"{OWNER}/{SLUG}",
            "--version-tag",
            VERSION_TAG,
            "--format",
            "onnx",
            "--weights-out",
            str(rig.target),
            "--config",
            str(rig.config),
            "--state-dir",
            str(rig.state),
            "--profile",
            "test",
        )
    assert code == 0, err
    assert f"Çözülen model: {OWNER}/{SLUG}" in out
    assert f"sürüm etiketi {VERSION_TAG}" in out
    assert rig.target.read_bytes() == DATA


def test_the_cli_json_carries_the_resolution(workspace, certificates, monkeypatch, capsys):
    with tag_rig(certificates, workspace, monkeypatch) as rig:
        code, out, err = rig.run_cli(
            capsys,
            "models",
            "download",
            "--model",
            f"{OWNER}/{SLUG}",
            "--version-tag",
            VERSION_TAG,
            "--format",
            "onnx",
            "--weights-out",
            str(rig.target),
            "--config",
            str(rig.config),
            "--state-dir",
            str(rig.state),
            "--output",
            "json",
        )
    assert code == 0, err
    envelope = json.loads(out)
    assert envelope["data"]["resolution"]["version_id"] == VERSION
    assert envelope["data"]["source"]["version_id"] == VERSION


def test_the_cli_text_says_when_a_partial_of_another_version_was_dropped(
    workspace, certificates, monkeypatch, capsys
):
    leave_partial_of_another_version(certificates, workspace)
    with tag_rig(certificates, workspace, monkeypatch) as rig:
        code, out, err = rig.run_cli(
            capsys,
            "models",
            "download",
            "--model",
            f"{OWNER}/{SLUG}",
            "--version-tag",
            VERSION_TAG,
            "--format",
            "onnx",
            "--weights-out",
            str(rig.target),
            "--config",
            str(rig.config),
            "--state-dir",
            str(rig.state),
        )
    assert code == 0, err
    assert "başka bir indirmeye (farklı sürüm, biçim ya da fold) aitti" in out


@pytest.mark.parametrize(
    "selection",
    [
        ["--version-id", VERSION, "--model", f"{OWNER}/{SLUG}", "--version-tag", VERSION_TAG],
        ["--version-id", VERSION, "--version-tag", VERSION_TAG],
        ["--model", f"{OWNER}/{SLUG}"],
        ["--version-tag", VERSION_TAG],
        [],
    ],
)
def test_the_version_is_named_one_whole_way_or_refused_with_no_request(
    workspace, certificates, monkeypatch, capsys, selection
):
    with tag_rig(certificates, workspace, monkeypatch) as rig:
        code, out, err = rig.run_cli(
            capsys,
            "models",
            "download",
            *selection,
            "--format",
            "onnx",
            "--weights-out",
            str(rig.target),
            "--config",
            str(rig.config),
            "--state-dir",
            str(rig.state),
            "--output",
            "json",
        )
    assert code == 2
    assert "invalid_request" in out + err
    assert rig.server.requests == []
    assert rig.names() == []


def test_the_secret_is_never_printed_by_the_tag_path(workspace, certificates, monkeypatch, capsys):
    with tag_rig(certificates, workspace, monkeypatch) as rig:
        code, out, err = rig.run_cli(
            capsys,
            "models",
            "download",
            "--model",
            f"{OWNER}/{SLUG}",
            "--version-tag",
            VERSION_TAG,
            "--format",
            "onnx",
            "--weights-out",
            str(rig.target),
            "--config",
            str(rig.config),
            "--state-dir",
            str(rig.state),
            "--output",
            "json",
        )
    assert code == 0, err
    assert SECRET not in out + err


# --- review round 1 of the tag path (P02-4f): what the first version left unproven ----------


def test_a_tag_download_with_a_digest_earns_sha256_matched(workspace, certificates, monkeypatch):
    with tag_rig(certificates, workspace, monkeypatch) as rig:
        summary = rig.call_tag(sha256=sha(DATA)).data
    assert summary.verification_level == "sha256_matched"
    assert summary.expectation_source == "user_supplied"


def test_a_tag_download_sends_its_format_and_fold_and_names_them(
    workspace, certificates, monkeypatch
):
    route = {f"{JSON_PATH}?format=pt&fold=2": json_route()}
    with tag_rig(certificates, workspace, monkeypatch, **route) as rig:
        summary = rig.call_tag(artifact_format="pt", fold=2).data
    assert f"{JSON_PATH}?format=pt&fold=2" in [r.path for r in rig.server.requests]
    assert (summary.source.format, summary.source.fold) == ("pt", 2)
    assert summary.resolution is not None and summary.resolution.version_id == VERSION


def test_a_same_version_restart_with_no_resume_names_no_other_download(
    workspace, certificates, monkeypatch
):
    with Rig(certificates, workspace) as rig:
        rig.provider.script = [Reply(body=DATA, headers=(("ETag", TAG),), truncate_at=CUT)]
        assert code_of(rig.call) == "download_incomplete"
    with tag_rig(certificates, workspace, monkeypatch) as rig:
        result = rig.call_tag(no_resume=True)
    assert result.warnings == ()
    assert result.data.resumed is False
    assert rig.target.read_bytes() == DATA


def test_the_catalog_time_is_given_back_to_the_download_deadline(
    workspace, certificates, monkeypatch
):
    """The catalog takes 31 s of a 30 s download: its time is paid back (up to its budget), so the
    resumable stage still gets its own checks. Without the refund this run times out."""
    import time as real_time

    from yorunge.adapters import download_engine

    class Clock:
        offset = 0.0

        def monotonic(self):
            return real_time.monotonic() + self.offset

        def __getattr__(self, name):
            return getattr(real_time, name)

    with Rig(certificates, workspace) as rig:
        rig.provider.script = [Reply(body=DATA, headers=(("ETag", TAG),), truncate_at=CUT)]
        assert code_of(rig.call) == "download_incomplete"
    clock = Clock()
    monkeypatch.setattr(download_engine, "time", clock)
    resolve = catalog_http.resolve_platform_version

    def slow_resolve(loader, owner, slug, tag):
        clock.offset += 31.0
        return resolve(loader, owner, slug, tag)

    monkeypatch.setattr(catalog_http, "resolve_platform_version", slow_resolve)
    with tag_rig(certificates, workspace, monkeypatch) as rig:
        summary = rig.call_tag(timeout=30).data
    assert (summary.resumed, summary.resumed_from_bytes) == (True, CUT)
    assert rig.target.read_bytes() == DATA


def test_after_a_switch_the_new_partial_resumes_by_its_tag(workspace, certificates, monkeypatch):
    leave_partial_of_another_version(certificates, workspace)
    with tag_rig(certificates, workspace, monkeypatch) as rig:
        rig.provider.script = [Reply(body=DATA, headers=(("ETag", TAG),), truncate_at=CUT)]
        assert code_of(lambda: rig.call_tag()) == "download_incomplete"
    with tag_rig(certificates, workspace, monkeypatch) as rig:
        result = rig.call_tag()
    assert result.warnings == ()
    assert (result.data.resumed, result.data.resumed_from_bytes) == (True, CUT)
    assert rig.target.read_bytes() == DATA


def test_the_help_names_the_tag_way_and_its_trade_off(capsys):
    from yorunge.cli import main

    with pytest.raises(SystemExit) as info:
        main(["models", "download", "--help"])
    out = " ".join(capsys.readouterr().out.split())
    assert info.value.code == 0
    assert "--model OWNER/SLUG" in out and "--version-tag TAG" in out
    assert "sahip adı olmayan modeller için --version-id" in out.lower()
    assert "tam bir stage bile katalog okunmadan yayımlanmaz" in out


def test_a_bad_selection_is_judged_before_the_target_is_looked_at(
    workspace, certificates, monkeypatch
):
    with tag_rig(certificates, workspace, monkeypatch) as rig:
        rig.target.write_bytes(b"keep me")
        assert code_of(lambda: rig.call_tag(model="no-slash")) == "invalid_request"
    assert rig.server.requests == []
    assert rig.target.read_bytes() == b"keep me"


def test_a_provider_version_identifier_that_is_no_uuid_is_an_invalid_answer(
    workspace, certificates, monkeypatch
):
    listing = reply([version_record(version_id="not-a-uuid")])
    with tag_rig(certificates, workspace, monkeypatch, listing=listing) as rig:
        assert code_of(lambda: rig.call_tag()) == "invalid_response"
    assert rig.json_calls() == [] and rig.names() == []


def test_a_repeated_version_tag_is_refused_before_any_request(
    workspace, certificates, monkeypatch, capsys
):
    with tag_rig(certificates, workspace, monkeypatch) as rig:
        code, out, err = rig.run_cli(
            capsys,
            "models",
            "download",
            "--model",
            f"{OWNER}/{SLUG}",
            "--version-tag",
            "9.9",
            "--version-tag",
            VERSION_TAG,
            "--format",
            "onnx",
            "--weights-out",
            str(rig.target),
            "--config",
            str(rig.config),
            "--state-dir",
            str(rig.state),
            "--output",
            "json",
        )
    assert code == 2
    assert "invalid_request" in out + err
    assert rig.server.requests == [] and rig.names() == []


def test_a_half_selection_names_the_two_ways_in_text(workspace, certificates, monkeypatch, capsys):
    with tag_rig(certificates, workspace, monkeypatch) as rig:
        code, out, err = rig.run_cli(
            capsys,
            "models",
            "download",
            "--model",
            f"{OWNER}/{SLUG}",
            "--format",
            "onnx",
            "--weights-out",
            str(rig.target),
            "--config",
            str(rig.config),
            "--state-dir",
            str(rig.state),
        )
    assert code == 2
    assert "--version-id" in out + err and "--version-tag" in out + err
    assert rig.server.requests == []


def test_a_closed_session_is_refused_before_the_lock_and_the_build(tmp_path):
    from yorunge.adapters.download_engine import run_resolved_download
    from yorunge.adapters.storage_transport import TransferSession

    session = TransferSession(credential(), storage_origins=(ORIGIN,))
    with session:
        pass  # entered and closed: no download may use it
    built = []

    def build():
        built.append(True)
        raise AssertionError("the catalog is not asked through a closed session")

    with pytest.raises(YorungeError) as info:
        run_resolved_download(tmp_path / "w.onnx", session, build, no_resume=False, timeout=30)
    assert info.value.code == "invalid_request"
    assert built == [] and list(tmp_path.iterdir()) == []


def test_an_out_of_bounds_timeout_is_refused_before_the_lock(tmp_path):
    from yorunge.adapters.download_engine import run_resolved_download
    from yorunge.adapters.storage_transport import TransferSession

    session = TransferSession(credential(), storage_origins=(ORIGIN,))
    with session:
        with pytest.raises(YorungeError) as info:
            run_resolved_download(
                tmp_path / "w.onnx", session, lambda: None, no_resume=False, timeout=10
            )
    assert info.value.code == "invalid_request"
    assert list(tmp_path.iterdir()) == []
