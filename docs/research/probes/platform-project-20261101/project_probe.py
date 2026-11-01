"""Explicit, bounded selected-project acceptance; no resource mutation or value publication."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[4]
HELPER_PATH = Path(__file__).resolve().parents[1] / "platform-20261101/account_probe.py"
# Compile the same verified bytes, without Python module/bytecode cache reuse.
expected_helper_hash = json.loads(
    (ROOT / "docs/research/p02-platform-reverse-observations.json").read_text()
)["probe_sha256"]
helper_bytes = HELPER_PATH.read_bytes()
verified_helper_hash = hashlib.sha256(helper_bytes).hexdigest()
if verified_helper_hash != expected_helper_hash:
    raise SystemExit("Helper source mismatch; no account request made.")
helper = ModuleType("platform_probe_snapshot")
helper.__file__ = str(HELPER_PATH)
exec(compile(helper_bytes, str(HELPER_PATH), "exec"), helper.__dict__)
PREP = ROOT / ".local/p02-pilot"
INPUT = PREP / "project-acceptance-input-20261101.json"
OUTPUT = PREP / "platform-selected-project-20261101.json"


class ProjectBudget(helper.Budget):
    """Four product GETs, then one missing-key detail control; the total is shared."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.report["limits"].update(logical_gets=5, attempts=5)

    def begin(self, endpoint, path, mode):
        if len(self.report["calls"]) >= 5:
            raise helper.YorungeError("invalid_request")
        return super().begin(endpoint, path, mode)

    def attempt(self, request, secret):
        if self.report["attempts"] >= 5:
            raise helper.YorungeError("invalid_request")
        super().attempt(request, secret)


def execute() -> None:
    os.umask(0o077)
    if Path.cwd().resolve() != ROOT:
        raise SystemExit("Run from the repository root; no request made.")
    import yorunge

    if not Path(yorunge.__file__).resolve().is_relative_to(ROOT / "src/yorunge"):
        raise SystemExit("Unexpected product source origin; no request made.")
    info = PREP.lstat()
    if (
        not stat.S_ISDIR(info.st_mode)
        or info.st_uid != os.getuid()
        or stat.S_IMODE(info.st_mode) != 0o700
    ):
        raise SystemExit("Unsafe preparation directory; no request made.")
    with OUTPUT.open("x") as stream:
        stream.write('{"outcome":"reserved_before_preparation"}\n')
    started = time.monotonic()
    budget = None
    try:
        expected_helper = json.loads(
            (ROOT / "docs/research/p02-platform-reverse-observations.json").read_text()
        )["probe_sha256"]
        if (
            hashlib.sha256(HELPER_PATH.read_bytes()).hexdigest() != verified_helper_hash
            or expected_helper != verified_helper_hash
        ):
            raise helper.YorungeError("invalid_request")
        project = helper.ID.validate_python(helper.private_json(INPUT)["project_id"], strict=True)
        values = helper.private_json(PREP / "credentials.json")
        secret = helper.SecretValue(values["PILOT_PLATFORM_KEY"])
        del values
        config = helper.tomllib.loads(
            helper.private_bytes(PREP / "config.toml").decode("utf-8", "strict")
        )
        profile = config["profiles"]["pilot"]
        target = helper.normalize_target(helper.ORIGIN + helper.BASE)
        if (
            helper.normalize_target(profile.get("platform_url", helper.ORIGIN + helper.BASE))
            != target
            or profile.get("platform_key_env") != "PILOT_PLATFORM_KEY"
        ):
            raise helper.YorungeError("invalid_service_target")
        paths = frozenset(
            helper.BASE + "/" + p
            for p in ("auth/me", "organizations", "projects", "projects/" + project)
        )
        budget = ProjectBudget(end=started + 30, output=OUTPUT, allowed_paths=paths)
        budget.report.update(
            purpose="selected_project_read_only_acceptance",
            started_at_utc=datetime.now(UTC).isoformat(),
            source_commit=subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
            ).strip(),
            probe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            shared_helper_sha256=verified_helper_hash,
        )
        names = helper.known_names()
        original_read = helper.platform_context.PlatformReader._read
        original_session = helper.platform_context.HttpSession
        previous_env = os.environ.get("PILOT_PLATFORM_KEY")

        async def observed(transport, snapshot, path, deadline, *, detail):
            if snapshot.context.project_id != project:
                raise helper.YorungeError("state_changed")
            row = budget.begin(helper.endpoint_name(path), helper.BASE + "/" + path, "selected_key")
            try:
                data = await original_read(
                    transport, snapshot, path, min(deadline, budget.end - 1), detail=detail
                )
                if data is not None:
                    kind = {
                        "auth/me": "me",
                        "organizations": "organizations",
                        "projects": "projects",
                    }.get(path, "detail")
                    raw = helper.projection.safe_raw(data, kind, secret)
                    row["schema_observation"] = helper.shape(raw, names)
                    row["predicates"] = helper.predicates(raw, kind, project if detail else None)
                else:
                    row["detail_not_found"] = True
                return data
            finally:
                budget.end_call()
                budget.persist()

        def owned():
            return helper.HttpSession(
                transport_factory=lambda: helper.SingleAttempt(
                    transport=helper.CountedWire(budget, secret)
                )
            )

        try:
            helper.platform_context.PlatformReader._read = staticmethod(observed)
            helper.platform_context.HttpSession = owned
            os.environ["PILOT_PLATFORM_KEY"] = secret.reveal()
            result = helper.api.discover_context(
                "evren-platform",
                config=PREP / "config.toml",
                profile="pilot",
                project=project,
                state_dir=PREP / "state",
            )
            from yorunge.domain.platform_discovery import PlatformContextDiscovery

            data = result.data
            selection = data.projects.selection
            checks = {
                "typed_result_returned": isinstance(data, PlatformContextDiscovery),
                "four_endpoint_observations": len(data.observations) == 4,
                "selected_id_matches_input": data.selected.project_id == project,
                "detail_observed": selection.state == "observed",
                "detail_id_matches_input": selection.project is not None
                and selection.project.id == project,
                "project_list_nonempty": bool(data.projects.items),
                "selected_project_in_listing": any(p.id == project for p in data.projects.items),
                "public_validation_unverified": data.validation == "unverified",
                "no_authorization_scope": data.authorization_scope is None,
                "provider_identity_unverified": data.provider.identity_status == "unverified",
                "provider_authority_ids_null": all(
                    getattr(data.provider, name) is None
                    for name in ("principal_id", "account_id", "organization_id", "project_id")
                ),
                "all_endpoint_auth_unknown": all(
                    v.authentication == "unknown" for v in data.observations
                ),
                "consistency_not_guaranteed": data.consistency == "not_guaranteed",
            }
            budget.report["product_acceptance"] = checks
            budget.report["project_count"] = len(data.projects.items)
        finally:
            helper.platform_context.PlatformReader._read = staticmethod(original_read)
            helper.platform_context.HttpSession = original_session
            if previous_env is None:
                os.environ.pop("PILOT_PLATFORM_KEY", None)
            else:
                os.environ["PILOT_PLATFORM_KEY"] = previous_env

        if all(checks.values()):
            # Only the newly exercised endpoint needs a missing-key observation.
            async def missing_key(transport):
                path = "projects/" + project
                row = budget.begin("platform_project_detail", helper.BASE + "/" + path, "no_key")
                try:
                    request = helper.HttpRequest(
                        target,
                        "GET",
                        path,
                        service_id="evren-platform",
                        read_only=False,
                        max_bytes=1048576,
                    )
                    try:
                        async with transport.open(request, deadline=budget.end - 1) as response:
                            content = bytearray()
                            async for chunk in response.chunks():
                                if len(content) + len(chunk) > 1048576:
                                    raise helper.YorungeError("invalid_response")
                                content.extend(chunk)
                        raw = helper.projection.safe_raw(bytes(content), "detail", secret)
                        row["schema_observation"] = helper.shape(raw, names)
                        row["missing_key_rejected"] = False
                    except helper.HttpStatusFailure as error:
                        row["missing_key_rejected"] = error.status_code in (401, 403)
                        if error.status_code not in (401, 403, 404):
                            raise
                finally:
                    budget.end_call()
                    budget.persist()

            with owned() as session:
                session.call(missing_key)
            if time.monotonic() >= budget.end:
                raise helper.YorungeError("transport_timeout")
            budget.report["outcome"] = "selected_project_observation_accepted"
        else:
            budget.report["outcome"] = "acceptance_predicate_failed"
    except helper.YorungeError as error:
        if budget is not None:
            budget.report.update(outcome="stopped_controlled", code=error.code)
    except Exception as error:
        if budget is not None:
            budget.report.update(
                outcome="preparation_or_analysis_failure", exception_class=type(error).__name__
            )
    finally:
        if budget is not None:
            budget.report["elapsed_seconds"] = round(time.monotonic() - started, 6)
            budget.persist()
            print(
                json.dumps(
                    {
                        k: budget.report[k]
                        for k in (
                            "outcome",
                            "attempts",
                            "body_bytes",
                            "elapsed_seconds",
                            "product_acceptance",
                            "project_count",
                        )
                        if k in budget.report
                    }
                )
            )
        else:
            print('{"outcome":"preparation_failed_before_network"}')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Run the separately authorized read-only acceptance once",
    )
    args = parser.parse_args()
    if not args.execute:
        parser.error("explicit --execute required; no request made")
    execute()


if __name__ == "__main__":
    main()
