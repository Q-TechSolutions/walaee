"""
تدوير رموز نقاط البيع في Redis.

الرمز يعيش في Redis لا في PostgreSQL لسببين:
  ١) القراءة تحدث عند كل مسح، ولمس القاعدة في هذا المسار الساخن
     يحوّل تدفّق الكاشير إلى عنق زجاجة.
  ٢) انتهاء الصلاحية بـ TTL مجاني، بينما تنظيف صفوف منتهية في
     PostgreSQL يحتاج مهمة دورية.

العمود `Terminal.current_code` نسخة للتدقيق فقط لا مصدرًا للحقيقة.

المرجع: docs/architecture/README.md — تدفق العملية الحرجة
"""

import secrets

from django.conf import settings
from django.core.cache import cache

# أحرف بلا ملتبسات: الكاشير قد يُملي الرمز صوتيًا عند تعطّل الشاشة
_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
_CODE_LENGTH = 8

_KEY_CODE = "pos:code:{code}"
_KEY_TERMINAL = "pos:terminal:{terminal_id}"


def generate_code() -> str:
    return "".join(secrets.choice(_ALPHABET) for _ in range(_CODE_LENGTH))


def issue_code(terminal_id) -> str:
    """
    يصدر رمزًا جديدًا لطرفية ويُبطل سابقه فورًا.

    الإبطال الفوري مقصود: ترك الرمز القديم صالحًا حتى انتهاء TTL
    يعني نافذة يُقبل فيها رمزان لنفس الطرفية.
    """
    terminal_key = _KEY_TERMINAL.format(terminal_id=terminal_id)

    previous = cache.get(terminal_key)
    if previous:
        cache.delete(_KEY_CODE.format(code=previous))

    code = generate_code()
    ttl = settings.POS_CODE_TTL_SECONDS

    cache.set(_KEY_CODE.format(code=code), str(terminal_id), timeout=ttl)
    cache.set(terminal_key, code, timeout=ttl)
    return code


def current_code(terminal_id) -> str | None:
    """الرمز الفعّال للطرفية، أو None إن انتهى."""
    return cache.get(_KEY_TERMINAL.format(terminal_id=terminal_id))


def resolve_code(code: str) -> str | None:
    """يترجم رمزًا إلى معرّف طرفية. None يعني منتهيًا أو غير موجود."""
    if not code:
        return None
    return cache.get(_KEY_CODE.format(code=code.strip().upper()))


def consume_code(code: str) -> None:
    """
    يستهلك الرمز فلا يُستخدم مرة أخرى.

    يُستدعى لحظة إنشاء العملية لا لحظة تأكيدها: بين الخطوتين قد تمر
    دقائق، وترك الرمز صالحًا خلالها يسمح لعميل آخر بالمسح على نفس
    الفاتورة.
    """
    if not code:
        return
    code = code.strip().upper()
    terminal_id = cache.get(_KEY_CODE.format(code=code))
    cache.delete(_KEY_CODE.format(code=code))
    if terminal_id:
        cache.delete(_KEY_TERMINAL.format(terminal_id=terminal_id))
