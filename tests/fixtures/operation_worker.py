"""Real process-death and credential-rotation boundaries for offline tests only."""

import os
import signal
import sys
import time
from pathlib import Path

from tests.conftest import execution_validator_fixture
from tests.fixtures.operation_backend import ProcessBackend
from yorunge import api
from yorunge.adapters import capability_cache, operation_repository
from yorunge.domain.capabilities import instant


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
    elif point == "receipt_after":
        cut("submitted", "after")
    elif point in {"admit_mid", "arm_mid", "receipt_mid"}:
        name = "insert_record" if point == "admit_mid" else "append_event"
        original = getattr(operation_repository, name)

        def mid(*args):
            original(*args)
            if point != "receipt_mid" or args[-1].sequence == 3:
                kill()

        setattr(operation_repository, name, mid)
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
    with api._operation_session(plan_id, backend, state_dir=Path(state)) as coordinator:
        claim = coordinator.admit(plan_id)
        if claim.ownership is not None:
            coordinator.dispatch(claim.job.operation.operation_id, claim.ownership)


if __name__ == "__main__":
    main()
