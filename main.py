"""系統進入點與排程引擎。"""

import argparse
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
SETTINGS_PATH = ROOT / "config" / "settings.yaml"
ENV_PATH = ROOT / ".env"

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

    print("未指定 --check，不啟動服務")
    return 2


if __name__ == "__main__":
    sys.exit(main())
