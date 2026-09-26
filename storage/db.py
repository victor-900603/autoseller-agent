from pathlib import Path

import aiosqlite

MIGRATIONS_TABLE = "schema_migrations"


async def open_db(path: str | Path) -> aiosqlite.Connection:
    """開啟 SQLite 並切 WAL 模式，列型別設為字典列。"""
    conn = await aiosqlite.connect(path)
    conn.row_factory = aiosqlite.Row
    await conn.execute("PRAGMA journal_mode=WAL")
    return conn


async def apply_migrations(conn: aiosqlite.Connection, migrations_dir: str | Path) -> list[str]:
    """按檔名排序套用未執行的遷移，回傳本次套用清單。"""
    directory = Path(migrations_dir)
    await conn.execute(
        f"CREATE TABLE IF NOT EXISTS {MIGRATIONS_TABLE} "
        "(name TEXT PRIMARY KEY, applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
    )
    cursor = await conn.execute(f"SELECT name FROM {MIGRATIONS_TABLE}")
    applied = {row[0] for row in await cursor.fetchall()}
    pending = sorted(p.name for p in directory.glob("*.sql") if p.name not in applied)
    for name in pending:
        await conn.executescript((directory / name).read_text(encoding="utf-8"))
        await conn.execute(f"INSERT INTO {MIGRATIONS_TABLE} (name) VALUES (?)", (name,))
    await conn.commit()
    return pending
