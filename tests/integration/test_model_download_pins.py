"""What the card claims of ``models download`` and the first suite varied too little (P02-3n R1).

The identity key is said to cover the registered target (origin and API root), the version, the
format and the fold; the timeout the caller gives is said to be the job's; every single-valued
option is said to be refused when it is repeated; the answer of the JSON call is said to be a 200
and nothing else; and the Python API takes the integers it names. Each of these held in the code
and was pinned by no test: a one-line mutant of each survived the suite.
"""

import json

import pytest

from tests.fixtures.http_server import Reply
from tests.fixtures.model_network import loopback_models
from tests.integration.test_download_engine import CUT, DATA, TAG
from tests.integration.test_model_download import (
    ENV,
    FILENAME,
    JSON_PATH,
    SIGNED,
    VERSION,
    Rig,
    json_route,
)
from tests.integration.test_model_download import certificates as certificates
from tests.integration.test_model_download import workspace as workspace
from tests.integration.test_upload_preparation import loopback_only as loopback_only
from yorunge import api
from yorunge.adapters.http_session import HttpSession
from yorunge.domain.download import DEFAULT_TIMEOUT_SECONDS
from yorunge.domain.errors import YorungeError

VERSION2 = "00000000-0000-4000-8000-000000000456"


def cut(rig):
    """Leave a resumable stage behind: the provider ends the first body early."""
    rig.provider.script = [Reply(body=DATA, headers=(("ETag", TAG),), truncate_at=CUT)]
    with pytest.raises(YorungeError) as error:
        rig.call()
    assert error.value.code == "download_incomplete"
    rig.provider.script = []
    rig.provider.seen.clear()


# --- the identity key: what a stage may be resumed by ---------------------------------------------


def test_a_stage_of_another_format_is_not_resumed_and_the_source_names_the_format(
    certificates, workspace
):
    with Rig(certificates, workspace, **{f"{JSON_PATH}?format=pt": json_route()}) as rig:
        cut(rig)
        summary = rig.call(artifact_format="pt").data
        assert (summary.resumed, summary.source.format) == (False, "pt")
        assert rig.provider.seen == [(None, None)]  # a whole body, no Range


@pytest.mark.parametrize("artifact_format", ["pt", "tflite"])
def test_every_format_the_command_offers_can_be_downloaded(
    certificates, workspace, artifact_format
):
    route = {f"{JSON_PATH}?format={artifact_format}": json_route()}
    with Rig(certificates, workspace, **route) as rig:
        assert rig.call(artifact_format=artifact_format).data.source.format == artifact_format


def test_a_stage_of_another_version_is_not_resumed(certificates, workspace):
    other = JSON_PATH.replace(VERSION, VERSION2)
    with Rig(certificates, workspace, **{f"{other}?format=onnx": json_route()}) as rig:
        cut(rig)
        values = {
            "artifact_format": "onnx",
            "weights_out": rig.target,
            "config": rig.config,
            "state_dir": rig.state,
        }
        with loopback_models(certificates[0], rig.server.port):
            summary = api.download_model_weights(VERSION2, **values).data
        assert (summary.resumed, summary.source.version_id) == (False, VERSION2)
        assert rig.provider.seen == [(None, None)]


def test_a_stage_of_another_api_root_is_not_resumed(certificates, workspace):
    state, config, out = workspace
    config.write_text(
        config.read_text()
        + f'[profiles.prefixed]\nplatform_key_env = "{ENV}"\n'
        + 'platform_url = "https://api.ssyz.org.tr/prefix/api/v1"\n'
    )
    prefixed_json = f"/prefix/api/v1/models/versions/{VERSION}/download?format=onnx"
    prefixed_signed = SIGNED.replace("/api/v1/", "/prefix/api/v1/", 1)
    body = json.dumps(
        {"download_url": "https://api.ssyz.org.tr" + prefixed_signed, "filename": FILENAME}
    ).encode()
    with Rig(certificates, workspace, **{prefixed_json: Reply(body=body)}) as rig:
        rig.server.routes[prefixed_signed] = rig.provider
        cut(rig)
        summary = rig.call(profile="prefixed").data
        assert summary.resumed is False
        assert rig.provider.seen == [(None, None)]


def test_a_stage_is_resumed_by_another_key_of_the_same_target(certificates, workspace, monkeypatch):
    """The key belongs to the target, not to a credential: this is what the reference says."""
    with Rig(certificates, workspace) as rig:
        cut(rig)
        monkeypatch.setenv(ENV, "another-synthetic-model-key-9917")
        summary = rig.call().data
        assert summary.resumed is True and summary.bytes == len(DATA)


# --- the timeout the caller gave is the job's -----------------------------------------------------


def test_the_timeout_the_caller_gave_is_the_timeout_of_the_job(
    certificates, workspace, monkeypatch
):
    import yorunge.adapters.model_download as module

    seen = []
    real = module.run_download

    def spy(job, session):
        seen.append(job.timeout)
        return real(job, session)

    monkeypatch.setattr(module, "run_download", spy)
    with Rig(certificates, workspace) as rig:
        rig.call(timeout=77)
        rig.target.unlink()
        rig.call()
        assert seen == [77, DEFAULT_TIMEOUT_SECONDS]


# --- the answer of the JSON call is a 200 and nothing else ----------------------------------------


@pytest.mark.parametrize("status", [201, 202, 203, 204, 205, 206])
def test_a_success_other_than_200_is_not_the_answer_and_no_signed_get_follows(
    certificates, workspace, status
):
    good = json.dumps({"download_url": "https://api.ssyz.org.tr" + SIGNED, "filename": "a"})
    route = lambda record, count: Reply(status=status, body=good.encode())  # noqa: E731
    with Rig(certificates, workspace, route=route) as rig:
        with pytest.raises(YorungeError) as error:
            rig.call()
        assert (error.value.code, error.value.exit_code) == ("invalid_response", 1)
        assert rig.signed() == [] and rig.names() == [] and len(rig.json_calls()) == 1


# --- the Python API takes the integers it names, and a progress receiver that can be called -------


@pytest.mark.parametrize(
    "changes",
    [
        {"fold": "3"},
        {"fold": 3.0},
        {"fold": True},
        {"timeout": "900"},
        {"timeout": 900.0},
        {"timeout": True},
        {"progress": "not callable"},
    ],
)
def test_the_python_api_judges_its_argument_types_before_any_request(
    certificates, workspace, changes
):
    with Rig(certificates, workspace) as rig:
        with pytest.raises(YorungeError) as error:
            rig.call(**changes)
        assert error.value.code == "invalid_request"
        assert rig.server.requests == [] and rig.names() == []


def test_an_async_progress_receiver_is_refused_instead_of_never_being_awaited(
    certificates, workspace
):
    async def progress(held, total):
        raise AssertionError("never awaited")

    with Rig(certificates, workspace) as rig:
        with pytest.raises(YorungeError) as error:
            rig.call(progress=progress)
        assert error.value.code == "invalid_request" and rig.server.requests == []


# --- a failure of the session's own close does not overwrite a delivered file ---------------------


def test_a_close_failure_after_the_file_was_published_is_not_the_result(
    certificates, workspace, monkeypatch
):
    real = HttpSession._close
    closed = []

    def failing(self, exc_type, exc, traceback):
        real(self, exc_type, exc, traceback)
        closed.append(exc_type)
        raise YorungeError("transport_failed")

    monkeypatch.setattr(HttpSession, "_close", failing)
    with Rig(certificates, workspace) as rig:
        summary = rig.call().data
        assert closed == [None]  # the close ran, after a body that was whole
        assert (summary.bytes, rig.target.read_bytes()) == (len(DATA), DATA)


# --- a store that other commands hold for a moment is waited for, within the window ---------------


def test_a_busy_store_is_waited_for_and_the_download_then_goes_through(
    certificates, workspace, monkeypatch
):
    import yorunge.adapters.model_download as module
    from yorunge.adapters.context_state import StateDiscovery

    real = StateDiscovery.capture
    attempts = []

    def busy_twice(self, *, deadline):
        attempts.append(deadline)
        if len(attempts) <= 2:
            raise YorungeError("state_busy")
        return real(self, deadline=deadline)

    monkeypatch.setattr(StateDiscovery, "capture", busy_twice)
    monkeypatch.setattr(module.time, "sleep", lambda seconds: None)
    with Rig(certificates, workspace) as rig:
        summary = rig.call().data
        assert len(attempts) == 3 and len(set(attempts)) == 1  # one window for all the attempts
        assert summary.bytes == len(DATA) and len(rig.json_calls()) == 1


def test_a_store_that_stays_busy_ends_with_state_busy_when_the_window_is_over(
    certificates, workspace, monkeypatch
):
    import yorunge.adapters.model_download as module
    from yorunge.adapters.context_state import StateDiscovery

    attempts = []

    def busy(self, *, deadline):
        attempts.append(deadline)
        assert len(attempts) < 200, "the retry loop never ends"  # a broken loop fails, not hangs
        raise YorungeError("state_busy")

    monkeypatch.setattr(StateDiscovery, "capture", busy)
    monkeypatch.setattr(module, "CAPTURE_SECONDS", 0.8)
    with Rig(certificates, workspace) as rig:
        with pytest.raises(YorungeError) as error:
            rig.call()
        assert error.value.code == "state_busy" and 2 <= len(attempts) < 40
        assert rig.server.requests == [] and rig.names() == []


def test_any_other_error_of_the_capture_is_not_retried(certificates, workspace, monkeypatch):
    from yorunge.adapters.context_state import StateDiscovery

    attempts = []

    def broken(self, *, deadline):
        attempts.append(1)
        raise YorungeError("credential_unavailable")

    monkeypatch.setattr(StateDiscovery, "capture", broken)
    with Rig(certificates, workspace) as rig:
        with pytest.raises(YorungeError) as error:
            rig.call()
        assert error.value.code == "credential_unavailable" and attempts == [1]


# --- the command line: single-valued options and the project --------------------------------------


@pytest.mark.parametrize("position", ["root", "models", "download"])
def test_a_project_is_refused_wherever_it_is_given(monkeypatch, position):
    """A weights download has no project; a root-level one used to be dropped without a word."""
    from yorunge.cli import main

    def never(*args, **kwargs):
        raise AssertionError("the command must not run")

    monkeypatch.setattr(api, "download_model_weights", never)
    project = ["--project", "00000000-0000-4000-8000-000000000004"]
    command = [
        "models",
        "download",
        "--version-id",
        VERSION,
        "--format",
        "onnx",
        "--weights-out",
        "/x/y.onnx",
    ]
    if position == "root":
        arguments = [*project, *command]
    elif position == "models":
        arguments = ["models", *project, *command[1:]]
    else:
        arguments = [*command, *project]
    assert main(arguments) == 2
