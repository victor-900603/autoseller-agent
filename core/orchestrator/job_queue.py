import asyncio

from core.contracts import Job

_MAX_SIZE = 100


class JobQueue:
    """單一消費者的先進先出佇列，冪等鍵去重範圍為未消費任務。"""

    def __init__(self, max_size: int = _MAX_SIZE) -> None:
        """建立底層佇列與未消費鍵集合。"""
        self._queue: asyncio.Queue[Job] = asyncio.Queue(maxsize=max_size)
        self._pending_keys: set[str] = set()

    async def put(self, job: Job) -> bool:
        """入列，冪等鍵重複直接丟棄；滿列時等待。"""
        if job.idempotency_key in self._pending_keys:
            return False
        self._pending_keys.add(job.idempotency_key)
        try:
            await self._queue.put(job)
        except Exception:
            self._pending_keys.discard(job.idempotency_key)
            raise
        return True

    def put_nowait(self, job: Job) -> bool:
        """入列，滿列直接拋錯。"""
        if job.idempotency_key in self._pending_keys:
            return False
        self._pending_keys.add(job.idempotency_key)
        try:
            self._queue.put_nowait(job)
        except Exception:
            self._pending_keys.discard(job.idempotency_key)
            raise
        return True

    async def get(self) -> Job:
        """取出任務並釋放其冪等鍵。"""
        job = await self._queue.get()
        self._pending_keys.discard(job.idempotency_key)
        return job

    def qsize(self) -> int:
        """回傳未消費任務數。"""
        return self._queue.qsize()

    def empty(self) -> bool:
        """佇列是否為空。"""
        return self._queue.empty()
