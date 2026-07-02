"""Unit tests for module.core.scheduler (PeriodicTask, Scheduler)."""

import asyncio
from unittest.mock import MagicMock

from module.core.scheduler import PeriodicTask, Scheduler

# ---------------------------------------------------------------------------
# PeriodicTask
# ---------------------------------------------------------------------------


class TestPeriodicTask:
    async def test_start_runs_body_then_stop(self):
        """start() ticks the body repeatedly; stop() halts it."""
        counter = {"n": 0}

        async def body():
            counter["n"] += 1

        task = PeriodicTask("t", run=body, interval=lambda: 0.01)
        task.start()
        assert task.running is True
        await asyncio.sleep(0.05)
        await task.stop()

        assert task.running is False
        assert counter["n"] >= 2

    async def test_stop_is_idempotent(self):
        """Calling stop() twice (or before start) does not raise."""
        task = PeriodicTask("t", run=lambda: asyncio.sleep(0), interval=lambda: 0.01)
        await task.stop()  # never started
        task.start()
        await task.stop()
        await task.stop()  # already stopped
        assert task.running is False

    async def test_exception_in_body_does_not_kill_loop(self):
        """A raising tick is logged and the loop keeps running."""
        counter = {"n": 0}

        async def body():
            counter["n"] += 1
            raise RuntimeError("boom")

        task = PeriodicTask("t", run=body, interval=lambda: 0.01)
        task.start()
        await asyncio.sleep(0.05)
        assert task.running is True  # still alive despite exceptions
        await task.stop()
        assert counter["n"] >= 2

    async def test_interval_read_live_each_tick(self):
        """interval() is invoked on every wait, so settings are read live."""
        interval = MagicMock(return_value=0.01)

        async def body():
            pass

        task = PeriodicTask("t", run=body, interval=interval)
        task.start()
        await asyncio.sleep(0.05)
        await task.stop()
        assert interval.call_count >= 2

    async def test_initial_delay_defers_first_tick(self):
        """With initial_delay set, the body does not run before the delay."""
        counter = {"n": 0}

        async def body():
            counter["n"] += 1

        task = PeriodicTask("t", run=body, interval=lambda: 0.01, initial_delay=10.0)
        task.start()
        await asyncio.sleep(0.03)
        # Still inside the initial delay window -> body has not run yet.
        assert counter["n"] == 0
        await task.stop()  # stop cleanly during the initial delay
        assert counter["n"] == 0

    async def test_initial_delay_then_runs(self):
        """After a short initial delay the body starts ticking."""
        counter = {"n": 0}

        async def body():
            counter["n"] += 1

        task = PeriodicTask("t", run=body, interval=lambda: 0.01, initial_delay=0.01)
        task.start()
        await asyncio.sleep(0.05)
        await task.stop()
        assert counter["n"] >= 1

    async def test_start_is_idempotent_no_double_task(self):
        """start() while already running does not spawn a second task."""

        async def body():
            await asyncio.sleep(0)

        task = PeriodicTask("t", run=body, interval=lambda: 0.01)
        task.start()
        first = task._task
        task.start()
        assert task._task is first
        await task.stop()

    async def test_enabled_reflects_callable(self):
        """enabled property proxies the provided callable."""
        flag = {"on": False}
        task = PeriodicTask(
            "t",
            run=lambda: asyncio.sleep(0),
            interval=lambda: 0.01,
            enabled=lambda: flag["on"],
        )
        assert task.enabled is False
        flag["on"] = True
        assert task.enabled is True


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------


class TestScheduler:
    async def test_start_all_only_enabled(self):
        """start_all starts enabled tasks and skips disabled ones."""

        async def body():
            await asyncio.sleep(0)

        enabled = PeriodicTask("on", run=body, interval=lambda: 0.01)
        disabled = PeriodicTask(
            "off", run=body, interval=lambda: 0.01, enabled=lambda: False
        )
        scheduler = Scheduler([enabled, disabled])

        scheduler.start_all()
        assert scheduler.running is True
        assert enabled.running is True
        assert disabled.running is False

        await scheduler.stop_all()

    async def test_stop_all_halts_and_clears_running(self):
        """stop_all stops every task and flips running to False."""

        async def body():
            await asyncio.sleep(0)

        t1 = PeriodicTask("a", run=body, interval=lambda: 0.01)
        t2 = PeriodicTask("b", run=body, interval=lambda: 0.01)
        scheduler = Scheduler([t1, t2])

        scheduler.start_all()
        await asyncio.sleep(0.02)
        await scheduler.stop_all()

        assert scheduler.running is False
        assert t1.running is False
        assert t2.running is False

    async def test_running_false_before_start(self):
        scheduler = Scheduler([])
        assert scheduler.running is False
