"""Owned network composition is rejected before a local state or credential boundary."""

from uuid import uuid4

import pytest

from yorunge import api
from yorunge.domain.errors import YorungeError


@pytest.mark.parametrize("which", ["backend", "observer"])
def test_session_port_preflight_runs_before_budget_state_or_credential_access(monkeypatch, which):
    called = []

    class Rejected:
        def preflight(self):
            called.append(which)
            raise YorungeError("invalid_request")

    def forbidden():
        pytest.fail("invalid owned context reached a use-case/IO boundary")

    monkeypatch.setattr(api, "_execution_budget", forbidden)
    context = api._operation_session(
        str(uuid4()),
        Rejected() if which == "backend" else object(),
        observer=Rejected() if which == "observer" else None,
    )
    with pytest.raises(YorungeError) as caught:
        with context:
            pytest.fail("rejected composition entered")
    assert caught.value.code == "invalid_request"
    assert called == [which]
