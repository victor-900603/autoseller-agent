import asyncio
from pathlib import Path

import pytest

from core.orchestrator.state_store import StateError, StateStore
from storage.db import apply_migrations, open_db

MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "storage" / "migrations"


async def _open_store(tmp_path):
    conn = await open_db(tmp_path / "test.db")
    await apply_migrations(conn, MIGRATIONS_DIR)
    return conn, StateStore(conn)


def test_create_and_get_product(tmp_path):
    async def scenario():
        conn, store = await _open_store(tmp_path)
        try:
            await store.create_product("p1", "測試商品", 2000, 1700, "電腦周邊", "描述", ["a.jpg"])
            return await store.get_product("p1")
        finally:
            await conn.close()

    product = asyncio.run(scenario())
    assert product["status"] == "DRAFT"
    assert product["suggested_price"] == 2000


def test_legal_transitions(tmp_path):
    async def scenario():
        conn, store = await _open_store(tmp_path)
        try:
            await store.create_product("p1", "測試商品", 2000, 1700)
            await store.transition_product("p1", "PUBLISHED")
            await store.set_carousell_item_id("p1", "item-9")
            await store.transition_product("p1", "SOLD")
            return await store.get_product("p1")
        finally:
            await conn.close()

    product = asyncio.run(scenario())
    assert product["status"] == "SOLD"
    assert product["carousell_item_id"] == "item-9"


def test_illegal_transition_rejected(tmp_path):
    async def scenario():
        conn, store = await _open_store(tmp_path)
        try:
            await store.create_product("p1", "測試商品", 2000, 1700)
            with pytest.raises(StateError):
                await store.transition_product("p1", "SOLD")
        finally:
            await conn.close()

    asyncio.run(scenario())


def test_missing_product_rejected(tmp_path):
    async def scenario():
        conn, store = await _open_store(tmp_path)
        try:
            with pytest.raises(StateError):
                await store.transition_product("ghost", "PUBLISHED")
        finally:
            await conn.close()

    asyncio.run(scenario())


def test_round_increments(tmp_path):
    async def scenario():
        conn, store = await _open_store(tmp_path)
        try:
            await store.get_or_create_session("s1", "p1", "buyer")
            first = await store.bump_round("s1")
            second = await store.bump_round("s1")
            return first, second
        finally:
            await conn.close()

    assert asyncio.run(scenario()) == (1, 2)


def test_bump_missing_session_rejected(tmp_path):
    async def scenario():
        conn, store = await _open_store(tmp_path)
        try:
            with pytest.raises(StateError):
                await store.bump_round("ghost")
        finally:
            await conn.close()

    asyncio.run(scenario())


def test_messages_trimmed_to_twenty(tmp_path):
    async def scenario():
        conn, store = await _open_store(tmp_path)
        try:
            for i in range(21):
                await store.append_message("s1", "buyer", f"msg-{i}")
            return await store.recent_messages("s1")
        finally:
            await conn.close()

    messages = asyncio.run(scenario())
    assert len(messages) == 20
    assert all(m["text"] != "msg-0" for m in messages)
    assert messages[0]["text"] == "msg-20"


def test_execution_log_returns_id(tmp_path):
    async def scenario():
        conn, store = await _open_store(tmp_path)
        try:
            return await store.log_execution("LISTING", "SUCCESS", product_id="p1")
        finally:
            await conn.close()

    assert isinstance(asyncio.run(scenario()), int)
