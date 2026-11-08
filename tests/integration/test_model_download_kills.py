"""Mutants of the API composition that no test of the first suite killed (P02-3n R1).

The options the user typed reach the engine, the key is looked at after the footing is judged, the
answer limit is exactly 1 MiB, a store change during the download does not fail a verified file and
the registered API base (not a literal) decides the route, the prefix and the identity.
"""

import asyncio
import json

import pytest

from tests.fixtures.http_server import Reply
from tests.integration.test_download_engine import CUT, DATA, TAG, sha
from tests.integration.test_model_download import (
    BASE,
    ENV,
    JSON_PATH,
    VERSION,
    Rig,
    address,
    json_route,
)
from tests.integration.test_model_download import certificates as certificates
from tests.integration.test_model_download import workspace as workspace
from tests.integration.test_upload_preparation import loopback_only as loopback_only
from yorunge.domain.errors import YorungeError


@pytest.fixture
def rig(certificates, workspace):
    with Rig(certificates, workspace) as held:
        yield held


def code_of(action):
    with pytest.raises(YorungeError) as error:
        action()
    return error.value.code


@pytest.mark.parametrize("fmt", ["onnx", "pt", "tflite"])
def test_every_format_reaches_the_provider_and_the_summary(certificates, workspace, fmt):
    with Rig(certificates, workspace) as rig:
        rig.server.routes[f"{JSON_PATH}?format={fmt}"] = json_route()
        summary = rig.call(artifact_format=fmt).data
        assert summary.source.format == fmt and summary.bytes == len(DATA)
        assert rig.json_calls()[0].path == f"{JSON_PATH}?format={fmt}"


def test_the_timeout_and_the_other_options_reach_the_engine(rig, monkeypatch):
    from yorunge.adapters import model_download as module

    seen = []
    original = module.run_download

    def spy(job, session, **kwargs):
        seen.append(job)
        return original(job, session, **kwargs)

    monkeypatch.setattr(module, "run_download", spy)
    rig.call(timeout=77, sha256=sha(DATA), no_resume=True)
    (job,) = seen
    assert job.timeout == 77 and job.expected_sha256 == sha(DATA) and job.no_resume is True
    assert job.progress is not None


def test_a_running_event_loop_is_refused_before_the_key_is_looked_at(rig, monkeypatch):
    monkeypatch.delenv(ENV)  # a missing key would be a later, different error

    async def inside():
        return rig.call()

    assert code_of(lambda: asyncio.run(inside())) == "invalid_request"
    assert rig.server.requests == []


def _padded(total):
    base = json.dumps({"download_url": address(), "filename": "f", "pad": ""})
    return json.dumps(
        {"download_url": address(), "filename": "f", "pad": "x" * (total - len(base))}
    ).encode()


def test_an_answer_of_exactly_one_mebibyte_is_accepted_and_one_byte_more_is_not(
    certificates, workspace
):
    exact = _padded(1024 * 1024)
    assert len(exact) == 1024 * 1024
    with Rig(certificates, workspace, route=lambda r, c: Reply(body=exact)) as rig:
        assert rig.call().data.bytes == len(DATA)
    over = _padded(1024 * 1024 + 1)
    with Rig(certificates, workspace, route=lambda r, c: Reply(body=over)) as rig:
        other = rig.directory / "second.onnx"
        assert code_of(lambda: rig.call(weights_out=other)) == "invalid_response"
        assert rig.signed() == []


def test_a_change_of_the_store_during_the_download_does_not_fail_a_verified_file(rig):
    import sqlite3

    database = rig.state / "state.sqlite3"
    changed = []

    def disturb(held, total):
        if not changed:
            changed.append(held)
            connection = sqlite3.connect(str(database), timeout=5)
            try:
                connection.execute("UPDATE cache_clock SET clock_generation = clock_generation + 1")
                connection.commit()
            finally:
                connection.close()

    summary = rig.call(progress=disturb).data
    assert changed and summary.bytes == len(DATA) and rig.target.read_bytes() == DATA


ALT = "/alt/v2"
ALT_JSON = f"{ALT}/models/versions/{VERSION}/download?format=onnx"
ALT_SIGNED_PATH = f"{ALT}/files/evren-models/weights.onnx"


def _alt_config(workspace):
    state, config, out = workspace
    config.write_text(
        config.read_text()
        + f'[profiles.alt]\nplatform_key_env = "{ENV}"\nplatform_url = "https://api.ssyz.org.tr{ALT}"\n'
    )


def test_a_platform_with_another_api_base_gets_its_own_route_and_prefix(certificates, workspace):
    _alt_config(workspace)
    good = address(path=ALT_SIGNED_PATH + "?sig=1")
    with Rig(certificates, workspace) as rig:
        rig.server.routes[ALT_JSON] = json_route(good)
        rig.server.routes[ALT_SIGNED_PATH + "?sig=1"] = rig.provider
        summary = rig.call(profile="alt").data
        assert summary.bytes == len(DATA) and rig.target.read_bytes() == DATA
        assert [r.path for r in rig.server.requests] == [ALT_JSON, ALT_SIGNED_PATH + "?sig=1"]


def test_an_address_below_the_default_base_is_not_below_the_alt_base(certificates, workspace):
    _alt_config(workspace)
    wrong = address(
        path=BASE + "/files/evren-models/weights.onnx?sig=1"
    )  # /api/v1/..., not /alt/v2/...
    with Rig(certificates, workspace) as rig:
        rig.server.routes[ALT_JSON] = json_route(wrong)
        assert code_of(lambda: rig.call(profile="alt")) == "invalid_response"
        assert rig.signed() == []


def test_a_stage_of_one_api_base_is_not_resumed_under_another(certificates, workspace):
    _alt_config(workspace)
    with Rig(certificates, workspace) as rig:
        rig.provider.script = [Reply(body=DATA, headers=(("ETag", TAG),), truncate_at=CUT)]
        assert code_of(rig.call) == "download_incomplete"  # a resumable stage under /api/v1
        good = address(path=ALT_SIGNED_PATH + "?sig=1")
        rig.server.routes[ALT_JSON] = json_route(good)
        rig.server.routes[ALT_SIGNED_PATH + "?sig=1"] = rig.provider
        summary = rig.call(profile="alt").data
        assert (summary.resumed, summary.resumed_from_bytes) == (False, 0)
        assert rig.provider.seen[-1] == (None, None)
