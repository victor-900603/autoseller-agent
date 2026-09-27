"""系統進入點與排程引擎。"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

import yaml

from core.contracts import Job
from core.orchestrator.job_queue import JobQueue
from core.orchestrator.scheduler import Scheduler
from storage.db import apply_migrations, open_db

ROOT = Path(__file__).resolve().parent
SETTINGS_PATH = ROOT / "config" / "settings.yaml"
ENV_PATH = ROOT / ".env"
MIGRATIONS_DIR = ROOT / "storage" / "migrations"
DEFAULT_DB_PATH = ROOT / "storage" / "app.db"

logger = logging.getLogger("autoseller")

REQUIRED_SETTINGS = [
    ("poll_interval", "chat_seconds"),
    ("poll_interval", "order_seconds"),
    ("pricing", "floor_ratio"),
    ("browser", "retry_limit"),
    ("listing", "image_limit"),
    ("screenshots", "retention_days"),
]

REQUIRED_ENV = ["TELEGRAM_BOT_TOKEN", "TELEGRAM_ADMIN_IDS", "TAVILY_API_KEY"]


def load_dotenv(path: Path) -> dict:
    """解析 .env 檔為字典，檔案不存在回傳空字典。"""
    values = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip()
    return values


def check() -> list:
    """檢查設定檔與環境變數，回傳問題清單（空清單表示通過）。"""
    problems = []

    if not SETTINGS_PATH.exists():
        problems.append(f"缺少設定檔：{SETTINGS_PATH}")
    else:
        try:
            settings = yaml.safe_load(SETTINGS_PATH.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as exc:
            problems.append(f"設定檔解析失敗：{exc}")
            settings = None
        if settings is not None:
            for section, key in REQUIRED_SETTINGS:
                section_value = settings.get(section)
                if not isinstance(section_value, dict) or section_value.get(key) is None:
                    problems.append(f"設定缺失：{section}.{key}")

    env = load_dotenv(ENV_PATH)
    provider = env.get("LLM_PROVIDER", "mock").strip() or "mock"
    for key in REQUIRED_ENV:
        if not env.get(key):
            problems.append(f"環境變數缺失：{key}")
    if provider != "mock" and not env.get("LLM_API_KEY"):
        problems.append("環境變數缺失：LLM_API_KEY（非 mock 模式必須提供）")

    return problems


def main(argv=None) -> int:
    """進入點，--check 檢查設定，無參數常駐運行。"""
    parser = argparse.ArgumentParser(description="autoseller-agent")
    parser.add_argument("--check", action="store_true", help="僅檢查設定與環境，不啟動服務")
    args = parser.parse_args(argv)

    if args.check:
        problems = check()
        if problems:
            print("設定檢查未通過：")
            for item in problems:
                print(f"  - {item}")
            return 1
        print("設定檢查通過")
        return 0

    return run()


def load_intervals() -> tuple:
    """讀取輪詢間隔（呼叫前須已通過檢查）。"""
    settings = yaml.safe_load(SETTINGS_PATH.read_text(encoding="utf-8"))
    return (
        settings["poll_interval"]["chat_seconds"],
        settings["poll_interval"]["order_seconds"],
    )


async def serve(
    db_path: Path = DEFAULT_DB_PATH,
    chat_interval: float = 180,
    order_interval: float = 600,
) -> None:
    """組裝儲存、佇列與排程器並運行至取消。"""
    conn = await open_db(db_path)
    try:
        await apply_migrations(conn, MIGRATIONS_DIR)
        queue: JobQueue = JobQueue()

        async def on_job(job: Job) -> None:
            logger.info("收到任務：%s", job.job_id)

        async def chat_poll() -> None:
            pass

        async def order_poll() -> None:
            pass

        def on_error(task_type: str, exc: Exception) -> None:
            logger.error("%s 失敗：%s", task_type, exc)

        scheduler = Scheduler(
            queue, on_job, chat_poll, order_poll, chat_interval, order_interval, on_error
        )
        scheduler.start()
        try:
            await asyncio.Event().wait()
        finally:
            await scheduler.stop()
    finally:
        await conn.close()


def run() -> int:
    """檢查通過後常駐運行，終止訊號結束。"""
    problems = check()
    if problems:
        print("設定檢查未通過：")
        for item in problems:
            print(f"  - {item}")
        return 1
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    chat_interval, order_interval = load_intervals()
    try:
        asyncio.run(serve(DEFAULT_DB_PATH, chat_interval, order_interval))
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
