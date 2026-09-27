import asyncio

from core.contracts import Job, JobType
from core.orchestrator.job_queue import JobQueue
from core.orchestrator.scheduler import Scheduler


def _job(key: str) -> Job:
    return Job(job_type=JobType.LISTING, payload={}, idempotency_key=key)


def _scheduler(process_job=None, chat_poll=None, order_poll=None, errors=None, **kwargs):
    calls = {"chat": 0, "order": 0, "jobs": []}

    async def default_process(job):
        calls["jobs"].append(job.idempotency_key)

    async def default_chat():
        calls["chat"] += 1

    async def default_order():
        calls["order"] += 1

    collected = []

    def on_error(task_type, exc):
        collected.append((task_type, exc))
        if errors is not None:
            errors.append((task_type, exc))

    scheduler = Scheduler(
        JobQueue(),
        process_job or default_process,
        chat_poll or default_chat,
        order_poll or default_order,
        chat_interval=kwargs.get("chat_interval", 0.05),
        order_interval=kwargs.get("order_interval", 0.05),
        on_error=on_error,
    )
    return scheduler, calls


def test_loops_invoke_handlers():
    async def scenario():
        scheduler, calls = _scheduler()
        scheduler.start()
        await asyncio.sleep(0.2)
        await scheduler.stop()
        return calls

    calls = asyncio.run(scenario())
    assert calls["chat"] >= 2
    assert calls["order"] >= 2


def test_failing_handler_continues():
    async def scenario():
        errors = []
        attempts = {"count": 0}

        async def flaky():
            attempts["count"] += 1
            if attempts["count"] == 1:
                raise RuntimeError("boom")

        scheduler, _ = _scheduler(chat_poll=flaky, errors=errors)
        scheduler.start()
        await asyncio.sleep(0.2)
        await scheduler.stop()
        return attempts["count"], errors

    count, errors = asyncio.run(scenario())
    assert count >= 2
    assert len(errors) == 1
    assert errors[0][0] == "CHAT_POLL"


def test_pause_blocks_consumption():
    async def scenario():
        scheduler, calls = _scheduler()
        queue = scheduler._queue
        scheduler.pause()
        scheduler.start()
        await queue.put(_job("k1"))
        await asyncio.sleep(0.1)
        paused_count = len(calls["jobs"])
        scheduler.resume()
        await asyncio.sleep(0.1)
        await scheduler.stop()
        return paused_count, len(calls["jobs"])

    paused_count, final_count = asyncio.run(scenario())
    assert paused_count == 0
    assert final_count == 1


def test_listing_error_isolated():
    async def scenario():
        errors = []

        async def bad_job(job):
            raise RuntimeError("job failed")

        scheduler, _ = _scheduler(process_job=bad_job, errors=errors)
        queue = scheduler._queue
        scheduler.start()
        await queue.put(_job("k1"))
        await queue.put(_job("k2"))
        await asyncio.sleep(0.2)
        await scheduler.stop()
        return errors

    errors = asyncio.run(scenario())
    assert len(errors) == 2
    assert all(task == "LISTING" for task, _ in errors)


def test_stop_ends_cleanly():
    async def scenario():
        scheduler, _ = _scheduler()
        scheduler.start()
        await scheduler.stop()
        return scheduler._tasks

    assert asyncio.run(scenario()) == []
