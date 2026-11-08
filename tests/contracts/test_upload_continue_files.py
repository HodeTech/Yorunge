"""The coordinator of a continuation's files, over a recording environment: what is asked, in what
order, and what stops it. No store, no network: the environment records every call it is given."""

import asyncio
from dataclasses import dataclass
from pathlib import Path

import pytest

from yorunge.application.upload_workflow import continue_files
from yorunge.domain.dataset_continuation import DatasetContinuationPlanV3
from yorunge.domain.errors import OperationError, YorungeError

FIXTURES = Path(__file__).parents[1] / "fixtures"


def plan_of(name):
    return DatasetContinuationPlanV3.model_validate_json((FIXTURES / name).read_bytes())


SELECTED = plan_of("dataset-continuation-plan-v3.json")  # files 0 and 2 of three
EVERY_FILE = plan_of("dataset-continuation-plan-v3-all-files.json")  # 0, 1 and 2
NO_FILE = plan_of("dataset-continuation-plan-v3-verification-only.json")  # check only


@dataclass
class Outcome:
    kind: str
    index: int | None
    upload: object = None
    receipt: object = None


class Effect:
    def __init__(self, environment, kind, index):
        self.environment, self.kind, self.index = environment, kind, index

    async def execute(self, arm):
        self.environment.calls.append(("execute", self.kind, self.index))
        await asyncio.sleep(0)
        if (self.kind, self.index) == self.environment.break_at:
            raise self.environment.error
        return Outcome(self.kind, self.index)

    async def aclose(self):
        self.environment.calls.append(("close", self.kind, self.index))


class Environment:
    """Records the calls of the coordinator; ``break_at`` makes one effect raise ``error``."""

    def __init__(self, plan, *, owned=True, break_at=None, error=None, slow_current=False):
        self.plan, self.owned, self.break_at, self.error = plan, owned, break_at, error
        self.slow_current = slow_current
        self.record = object()
        self.calls = []

    @property
    def write_owned(self):
        return self.owned

    async def current(self, kind):
        self.calls.append(("current", kind))
        if self.slow_current:
            await asyncio.sleep(0.02)  # long enough for a worker started before to have failed
        return object()

    def prepare(self, kind, index=None):
        self.calls.append(("prepare", kind, index))
        return Effect(self, kind, index)

    def arm(self, check, kind, index=None):
        self.calls.append(("arm", kind, index))
        return object()

    def publish(self, outcome):
        self.calls.append(("publish", outcome.kind, outcome.index))

    def validate_uploads(self):
        self.calls.append(("validate",))

    def admit(self, check):
        raise AssertionError("the coordinator never admits")

    def failure(self, error):
        self.calls.append(("failure", type(error).__name__))
        return None

    def names(self, name):
        return [call[1:] for call in self.calls if call[0] == name]


def run(environment):
    return asyncio.run(continue_files(environment))


def test_a_continuation_that_sends_nothing_asks_for_nothing():
    environment = Environment(NO_FILE)
    assert run(environment) is environment.record
    assert environment.calls == []


def test_a_continuation_that_was_never_admitted_is_a_conflict_not_an_assertion():
    environment = Environment(SELECTED)
    environment.record = None
    with pytest.raises(YorungeError) as error:
        run(environment)
    assert error.value.code == "operation_conflict"
    assert [call[0] for call in environment.calls] == ["failure"]  # and nothing was asked


def test_a_process_that_does_not_own_the_operation_asks_for_nothing():
    environment = Environment(SELECTED, owned=False)
    assert run(environment) is environment.record
    assert environment.calls == []


def test_the_selected_files_are_presigned_in_order_then_put_together_and_confirmed_in_order():
    environment = Environment(SELECTED)
    run(environment)
    assert environment.names("arm") == [
        ("presign", 0),
        ("presign", 2),
        ("put", 0),
        ("put", 2),
        ("confirm", 0),
        ("confirm", 2),
    ]
    # Every file's three stages once and no create or link, whatever the check asked for.
    assert environment.names("prepare") == environment.names("arm")
    assert {call[1] for call in environment.calls if call[0] == "current"} == {
        "presign",
        "put",
        "confirm",
    }
    # All the presigns, then the uploads are validated, then the first put.
    order = [call[0] if call[0] != "arm" else call[1] for call in environment.calls]
    assert order.index("validate") > max(i for i, c in enumerate(order) if c == "presign")
    assert order.index("validate") < order.index("put")
    assert environment.calls.count(("validate",)) == 1


def test_two_files_are_put_at_once_and_the_third_waits_for_their_confirms():
    environment = Environment(EVERY_FILE)
    run(environment)
    arms = environment.names("arm")
    assert arms[:3] == [("presign", 0), ("presign", 1), ("presign", 2)]
    # The first batch: both puts armed before either confirm; its confirms before the next put.
    assert arms[3:5] == [("put", 0), ("put", 1)]
    assert arms[5:7] == [("confirm", 0), ("confirm", 1)]
    assert arms[7:] == [("put", 2), ("confirm", 2)]


def test_every_effect_is_released_whether_it_succeeded_or_not():
    environment = Environment(EVERY_FILE)
    run(environment)
    assert sorted(environment.names("close")) == sorted(environment.names("prepare"))


def test_a_presign_that_fails_stops_the_continuation_before_anything_else_is_armed():
    boom = OperationError("operation_uncertain", "00000000-0000-4000-8000-000000000001")
    environment = Environment(EVERY_FILE, break_at=("presign", 1), error=boom)
    with pytest.raises(OperationError) as error:
        run(environment)
    assert error.type is type(boom)
    assert environment.names("arm") == [("presign", 0), ("presign", 1)]
    assert environment.names("failure") == [("OperationError",)]


def test_a_put_that_fails_stops_the_batch_before_the_other_worker_is_armed():
    boom = OperationError("operation_uncertain", "00000000-0000-4000-8000-000000000001")
    environment = Environment(EVERY_FILE, break_at=("put", 0), error=boom, slow_current=True)
    with pytest.raises(OperationError):
        run(environment)
    arms = environment.names("arm")
    assert ("put", 0) in arms
    assert ("put", 1) not in arms  # no second permit after the failure
    assert not any(kind == "confirm" for kind, _ in arms)


def test_a_confirm_that_fails_stops_the_confirms_after_it():
    boom = OperationError("operation_uncertain", "00000000-0000-4000-8000-000000000001")
    environment = Environment(EVERY_FILE, break_at=("confirm", 0), error=boom)
    with pytest.raises(OperationError):
        run(environment)
    arms = environment.names("arm")
    assert ("confirm", 0) in arms
    assert ("confirm", 1) not in arms
    assert ("put", 2) not in arms


def test_an_environment_that_has_nothing_to_say_of_a_failure_lets_it_through_unchanged():
    boom = RuntimeError("not an operation's error")
    environment = Environment(SELECTED, break_at=("presign", 0), error=boom)
    with pytest.raises(RuntimeError) as error:
        run(environment)
    assert error.value is boom


def test_a_cancelled_continuation_tells_the_environment_and_stays_cancelled():
    environment = Environment(SELECTED, break_at=("presign", 0), error=asyncio.CancelledError())
    with pytest.raises(asyncio.CancelledError):
        run(environment)
    assert environment.names("failure") == [("CancelledError",)]
