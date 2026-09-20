"""
قراءة متغيرات البيئة بأنواعها.

يُحمَّل ملف .env من جذر المستودع إن وُجد — في التطوير فقط.
في الإنتاج المتغيرات تأتي من المنصة ولا يوجد ملف .env أصلًا.
"""

import os
from pathlib import Path

try:
    from dotenv import load_dotenv

    # backend/config/settings/env.py -> backend/config/settings -> .. -> .. -> الجذر
    _root = Path(__file__).resolve().parent.parent.parent.parent
    load_dotenv(_root / ".env", override=False)
except ImportError:  # pragma: no cover - python-dotenv غير مثبّت في الإنتاج
    pass


_TRUE = {"1", "true", "yes", "on"}


def env_str(key: str, default: str = "") -> str:
    value = os.environ.get(key)
    return default if value is None or value == "" else value


def env_bool(key: str, default: bool = False) -> bool:
    value = os.environ.get(key)
    if value is None or value == "":
        return default
    return value.strip().lower() in _TRUE


def env_int(key: str, default: int) -> int:
    value = os.environ.get(key)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError:
        return default


def env_list(key: str, default: list[str] | None = None) -> list[str]:
    value = os.environ.get(key)
    if value is None or value.strip() == "":
        return list(default or [])
    return [item.strip() for item in value.split(",") if item.strip()]
