import asyncio
from pathlib import Path

from bot.telegram_app import TelegramApp
from core.contracts import JobType
from core.orchestrator.job_queue import JobQueue
from core.orchestrator.state_store import StateStore
from storage.db import apply_migrations, open_db

MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "storage" / "migrations"
ADMIN = 1001
OUTSIDER = 9999


class FakeMessage:
    def __init__(self):
        self.replies = []

    async def reply_text(self, text):
        self.replies.append(text)


class FakeUser:
    def __init__(self, user_id):
        self.id = user_id


class FakeQuery:
    def __init__(self, user_id, data):
        self.from_user = FakeUser(user_id)
        self.data = data
        self.answers = []
        self.cleared = False

    async def answer(self, text):
        self.answers.append(text)

    async def edit_message_reply_markup(self, reply_markup):
        self.cleared = reply_markup is None


class FakeUpdate:
    def __init__(self, user_id, data=None):
        self.effective_user = FakeUser(user_id)
        self.message = FakeMessage()
        self.callback_query = FakeQuery(user_id, data) if data is not None else None


class FakeContext:
    def __init__(self, args=None):
        self.args = args or []


class FakeScheduler:
    def __init__(self):
        self.paused = False

    def pause(self):
        self.paused = True

    def resume(self):
        self.paused = False


async def _open_store(tmp_path):
    conn = await open_db(tmp_path / "test.db")
    await apply_migrations(conn, MIGRATIONS_DIR)
    return conn, StateStore(conn)


def _app(store):
    queue = JobQueue()
    return TelegramApp("token", {ADMIN}, store, queue, FakeScheduler()), queue


def test_non_admin_ignored(tmp_path):
    async def scenario():
        conn, store = await _open_store(tmp_path)
        try:
            app, _ = _app(store)
            update = FakeUpdate(OUTSIDER)
            await app.start_cmd(update, FakeContext())
            await app.pending_cmd(update, FakeContext())
            return update.message.replies
        finally:
            await conn.close()

    assert asyncio.run(scenario()) == []


def test_pending_lists_drafts(tmp_path):
    async def scenario():
        conn, store = await _open_store(tmp_path)
        try:
            await store.create_product("p1", "測試商品", 2000, 1700)
            app, _ = _app(store)
            update = FakeUpdate(ADMIN)
            await app.pending_cmd(update, FakeContext())
            return update.message.replies
        finally:
            await conn.close()

    replies = asyncio.run(scenario())
    assert len(replies) == 1
    assert "p1" in replies[0]


def test_pending_empty(tmp_path):
    async def scenario():
        conn, store = await _open_store(tmp_path)
        try:
            app, _ = _app(store)
            update = FakeUpdate(ADMIN)
            await app.pending_cmd(update, FakeContext())
            return update.message.replies
        finally:
            await conn.close()

    assert asyncio.run(scenario()) == ["目前無待審核。"]


def test_status_reports_product(tmp_path):
    async def scenario():
        conn, store = await _open_store(tmp_path)
        try:
            await store.create_product("p1", "測試商品", 2000, 1700)
            app, _ = _app(store)
            update = FakeUpdate(ADMIN)
            await app.status_cmd(update, FakeContext(args=["p1"]))
            await app.status_cmd(update, FakeContext(args=["ghost"]))
            await app.status_cmd(update, FakeContext())
            return update.message.replies
        finally:
            await conn.close()

    replies = asyncio.run(scenario())
    assert "DRAFT" in replies[0]
    assert replies[1] == "查無此商品。"
    assert replies[2].startswith("用法：")


def test_pause_resume_delegate(tmp_path):
    async def scenario():
        conn, store = await _open_store(tmp_path)
        try:
            scheduler = FakeScheduler()
            queue = JobQueue()
            app = TelegramApp("token", {ADMIN}, store, queue, scheduler)
            update = FakeUpdate(ADMIN)
            await app.pause_cmd(update, FakeContext())
            paused = scheduler.paused
            await app.resume_cmd(update, FakeContext())
            return paused, scheduler.paused, update.message.replies
        finally:
            await conn.close()

    paused, resumed, replies = asyncio.run(scenario())
    assert (paused, resumed) == (True, False)
    assert replies == ["已暫停刊登消費。", "已恢復刊登消費。"]


def test_approve_enqueues(tmp_path):
    async def scenario():
        conn, store = await _open_store(tmp_path)
        try:
            app, queue = _app(store)
            update = FakeUpdate(ADMIN, "approve:p1")
            await app.review_callback(update, FakeContext())
            job = await queue.get()
            return job, update.callback_query.answers
        finally:
            await conn.close()

    job, answers = asyncio.run(scenario())
    assert job.job_type == JobType.LISTING
    assert job.payload == {"product_id": "p1"}
    assert job.idempotency_key == "listing:p1"
    assert answers == ["已排入刊登。"]


def test_reject_logs_without_enqueue(tmp_path):
    async def scenario():
        conn, store = await _open_store(tmp_path)
        try:
            app, queue = _app(store)
            update = FakeUpdate(ADMIN, "reject:p1")
            await app.review_callback(update, FakeContext())
            cursor = await conn.execute(
                "SELECT status FROM execution_logs WHERE product_id = 'p1'"
            )
            rows = await cursor.fetchall()
            return queue.empty(), update.callback_query.answers, [r[0] for r in rows]
        finally:
            await conn.close()

    empty, answers, statuses = asyncio.run(scenario())
    assert empty is True
    assert answers == ["已退回。"]
    assert statuses == ["FAILURE"]


def test_list_products_filter(tmp_path):
    async def scenario():
        conn, store = await _open_store(tmp_path)
        try:
            await store.create_product("p1", "甲", 2000, 1700)
            await store.create_product("p2", "乙", 2000, 1700)
            await store.transition_product("p2", "PUBLISHED")
            drafts = await store.list_products("DRAFT")
            all_products = await store.list_products()
            return drafts, all_products
        finally:
            await conn.close()

    drafts, all_products = asyncio.run(scenario())
    assert [p["id"] for p in drafts] == ["p1"]
    assert len(all_products) == 2
