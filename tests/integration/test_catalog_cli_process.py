"""The catalog commands as real processes: a closed output is an ordinary exit, not a traceback."""

import os
import subprocess
import sys

CLOSED_STDOUT = [
    sys.executable,
    "-c",
    "import os,sys; os.close(1); os.execv(sys.argv[1], sys.argv[1:])",
    sys.executable,
    "-m",
    "yorunge",
]


def test_a_closed_stdout_is_an_ordinary_error_exit_not_a_traceback(tmp_path):
    # A port other than the one the profile may use makes the profile invalid before any request,
    # so the command reaches its error report with nothing listening anywhere.
    config = tmp_path / "config.toml"
    config.write_text(
        'schema_version = 1\nactive_profile = "work"\n[profiles.work]\n'
        'platform_url = "https://localhost:9/api/v1"\nplatform_key_env = "EVREN_PLATFORM_API_KEY"\n'
    )
    environment = dict(os.environ, HOME=str(tmp_path))
    completed = subprocess.run(
        [*CLOSED_STDOUT, "models", "list", "--service", "evren-platform", "--config", str(config)],
        capture_output=True,
        env=environment,
        timeout=120,
    )
    assert completed.returncode == 2
    assert completed.stdout == b""  # the descriptor was closed: nothing was written to it
    assert b"Traceback" not in completed.stderr
    assert "Profil geçersiz".encode() in completed.stderr
