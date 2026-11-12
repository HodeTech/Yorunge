"""An interrupted upload is finished by real CLI processes and their own words (P02-3i).

A person (or a CI job) whose upload stopped after two of three files has nothing but the commands'
outputs: ``show`` points at ``resume``, the report says what is left, ``resume --prepare`` saves the
plan, ``review`` shows the one file it sends, ``approve`` and ``start`` finish it, and ``show`` of
the source then names its continuation. Nothing is edited by hand, no command asks a question,
machine output stays machine output, and every error keeps the identity of the operation.
"""

import json
import signal
import subprocess
import threading

import pytest

from tests.contracts.test_platform_upload_codec import SCOPE
from tests.fixtures.http_server import TlsServer
from tests.fixtures.upload_provider import DATASET, UploadProvider
from tests.integration.test_upload_cli import command, execute
from tests.integration.test_upload_file_workflow import many
from tests.integration.test_upload_http_budget import SECRET
from tests.integration.test_upload_preparation import certificates as certificates
from tests.integration.test_upload_preparation import loopback_only as loopback_only
from tests.integration.test_upload_preparation import prepared_input as prepared_input
from tests.integration.test_upload_public_api import public_inputs as public_inputs
from tests.integration.test_upload_resume_observation import lose_confirm_of

PRIVATE = (
    SECRET,
    # what the product keeps to itself
    "object_key",
    "created_dataset",
    "write_access",
    "baseline",
    "credential_id",
    # what the provider says about itself: owner and slug, an unconsumed field, a signed address
    "owner_username",
    "test-user",
    "test-dataset",
    "fixture metadata",
    "upload/put",
    "objects/blob",
)


class Journey:
    """One person's terminal: the same state, config and output format for every command."""

    def __init__(self, server, data, manifest, config, output):
        self.server, self.data, self.manifest = server, data, manifest
        self.config, self.output = config, output
        self.transcript: list[bytes] = []

    def run(self, *args, context=True, timeout=120):
        base = ["datasets", "upload", *args, "--state-dir", str(self.data[0])]
        if context:
            base += ["--config", str(self.config)]
        process = execute(self.server, *base, "--output", self.output, timeout=timeout)
        self.transcript += [process.stdout, process.stderr]
        return process

    def done(self, process):
        """The success of a command: exit 0, nothing on stderr, one machine document on stdout."""
        assert process.returncode == 0, process.stderr.decode("utf-8", "replace")
        assert process.stderr == b""
        value = json.loads(process.stdout)
        if self.output == "ndjson":
            assert value["event"] == "result"
            assert value["sequence"] == 1
            return value["payload"]["data"], value["operation_id"]
        assert value["operation_id"] is None
        return value["data"], None

    def failed(self, process, code, exit_code):
        """The error of a command: its exit code, a closed code and the operation it is about.

        Nothing was published before it, so it is the closed envelope on stderr in every format
        (an NDJSON error event follows events that came first, and there are none here).
        """
        assert process.returncode == exit_code, (process.returncode, process.stderr)
        assert process.stdout == b""
        envelope = json.loads(process.stderr)
        assert envelope["code"] == code, envelope
        return envelope

    def plan_and_stop(self, provider):
        """The original upload, until the provider's lost answer stops it: the source operation."""
        planned = self.run(
            "plan",
            str(self.data[1]),
            "--manifest",
            str(self.manifest),
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
        plan, _ = self.done(planned)
        approved = self.run(
            "approve",
            "--plan-id",
            plan["plan_id"],
            "--confirm",
            plan["plan_digest"],
            "--accept-unverified-authority",
            "--accept-unpriced-cost",
        )
        self.done(approved)
        stopped = self.run("start", "--plan-id", plan["plan_id"])
        envelope = self.failed(stopped, "operation_uncertain", 5)
        assert envelope["operation_id"] is not None
        return envelope["operation_id"]


def world(public_inputs, remembered=True, then_also_lose=()):
    """Three files; the provider loses the answer to the confirm of the second, and to those of
    ``then_also_lose`` (files only a later attempt gets to confirm)."""
    data, manifest, config = public_inputs
    data = many(data)
    manifest.write_bytes(data[2].encoded())
    provider = UploadProvider(SCOPE.owner.id, SCOPE.project_id)
    lose_confirm_of(provider, "two.bin", remembered=remembered)
    for name in then_also_lose:
        lose_confirm_of(provider, name)
    return data, manifest, config, provider


def no_secret_anywhere(journey):
    text = b"".join(journey.transcript).decode("utf-8", "replace")
    for private in PRIVATE:
        assert private not in text, private


@pytest.mark.parametrize("output", ["json", "ndjson"])
def test_an_upload_that_stopped_is_finished_by_the_commands_alone(
    public_inputs, certificates, output
):
    data, manifest, config, provider = world(public_inputs)
    with TlsServer(certificates, provider.routes()) as server:
        journey = Journey(server, data, manifest, config, output)
        source = journey.plan_and_stop(provider)
        # what is left is read, never written: the report does not touch the store or the files
        needs_the_choice = journey.run("resume", "--operation-id", source)
        assert journey.failed(needs_the_choice, "approval_required", 4)["operation_id"] == source
        read = journey.run("resume", "--operation-id", source, "--accept-unverified-read")
        report, stream = journey.done(read)
        assert report["kind"] == "dataset_upload_resume_report"
        assert report["eligible"] is True
        assert (report["blockers"], report["recommended_action"]) == ([], "prepare")
        assert report["observation"]["send_files"] == 1
        assert report["plan_id"] is None
        if output == "ndjson":
            assert stream == source  # the stream is about the operation it was asked about
        provider.represign = True
        prepared, _ = journey.done(
            journey.run("resume", "--operation-id", source, "--accept-unverified-read", "--prepare")
        )
        plan_id = prepared["plan_id"]
        assert plan_id is not None
        assert prepared["plan_digest"] is not None
        review, _ = journey.done(journey.run("review", "--plan-id", plan_id, context=False))
        assert review["summary"]["schema_version"] == 3
        assert review["request_limits"]["max_presign"] == 1
        assert review["manifest"]["file_count"] == 3
        approved, _ = journey.done(
            journey.run(
                "approve",
                "--plan-id",
                plan_id,
                "--confirm",
                prepared["plan_digest"],
                "--accept-unverified-authority",
                "--accept-unpriced-cost",
            )
        )
        assert approved["approval_status"] == "approved"
        assert approved["continuation_of"] == source
        sent = len(provider.events)
        started, _ = journey.done(journey.run("start", "--plan-id", plan_id))
        assert started["operation_status"] == "succeeded"
        assert started["verification_level"] == "metadata"
        assert started["continuation_of"] == source
        assert provider.events[sent:] == ["presign", "put", "confirm"]
        no_secret_anywhere(journey)
        # the source is history now, and its own `show` says who continued it
        shown, _ = journey.done(journey.run("show", "--operation-id", source, context=False))
        assert shown["operation_status"] == "unknown"
        again = journey.run(
            "resume", "--operation-id", source, "--accept-unverified-read", "--prepare"
        )
        envelope = journey.failed(again, "continuation_not_possible", 2)
        assert envelope["operation_id"] == source
        assert envelope["details"]["blockers"] == ["source_superseded"]


def test_the_text_a_person_reads_leads_from_each_step_to_the_next(public_inputs, certificates):
    data, manifest, config, provider = world(public_inputs)
    with TlsServer(certificates, provider.routes()) as server:
        journey = Journey(server, data, manifest, config, "text")
        # the original upload is made with machine output, as a script would; the rest is read
        machine = Journey(server, data, manifest, config, "json")
        source = machine.plan_and_stop(provider)
        shown = journey.run("show", "--operation-id", source, context=False)
        assert shown.returncode == 0
        assert shown.stderr == b""
        text = shown.stdout.decode()
        assert f"Devam için: yorunge datasets upload resume --operation-id {source}" in text
        report = journey.run("resume", "--operation-id", source, "--accept-unverified-read")
        assert report.returncode == 0, report.stderr
        text = report.stdout.decode()
        assert f"Devam raporu — kaynak iş: {source}" in text
        assert "Devam edilebilir; plan kaydedilmedi (salt okuma raporu)." in text
        assert "Gönderilecek: 1 dosya" in text
        assert "Hazırla: yorunge datasets upload resume" in text
        assert "--prepare" in text
        provider.represign = True
        prepared = journey.run(
            "resume", "--operation-id", source, "--accept-unverified-read", "--prepare"
        )
        text = prepared.stdout.decode()
        assert "Devam planı kaydedildi: " in text
        assert "İncele: yorunge datasets upload review" in text
        plan_id = text.split("Devam planı kaydedildi: ")[1].split(" ")[0]
        digest = text.split("(digest: ")[1].split(")")[0]
        reviewed = journey.run("review", "--plan-id", plan_id, context=False).stdout.decode()
        assert f"Devam: {source} işinin kalanını gönderir; 1 dosya gönderilir" in reviewed
        assert "Bu devamda gönderilecek: 1 dosya" in reviewed
        assert "Devam başlatma maliyet üst sınırı" in reviewed or "Fiyat doğrulanmadı" in reviewed
        approve = f"yorunge datasets upload approve --plan-id {plan_id} --confirm {digest}"
        assert approve in reviewed
        no_secret_anywhere(journey)


def test_a_refused_continuation_explains_itself_in_text_and_keeps_the_operation(
    public_inputs, certificates
):
    data, manifest, config, provider = world(public_inputs)
    with TlsServer(certificates, provider.routes()) as server:
        machine = Journey(server, data, manifest, config, "json")
        source = machine.plan_and_stop(provider)
        provider.represign = True
        prepared, _ = machine.done(
            machine.run("resume", "--operation-id", source, "--accept-unverified-read", "--prepare")
        )
        machine.done(
            machine.run(
                "approve",
                "--plan-id",
                prepared["plan_id"],
                "--confirm",
                prepared["plan_digest"],
                "--accept-unverified-authority",
                "--accept-unpriced-cost",
            )
        )
        machine.done(machine.run("start", "--plan-id", prepared["plan_id"]))
        person = Journey(server, data, manifest, config, "text")
        refused = person.run(
            "resume", "--operation-id", source, "--accept-unverified-read", "--prepare"
        )
        assert refused.returncode == 2
        assert refused.stdout == b""
        text = refused.stderr.decode()
        assert "Devam bu işten şu an hazırlanamıyor." in text
        assert "- source_superseded: Bu kaynağın iptal edilmemiş bir devamı zaten var." in text
        assert f"İş: {source}" in text
        assert f"Rapor: yorunge datasets upload resume --operation-id {source}" in text
        # `reconcile` of the source is refused for the continuation, and says whose it names
        listed, _ = machine.done(machine.run("list", context=False))
        successor = listed["uploads"][-1]["operation_id"]
        assert successor != source
        reconcile = person.run("reconcile", "--operation-id", source, "--accept-unverified-read")
        assert reconcile.returncode == 2
        assert reconcile.stdout == b""
        text = reconcile.stderr.decode()
        assert f"İş: {successor}" in text
        assert f"İstediğiniz iş {source} değil; yukarıdaki iş ona bağlı" in text
        assert f"İncele: yorunge datasets upload show --operation-id {successor}" in text
        no_secret_anywhere(person)


def test_a_continuation_that_stops_too_is_resumed_in_its_turn(public_inputs, certificates):
    """The chain: the first continuation loses an answer as well, and the second `resume` of the
    commands' own output (the continuation's operation, not the original's) finishes the dataset."""
    # "ölçüm.bin" is the file the first continuation sends: its answer is lost as well
    data, manifest, config, provider = world(public_inputs, then_also_lose=("ölçüm.bin",))
    with TlsServer(certificates, provider.routes()) as server:
        journey = Journey(server, data, manifest, config, "json")
        source = journey.plan_and_stop(provider)
        provider.represign = True
        flags = ("--accept-unverified-authority", "--accept-unpriced-cost")

        def continue_from(operation):
            prepared, _ = journey.done(
                journey.run(
                    "resume", "--operation-id", operation, "--accept-unverified-read", "--prepare"
                )
            )
            journey.done(
                journey.run(
                    "approve",
                    "--plan-id",
                    prepared["plan_id"],
                    "--confirm",
                    prepared["plan_digest"],
                    *flags,
                )
            )
            return prepared["plan_id"]

        first = continue_from(source)
        stopped = journey.run("start", "--plan-id", first)
        interrupted = journey.failed(stopped, "operation_uncertain", 5)["operation_id"]
        assert interrupted != source
        # the second interruption points at the continuation, which is the operation to resume
        report, _ = journey.done(
            journey.run("resume", "--operation-id", interrupted, "--accept-unverified-read")
        )
        assert report["eligible"] is True
        assert report["source_operation_id"] == interrupted
        assert report["observation"]["send_files"] == 0  # everything is on the provider already
        second = continue_from(interrupted)
        done, _ = journey.done(journey.run("start", "--plan-id", second))
        assert done["operation_status"] == "succeeded"
        assert done["verification_level"] == "metadata"
        assert done["continuation_of"] == interrupted
        assert done["continuation_files"] == 0  # a check of the dataset, nothing sent
        # each source in the chain names its own continuation, not the tip
        for ancestor in (source, interrupted):
            refused = journey.run(
                "resume", "--operation-id", ancestor, "--accept-unverified-read", "--prepare"
            )
            assert journey.failed(refused, "continuation_not_possible", 2)["details"][
                "blockers"
            ] == ["source_superseded"]
        no_secret_anywhere(journey)


# --- what a person reads when `resume` itself goes wrong ------------------------------------------


@pytest.mark.parametrize(
    "arguments,code,exit_code,hint",
    [
        ((), "approval_required", 4, "dataset’in okunması için --accept-unverified-read"),
        (("--accept-unconfirmed-effects",), "invalid_request", 2, "seçenekleri yardımla"),
        (("--accept-unverified-read", "--accept-unconfirmed-effects"), "invalid_request", 2, None),
    ],
    ids=["no choice", "flag without prepare, no choice", "flag without prepare"],
)
def test_resume_errors_say_what_to_do_in_text_and_keep_the_machine_envelope_as_it_is(
    public_inputs, certificates, arguments, code, exit_code, hint
):
    data, manifest, config, provider = world(public_inputs)
    with TlsServer(certificates, provider.routes()) as server:
        source = Journey(server, data, manifest, config, "json").plan_and_stop(provider)
        text = Journey(server, data, manifest, config, "text").run(
            "resume", "--operation-id", source, *arguments
        )
        machine = Journey(server, data, manifest, config, "json").run(
            "resume", "--operation-id", source, *arguments
        )
    assert (text.returncode, machine.returncode) == (exit_code, exit_code)
    envelope = json.loads(machine.stderr)
    assert envelope["code"] == code
    assert envelope["operation_id"] == source
    assert "hint" not in json.dumps(envelope)
    assert list(envelope["details"]) == [
        "reason_code",
        "capacity_kind",
    ]
    if hint is not None:
        assert hint in text.stderr.decode()
    assert f"İş: {source}" in text.stderr.decode()


def test_resume_arguments_are_judged_like_every_other_command(public_inputs, certificates):
    data, manifest, config, provider = world(public_inputs)
    with TlsServer(certificates, provider.routes()) as server:
        journey = Journey(server, data, manifest, config, "json")
        requests = len(server.requests)
        for arguments in (
            (),  # no operation
            ("--operation-id", "not-a-uuid"),
            ("--operation-id", "00000000-0000-4000-8000-0000000000aa", "--prepare", "--prepare"),
            ("--operation-id", "00000000-0000-4000-8000-0000000000aa", "--nope"),
        ):
            refused = journey.run("resume", *arguments)
            assert refused.returncode == 2
            assert refused.stdout == b""
            assert json.loads(refused.stderr)["code"] == "invalid_request"
        missing = journey.run(
            "resume",
            "--operation-id",
            "00000000-0000-4000-8000-0000000000aa",
            "--accept-unverified-read",
        )
        assert journey.failed(missing, "operation_not_found", 2)["operation_id"] == (
            "00000000-0000-4000-8000-0000000000aa"
        )
        assert len(server.requests) == requests  # not one request for a mistake


# --- the two ways a `resume` can end without its answer being read -------------------------------


def kept(state_dir):
    """What the store holds of uploads, as a person sees it (plans and operations with status)."""
    from yorunge import api

    page = api.list_dataset_uploads(state_dir=state_dir, limit=100).data
    return sorted((u.plan_id, u.operation_id, u.operation_status) for u in page.uploads)


def effects(provider):
    return (provider.create_calls, provider.link_calls, provider.put_calls, provider.confirm_calls)


@pytest.mark.parametrize("prepare", [False, True], ids=["report", "prepare"])
def test_a_closed_stdout_is_output_closed_with_the_source_and_never_sends_anything(
    public_inputs, certificates, prepare
):
    data, manifest, config, provider = world(public_inputs)
    with TlsServer(certificates, provider.routes()) as server:
        machine = Journey(server, data, manifest, config, "json")
        source = machine.plan_and_stop(provider)
        provider.represign = True
        before, sent = kept(data[0]), effects(provider)
        arguments = ["resume", "--operation-id", source, "--accept-unverified-read"]
        process = subprocess.Popen(
            command(
                server,
                "datasets",
                "upload",
                *arguments,
                *(["--prepare"] if prepare else []),
                "--state-dir",
                str(data[0]),
                "--config",
                str(config),
                "--output",
                "json",
            ),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            process.stdout.close()
            process.stdout = None
            _, stderr = process.communicate(timeout=60)
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate(timeout=10)
        assert process.returncode == 6
        failure = json.loads(stderr)
        assert failure["code"] == "output_closed"
        assert failure["operation_id"] == source  # the one a person looks at, as for every error
        assert effects(provider) == sent  # resume reads the provider; it never writes to it
        after = kept(data[0])
        if not prepare:
            assert after == before  # a report saves nothing
        else:
            # the plan was saved before its description could not be written: it is found again
            # by `list`, and a second prepare is one more draft, never a replay of anything
            assert len(after) == len(before) + 1
            saved = [row for row in after if row not in before]
            assert saved[0][1] is None
            assert saved[0][0] is not None
            again, _ = machine.done(machine.run(*arguments, "--prepare"))
            assert again["plan_id"] not in (row[0] for row in after)
            assert effects(provider) == sent


def test_sigint_while_resume_reads_the_dataset_is_cancelled_with_nothing_saved(
    public_inputs, certificates
):
    data, manifest, config, provider = world(public_inputs)
    routes = provider.routes()
    path = f"/api/v1/datasets/{DATASET}/items?limit=128"
    original = routes[path]
    ready, release = threading.Event(), threading.Event()

    def waiting(request, calls):
        ready.set()
        assert release.wait(30), "read signal fixture was not released"
        return original(request, calls)

    with TlsServer(certificates, routes) as server:
        machine = Journey(server, data, manifest, config, "json")
        source = machine.plan_and_stop(provider)
        provider.represign = True
        before, sent = kept(data[0]), effects(provider)
        routes[path] = waiting
        process = subprocess.Popen(
            command(
                server,
                "datasets",
                "upload",
                "resume",
                "--operation-id",
                source,
                "--accept-unverified-read",
                "--prepare",
                "--state-dir",
                str(data[0]),
                "--config",
                str(config),
                "--output",
                "ndjson",
            ),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            assert ready.wait(30), "the dataset was never read from the actual TLS server"
            process.send_signal(signal.SIGINT)
            stdout, stderr = process.communicate(timeout=30)
        finally:
            release.set()
            if process.poll() is None:
                process.kill()
                process.communicate(timeout=10)
        assert process.returncode == 6
        assert stdout == b""
        error = json.loads(stderr)
        assert error["code"] == "request_cancelled"
        assert error["operation_id"] == source
        assert kept(data[0]) == before  # no plan: a prepare cancelled in its read freezes nothing
        assert effects(provider) == sent
        routes[path] = original
        # and the same command, asked again, is simply the answer it would have been
        report, _ = machine.done(
            machine.run("resume", "--operation-id", source, "--accept-unverified-read")
        )
        assert report["eligible"] is True
        assert report["plan_id"] is None
