"""Real CLI subprocesses use the shared API; machine output remains UTF-8 and progress-free."""

import json
import os
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import pytest

from tests.contracts.test_platform_upload_codec import SCOPE
from tests.fixtures.http_server import TlsServer
from tests.fixtures.upload_provider import DATASET, UploadProvider
from tests.integration.test_upload_file_workflow import many
from tests.integration.test_upload_preparation import certificates as certificates
from tests.integration.test_upload_preparation import loopback_only as loopback_only
from tests.integration.test_upload_preparation import prepared_input as prepared_input
from tests.integration.test_upload_public_api import public_inputs as public_inputs

FIXTURE = Path(__file__).parents[1] / "fixtures" / "upload_console.py"


def command(server, *args):
    return [
        sys.executable,
        "-I",
        "-W",
        "error",
        str(FIXTURE),
        "--ca",
        str(server.certificates[0]),
        "--port",
        str(server.port),
        "--",
        *args,
    ]


def execute(server, *args):
    environment = dict(os.environ)
    environment.update(LC_ALL="C", PYTHONIOENCODING="ascii", PYTHONUTF8="0")
    return subprocess.run(command(server, *args), env=environment, capture_output=True, timeout=30)


def result(process, output):
    assert process.returncode == 0, process.stderr.decode("utf-8", "strict")
    value = json.loads(process.stdout.decode("utf-8", "strict"))
    if output == "ndjson":
        assert value["event"] == "result" and value["sequence"] == 1
        value = value["payload"]
    assert value["operation_id"] is None and not process.stderr
    return value["data"]


@pytest.mark.parametrize("output", ["json", "ndjson"])
def test_real_cli_plan_review_approve_start_show_and_history(public_inputs, certificates, output):
    data, manifest, config = public_inputs
    data = many(data)
    manifest.write_bytes(data[2].encoded())
    provider = UploadProvider(SCOPE.owner.id, SCOPE.project_id, name="örnek-uydu")
    with TlsServer(certificates, provider.routes()) as server:
        common = ("--state-dir", str(data[0]), "--output", output)
        created = execute(
            server,
            "datasets",
            "upload",
            "plan",
            str(data[1]),
            "--manifest",
            str(manifest),
            "--name",
            "örnek-uydu",
            "--project",
            SCOPE.project_id,
            "--owner-user",
            SCOPE.owner.id,
            "--modality",
            "VISION",
            "--unpriced",
            "--admission-policy",
            "explicit-attempt",
            "--config",
            str(config),
            "--profile",
            "test",
            *common,
        )
        plan = result(created, output)
        assert plan["plan_status"] == "attempt_ready" and plan["operation_id"] is None
        checked = result(
            execute(server, "datasets", "upload", "review", "--plan-id", plan["plan_id"], *common),
            output,
        )
        assert checked["parameters"]["name"] == "örnek-uydu"
        assert checked["selected_project_id"] == SCOPE.project_id
        assert checked["manifest"]["file_count"] == 3
        assert "credential_id" not in json.dumps(checked)
        approved = result(
            execute(
                server,
                "datasets",
                "upload",
                "approve",
                "--plan-id",
                plan["plan_id"],
                "--confirm",
                plan["plan_digest"],
                "--accept-unverified-authority",
                "--accept-unpriced-cost",
                "--config",
                str(config),
                *common,
            ),
            output,
        )
        assert approved["approval_status"] == "approved"
        started = execute(
            server,
            "datasets",
            "upload",
            "start",
            "--plan-id",
            plan["plan_id"],
            "--config",
            str(config),
            *common,
        )
        summary = result(started, output)
        assert summary["operation_status"] == "succeeded" and summary["dataset_id"] == DATASET
        assert summary["verification_level"] == "metadata" and not summary["authority_verified"]
        if output == "ndjson":
            assert json.loads(started.stdout)["operation_id"] == summary["operation_id"]
        count = len(server.requests)
        shown = result(
            execute(server, "datasets", "upload", "show", "--plan-id", plan["plan_id"], *common),
            output,
        )
        page = result(execute(server, "datasets", "upload", "list", *common), output)
        assert shown == summary and page["uploads"] == [summary]
        assert len(server.requests) == count
        assert provider.create_calls == provider.link_calls == 1
        assert provider.put_calls == provider.confirm_calls == 3
        assert sum(r.method == "GET" for r in server.requests) == 22


@pytest.mark.parametrize("action", ["review", "revoke", "list", "show"])
def test_local_cli_upload_commands_do_not_load_http_credentials_or_config(cli, tmp_path, action):
    from yorunge import api

    root = tmp_path / "state"
    api.initialize_state(state_dir=root)
    identity = str(uuid4())
    args = ["datasets", "upload", action, "--state-dir", str(root), "--output", "json"]
    if action != "list":
        args += ["--plan-id", identity]
    found = cli(*args, state=True, recipe_loader=False)
    assert found.returncode == (0 if action == "list" else 2), found.stderr
    assert not found.stderr if action == "list" else not found.stdout
    if action != "list":
        assert json.loads(found.stderr)["code"] == "upload_plan_not_found"


@pytest.mark.parametrize(
    "arguments",
    [
        ["--output=json", "--output", "ndjson"],
        ["--limit", "1", "--limit=2"],
        ["--cursor", "bad", "--cursor=other"],
        ["--state-dir", "a", "--state-dir=b"],
    ],
)
def test_upload_duplicate_options_fail_closed_before_state(cli, arguments):
    found = cli("datasets", "upload", "list", *arguments, "--output=json")
    assert found.returncode == 2 and not found.stdout
    assert json.loads(found.stderr)["code"] == "invalid_request"


@pytest.mark.parametrize(
    "path",
    [
        (),
        ("datasets",),
        ("datasets", "upload"),
        ("datasets", "upload", "plan"),
        ("datasets", "upload", "start"),
    ],
)
def test_upload_help_remains_metadata_only(cli, path):
    found = cli(*path, "--help", metadata=True, recipe_loader=False)
    assert found.returncode == 0 and found.stdout and not found.stderr


def test_local_cli_rejects_inherited_context_instead_of_reading_it(cli):
    found = cli("--config", "private-missing-config", "datasets", "upload", "list", "--output=json")
    assert found.returncode == 2 and not found.stdout
    assert json.loads(found.stderr)["code"] == "invalid_request"


def approved_cli(server, inputs):
    data, manifest, config = inputs
    args = ("--state-dir", str(data[0]), "--output", "json")
    plan = result(
        execute(
            server,
            "datasets",
            "upload",
            "plan",
            str(data[1]),
            "--manifest",
            str(manifest),
            "--name",
            "sample",
            "--project",
            SCOPE.project_id,
            "--owner-user",
            SCOPE.owner.id,
            "--modality",
            "VISION",
            "--unpriced",
            "--admission-policy",
            "explicit-attempt",
            "--config",
            str(config),
            "--profile",
            "test",
            *args,
        ),
        "json",
    )
    result(
        execute(
            server,
            "datasets",
            "upload",
            "approve",
            "--plan-id",
            plan["plan_id"],
            "--confirm",
            plan["plan_digest"],
            "--accept-unverified-authority",
            "--accept-unpriced-cost",
            "--config",
            str(config),
            *args,
        ),
        "json",
    )
    return plan


def test_closed_stdout_after_durable_success_reports_same_id_and_never_replays(
    public_inputs, certificates
):
    from yorunge import api

    data, _, config = public_inputs
    provider = UploadProvider(SCOPE.owner.id, SCOPE.project_id)
    with TlsServer(certificates, provider.routes()) as server:
        plan = approved_cli(server, public_inputs)
        process = subprocess.Popen(
            command(
                server,
                "datasets",
                "upload",
                "start",
                "--plan-id",
                plan["plan_id"],
                "--config",
                str(config),
                "--state-dir",
                str(data[0]),
                "--output",
                "json",
            ),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            process.stdout.close()
            process.stdout = None
            _, stderr = process.communicate(timeout=30)
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate(timeout=10)
        assert process.returncode == 6
        failure = json.loads(stderr)
        assert failure["code"] == "output_closed" and failure["operation_id"] is not None
        shown = api.show_dataset_upload(plan_id=plan["plan_id"], state_dir=data[0]).data
        assert (
            shown.operation_id == failure["operation_id"] and shown.operation_status == "succeeded"
        )
        count = len(server.requests)
        found = result(
            execute(
                server,
                "datasets",
                "upload",
                "start",
                "--plan-id",
                plan["plan_id"],
                "--state-dir",
                str(data[0]),
                "--output",
                "json",
            ),
            "json",
        )
        assert found["operation_id"] == shown.operation_id and len(server.requests) == count
        assert provider.create_calls == provider.link_calls == provider.put_calls == 1


def test_actual_cli_sigint_during_create_preserves_unknown_id_and_zero_replay(
    public_inputs, certificates
):
    import signal
    import threading

    from yorunge import api
    from yorunge.adapters.state import open_existing_store
    from yorunge.adapters.upload_repository import StateUploads

    data, _, config = public_inputs
    ready, release = threading.Event(), threading.Event()
    provider = UploadProvider(SCOPE.owner.id, SCOPE.project_id)

    def wait():
        ready.set()
        assert release.wait(15), "create signal fixture was not released"

    provider.after_create = wait
    with TlsServer(certificates, provider.routes()) as server:
        plan = approved_cli(server, public_inputs)
        process = subprocess.Popen(
            command(
                server,
                "datasets",
                "upload",
                "start",
                "--plan-id",
                plan["plan_id"],
                "--config",
                str(config),
                "--state-dir",
                str(data[0]),
                "--output",
                "json",
            ),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            assert ready.wait(15), "create never reached the actual TLS server"
            process.send_signal(signal.SIGINT)
            stdout, stderr = process.communicate(timeout=15)
        finally:
            release.set()
            if process.poll() is None:
                process.kill()
                process.communicate(timeout=10)
        assert process.returncode == 5 and not stdout
        failure = json.loads(stderr)
        assert failure["code"] == "operation_uncertain" and failure["operation_id"] is not None
        shown = api.show_dataset_upload(plan_id=plan["plan_id"], state_dir=data[0]).data
        assert shown.operation_id == failure["operation_id"] and shown.operation_status == "unknown"
        with open_existing_store(data[0]) as store:
            view = StateUploads(store).show(operation_id=shown.operation_id)
            assert (
                len(view.intents) == 1 and not view.receipts and view.operation.dataset_id is None
            )
            assert store.verify().store_schema_version == 7
        count = len(server.requests)
        again = execute(
            server,
            "datasets",
            "upload",
            "start",
            "--plan-id",
            plan["plan_id"],
            "--state-dir",
            str(data[0]),
            "--output",
            "text",
        )
        assert again.returncode == 5 and shown.operation_id.encode() in again.stderr
        assert not again.stdout and len(server.requests) == count
        assert provider.create_calls == 1 and provider.link_calls == provider.put_calls == 0


def test_actual_pty_progress_uses_transport_and_confirmed_byte_counts(public_inputs, certificates):
    import errno
    import re
    import threading
    import time

    data, artifact, config = public_inputs
    data = many(data)
    artifact.write_bytes(data[2].encoded())
    inputs = data, artifact, config
    provider = UploadProvider(SCOPE.owner.id, SCOPE.project_id)
    routes = provider.routes()
    path = f"/api/v1/datasets/{DATASET}/upload/confirm"
    original = routes[path]

    def delayed(request, count):
        reply = original(request, count)
        time.sleep(0.13)
        return reply

    routes[path] = delayed
    with TlsServer(certificates, routes) as server:
        plan = approved_cli(server, inputs)
        master, slave = os.openpty()
        progress, read_errors = bytearray(), []

        def drain():
            while True:
                try:
                    part = os.read(master, 4096)
                except OSError as error:
                    if error.errno != errno.EIO:
                        read_errors.append(error.errno)
                    return
                if not part:
                    return
                progress.extend(part)

        # On macOS unread PTY bytes may disappear when its last slave closes.
        # Drain concurrently, before starting the writer, rather than after exit.
        reader = threading.Thread(target=drain)
        reader.start()
        process = subprocess.Popen(
            command(
                server,
                "datasets",
                "upload",
                "start",
                "--plan-id",
                plan["plan_id"],
                "--config",
                str(config),
                "--state-dir",
                str(data[0]),
                "--output",
                "text",
            ),
            stdout=subprocess.PIPE,
            stderr=slave,
        )
        os.close(slave)
        try:
            stdout, _ = process.communicate(timeout=30)
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate(timeout=10)
            reader.join(timeout=5)
            os.close(master)
        assert not reader.is_alive() and not read_errors
        text = bytes(progress).decode("utf-8", "strict")
        assert process.returncode == 0 and "metadata" in stdout.decode("utf-8", "strict")
        identity = re.search(r"^İş: ([a-f0-9-]{36})$", stdout.decode("utf-8"), re.MULTILINE)
        assert identity is not None
        assert all(line.startswith(f"İş {identity.group(1)} |") for line in text.splitlines())
        counts = re.findall(r"Taşımaya verilen: (\d+)/(\d+) byte", text)
        assert len(counts) >= 2 and any(int(sent) > 0 for sent, total in counts), repr(text)
        assert int(counts[-1][0]) == int(counts[-1][1]) == data[2].total_bytes
        assert f"Onaylı: 3/3 dosya, {data[2].total_bytes} byte" in text
        assert SCOPE.owner.id not in text and "sample" not in text
        assert all(int(sent) <= int(total) for sent, total in counts)


def test_non_tty_text_start_has_no_progress_or_prompt(public_inputs, certificates):
    provider = UploadProvider(SCOPE.owner.id, SCOPE.project_id)
    with TlsServer(certificates, provider.routes()) as server:
        plan = approved_cli(server, public_inputs)
        process = execute(
            server,
            "datasets",
            "upload",
            "start",
            "--plan-id",
            plan["plan_id"],
            "--config",
            str(public_inputs[2]),
            "--state-dir",
            str(public_inputs[0][0]),
            "--output",
            "text",
            "--non-interactive",
        )
        assert process.returncode == 0 and not process.stderr
        assert "metadata doğrulaması" in process.stdout.decode("utf-8", "strict")
        assert DATASET.encode() in process.stdout
        assert provider.create_calls == provider.link_calls == provider.put_calls == 1


def test_actual_cli_sigint_during_read_is_code_six_without_new_effects(public_inputs, certificates):
    import signal
    import threading

    from tests.fixtures.http_server import Reply
    from yorunge import api
    from yorunge.adapters.state import open_existing_store
    from yorunge.adapters.upload_repository import StateUploads

    data, _, config = public_inputs
    provider = UploadProvider(SCOPE.owner.id, SCOPE.project_id)
    routes = provider.routes()
    path = f"/api/v1/datasets/{DATASET}/items?limit=128"
    original = routes[path]
    routes[path] = Reply(status=503)
    ready, release = threading.Event(), threading.Event()
    with TlsServer(certificates, routes) as server:
        plan = approved_cli(server, public_inputs)
        first = execute(
            server,
            "datasets",
            "upload",
            "start",
            "--plan-id",
            plan["plan_id"],
            "--config",
            str(config),
            "--state-dir",
            str(data[0]),
            "--output",
            "json",
        )
        assert first.returncode == 5
        identity = json.loads(first.stderr)["operation_id"]
        count = len(server.requests)
        denied = execute(
            server,
            "datasets",
            "upload",
            "reconcile",
            "--operation-id",
            identity,
            "--config",
            str(config.parent / "missing"),
            "--state-dir",
            str(data[0]),
            "--output",
            "json",
        )
        assert denied.returncode == 4 and json.loads(denied.stderr)["operation_id"] == identity
        assert len(server.requests) == count

        def waiting(request, calls):
            ready.set()
            assert release.wait(15), "read signal fixture was not released"
            return original(request, calls)

        routes[path] = waiting
        process = subprocess.Popen(
            command(
                server,
                "datasets",
                "upload",
                "reconcile",
                "--operation-id",
                identity,
                "--accept-unverified-read",
                "--config",
                str(config),
                "--state-dir",
                str(data[0]),
                "--output",
                "ndjson",
            ),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            assert ready.wait(15), "read never reached the actual TLS server"
            process.send_signal(signal.SIGINT)
            stdout, stderr = process.communicate(timeout=15)
        finally:
            release.set()
            if process.poll() is None:
                process.kill()
                process.communicate(timeout=10)
        assert process.returncode == 6 and not stdout
        error = json.loads(stderr)
        assert error["code"] == "request_cancelled" and error["operation_id"] == identity
        found = api.show_dataset_upload(operation_id=identity, state_dir=data[0]).data
        assert found.operation_status == "unknown"
        assert provider.create_calls == provider.link_calls == provider.put_calls == 1
        assert provider.confirm_calls == 1
        with open_existing_store(data[0]) as store:
            view = StateUploads(store).show(operation_id=identity)
            assert len(view.receipts) == 5 and view.operation.lease is None
            assert view.verification is None and store.verify().store_schema_version == 7


def test_duplicate_tags_fail_before_any_external_dependency(cli):
    found = cli(
        "datasets",
        "upload",
        "plan",
        "source",
        "--manifest",
        "manifest.json",
        "--name",
        "sample",
        "--project",
        SCOPE.project_id,
        "--owner-user",
        SCOPE.owner.id,
        "--modality",
        "VISION",
        "--unpriced",
        "--admission-policy",
        "explicit-attempt",
        "--tag",
        "same",
        "--tag=same",
        "--output=json",
        recipe_loader=False,
    )
    assert found.returncode == 2 and not found.stdout
    assert json.loads(found.stderr)["code"] == "invalid_request"
