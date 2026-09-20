"""
محرك الشرائح.

يحوّل وصفًا بسيطًا يكتبه التاجر من الواجهة إلى استعلام على العضويات.
الوصف بيانات لا كود: تنفيذ تعبير يكتبه مستخدم على قاعدة البيانات
هو ثغرة تنفيذ عن بُعد مهما بدا محدودًا.

شكل الوصف:
    {
      "inactive_days": 30,        العملاء الذين لم يشتروا منذ ٣٠ يومًا
      "min_balance": 100,         رصيد لا يقل عن
      "max_balance": 500,
      "joined_within_days": 7,    انضموا خلال أسبوع
      "tier": "gold",
      "has_consent": true         الافتراضي دائمًا
    }
"""

from datetime import timedelta

from django.db.models import Exists, Max, OuterRef, Q
from django.utils import timezone

from apps.loyalty.models import Balance, Membership

# مفاتيح مقبولة فقط. أي مفتاح آخر يُرفض بدل أن يُتجاهَل بصمت،
# لأن تجاهله يعني إرسال حملة لشريحة أوسع مما قصده التاجر.
ALLOWED_KEYS = {
    "inactive_days",
    "active_within_days",
    "min_balance",
    "max_balance",
    "joined_within_days",
    "tier",
    "program_id",
}


class InvalidSegment(ValueError):
    """وصف شريحة غير صالح."""


def validate(query: dict) -> dict:
    """يتحقق من الوصف ويعيده منظَّفًا."""
    if not isinstance(query, dict):
        raise InvalidSegment("وصف الشريحة يجب أن يكون كائنًا.")

    unknown = set(query) - ALLOWED_KEYS
    if unknown:
        raise InvalidSegment("مفاتيح غير معروفة: " + "، ".join(sorted(unknown)))

    cleaned = {}
    for key in ("inactive_days", "active_within_days", "joined_within_days"):
        if key in query:
            value = _positive_int(query[key], key)
            cleaned[key] = value

    for key in ("min_balance", "max_balance"):
        if key in query:
            cleaned[key] = _positive_int(query[key], key)

    if "tier" in query:
        cleaned["tier"] = str(query["tier"])[:40]

    if "program_id" in query:
        cleaned["program_id"] = str(query["program_id"])

    if (
        "min_balance" in cleaned
        and "max_balance" in cleaned
        and cleaned["min_balance"] > cleaned["max_balance"]
    ):
        raise InvalidSegment("الحد الأدنى للرصيد أكبر من الحد الأقصى.")

    return cleaned


def _positive_int(value, key: str) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise InvalidSegment(f"{key} يجب أن يكون رقمًا صحيحًا.") from exc
    if number < 0:
        raise InvalidSegment(f"{key} لا يكون سالبًا.")
    return number


def resolve(brand, query: dict):
    """
    يُرجع queryset العضويات المستهدفة.

    الموافقة شرط غير قابل للتجاوز: عميل بلا موافقة مسجّلة لا يدخل
    أي شريحة، مهما طابق بقية المعايير.
    """
    cleaned = validate(query or {})

    memberships = (
        Membership.objects.filter(
            brand=brand,
            status=Membership.STATUS_ACTIVE,
            customer__deleted_at__isnull=True,
            customer__consent_at__isnull=False,
        )
        .select_related("customer")
        .annotate(last_activity=Max("entries__created_at"))
    )

    now = timezone.now()

    if "inactive_days" in cleaned:
        cutoff = now - timedelta(days=cleaned["inactive_days"])
        # من لم يتعامل قط يُعدّ خاملًا أيضًا — وهو غالبًا أهم مستهدَف
        memberships = memberships.filter(
            Q(last_activity__lt=cutoff) | Q(last_activity__isnull=True)
        )

    if "active_within_days" in cleaned:
        cutoff = now - timedelta(days=cleaned["active_within_days"])
        memberships = memberships.filter(last_activity__gte=cutoff)

    if "joined_within_days" in cleaned:
        cutoff = now - timedelta(days=cleaned["joined_within_days"])
        memberships = memberships.filter(joined_at__gte=cutoff)

    if "tier" in cleaned:
        memberships = memberships.filter(tier=cleaned["tier"])

    balances = Balance.objects.filter(membership=OuterRef("pk"))
    if "program_id" in cleaned:
        balances = balances.filter(program_id=cleaned["program_id"])
    if "min_balance" in cleaned:
        balances = balances.filter(amount__gte=cleaned["min_balance"])
    if "max_balance" in cleaned:
        balances = balances.filter(amount__lte=cleaned["max_balance"])

    if {"min_balance", "max_balance", "program_id"} & set(cleaned):
        memberships = memberships.filter(Exists(balances))

    return memberships.distinct()


def describe(query: dict) -> str:
    """وصف عربي مقروء للشريحة — يُعرض في شاشة التأكيد قبل الإرسال."""
    cleaned = validate(query or {})
    if not cleaned:
        return "كل عملاء العلامة الموافقين على التواصل"

    parts = []
    if "inactive_days" in cleaned:
        parts.append(f"لم يشتروا منذ {cleaned['inactive_days']} يومًا")
    if "active_within_days" in cleaned:
        parts.append(f"اشتروا خلال {cleaned['active_within_days']} يومًا")
    if "joined_within_days" in cleaned:
        parts.append(f"انضموا خلال {cleaned['joined_within_days']} يومًا")
    if "min_balance" in cleaned:
        parts.append(f"رصيدهم {cleaned['min_balance']} فأكثر")
    if "max_balance" in cleaned:
        parts.append(f"رصيدهم {cleaned['max_balance']} فأقل")
    if "tier" in cleaned:
        parts.append(f"مستوى {cleaned['tier']}")

    return "عملاء " + " و".join(parts)
