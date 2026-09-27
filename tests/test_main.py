import asyncio
from pathlib import Path

import main
from storage.db import open_db


def test_run_refuses_without_env():
    assert main.run() == 1


def test_serve_builds_db_and_shuts_down(tmp_path):
    async def scenario():
        db_path = tmp_path / "serve.db"
        try:
            await asyncio.wait_for(
                main.serve(db_path, chat_interval=0.05, order_interval=0.05), timeout=0.2
            )
        except TimeoutError:
            pass
        return db_path

    db_path = asyncio.run(scenario())
    assert Path(db_path).exists()


def test_serve_applies_migrations(tmp_path):
    async def scenario():
        db_path = tmp_path / "serve.db"
        try:
            await asyncio.wait_for(
                main.serve(db_path, chat_interval=0.05, order_interval=0.05), timeout=0.2
            )
        except TimeoutError:
            pass
        conn = await open_db(db_path)
        cursor = await conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'products'"
        )
        found = await cursor.fetchone() is not None
        await conn.close()
        return found

    assert asyncio.run(scenario()) is True


def test_load_intervals_matches_settings():
    chat_interval, order_interval = main.load_intervals()
    assert (chat_interval, order_interval) == (180, 600)
