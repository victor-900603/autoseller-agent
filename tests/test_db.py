import asyncio
from pathlib import Path

from storage.db import apply_migrations, open_db

MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "storage" / "migrations"


def _run(coro):
    return asyncio.run(coro)


async def _tables(conn):
    cursor = await conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
    )
    return {row[0] for row in await cursor.fetchall()}


def test_migrations_apply(tmp_path):
    async def scenario():
        conn = await open_db(tmp_path / "test.db")
        applied = await apply_migrations(conn, MIGRATIONS_DIR)
        tables = await _tables(conn)
        await conn.close()
        return applied, tables

    applied, tables = _run(scenario())
    assert applied == ["001_init.sql", "002_chat_messages.sql"]
    assert {"products", "chat_sessions", "chat_messages", "execution_logs"} <= tables


def test_migrations_rerun_noop(tmp_path):
    async def scenario():
        conn = await open_db(tmp_path / "test.db")
        await apply_migrations(conn, MIGRATIONS_DIR)
        second = await apply_migrations(conn, MIGRATIONS_DIR)
        await conn.close()
        return second

    assert _run(scenario()) == []


def test_wal_mode(tmp_path):
    async def scenario():
        conn = await open_db(tmp_path / "test.db")
        cursor = await conn.execute("PRAGMA journal_mode")
        mode = (await cursor.fetchone())[0]
        await conn.close()
        return mode

    assert _run(scenario()) == "wal"
