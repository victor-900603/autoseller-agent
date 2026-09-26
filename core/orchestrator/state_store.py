import json

import aiosqlite

_ALLOWED_TRANSITIONS = {
    "DRAFT": ("PUBLISHED",),
    "PUBLISHED": ("SOLD", "DELISTED"),
    "SOLD": (),
    "DELISTED": (),
}

_MESSAGE_KEEP = 20


class StateError(Exception):
    pass


class StateStore:
    def __init__(self, conn: aiosqlite.Connection) -> None:
        self._conn = conn

    async def create_product(
        self,
        product_id: str,
        title: str,
        suggested_price: int,
        floor_price: int,
        category: str = "",
        description: str = "",
        image_paths: list[str] | None = None,
    ) -> None:
        """建立草稿商品，圖片清單以 JSON 存欄。"""
        await self._conn.execute(
            "INSERT INTO products "
            "(id, title, status, suggested_price, floor_price, category, "
            "description, images_json) VALUES (?, ?, 'DRAFT', ?, ?, ?, ?, ?)",
            (
                product_id,
                title,
                suggested_price,
                floor_price,
                category,
                description,
                json.dumps(image_paths or [], ensure_ascii=False),
            ),
        )
        await self._conn.commit()

    async def get_product(self, product_id: str) -> dict | None:
        """讀取商品，不存在回傳空值。"""
        cursor = await self._conn.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def transition_product(self, product_id: str, to_state: str) -> None:
        """轉換商品狀態，不存在或非法轉換拋錯。"""
        product = await self.get_product(product_id)
        if product is None:
            raise StateError(f"商品不存在：{product_id}")
        if to_state not in _ALLOWED_TRANSITIONS.get(product["status"], ()):
            raise StateError(f"非法狀態轉換：{product['status']} -> {to_state}")
        await self._conn.execute(
            "UPDATE products SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (to_state, product_id),
        )
        await self._conn.commit()

    async def set_carousell_item_id(self, product_id: str, item_id: str) -> None:
        """回寫平台商品編號，供後續訂單比對。"""
        await self._conn.execute(
            "UPDATE products SET carousell_item_id = ? WHERE id = ?", (item_id, product_id)
        )
        await self._conn.commit()

    async def _get_session(self, session_id: str) -> dict | None:
        """讀取會話，不存在回傳空值。"""
        cursor = await self._conn.execute(
            "SELECT * FROM chat_sessions WHERE session_id = ?", (session_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def get_or_create_session(
        self, session_id: str, product_id: str, buyer_username: str
    ) -> dict:
        """讀取會話，不存在即建。"""
        session = await self._get_session(session_id)
        if session is None:
            await self._conn.execute(
                "INSERT INTO chat_sessions (session_id, product_id, buyer_username) "
                "VALUES (?, ?, ?)",
                (session_id, product_id, buyer_username),
            )
            await self._conn.commit()
            return await self.get_or_create_session(session_id, product_id, buyer_username)
        return session

    async def bump_round(self, session_id: str) -> int:
        """輪次加一並回傳，會話不存在拋錯。"""
        cursor = await self._conn.execute(
            "UPDATE chat_sessions SET negotiation_round = negotiation_round + 1, "
            "updated_at = CURRENT_TIMESTAMP WHERE session_id = ?",
            (session_id,),
        )
        if cursor.rowcount == 0:
            raise StateError(f"會話不存在：{session_id}")
        await self._conn.commit()
        session = await self._get_session(session_id)
        return session["negotiation_round"]

    async def append_message(
        self, session_id: str, role: str, text: str, amount: int | None = None
    ) -> None:
        """寫入對話並滾動刪除超出保留則數的舊訊息。"""
        await self._conn.execute(
            "INSERT INTO chat_messages (session_id, role, text, amount_parsed) "
            "VALUES (?, ?, ?, ?)",
            (session_id, role, text, amount),
        )
        await self._conn.execute(
            "DELETE FROM chat_messages WHERE id NOT IN "
            "(SELECT id FROM chat_messages WHERE session_id = ? "
            "ORDER BY id DESC LIMIT ?)",
            (session_id, _MESSAGE_KEEP),
        )
        await self._conn.commit()

    async def recent_messages(self, session_id: str, limit: int = _MESSAGE_KEEP) -> list[dict]:
        """倒序讀取對話，供審核追溯。"""
        cursor = await self._conn.execute(
            "SELECT * FROM chat_messages WHERE session_id = ? ORDER BY id DESC LIMIT ?",
            (session_id, limit),
        )
        return [dict(row) for row in await cursor.fetchall()]

    async def log_execution(
        self,
        task_type: str,
        status: str,
        job_id: str | None = None,
        product_id: str | None = None,
        session_id: str | None = None,
        screenshot_path: str | None = None,
        error_message: str | None = None,
    ) -> int:
        """寫入稽核日誌，回傳日誌編號。"""
        cursor = await self._conn.execute(
            "INSERT INTO execution_logs "
            "(job_id, task_type, product_id, session_id, status, screenshot_path, "
            "error_message) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (job_id, task_type, product_id, session_id, status, screenshot_path, error_message),
        )
        await self._conn.commit()
        return cursor.lastrowid
