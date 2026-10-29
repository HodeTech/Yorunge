"""Offline, test-only subprocess effect; never registered by the product."""

import os
import subprocess
import sys
from pathlib import Path

from yorunge.application.operations import Submission


class ProcessBackend:
    def __init__(self, marker: Path, *, mode="accepted", before=None):
        self.marker, self.mode, self.before = marker, mode, before
        self.calls = 0
        self.deadline = None

    def start(self, request, *, deadline):
        self.calls += 1
        self.deadline = deadline
        if self.before:
            self.before(request, deadline)
        if self.mode == "not_sent":
            raise ConnectionRefusedError("synthetic private transport detail")
        subprocess.run(
            [
                sys.executable,
                "-c",
                "import os,sys; f=open(sys.argv[1],'ab'); "
                "f.write((sys.argv[2]+'\\n').encode()); f.flush(); os.fsync(f.fileno()); f.close()",
                str(self.marker),
                request.attempt_id,
            ],
            check=True,
            timeout=5,
        )
        if self.mode == "lost_reply":
            raise TimeoutError("synthetic private transport detail")
        if self.mode == "kill_after_effect":
            import signal

            os.kill(os.getpid(), signal.SIGKILL)
        return Submission(
            correlation=request.admission.correlation,
            authority=request.admission.authorities[0],
            provider_run_id="fixture-run-1",
            provider_status="queued",
            running=False,
        )

    def effects(self):
        return self.marker.read_text().splitlines() if self.marker.exists() else []


class ReadObserver:
    def __init__(self, clock, *, marker=None):
        self.clock = clock
        self.marker = marker
        self.kind, self.execution, self.delivery = "observed", "succeeded", "complete"
        self.change = self.access_change = None
        self.requests = []

    def authorize(self, request, *, deadline):
        from datetime import timedelta

        from yorunge.application.operation_observations import ReadAccess
        from yorunge.domain.capabilities import AuthorizationScope, timestamp

        assert deadline > self.clock.monotonic()
        access = ReadAccess(
            authorities=tuple(
                authority.model_copy(
                    update={
                        "authorization_scope": AuthorizationScope(
                            permissions=("read",), resources=()
                        )
                        if authority.service_id != "local"
                        else None,
                    }
                )
                for authority in request.authorities
            ),
            checked_at=timestamp(self.clock.now()),
            expires_at=timestamp(self.clock.now() + timedelta(seconds=60)),
        )
        return self.access_change(access) if self.access_change else access

    def observe(self, request, access, *, deadline):
        from yorunge.application.operation_observations import OperationObservation

        assert deadline > self.clock.monotonic()
        self.requests.append(request)
        if self.marker is not None:
            assert request.attempt_id in self.marker.read_text().splitlines()
        result = OperationObservation(
            kind=self.kind,
            correlation=request.admission.correlation,
            authority=access.authorities[0],
            provider_run_id=request.provider_run_id or "fixture-run-1",
            provider_status="complete",
            provider_exit_code=0,
            execution_status=self.execution,
            delivery_status=self.delivery,
        )
        return self.change(result) if self.change else result
