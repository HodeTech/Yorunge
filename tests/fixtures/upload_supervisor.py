"""Keep the owned process-group leader until the CI parent closes its control socket."""

from __future__ import annotations

import argparse
import os
import select
import signal
import socket
import subprocess


def parent_closed(control):
    ready, _, _ = select.select([control], [], [], 0.05)
    if ready and control.recv(1) == b"":
        # This process created the session; never signal a caller's group.
        os.killpg(os.getpgrp(), signal.SIGKILL)


def supervise(control, command):
    if os.getpid() != os.getpgrp() or os.getsid(0) != os.getpid():
        raise ValueError("upload supervisor must own its session")
    process = subprocess.Popen(command, stdin=subprocess.DEVNULL, close_fds=True)
    try:
        while True:
            parent_closed(control)
            code = process.poll()
            if code is not None:
                control.sendall(f"{code}\n".encode("ascii"))
                break
        # Remain an unreaped group leader, even after controller failure. The
        # parent can now kill this exact group without a PID-reuse window.
        while True:
            parent_closed(control)
    finally:
        # Any supervisor error must also stop its own descendants.
        os.killpg(os.getpgrp(), signal.SIGKILL)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--control-fd", required=True, type=int)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        parser.error("controller command required")
    with socket.socket(fileno=args.control_fd) as control:
        supervise(control, command)


if __name__ == "__main__":
    main()
