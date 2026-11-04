"""Scheduler boundary: an observed worker failure must prevent the next arm."""

import asyncio
from functools import partial

import pytest

from yorunge.application.upload_workflow import _drain, _put_batch


class Batch:
    def __init__(self):
        self.currents, self.arms, self.published, self.closed = 0, [], [], []
        self.publish_error, self.close_error = None, None

    async def current(self, kind):
        self.currents += 1
        if self.currents == 2:
            await self.before_second()

    async def before_second(self):
        pass

    def prepare(self, kind, index):
        batch = self

        class Call:
            async def execute(self, arm):
                return await batch.execute(index)

            async def aclose(self):
                batch.closed.append(index)
                if index == 0 and batch.close_error is not None:
                    raise batch.close_error

        return Call()

    def arm(self, check, kind, index):
        self.arms.append(index)

    async def execute(self, index):
        return index

    def publish(self, outcome):
        self.published.append(outcome)
        if outcome == 0 and self.publish_error is not None:
            raise self.publish_error


@pytest.mark.parametrize("failing_index", [0, 1])
def test_simultaneous_success_is_published_before_sibling_failure(failing_index):
    async def run():
        batch = Batch()
        failure = RuntimeError("PUT failed")

        async def finished(index):
            if index == failing_index:
                raise failure
            return index

        tasks = [asyncio.create_task(finished(index)) for index in range(2)]
        await asyncio.gather(*tasks, return_exceptions=True)
        with pytest.raises(RuntimeError) as raised:
            await _drain(batch, tasks)
        assert raised.value is failure
        assert batch.published == [1 - failing_index]

    asyncio.run(run())


@pytest.mark.parametrize("boundary", ["current", "prepare", "arm"])
def test_already_completed_put_is_published_if_next_stage_cannot_arm(boundary):
    async def run():
        first_done = asyncio.Event()
        failure = RuntimeError("next boundary failed")

        class Stopped(Batch):
            async def before_second(self):
                await first_done.wait()
                if boundary == "current":
                    raise failure

            async def execute(self, index):
                first_done.set()
                return index

            def prepare(self, kind, index):
                if index == 1 and boundary == "prepare":
                    raise failure
                return super().prepare(kind, index)

            def arm(self, check, kind, index):
                if index == 1 and boundary == "arm":
                    raise failure
                super().arm(check, kind, index)

        batch = Stopped()
        with pytest.raises(RuntimeError) as raised:
            await _put_batch(batch, range(2))
        assert raised.value is failure
        assert batch.published == [0]
        assert batch.arms == [0]
        assert batch.closed == ([0, 1] if boundary == "arm" else [0])

    asyncio.run(run())


def test_publish_reply_loss_is_not_retried_and_other_receipt_still_has_one_attempt():
    async def run():
        batch = Batch()
        batch.publish_error = RuntimeError("receipt committed but reply lost")
        batch.close_error = ValueError("secondary close failed")
        with pytest.raises(RuntimeError) as raised:
            await _put_batch(batch, range(2))
        assert raised.value is batch.publish_error
        assert batch.published == [0, 1]
        assert batch.arms == [0, 1]
        assert batch.closed == [0, 1]

    asyncio.run(run())


def test_cancelled_pending_worker_can_return_a_validated_response_during_cleanup():
    async def run():
        first_entered = asyncio.Event()
        failure = RuntimeError("sibling PUT failed")

        class Completing(Batch):
            async def execute(self, index):
                if index == 1:
                    await first_entered.wait()
                    raise failure
                first_entered.set()
                try:
                    await asyncio.Event().wait()
                except asyncio.CancelledError:
                    return index

        batch = Completing()
        with pytest.raises(RuntimeError) as raised:
            await _put_batch(batch, range(2))
        assert raised.value is failure
        assert batch.published == [0]
        assert batch.closed == [0, 1]

    asyncio.run(run())


def test_actual_owner_cancellation_survives_publication_and_close_failures():
    async def run():
        both_entered = asyncio.Event()
        entered = []

        class Cancelling(Batch):
            async def execute(self, index):
                entered.append(index)
                if len(entered) == 2:
                    both_entered.set()
                try:
                    await asyncio.Event().wait()
                except asyncio.CancelledError:
                    if index == 0:
                        return index
                    raise

        batch = Cancelling()
        batch.publish_error = RuntimeError("receipt lost")
        batch.close_error = ValueError("close failed")
        owner = asyncio.create_task(_put_batch(batch, range(2)))
        await both_entered.wait()
        owner.cancel("operator stop")
        with pytest.raises(asyncio.CancelledError) as raised:
            await owner
        assert raised.value.args == ("operator stop",)
        assert batch.published == [0]
        assert batch.closed == [0, 1]
        assert owner.cancelled()

    asyncio.run(run())


def test_owner_cancel_during_error_cleanup_takes_priority_and_keeps_returned_response():
    async def run():
        cleanup_entered = asyncio.Event()

        class Finishing(Batch):
            async def execute(self, index):
                if index == 1:
                    raise RuntimeError("worker failed first")
                try:
                    await asyncio.Event().wait()
                except asyncio.CancelledError:
                    cleanup_entered.set()
                    try:
                        await asyncio.Event().wait()
                    except asyncio.CancelledError:
                        return index

        batch = Finishing()
        owner = asyncio.create_task(_put_batch(batch, range(2)))
        await cleanup_entered.wait()
        owner.cancel("stop during cleanup")
        with pytest.raises(asyncio.CancelledError):
            await owner
        # gather can discard cancel()'s optional message when its final child
        # consumes cancellation; the public contract is the exception type.
        assert owner.cancelled()
        assert batch.published == [0]
        assert batch.closed == [0, 1]

    asyncio.run(run())


def test_worker_failure_during_next_current_prevents_second_arm():
    async def run():
        failed, events = asyncio.Event(), []

        class Call:
            def __init__(self, index):
                self.index = index

            async def execute(self, arm):
                events.append(("execute", self.index))
                if self.index == 0:
                    failed.set()
                    raise ValueError("first PUT failed")

            async def aclose(self):
                events.append(("close", self.index))

        class Environment:
            currents = 0

            async def current(self, kind):
                self.currents += 1
                if self.currents == 2:
                    await failed.wait()

            def prepare(self, kind, index):
                events.append(("prepare", index))
                return Call(index)

            def arm(self, check, kind, index):
                events.append(("arm", index))

            def publish(self, outcome):
                pytest.fail("failed batch published an outcome")

        rejected_call = partial(_put_batch, Environment(), range(2))
        with pytest.raises(ValueError, match="first PUT failed"):
            await rejected_call()
        assert events == [("prepare", 0), ("arm", 0), ("execute", 0), ("close", 0)]

    asyncio.run(run())
