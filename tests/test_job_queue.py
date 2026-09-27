import asyncio

import pytest

from core.contracts import Job, JobType
from core.orchestrator.job_queue import JobQueue


def _job(key: str, job_type: JobType = JobType.LISTING) -> Job:
    return Job(job_type=job_type, payload={}, idempotency_key=key)


def test_fifo_order():
    async def scenario():
        queue = JobQueue()
        await queue.put(_job("k1"))
        await queue.put(_job("k2"))
        first = await queue.get()
        second = await queue.get()
        return first.idempotency_key, second.idempotency_key

    assert asyncio.run(scenario()) == ("k1", "k2")


def test_duplicate_key_dropped():
    async def scenario():
        queue = JobQueue()
        accepted = await queue.put(_job("k1"))
        dropped = await queue.put(_job("k1"))
        return accepted, dropped, queue.qsize()

    assert asyncio.run(scenario()) == (True, False, 1)


def test_distinct_keys_accepted():
    async def scenario():
        queue = JobQueue()
        await queue.put(_job("k1"))
        await queue.put(_job("k2", JobType.CHAT_REPLY))
        return queue.qsize()

    assert asyncio.run(scenario()) == 2


def test_full_queue_raises_nowait():
    async def scenario():
        queue = JobQueue(max_size=1)
        queue.put_nowait(_job("k1"))
        with pytest.raises(asyncio.QueueFull):
            queue.put_nowait(_job("k2"))

    asyncio.run(scenario())


def test_consumed_key_resubmittable():
    async def scenario():
        queue = JobQueue()
        await queue.put(_job("k1"))
        await queue.get()
        return await queue.put(_job("k1"))

    assert asyncio.run(scenario()) is True


def test_empty_initially():
    async def scenario():
        return JobQueue().empty()

    assert asyncio.run(scenario()) is True
