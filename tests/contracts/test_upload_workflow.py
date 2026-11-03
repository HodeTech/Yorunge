"""Scheduler boundary: an observed worker failure must prevent the next arm."""

import asyncio

import pytest

from yorunge.application.upload_workflow import _put_batch


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

        with pytest.raises(ValueError, match="first PUT failed"):
            await _put_batch(Environment(), range(2))
        assert events == [("prepare", 0), ("arm", 0), ("execute", 0), ("close", 0)]

    asyncio.run(run())
