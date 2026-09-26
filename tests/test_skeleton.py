import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_settings_defaults():
    settings = yaml.safe_load((ROOT / "config" / "settings.yaml").read_text(encoding="utf-8"))
    assert settings["poll_interval"]["chat_seconds"] == 180
    assert settings["poll_interval"]["order_seconds"] == 600
    assert settings["pricing"]["floor_ratio"] == 0.85


def test_selectors_exposed():
    from config.platform_selectors import CHAT_UNREAD_BADGE

    assert CHAT_UNREAD_BADGE == ".chat-unread-badge"


def test_check_reports_missing_env():
    proc = subprocess.run(
        [sys.executable, str(ROOT / "main.py"), "--check"],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )
    assert proc.returncode in (0, 1)
    assert "設定檢查" in proc.stdout
