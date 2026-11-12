"""A process killed while it uploads leaves an operation that the commands themselves lead out of.

A killed `start` is not an uncertain answer: the operation stays `running` (latched) until its
lease lapses. The card's first acceptance clause walks exactly this: plan → start → SIGKILL at a
boundary → `show` (the direction) → `resume` (the report) → `resume --prepare` → `review` →
`approve` → `start` → `show`, with real processes, nothing edited by hand and nothing asked of the
provider that a continuation does not need. The lease of the dead process (150 s) lapses on a
clock shifted by 200 s, which the test console applies to every command after the kill.
"""

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

from tests.contracts.test_platform_upload_codec import SCOPE
from tests.fixtures.http_server import TlsServer
from tests.fixtures.upload_provider import UploadProvider
from tests.integration.test_upload_continuation_cli import Journey
from tests.integration.test_upload_file_workflow import many
from tests.integration.test_upload_preparation import certificates as certificates
from tests.integration.test_upload_preparation import loopback_only as loopback_only
from tests.integration.test_upload_preparation import prepared_input as prepared_input
from tests.integration.test_upload_public_api import public_inputs as public_inputs

CONSOLE = Path(__file__).parents[1] / "fixtures" / "upload_kill_console.py"
LAPSED = 200.0  # seconds: past the 150 s lease of a process that is dead


def environment():
    return {**os.environ, "LC_ALL": "C", "PYTHONIOENCODING": "ascii", "PYTHONUTF8": "0"}


def console(server, *args, shift=0.0, checkpoint=None, ready=None):
    return [
        sys.executable,
        "-I",
        "-W",
        "error",
        str(CONSOLE),
        "--ca",
        str(server.certificates[0]),
        "--port",
        str(server.port),
        "--clock-shift",
        str(shift),
        *(["--checkpoint", checkpoint, "--ready", str(ready)] if checkpoint else []),
        "--",
        *args,
    ]


class Terminal(Journey):
    """One person's terminal on the console that can shift the clock and be killed."""

    def run(self, *args, context=True, timeout=180, shift=0.0):
        base = ["datasets", "upload", *args, "--state-dir", str(self.data[0])]
        if context:
            base += ["--config", str(self.config)]
        process = subprocess.run(
            console(self.server, *base, "--output", self.output, shift=shift),
            env=environment(),
            capture_output=True,
            timeout=timeout,
        )
        self.transcript += [process.stdout, process.stderr]
        return process

    def killed_start(self, plan_id, checkpoint, ready, shift=0.0):
        """`start`, paused after the armed stage `checkpoint` and killed there: returncode -9."""
        base = ["datasets", "upload", "start", "--plan-id", plan_id]
        base += ["--state-dir", str(self.data[0]), "--config", str(self.config)]
        process = subprocess.Popen(
            console(
                self.server,
                *base,
                "--output",
                "json",
                shift=shift,
                checkpoint=checkpoint,
                ready=ready,
            ),
            env=environment(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            end = time.monotonic() + 90
            while not ready.exists():
                assert process.poll() is None, process.stderr.read()
                assert time.monotonic() < end, "the command never reached the boundary"
                time.sleep(0.05)
            process.send_signal(signal.SIGKILL)
            process.communicate(timeout=30)
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate(timeout=10)
        return process.returncode


FLAGS = ("--accept-unverified-authority", "--accept-unpriced-cost")


@pytest.mark.parametrize("boundary", ["presign-0", "confirm-0", "confirm-1"])
def test_a_killed_start_is_finished_by_the_commands_alone(public_inputs, certificates, boundary):
    data, manifest, config = public_inputs
    data = many(data)
    manifest.write_bytes(data[2].encoded())
    provider = UploadProvider(SCOPE.owner.id, SCOPE.project_id)
    with TlsServer(certificates, provider.routes()) as server:
        terminal = Terminal(server, data, manifest, config, "json")
        planned, _ = terminal.done(
            terminal.run(
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
                "--profile",
                "test",
            )
        )
        plan_id = planned["plan_id"]
        terminal.done(
            terminal.run(
                "approve",
                "--plan-id",
                plan_id,
                "--confirm",
                planned["plan_digest"],
                *FLAGS,
            )
        )
        killed = terminal.killed_start(plan_id, boundary, config.parent / f"{boundary}.ready")
        assert killed == -signal.SIGKILL
        provider.represign = True  # a file the dead process presigned may be presigned again
        shown, _ = terminal.done(terminal.run("show", "--plan-id", plan_id, context=False))
        source = shown["operation_id"]
        assert shown["operation_status"] == "running"
        person = Terminal(server, data, manifest, config, "text")

        # (1) the lease of the dead process has not lapsed: `show` says who is in the way, and the
        # error of `start` and of `resume --prepare` lead to that same explanation
        live = person.run("show", "--operation-id", source, context=False)
        text = live.stdout.decode()
        assert live.returncode == 0
        assert "Devam şu an mümkün değil (yerel kayda göre):" in text
        assert "- source_active:" in text
        assert "Lease bitince raporu yeniden alın" in text
        assert "Devam için:" not in text
        again = person.run("start", "--plan-id", plan_id)
        assert again.returncode == 5
        assert f"show --operation-id {source}" in again.stderr.decode()
        waiting = person.run(
            "resume", "--operation-id", source, "--accept-unverified-read", "--prepare"
        )
        assert waiting.returncode == 2
        assert waiting.stdout == b""
        waiting_text = waiting.stderr.decode()
        assert "lease'i dolmadı (en çok 150 sn)" in waiting_text
        assert f"resume --operation-id {source} --accept-unverified-read" in waiting_text

        # (2) the lease has lapsed (a clock 200 s on): `show` now points at the report
        lapsed = person.run("show", "--operation-id", source, context=False, shift=LAPSED)
        assert f"Devam için: yorunge datasets upload resume --operation-id {source}" in (
            lapsed.stdout.decode()
        )

        # (3) the journey, every command on that same later clock
        machine = Terminal(server, data, manifest, config, "json")
        report, _ = machine.done(
            machine.run(
                "resume", "--operation-id", source, "--accept-unverified-read", shift=LAPSED
            )
        )
        assert report["eligible"] is True
        assert report["recommended_action"] == "prepare"
        uncertain = (
            ("--accept-unconfirmed-effects",)
            if report["observation"]["unconfirmed_ack_required"]
            else ()
        )
        prepared, _ = machine.done(
            machine.run(
                "resume",
                "--operation-id",
                source,
                "--accept-unverified-read",
                "--prepare",
                *uncertain,
                shift=LAPSED,
            )
        )
        review, _ = machine.done(
            machine.run("review", "--plan-id", prepared["plan_id"], context=False, shift=LAPSED)
        )
        assert review["summary"]["schema_version"] == 3
        machine.done(
            machine.run(
                "approve",
                "--plan-id",
                prepared["plan_id"],
                "--confirm",
                prepared["plan_digest"],
                *FLAGS,
                *uncertain,
                shift=LAPSED,
            )
        )
        finished, _ = machine.done(
            machine.run("start", "--plan-id", prepared["plan_id"], shift=LAPSED)
        )
        assert finished["operation_status"] == "succeeded"
        assert finished["verification_level"] == "metadata"
        assert finished["continuation_of"] == source
        # the dataset holds the three distinct files, once each: nothing was sent twice
        assert sorted(provider.confirmed) == sorted(file.path for file in data[2].files)
        # and the source says who continued it
        history = person.run("show", "--operation-id", source, context=False, shift=LAPSED)
        assert f"Devamı: {finished['operation_id']}" in history.stdout.decode()
        body = json.dumps(json.loads(machine.transcript[-2]))
        for private in ("object_key", "created_dataset", "write_access", "credential_id"):
            assert private not in body


LAPSED_AGAIN = 400.0  # past the lease of the dead continuation, which began on the clock LAPSED


def test_a_killed_continuation_is_itself_continued_by_the_commands_alone(
    public_inputs, certificates
):
    """The chain with real kills: the original and then its continuation die with a SIGKILL.

    The second death leaves the continuation `running`; once its lease has lapsed `show` of the
    continuation (not of the original) points at `resume --operation-id <continuation>`, and the
    commands finish the dataset once: every file is on the provider exactly once.
    """
    data, manifest, config = public_inputs
    data = many(data)
    manifest.write_bytes(data[2].encoded())
    provider = UploadProvider(SCOPE.owner.id, SCOPE.project_id)
    with TlsServer(certificates, provider.routes()) as server:
        machine = Terminal(server, data, manifest, config, "json")
        planned, _ = machine.done(
            machine.run(
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
                "--profile",
                "test",
            )
        )
        machine.done(
            machine.run(
                "approve",
                "--plan-id",
                planned["plan_id"],
                "--confirm",
                planned["plan_digest"],
                *FLAGS,
            )
        )
        original = machine.killed_start(
            planned["plan_id"], "presign-0", config.parent / "original.ready"
        )
        assert original == -signal.SIGKILL
        provider.represign = True

        def continuation_plan(source, shift):
            report, _ = machine.done(
                machine.run(
                    "resume", "--operation-id", source, "--accept-unverified-read", shift=shift
                )
            )
            assert report["eligible"] is True
            uncertain = (
                ("--accept-unconfirmed-effects",)
                if report["observation"]["unconfirmed_ack_required"]
                else ()
            )
            prepared, _ = machine.done(
                machine.run(
                    "resume",
                    "--operation-id",
                    source,
                    "--accept-unverified-read",
                    "--prepare",
                    *uncertain,
                    shift=shift,
                )
            )
            machine.done(
                machine.run(
                    "approve",
                    "--plan-id",
                    prepared["plan_id"],
                    "--confirm",
                    prepared["plan_digest"],
                    *FLAGS,
                    *uncertain,
                    shift=shift,
                )
            )
            return prepared["plan_id"]

        source = machine.done(machine.run("show", "--plan-id", planned["plan_id"], context=False))[
            0
        ]["operation_id"]
        first = continuation_plan(source, LAPSED)
        killed = machine.killed_start(
            first, "cont-confirm-1", config.parent / "continuation.ready", shift=LAPSED
        )
        assert killed == -signal.SIGKILL
        dead = machine.done(machine.run("show", "--plan-id", first, context=False))[0]
        continuation = dead["operation_id"]
        assert continuation != source
        assert dead["operation_status"] == "running"

        # the lease of the dead continuation has not lapsed (the clock is 200 s on, its lease
        # began there): `show` says who is in the way, and does not point at the original
        person = Terminal(server, data, manifest, config, "text")
        live = person.run("show", "--operation-id", continuation, context=False, shift=LAPSED)
        text = live.stdout.decode()
        assert "Devam şu an mümkün değil (yerel kayda göre):" in text
        assert "- source_active:" in text
        assert "Devam için:" not in text

        # once it has: the direction names the CONTINUATION, and the commands finish the job
        lapsed = person.run(
            "show", "--operation-id", continuation, context=False, shift=LAPSED_AGAIN
        )
        assert (
            f"Devam için: yorunge datasets upload resume --operation-id {continuation}"
            in lapsed.stdout.decode()
        )
        second = continuation_plan(continuation, LAPSED_AGAIN)
        finished, _ = machine.done(machine.run("start", "--plan-id", second, shift=LAPSED_AGAIN))
        assert finished["operation_status"] == "succeeded"
        assert finished["continuation_of"] == continuation
        assert finished["verification_level"] == "metadata"
        # three files, once each: nothing the first continuation confirmed was sent again
        assert sorted(provider.confirmed) == sorted(file.path for file in data[2].files)
