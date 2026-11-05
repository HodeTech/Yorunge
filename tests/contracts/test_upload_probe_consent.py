"""The two independent operator gates precede provenance, secrets, state and I/O."""

import runpy
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    "script,flag",
    [
        ("upload_live_acceptance.py", "accept_live_unpriced_write"),
        ("upload_owned_diagnostic.py", "accept_read_diagnostic"),
        ("upload_link_diagnostic.py", "accept_link_probe"),
        ("upload_storage_diagnostic.py", "accept_storage_probe"),
    ],
)
@pytest.mark.parametrize("isolated,consent", [(True, False), (False, True)])
def test_each_gate_rejects_independently_before_private_work(
    script, flag, isolated, consent, tmp_path, monkeypatch
):
    helper = runpy.run_path(str(ROOT / "scripts" / script))
    namespace = helper["run"].__globals__

    def forbidden(*args, **kwargs):
        raise AssertionError("operator gate reached private work")

    monkeypatch.setitem(namespace, "sys", SimpleNamespace(flags=SimpleNamespace(isolated=isolated)))
    monkeypatch.setitem(namespace, "runpy", SimpleNamespace(run_path=forbidden))
    for name in ("credential", "historical_context", "provider_uuid"):
        if name in namespace:
            monkeypatch.setitem(namespace, name, forbidden)
    args = SimpleNamespace(**{flag: consent}, workspace=tmp_path / "must-not-exist")
    with pytest.raises(ValueError, match="isolated.*(consent|authorization)"):
        helper["run"](args)
    assert not args.workspace.exists()
