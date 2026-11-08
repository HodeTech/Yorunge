"""``api.download_model_weights`` against a real loopback TLS provider (ADR-0032 §1).

The user's side is real: the state store, the profile config, the key in its environment variable,
the product's own guarded transport (a TransferSession, with the JSON call and the signed GET on
one pool). The provider is scripted. Each journey is judged on the wire (what was asked, how often,
with which credential), on disk (the target and what is left around it) and in the result.
"""

import json
import stat

import pytest

from tests.fixtures.http_server import Reply, TlsServer, certificate
from tests.fixtures.model_network import HOSTS, loopback_models
from tests.integration.test_download_engine import CUT, DATA, TAG, Provider, framed, sha
from tests.integration.test_upload_preparation import loopback_only as loopback_only
from yorunge import api
from yorunge.domain.download import download_names, identity_key
from yorunge.domain.errors import YorungeError

ENV = "MODEL_DOWNLOAD_TEST_KEY"
SECRET = "synthetic-model-download-key-5521"
VERSION = "00000000-0000-4000-8000-000000000123"
BASE = "/api/v1"
PREFIX = BASE + "/files/evren-models/"
JSON_PATH = f"{BASE}/models/versions/{VERSION}/download"
SIGNED_PATH = PREFIX + "weights.onnx"
QUERY = "?X-Amz-Credential=scope%2Fpart&signature=PRIVATE-URL-CANARY%2B%3D&x=1&x=2"
SIGNED = SIGNED_PATH + QUERY
NAME = "weights.onnx"
FILENAME = "provider-chosen-name-CANARY.onnx"


@pytest.fixture(scope="module")
def certificates(tmp_path_factory):
    return certificate(tmp_path_factory.mktemp("model-download-tls"), names=(*HOSTS, "localhost"))


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    state = tmp_path / "state"
    api.initialize_state(state_dir=state)
    config = tmp_path / "config.toml"
    config.write_text(
        f'''schema_version = 1
active_profile = "test"
[profiles.test]
platform_key_env = "{ENV}"
[profiles.elsewhere]
platform_key_env = "{ENV}"
platform_url = "https://other.ssyz.org.tr/api/v1"
'''
    )
    monkeypatch.setenv(ENV, SECRET)
    out = tmp_path / "out"
    out.mkdir()
    return state, config, out


def address(host="api.ssyz.org.tr", path=SIGNED):
    return f"https://{host}{path}"


def json_route(url=None, **fields):
    body = json.dumps({"download_url": url or address(), "filename": FILENAME, **fields}).encode()
    return lambda record, count: Reply(body=body)


class Rig:
    """A provider behind a TLS server, the user's workspace and one call of the API."""

    def __init__(self, certificates, workspace, provider=None, *, route=None, **extra):
        self.state, self.config, self.directory = workspace
        self.provider = provider or Provider()
        self.certificates = certificates
        self.server = TlsServer(
            certificates,
            {
                f"{JSON_PATH}?format=onnx": route or json_route(),
                SIGNED: self.provider,
                **extra,
            },
        )
        self.reports = []

    def __enter__(self):
        self.server.__enter__()
        return self

    def __exit__(self, *exc):
        self.server.__exit__(*exc)

    @property
    def target(self):
        return self.directory / NAME

    def names(self):
        return sorted(p.name for p in self.directory.iterdir())

    def call(self, **changes):
        values = {
            "artifact_format": "onnx",
            "weights_out": self.target,
            "config": self.config,
            "state_dir": self.state,
            "progress": lambda held, total: self.reports.append((held, total)),
        }
        values.update(changes)
        with loopback_models(self.certificates[0], self.server.port):
            return api.download_model_weights(VERSION, **values)

    def json_calls(self):
        return [r for r in self.server.requests if r.path.startswith(JSON_PATH)]

    def signed(self):
        return [r for r in self.server.requests if r.path == SIGNED]


@pytest.fixture
def rig(certificates, workspace):
    with Rig(certificates, workspace) as held:
        yield held


def code_of(action):
    with pytest.raises(YorungeError) as error:
        action()
    return error.value.code


# --- a whole download -----------------------------------------------------------------------------


def test_the_weights_come_by_the_json_call_with_the_key_then_a_signed_get_without_it(rig):
    result = rig.call()
    summary = result.data
    assert summary.kind == "download_summary"
    assert summary.output_path == str(rig.target)
    assert (summary.bytes, summary.sha256) == (len(DATA), sha(DATA))
    assert (summary.verification_level, summary.expectation_source) == ("transfer_complete", "none")
    assert (summary.resumed, summary.resumed_from_bytes) == (False, 0)
    assert summary.source.model_dump() == {
        "kind": "model_version",
        "version_id": VERSION,
        "format": "onnx",
        "fold": None,
    }
    assert rig.target.read_bytes() == DATA
    assert rig.names() == [NAME]  # nothing else is left
    assert stat.S_IMODE(rig.target.stat().st_mode) == 0o600
    first, second = rig.server.requests  # exactly one JSON call, then exactly one signed GET
    assert (first.method, first.path) == ("GET", f"{JSON_PATH}?format=onnx")
    assert first.header("X-API-Key") == SECRET
    assert (second.method, second.path) == ("GET", SIGNED)  # the signature's bytes, untouched
    sent = {name.lower() for name, _ in second.headers}
    assert sent <= {"host", "accept-encoding", "user-agent", "connection"}, sent
    assert second.header("X-API-Key") is None
    assert second.header("Authorization") is None
    assert second.header("Accept-Encoding") == "identity"
    assert second.header("Range") is None


def test_the_provider_chosen_name_never_becomes_the_name_of_the_output(rig):
    rig.call()
    assert rig.names() == [NAME]
    assert FILENAME not in " ".join(rig.names())


def test_the_progress_runs_from_a_first_report_to_the_whole_object(rig):
    rig.call()
    helds = [held for held, _ in rig.reports]
    assert helds == sorted(set(helds))
    assert rig.reports[-1] == (len(DATA), len(DATA))
    assert all(total == len(DATA) for _, total in rig.reports)


def test_without_a_progress_receiver_nothing_is_reported_and_nothing_breaks(rig):
    assert rig.call(progress=None).data.bytes == len(DATA)


# --- a fold, and what a stage belongs to ----------------------------------------------------------


def test_a_fold_is_asked_for_only_if_it_was_given_and_is_part_of_what_a_stage_belongs_to(
    certificates, workspace
):
    route = json_route()
    with Rig(certificates, workspace, route=None) as rig:
        rig.server.routes[f"{JSON_PATH}?format=onnx&fold=3"] = route
        rig.server.routes[f"{JSON_PATH}?format=onnx&fold=4"] = route
        rig.provider.script = [Reply(body=DATA, headers=(("ETag", TAG),), truncate_at=CUT)]
        assert code_of(lambda: rig.call(fold=3)) == "download_incomplete"
        assert rig.json_calls()[0].path.endswith("?format=onnx&fold=3")
        names = download_names(NAME)
        assert rig.names() == sorted([names.stage, names.sidecar])  # a resumable partial of fold 3
        summary = rig.call(fold=4).data  # another fold: the stage of fold 3 is not resumed
        assert (summary.resumed, summary.resumed_from_bytes, summary.source.fold) == (False, 0, 4)
        assert rig.provider.seen[-1] == (None, None)  # a plain request from the first byte
        assert rig.target.read_bytes() == DATA
        assert rig.names() == [NAME]


def test_no_fold_is_sent_when_none_was_given(rig):
    rig.call()
    assert all("fold" not in r.path for r in rig.json_calls())


def test_the_identity_key_of_a_job_is_made_from_the_same_things_the_summary_names(rig):
    # a stage belongs to (service, version, format, fold): an identical call finds its own partial
    rig.provider.script = [Reply(body=DATA, headers=(("ETag", TAG),), truncate_at=CUT)]
    assert code_of(rig.call) == "download_incomplete"
    expected = identity_key(
        origin="https://api.ssyz.org.tr",
        api_base_path=BASE,
        kind="model_version",
        resource_id=VERSION,
        artifact_format="onnx",
        fold=None,
    )
    sidecar = rig.directory / download_names(NAME).sidecar
    assert json.loads(sidecar.read_text())["identity_key"] == expected


# --- the expectation ------------------------------------------------------------------------------


def test_an_expected_digest_that_matches_earns_the_level_it_names(rig):
    summary = rig.call(sha256=sha(DATA)).data
    assert (summary.verification_level, summary.expectation_source) == (
        "sha256_matched",
        "user_supplied",
    )


def test_an_expected_digest_that_differs_ends_in_a_mismatch_and_no_target(rig):
    with pytest.raises(YorungeError) as error:
        rig.call(sha256="00" * 32)
    assert error.value.code == "download_integrity_mismatch"
    assert error.value.exit_code == 7
    assert rig.names() == []  # no target, no stage, no sidecar: the mismatch does not loop


# --- an answer that is not a model address ends before the signed request -------------------------


@pytest.mark.parametrize(
    "url",
    [
        address(path=PREFIX.removesuffix("/") + "x/w.onnx" + QUERY),
        address(path=BASE + "/files/w.onnx" + QUERY),  # the DATASET bucket
        address(path="/files/evren-models/w.onnx" + QUERY),  # not below the API base
        address("other.ssyz.org.tr", SIGNED),  # another origin
        "http://api.ssyz.org.tr" + SIGNED,
        "https://user:pw@api.ssyz.org.tr" + SIGNED,
        address() + "#fragment",
        address(path=PREFIX + "../w.onnx" + QUERY),
        address(path=PREFIX + "w.onnx?" + "a" * 17000),
        address() + "&leak=" + SECRET,
    ],
    ids=[
        "longer-bucket-name",
        "dataset-bucket",
        "not-below-api-base",
        "other-origin",
        "http",
        "userinfo",
        "fragment",
        "dot-segment",
        "oversize",
        "key-in-address",
    ],
)
def test_an_address_that_is_not_below_the_model_prefix_is_refused_and_never_requested(
    certificates, workspace, url
):
    with Rig(certificates, workspace, route=json_route(url)) as rig:
        assert code_of(rig.call) == "invalid_response"
        assert len(rig.json_calls()) == 1
        assert rig.signed() == []  # the signed GET never went out
        assert rig.names() == []


@pytest.mark.parametrize(
    "body",
    [b"", b"null", b"[]", b"{}", b"not json", b'{"download_url": 5, "filename": "a"}'],
)
def test_an_answer_that_is_not_the_two_strings_is_refused(certificates, workspace, body):
    with Rig(certificates, workspace, route=lambda record, count: Reply(body=body)) as rig:
        assert code_of(rig.call) == "invalid_response"
        assert rig.signed() == []
        assert rig.names() == []


@pytest.mark.parametrize("name", ["a/b.onnx", "..", "", "x\ny"])
def test_a_provider_name_that_is_not_a_plain_name_is_refused(certificates, workspace, name):
    route = json_route(filename=name)
    with Rig(certificates, workspace, route=route) as rig:
        assert code_of(rig.call) == "invalid_response"
        assert rig.signed() == []


def test_a_key_echoed_by_the_provider_is_refused_wherever_it_is(certificates, workspace):
    with Rig(certificates, workspace, route=json_route(echo={"deep": [SECRET]})) as rig:
        assert code_of(rig.call) == "invalid_response"
        assert rig.signed() == []


# --- the statuses of the JSON call ----------------------------------------------------------------


@pytest.mark.parametrize(
    "status,code,exit_code,attempts",
    [
        (401, "remote_access_denied", 3, 1),
        (403, "remote_access_denied", 3, 1),  # also a licence or terms block: never accepted for us
        (404, "remote_failed", 1, 1),
        (429, "remote_rate_limited", 1, 2),
        (500, "remote_failed", 1, 1),
        (503, "remote_failed", 1, 2),  # the read policy: at most two attempts, never a third
    ],
)
def test_a_status_of_the_json_call_is_a_closed_error_and_no_signed_get_follows(
    certificates, workspace, status, code, exit_code, attempts
):
    reply = Reply(status=status, body=b'{"detail":"PRIVATE-DETAIL"}')
    with Rig(certificates, workspace, route=lambda record, count: reply) as rig:
        with pytest.raises(YorungeError) as error:
            rig.call()
        assert (error.value.code, error.value.exit_code) == (code, exit_code)
        assert "PRIVATE-DETAIL" not in str(error.value)
        assert rig.signed() == []
        assert rig.names() == []
        assert len(rig.json_calls()) == attempts
        assert all(r.header("X-API-Key") == SECRET for r in rig.json_calls())


def test_a_redirect_of_the_json_call_is_not_followed_and_the_key_goes_nowhere_else(
    certificates, workspace
):
    reply = Reply(status=302, body=b"", headers=(("Location", "https://other.ssyz.org.tr/x"),))
    with Rig(certificates, workspace, route=lambda record, count: reply) as rig:
        with pytest.raises(YorungeError):
            rig.call()
        assert len(rig.server.requests) <= 2
        assert rig.signed() == []
        assert {r.path for r in rig.server.requests} == {f"{JSON_PATH}?format=onnx"}


# --- resuming, and the local state before the network ---------------------------------------------


def test_a_cut_download_resumes_with_the_same_call_from_where_it_stopped(rig):
    rig.provider.script = [Reply(body=DATA, headers=(("ETag", TAG),), truncate_at=CUT)]
    assert code_of(rig.call) == "download_incomplete"
    names = download_names(NAME)
    assert rig.names() == sorted([names.stage, names.sidecar])  # resumable: kept
    summary = rig.call().data
    assert (summary.resumed, summary.resumed_from_bytes, summary.bytes) == (True, CUT, len(DATA))
    assert rig.provider.seen == [(None, None), (f"bytes={CUT}-", TAG)]
    assert len(rig.json_calls()) == 2
    assert len(rig.signed()) == 2
    assert rig.target.read_bytes() == DATA
    assert rig.names() == [NAME]


def test_a_whole_stage_is_published_with_no_request_at_all_the_json_call_included(rig):
    rig.provider.script = [Reply(body=DATA, headers=(("ETag", TAG),))]

    def interrupted(held, total):
        if held >= len(DATA) - 1:  # the last in-loop report: raised AFTER the whole body is marked
            raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        rig.call(progress=interrupted)
    names = download_names(NAME)
    assert rig.names() == sorted([names.stage, names.sidecar])
    before = len(rig.server.requests)
    summary = rig.call().data
    assert len(rig.server.requests) == before  # nothing was asked of the network, not even the JSON
    assert (summary.resumed, summary.resumed_from_bytes) == (True, len(DATA))
    assert rig.target.read_bytes() == DATA
    assert rig.names() == [NAME]


def test_a_target_that_exists_is_refused_before_any_request_and_left_alone(rig):
    rig.target.write_bytes(b"mine")
    assert code_of(rig.call) == "download_output_exists"
    assert rig.server.requests == []
    assert rig.target.read_bytes() == b"mine"
    assert rig.names() == [NAME]


def test_a_stage_of_another_service_is_not_resumed(certificates, workspace, monkeypatch):
    state, config, directory = workspace
    with Rig(certificates, workspace) as rig:
        rig.provider.script = [Reply(body=DATA, headers=(("ETag", TAG),), truncate_at=CUT)]
        assert code_of(rig.call) == "download_incomplete"
        # the same target and version id, now through the profile of the second host
        rig.server.routes[f"{JSON_PATH}?format=onnx"] = json_route(address("other.ssyz.org.tr"))
        with loopback_models(certificates[0], rig.server.port):
            summary = api.download_model_weights(
                VERSION,
                artifact_format="onnx",
                weights_out=rig.target,
                config=config,
                profile="elsewhere",
                state_dir=state,
            ).data
        assert (summary.resumed, summary.resumed_from_bytes) == (False, 0)
        assert rig.provider.seen[-1] == (None, None)
        assert rig.target.read_bytes() == DATA


def test_no_resume_drops_what_is_provably_ours_and_downloads_again(rig):
    rig.provider.script = [Reply(body=DATA, headers=(("ETag", TAG),), truncate_at=CUT)]
    assert code_of(rig.call) == "download_incomplete"
    summary = rig.call(no_resume=True).data
    assert (summary.resumed, summary.resumed_from_bytes) == (False, 0)
    assert rig.provider.seen[-1] == (None, None)
    assert rig.names() == [NAME]


def test_a_chunked_answer_is_whole_when_terminated(certificates, workspace):
    chunked = Reply(body=framed(DATA), headers=(("Transfer-Encoding", "chunked"), ("ETag", TAG)))
    with Rig(certificates, workspace) as rig:
        rig.provider.script = [chunked]
        summary = rig.call().data
        assert summary.bytes == len(DATA)
        assert all(total is None for _, total in rig.reports[-3:])


# --- the arguments are judged before the key or the state is touched ------------------------------


@pytest.mark.parametrize(
    "changes",
    [
        {"artifact_format": "gguf"},
        {"artifact_format": None},
        {"artifact_format": "ONNX"},
        {"fold": -1},
        {"fold": 1025},
        {"fold": True},
        {"fold": 1.0},
        {"sha256": "A" * 64},
        {"sha256": "a" * 63},
        {"sha256": "g" * 64},
        {"sha256": 5},
        {"timeout": 29},
        {"timeout": 3601},
        {"timeout": True},
        {"timeout": 900.0},
        {"timeout": "900x"},
        {"no_resume": 1},
        {"no_resume": None},
        {"progress": "not callable"},
        {"weights_out": "relative-str-is-not-a-path"},
        {"state_dir": "not-a-path"},
        {"config": "not-a-path"},
    ],
    ids=lambda changes: next(iter(changes)) + "=" + repr(next(iter(changes.values())))[:12],
)
def test_an_argument_that_is_wrong_is_refused_before_the_key_is_read(
    certificates, workspace, monkeypatch, changes
):
    monkeypatch.delenv(ENV)  # a missing key would be a different, later error
    with Rig(certificates, workspace) as rig:
        assert code_of(lambda: rig.call(**changes)) == "invalid_request"
        assert rig.server.requests == []
        assert rig.names() == []


@pytest.mark.parametrize(
    "version",
    [
        "not-a-uuid",
        "",
        None,
        5,
        "7B0E5E7A-0C37-4A8A-9D7E-3A9F4B8F9D11",
        VERSION + " ",
        VERSION[:-1],
    ],
)
def test_a_version_id_that_is_not_a_canonical_uuid_is_refused(
    certificates, workspace, monkeypatch, version
):
    monkeypatch.delenv(ENV)
    with Rig(certificates, workspace) as rig, loopback_models(certificates[0], rig.server.port):
        assert (
            code_of(
                lambda: api.download_model_weights(
                    version,  # type: ignore[arg-type]
                    artifact_format="onnx",
                    weights_out=rig.target,
                    config=rig.config,
                    state_dir=rig.state,
                )
            )
            == "invalid_request"
        )
        assert rig.server.requests == []


def test_a_missing_key_is_a_closed_error_before_any_request(certificates, workspace, monkeypatch):
    monkeypatch.delenv(ENV)
    with Rig(certificates, workspace) as rig:
        with pytest.raises(YorungeError) as error:
            rig.call()
        assert error.value.code.startswith("credential") or error.value.code.endswith("missing")
        assert rig.server.requests == []
        assert rig.names() == []


def test_a_running_event_loop_is_refused_before_anything_else(rig):
    import asyncio

    async def inside():
        return rig.call()

    with pytest.raises(YorungeError) as error:
        asyncio.run(inside())
    assert error.value.code == "invalid_request"
    assert rig.server.requests == []


# --- nothing private ------------------------------------------------------------------------------


def test_nothing_private_is_left_in_the_state_the_directory_or_the_result(rig, caplog):
    import logging

    caplog.set_level(logging.DEBUG)
    rig.provider.script = [Reply(body=DATA, headers=(("ETag", TAG),), truncate_at=CUT)]
    with pytest.raises(YorungeError) as error:
        rig.call()
    result = rig.call()
    canaries = [SECRET, "PRIVATE-URL-CANARY", FILENAME, "X-Amz-Credential", TAG]
    texts = [repr(error.value), str(error.value), result.model_dump_json(), caplog.text]
    for path in (rig.state, rig.directory):
        for item in path.rglob("*"):
            if item.is_file() and item != rig.target:
                texts.append(item.read_bytes().decode("latin-1"))
    for text in texts:
        for canary in canaries:
            assert canary not in text, canary
