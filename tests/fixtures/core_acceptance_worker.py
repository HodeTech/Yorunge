"""Test-only full-core composition; product imports use the active installation.

Only this worker installs the trusted execution proof. No fixture backend or
positive execution producer is registered in the product.
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import ssl
import sys
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Literal

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.conftest import execution_validator_fixture  # noqa: E402
from tests.fixtures.http_operations import NetworkBackend  # noqa: E402
from tests.fixtures.http_server import LoopbackTransport, loopback_sockets  # noqa: E402
from yorunge import api  # noqa: E402
from yorunge.adapters import capability_cache  # noqa: E402
from yorunge.adapters.http_session import HttpSession  # noqa: E402
from yorunge.adapters.http_transport import HttpxTransport  # noqa: E402
from yorunge.application.http_transport import HttpCredential, HttpRequest  # noqa: E402
from yorunge.application.stream_results import open_stream  # noqa: E402
from yorunge.cli.output import OutputRenderer  # noqa: E402
from yorunge.domain.capabilities import instant  # noqa: E402
from yorunge.domain.errors import YorungeError  # noqa: E402
from yorunge.domain.models import Model  # noqa: E402
from yorunge.domain.operations import OperationLease  # noqa: E402

STREAM_ID = "5cbcd726-42dd-4ab5-ac7c-03c33f306c93"
SELECTED_ENV = "YORUNGE_ACCEPTANCE_PLATFORM_TOKEN"


class AcceptanceReceipt(Model):
    provider_run_id: str
    input_sha256: str
    result_code: Literal["fixture-complete"]


def save(root: Path, name: str, value: object) -> None:
    with (root / name).open("w", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True)
        stream.flush()
        os.fsync(stream.fileno())


def load(root: Path, name: str):
    return json.loads((root / name).read_text(encoding="utf-8"))


def install_clock(root: Path) -> None:
    class Clock:
        def now(self):
            return instant((root / "clock.txt").read_text(encoding="ascii"))

        def monotonic(self):
            return time.monotonic()

    capability_cache.SystemClock = Clock


def bootstrap(root: Path) -> None:
    config, state = root / "config.toml", root / "state"
    initialized = api.initialize_config(config=config, profile="work", project="fixture-project")
    created = api.initialize_state(state_dir=state)
    # Endpoint/account setters are not public yet. Explicit test configuration
    # follows the real public initializer, without adding product setters.
    config.write_text(
        'schema_version=1\nactive_profile="work"\n[profiles.work]\n'
        'account_id="fixture-account"\nproject_id="fixture-project"\n'
        'platform_url="https://localhost/v1"\n'
        f'platform_key_env="{SELECTED_ENV}"\n'
        'llm_key_env="YORUNGE_ACCEPTANCE_UNUSED_LLM_TOKEN"\n',
        encoding="utf-8",
    )
    context = api.show_context(config=config)
    identity = api.observe_credential("evren-platform", config=config, state_dir=state)
    options = {
        "config": config,
        "recipe": root / "recipe.yaml",
        "input_root": root / "inputs",
        "state_dir": state,
    }
    # Public producer remains blocked even for the same fully bound input.
    public = api.prepare_execution_plan(**options).data
    try:
        api.approve_execution_plan(
            public.plan.plan_id, public.plan.digest, config=config, state_dir=state
        )
    except YorungeError as error:
        public_approval_error = error.code
    else:
        raise AssertionError("public draft unexpectedly approved")
    api._execution_validator = execution_validator_fixture
    prepared = api.prepare_execution_plan(**options).data
    approved = api.approve_execution_plan(
        prepared.plan.plan_id, prepared.plan.digest, config=config, state_dir=state
    ).data
    save(
        root,
        "prepared.json",
        {
            "initialized": initialized.model_dump(mode="json"),
            "state": created.model_dump(mode="json"),
            "context": context.model_dump(mode="json"),
            "identity": identity.model_dump(mode="json"),
            "public": public.model_dump(mode="json"),
            "public_approval_error": public_approval_error,
            "prepared": prepared.model_dump(mode="json"),
            "approval": approved.model_dump(mode="json"),
        },
    )


def mutation(root: Path, kind: str, validator) -> None:
    if kind == "input":
        file = root / "inputs" / "manifest.json"
        before = file.stat()
        file.write_bytes(b"X" * before.st_size)
        os.utime(file, ns=(before.st_atime_ns, before.st_mtime_ns))
    elif kind in {"credential", "revoke"}:

        def change(assessment):
            validator.change = None
            if kind == "credential":
                os.environ[SELECTED_ENV] = "rotated-synthetic-acceptance-secret"
                api.observe_credential(
                    "evren-platform", config=root / "config.toml", state_dir=root / "state"
                )
            else:
                api.revoke_execution_approval(
                    load(root, "prepared.json")["prepared"]["plan"]["plan_id"],
                    state_dir=root / "state",
                )
            return assessment

        validator.change = change


def watch(root: Path, coordinator, http: HttpSession, renderer: OutputRenderer) -> int:
    identifier = load(root, "claim.json")["operation_id"]
    record = coordinator.repository.operation(identifier)
    plan = coordinator.repository.plan(record.admission.plan_id)
    # The product resolver captures the selected identity/credential. The stream
    # uses that snapshot, rather than rediscovering an env name after dispatch.
    context = coordinator.resolve_read(plan)
    bound = context.credentials[0]
    request = HttpRequest(
        bound.credential.target,
        "GET",
        "fixture/events",
        query=(
            ("operation_id", identifier),
            ("stream_id", STREAM_ID),
            ("correlation", record.admission.correlation),
        ),
        credential=HttpCredential(
            "Authorization",
            bound.credential.secret,
            prefix="Bearer ",
            target=bound.credential.target,
            service_id="evren-platform",
        ),
        service_id="evren-platform",
        read_only=True,
    )

    async def consume(client):
        async with open_stream(
            client,
            request,
            AcceptanceReceipt,
            deadline=time.monotonic() + 5,
            stream_id=STREAM_ID,
            operation_id=identifier,
        ) as stream:
            async for event in stream:
                renderer.event(event)

    http.call(consume)
    return renderer.finish()


def network(args, renderer: OutputRenderer) -> int:
    root = args.root
    prepared = load(root, "prepared.json")["prepared"]["plan"]
    plan_id = prepared["plan_id"]
    if args.mutation == "target":
        config = root / "config.toml"
        config.write_text(
            config.read_text().replace("https://localhost/v1", "https://other.invalid/v1")
        )
    context = ssl.create_default_context(cafile=str(args.ca))
    with HttpSession(
        transport_factory=lambda: HttpxTransport(transport=LoopbackTransport(args.port, context))
    ) as http:
        backend = NetworkBackend(http)
        validator = execution_validator_fixture()
        api._execution_validator = lambda: validator
        with api._operation_session(
            plan_id,
            backend,
            observer=backend,
            config=root / "config.toml",
            state_dir=root / "state",
        ) as coordinator:
            if args.command == "dispatch":
                claim = coordinator.admit(plan_id)
                identifier, owner = claim.job.operation.operation_id, claim.ownership
                renderer.operation_id = identifier
                assert owner is not None
                save(
                    root,
                    "claim.json",
                    {
                        "operation_id": identifier,
                        "ownership": owner.model_dump(mode="json"),
                        "plan_id": plan_id,
                        "plan_digest": prepared["digest"],
                    },
                )
                mutation(root, args.mutation, validator)
                if args.failure == "deadline":
                    backend.start_timeout = 0.1
                if args.failure == "cancel":
                    backend.cancel_after_headers = True
                submitted = coordinator.dispatch(identifier, owner)
                save(root, "submitted.json", submitted.model_dump(mode="json"))
                if args.stream:
                    watch(root, coordinator, http, renderer)
                if args.reconcile:
                    final = coordinator.reconcile(identifier, owner)
                    save(root, "finished.json", final.model_dump(mode="json"))
            else:
                original = load(root, "claim.json")
                identifier = original["operation_id"]
                renderer.operation_id = identifier
                if args.command == "watch":
                    return watch(root, coordinator, http, renderer)
                old = OperationLease.model_validate_json(json.dumps(original["ownership"]))
                claim = coordinator.takeover(identifier)
                assert claim.ownership is not None
                errors = {}
                for name, action in (
                    ("stale_owner", lambda: coordinator.renew(identifier, old)),
                    ("redispatch", lambda: coordinator.dispatch(identifier, claim.ownership)),
                ):
                    try:
                        action()
                    except YorungeError as error:
                        errors[name] = error.code
                    else:
                        raise AssertionError("old ownership or second dispatch was accepted")
                outcome = coordinator.reconcile(identifier, claim.ownership)
                record = coordinator.repository.operation(identifier)
                save(
                    root,
                    "recovered.json",
                    {
                        "job": outcome.model_dump(mode="json"),
                        "record": record.model_dump(mode="json"),
                        "errors": errors,
                        "start_calls": backend.calls,
                        "takeover_status": claim.job.operation.status,
                    },
                )
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("bootstrap", "dispatch", "watch", "recover", "jobs"))
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--ca", type=Path)
    parser.add_argument("--port", type=int)
    parser.add_argument("--stream", action="store_true")
    parser.add_argument("--reconcile", action="store_true")
    parser.add_argument(
        "--mutation", default="none", choices=("none", "target", "credential", "revoke", "input")
    )
    parser.add_argument("--failure", default="none", choices=("none", "deadline", "cancel"))
    args = parser.parse_args(argv)
    install_clock(args.root)
    renderer = OutputRenderer("ndjson", stream_id=STREAM_ID)
    try:
        with loopback_sockets(socket.socket.connect, socket.socket.connect_ex, socket.getaddrinfo):
            if args.command == "bootstrap":
                bootstrap(args.root)
                return 0
            if args.command == "jobs":
                # Neither the test proof nor network composition is needed to
                # query persisted history from a fresh interpreter.
                identifier = load(args.root, "claim.json")["operation_id"]
                print(api.show_job(identifier, state_dir=args.root / "state").model_dump_json())
                return 0
            return network(args, renderer)
    except YorungeError as error:
        return renderer.error(error)
    except KeyboardInterrupt:
        return renderer.error(YorungeError("request_cancelled"))


if __name__ == "__main__":
    raise SystemExit(main())
