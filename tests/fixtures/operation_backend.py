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
