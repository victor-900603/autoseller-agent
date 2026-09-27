import asyncio
from collections.abc import Awaitable, Callable

from core.contracts import Job
from core.orchestrator.job_queue import JobQueue

Handler = Callable[[], Awaitable[None]]
JobHandler = Callable[[Job], Awaitable[None]]
ErrorHandler = Callable[[str, Exception], None]


def _silent_error(task_type: str, exc: Exception) -> None:
    pass


class Scheduler:
    """三迴圈擁有者，處理器由外部注入，異常各自隔離。"""

    def __init__(
        self,
        queue: JobQueue,
        process_job: JobHandler,
        chat_poll: Handler,
        order_poll: Handler,
        chat_interval: float = 180,
        order_interval: float = 600,
        on_error: ErrorHandler = _silent_error,
    ) -> None:
        """注入佇列、處理器、間隔與錯誤回呼，初始為運行狀態。"""
        self._queue = queue
        self._process_job = process_job
        self._chat_poll = chat_poll
        self._order_poll = order_poll
        self._chat_interval = chat_interval
        self._order_interval = order_interval
        self._on_error = on_error
        self._resume = asyncio.Event()
        self._resume.set()
        self._tasks: list[asyncio.Task] = []

    def start(self) -> None:
        """啟動刊登消費、聊聊輪詢、訂單輪詢三個任務。"""
        self._tasks = [
            asyncio.create_task(self._listing_loop(), name="listing"),
            asyncio.create_task(self._poll_loop("CHAT_POLL", self._chat_poll, self._chat_interval)),
            asyncio.create_task(
                self._poll_loop("ORDER_CHECK", self._order_poll, self._order_interval)
            ),
        ]

    async def stop(self) -> None:
        """取消並等待三任務結束。"""
        for task in self._tasks:
            task.cancel()
        for task in self._tasks:
            try:
                await task
            except asyncio.CancelledError:
                pass
        self._tasks = []

    def pause(self) -> None:
        """暫停刊登消費，輪詢不受影響。"""
        self._resume.clear()

    def resume(self) -> None:
        """恢復刊登消費。"""
        self._resume.set()

    async def _listing_loop(self) -> None:
        """取任務並處理，異常回報後繼續。"""
        while True:
            await self._resume.wait()
            job = await self._queue.get()
            try:
                await self._process_job(job)
            except Exception as exc:
                self._on_error("LISTING", exc)

    async def _poll_loop(self, task_type: str, handler: Handler, interval: float) -> None:
        """執行處理器後固定延遲，異常回報後繼續。"""
        while True:
            try:
                await handler()
            except Exception as exc:
                self._on_error(task_type, exc)
            await asyncio.sleep(interval)
