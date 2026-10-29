"""Real process-death and credential-rotation boundaries for offline tests only."""

import json
import os
import signal
import sys
import time
from pathlib import Path

from tests.conftest import execution_validator_fixture
from tests.fixtures.operation_backend import ProcessBackend, ReadObserver
from yorunge import api
from yorunge.adapters import capability_cache, operation_repository
from yorunge.domain.capabilities import instant
from yorunge.domain.errors import YorungeError


def main():
    point, state, plan_id, marker, now, *extra = sys.argv[1:]

    def wait(path):
        end = time.monotonic() + 8
        while not Path(path).exists():
            if time.monotonic() > end:
                raise TimeoutError("test process barrier timed out")
            time.sleep(0.005)

    class Clock:
        def now(self):
            return instant(Path(extra[2]).read_text()) if point == "paused" else instant(now)

        def monotonic(self):
            return time.monotonic()

    capability_cache.SystemClock = Clock
    api._execution_validator = execution_validator_fixture
    if point == "rotate":
        config, service = extra
        name = "EVREN_LLM_API_KEY" if service == "evren-llm" else "EVREN_PLATFORM_API_KEY"
        os.environ[name] = "changed-synthetic-credential"
        api.observe_credential(service, config=Path(config), state_dir=Path(state))
        return
    if point in {"forget", "revoke", "reset"}:
        try:
            if point == "forget":
                api.forget_execution_plan(plan_id, extra[0], state_dir=Path(state))
            elif point == "revoke":
                api.revoke_execution_approval(plan_id, state_dir=Path(state))
            else:
                api.reset_identity(extra[0], state_dir=Path(state))
            code = "ok"
        except YorungeError as error:
            code = error.code
        print(json.dumps({"code": code}))
        return

    def kill():
        os.kill(os.getpid(), signal.SIGKILL)

    def cut(name, timing):
        original = getattr(operation_repository.StateOperations, name)

        def wrapped(self, *args):
            if timing == "before":
                kill()
            result = original(self, *args)
            kill()
            return result

        setattr(operation_repository.StateOperations, name, wrapped)

    if point in {"admit_before", "admit_after", "arm_before", "arm_after"}:
        name, timing = point.split("_")
        cut(name, timing)
    elif point == "fork_after_arm":
        original_arm = operation_repository.StateOperations.arm

        def fork_after_arm(self, *args):
            record = original_arm(self, *args)
            pid = os.fork()
            if pid:
                os.waitpid(pid, 0)
            return record

        operation_repository.StateOperations.arm = fork_after_arm
    elif point == "receipt_after":
        cut("submitted", "after")
    elif point in {"outcome_before", "outcome_after"}:
        cut("reconcile", point.split("_")[1])
    elif point == "outcome_mid":
        original_outcome = operation_repository.write_outcome

        def outcome_mid(*args):
            original_outcome(*args)
            kill()

        operation_repository.write_outcome = outcome_mid
    elif point in {"admit_mid", "arm_mid", "receipt_mid"}:
        name = "insert_record" if point == "admit_mid" else "append_event"
        original = getattr(operation_repository, name)

        def mid(*args):
            original(*args)
            if point != "receipt_mid" or args[-1].sequence == 3:
                kill()

        setattr(operation_repository, name, mid)
    if point.startswith("reset_"):
        from yorunge.adapters import maintenance, operation_maintenance

        if point.endswith("mid"):
            original_reset_write = operation_maintenance.write_record

            def reset_mid(*args, **kwargs):
                original_reset_write(*args, **kwargs)
                kill()

            operation_maintenance.write_record = reset_mid
        else:
            original_reset = maintenance._reset_current

            def reset_after(*args):
                result = original_reset(*args)
                kill()
                return result

            maintenance._reset_current = reset_after
    backend = ProcessBackend(
        Path(marker), mode=point if point == "kill_after_effect" else "accepted"
    )
    if point in {"contend", "paused"}:
        ready, release = extra[:2]

        def barrier(*args):
            Path(ready).write_text("ready")
            wait(release)

        if point == "paused":
            backend.before = barrier
        else:
            original_admit = operation_repository.StateOperations.admit

            def admit(self, *args):
                barrier()
                return original_admit(self, *args)

            operation_repository.StateOperations.admit = admit
    observer = ReadObserver(Clock(), marker=backend.marker)
    with api._operation_session(
        plan_id, backend, observer=observer, state_dir=Path(state)
    ) as coordinator:
        claim = coordinator.admit(plan_id)
        if claim.ownership is not None and not point.startswith("reset_unarmed_"):
            coordinator.dispatch(claim.job.operation.operation_id, claim.ownership)
        if point.startswith("outcome_"):
            coordinator.reconcile(claim.job.operation.operation_id, claim.ownership)
    if point.startswith("reset_"):
        preview = api.preview_identity_reset(state_dir=Path(state)).data
        api.reset_identity(preview.digest, state_dir=Path(state))


if __name__ == "__main__":
    main()
