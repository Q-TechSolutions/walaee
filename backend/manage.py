#!/usr/bin/env python
"""أداة إدارة Django."""

import os
import sys


def main() -> None:
    # مخرجات كل الأوامر عربية، وترميز الطرفية الافتراضي على ويندوز
    # (cp1252) لا يمثّلها فيُسقِط الأمر بـ UnicodeEncodeError بعد أن
    # يكون نفّذ عمله فعلًا — وهو أسوأ شكل للفشل.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:  # pragma: no cover
        raise ImportError("تعذّر استيراد Django. فعّل البيئة الافتراضية وشغّل: make install") from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
