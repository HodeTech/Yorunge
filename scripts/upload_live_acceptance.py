"""One separately authorized public-API acceptance; never retry this workspace."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import runpy
import stat
import sys
import time
import tomllib
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from yorunge import api  # noqa: E402
from yorunge.adapters.state import open_existing_store  # noqa: E402
from yorunge.adapters.upload_http import UploadSession  # noqa: E402
from yorunge.adapters.upload_preparation import _limits  # noqa: E402
from yorunge.adapters.upload_repository import StateUploads  # noqa: E402
from yorunge.application import platform_upload_codec as codec  # noqa: E402
from yorunge.application.http_transport import HttpCredential, HttpRequest  # noqa: E402
from yorunge.application.upload_budget import UploadBudget  # noqa: E402
from yorunge.domain.credentials import SecretValue, normalize_target  # noqa: E402
from yorunge.domain.dataset_manifest import DatasetManifest  # noqa: E402
from yorunge.domain.dataset_upload import UploadOwner, UploadParameters, provider_uuid  # noqa: E402
from yorunge.domain.errors import OperationError, YorungeError  # noqa: E402
from yorunge.domain.platform_upload import ProviderProject  # noqa: E402

GUARD = runpy.run_path(str(ROOT / "scripts/upload_pilot_guard.py"))
LIMITS, PilotGuard = GUARD["LIMITS"], GUARD["PilotGuard"]
TARGET = normalize_target("https://api.ssyz.org.tr/api/v1")
FROZEN = ROOT / "docs/research/probes/platform-upload-pilot-20261102/pilot.py"
FROZEN_SHA = "c7a192c3ac9b5f25613fe817d4138951d18814376058705ae141f375e3e984cf"


def encoded(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
    ).encode()


def write(path: Path, value: object) -> None:
    with path.open("xb") as target:
        target.write(encoded(value))
        target.flush()
        os.fsync(target.fileno())


def private_file(path: Path) -> bytes:
    if path.is_symlink() or any(parent.is_symlink() for parent in path.parents):
        raise ValueError("private pilot file must not use symlinks")
    with path.open("rb") as source:
        info = os.fstat(source.fileno())
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) & 0o077
            or info.st_size > 65_536
        ):
            raise ValueError("private bounded pilot file required")
        content = source.read(65_537)
    if len(content) > 65_536:
        raise ValueError("pilot file grew beyond limit")
    return content


def credential(config: Path, credentials: Path) -> tuple[str, str]:
    spec = tomllib.loads(private_file(config).decode("utf-8"))
    profile = spec["active_profile"]
    selected = spec["profiles"][profile]
    if normalize_target(selected["platform_url"]) != TARGET:
        raise ValueError("pilot requires the canonical Platform target")
    reference = selected["platform_key_env"]
    if reference != "PILOT_PLATFORM_KEY":
        raise ValueError("pilot requires the previously prepared Platform key reference")
    from yorunge.application.response_json import parse_json

    keys = parse_json(private_file(credentials), max_bytes=65_536)
    if type(keys) is not dict or type(keys.get(reference)) is not str:
        raise ValueError("prepared Platform credential missing")
    return profile, keys[reference]


def fixtures(work: Path) -> DatasetManifest:
    if hashlib.sha256(FROZEN.read_bytes()).hexdigest() != FROZEN_SHA:
        raise ValueError("frozen synthetic image helper changed")
    images = runpy.run_path(str(FROZEN))["fixtures"]()
    source = work / "source"
    source.mkdir(mode=0o700)
    for name, content in images:
        with (source / name).open("xb") as target:
            target.write(content)
    api.inspect_dataset(source, manifest_out=work / "manifest.json")
    return DatasetManifest.model_validate_json((work / "manifest.json").read_bytes())


def select_owner(project_id: str, secret: SecretValue, manifest: DatasetManifest) -> UploadOwner:
    key = HttpCredential("X-API-Key", secret, target=TARGET, service_id="evren-platform")
    endpoint = "projects/" + codec.segment(project_id, secret)
    budget = UploadBudget(_limits(manifest), end=time.monotonic() + 30, read_only=True)

    async def observe(client: Any) -> ProviderProject:
        request = HttpRequest(
            TARGET,
            "GET",
            endpoint,
            credential=key,
            service_id="evren-platform",
            read_only=True,
            upload_endpoint="project",
        )
        reserved = budget.reserve("read")
        try:
            async with client.open_budgeted(request, reserved, deadline=budget.end) as response:
                content = b"".join([part async for part in response.chunks()])
        finally:
            if not reserved._closed:
                reserved.finish()
        raw = codec.raw(content, "project", secret)
        if type(raw) is not dict:
            raise YorungeError("invalid_response")
        selected = {name: raw[name] for name in ("id", "owner_id", "org_id", "visibility")}
        result = ProviderProject.model_validate_json(encoded(selected))
        if result.id != project_id:
            raise YorungeError("invalid_response")
        return result

    session = UploadSession(key, budget)
    with session:
        selected = session.exchange(observe)
    return (
        UploadOwner(kind="organization", id=selected.org_id)
        if selected.org_id
        else UploadOwner(kind="user", id=selected.owner_id)
    )


def flow(
    args: argparse.Namespace, manifest: DatasetManifest, owner: UploadOwner, profile: str
) -> str:
    options: dict[str, Any] = {
        "config": args.config,
        "profile": profile,
        "state_dir": args.workspace / "state",
    }
    prepared = api.prepare_dataset_upload(
        args.workspace / "source",
        manifest=args.workspace / "manifest.json",
        owner=owner,
        parameters=UploadParameters(
            name="yorunge-acceptance-" + args.workspace.name,
            modality="VISION",
            visibility="private",
            contributions_enabled=False,
            license=None,
            tags=(),
        ),
        project=args.project,
        admission_policy="explicit_attempt",
        unpriced=True,
        **options,
    ).data
    write(args.workspace / "plan-identity.json", {"plan_id": prepared.plan_id})
    if prepared.risks != ("authority_unverified", "cost_unverified") or prepared.blockers:
        raise ValueError("pilot requires exactly the reviewed unknown authority/cost policy")
    api.approve_dataset_upload(
        prepared.plan_id,
        prepared.plan_digest,
        accept_unverified_authority=True,
        accept_unpriced_cost=True,
        **options,
    )
    result = api.start_dataset_upload(prepared.plan_id, **options).data
    write(
        args.workspace / "operation-identity.json",
        {
            "operation_id": result.operation_id,
            "dataset_id": result.dataset_id,
        },
    )
    if result.operation_status != "succeeded" or result.verification_level != "metadata":
        raise ValueError("pilot did not produce durable metadata success")
    if result.authority_verified or result.remote_bytes_verified or result.operation_id is None:
        raise ValueError("pilot must not upgrade authority or remote-byte evidence")
    verify_files(args.workspace, result.operation_id, manifest)
    return result.operation_id


def verify_files(work: Path, operation_id: str, manifest: DatasetManifest) -> None:
    with open_existing_store(work / "state") as store:
        view = StateUploads(store).show(operation_id=operation_id)
        proof = view.verification
        if proof is None or len(view.intents) != 11 or len(view.receipts) != 11:
            raise ValueError("pilot requires the complete durable stage graph")
        if any(receipt.result != "accepted" for receipt in view.receipts) or len(proof.files) != 3:
            raise ValueError("pilot requires all accepted receipts and three verified files")
        for expected, observed in zip(manifest.files, proof.files, strict=True):
            if (
                expected.size,
                expected.sha256,
                hashlib.sha256(expected.path.encode()).hexdigest(),
            ) != (
                observed.size_bytes,
                observed.sha256,
                observed.path_digest,
            ):
                raise ValueError("pilot metadata differs from original synthetic files")
        if len({file.item_id for file in proof.files}) != 3:
            raise ValueError("same-content different-name files require distinct remote items")


def run(args: argparse.Namespace) -> dict[str, Any]:
    if not sys.flags.isolated or not args.accept_live_unpriced_write:
        raise ValueError("isolated installed runtime and separate live consent required")
    provider_uuid(args.project)
    worker = runpy.run_path(str(ROOT / "tests/fixtures/upload_native_client.py"))
    driver = runpy.run_path(str(ROOT / "scripts/benchmark-upload.py"))
    before = driver["EVIDENCE"]["source"](ROOT)
    locked = driver["STREAM"]["locked_runtime"](ROOT)
    wheel = driver["WHEEL"]["snapshot"](args.wheel, before["source_sha256"], locked["yorunge"])
    expected = {
        "source_sha256": before["source_sha256"],
        "locked_runtime": locked,
        "metadata_sha256": wheel["metadata_sha256"],
    }
    worker["provenance"](expected, Path(sys.prefix))
    profile, value = credential(args.config, args.credentials)
    secret = SecretValue(value)
    os.umask(0o077)
    # This exclusive directory is the permanent no-retry marker, before any HTTP.
    driver["STREAM"]["new_path"](args.workspace).mkdir(mode=0o700)
    write(args.workspace / "started.json", {"source_commit": before["commit"], "limits": LIMITS})
    write(args.workspace / "source-before.json", before)
    descriptor = os.open(args.workspace.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    manifest = fixtures(args.workspace)
    api.initialize_state(state_dir=args.workspace / "state")
    guard = PilotGuard()
    receipt: dict[str, Any] = {
        "schema_version": 1,
        "outcome": "incomplete",
        "source_commit": before["commit"],
    }
    previous = os.environ.get("PILOT_PLATFORM_KEY")
    try:
        os.environ["PILOT_PLATFORM_KEY"] = value
        with guard.install():
            owner = select_owner(args.project, secret, manifest)
            flow(args, manifest, owner, profile)
        worker["provenance"](expected, Path(sys.prefix))
        after = driver["EVIDENCE"]["source"](ROOT)
        write(args.workspace / "source-after.json", after)
        if before != after:
            raise ValueError("pilot source changed during acceptance")
        if (
            driver["WHEEL"]["snapshot"](args.wheel, after["source_sha256"], locked["yorunge"])
            != wheel
        ):
            raise ValueError("pilot wheel changed during acceptance")
        snapshot = guard.snapshot()
        if snapshot["open_reservations"] or snapshot["response_pending"]:
            raise ValueError("pilot left a live HTTP reservation")
        if snapshot["actual"]["upload_bytes"] != manifest.total_bytes:
            raise ValueError("pilot upload counter differs from original synthetic files")
        receipt.update(
            outcome="metadata_succeeded",
            authority_verified=False,
            pricing_verified=False,
            remote_bytes_verified=False,
            same_hash_different_names=True,
            complete_accepted_graph=True,
        )
    except YorungeError as error:
        receipt["error_code"] = error.code
        if isinstance(error, OperationError):
            write(args.workspace / "uncertain-identity.json", {"operation_id": error.operation_id})
        raise
    finally:
        if previous is None:
            os.environ.pop("PILOT_PLATFORM_KEY", None)
        else:
            os.environ["PILOT_PLATFORM_KEY"] = previous
        receipt.update(counters=guard.snapshot(), fixture_bytes=manifest.total_bytes)
        write(args.workspace / "receipt.json", receipt)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("config", "credentials", "workspace", "wheel"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--accept-live-unpriced-write", action="store_true")
    args = parser.parse_args()
    try:
        result = run(args)
    except BaseException:
        # Do not render private provider/credential exceptions or tracebacks.
        result = None
    if result is None:
        print(
            "Pilot stopped. Preserve the workspace; inspect the same operation locally.",
            file=sys.stderr,
        )
        return 1
    print("Pilot completed: metadata only; authority, pricing and remote bytes remain unverified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
