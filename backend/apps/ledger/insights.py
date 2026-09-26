"""
قواعد إحصائية بسيطة — لا تعلّم آلي.

التقرير (م-١٢) يرفض تسمية هذا «ذكاءً اصطناعيًا» في السنة الأولى،
لسبب عملي لا تسويقي: النموذج المتعلّم يحتاج بيانات لن تتوفّر قبل
اثني عشر شهرًا، والوعد بما لا يُسلَّم يُستنزف به الفريق ويُفقَد به
المصداقية. وحدّد ثلاث حالات تعمل بحساب متوسطات ويمكن تسليمها من
الشهر الأول:

  ١) العملاء المعرّضون للفقدان — منفّذة في `apps.loyalty.views`
     كشريحة، لأنها تُقرأ كقائمة يُطلق عليها التاجر حملة.
  ٢) قيمة المكافأة المقترحة — هنا.
  ٣) أفضل يوم وساعة لإرسال الحملة — هنا.

القاعدة الحاكمة في الاثنتين: **لا تُقترح توصية على بيانات لا
تكفي**. اقتراح مبنيّ على سبع فواتير يبدو في الشاشة مطابقًا
لاقتراح مبنيّ على سبعة آلاف، والتاجر يسعّر مكافأته عليه. لذلك
تُعاد `confidence` مع كل نتيجة، وتُعاد `None` تحتها عتبة الكفاية
بدل رقم لا يستحق أن يُبنى عليه قرار.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.db.models import Avg, Count
from django.utils import timezone

from apps.loyalty.models import LoyaltyProgram

from .models import Transaction

#: أقل عدد فواتير يُبنى عليه اقتراح سعر. دونها المتوسط يتحرّك
#: بفاتورة واحدة شاذّة.
MIN_INVOICES = 30

#: أقل عدد زيارات يُبنى عليه اقتراح توقيت. أقل من ذلك ليس نمطًا
#: بل صدفة.
MIN_VISITS = 40

#: نافذة القراءة. أطول منها يخلط موسمًا بموسم، وأقصر يجعل أسبوعًا
#: واحدًا شاذًّا يقود التوصية.
WINDOW_DAYS = 90

#: نسبة المكافأة من متوسط الفاتورة. هذه ليست قاعدة رياضية بل عرف
#: قطاعي: أقل من ٥٪ لا يُشعر العميل بشيء، وأكثر من ١٥٪ يأكل هامش
#: التاجر في قطاعات هامشها ضيّق أصلًا.
REWARD_SHARE = Decimal("0.10")
REWARD_SHARE_LOW = Decimal("0.05")
REWARD_SHARE_HIGH = Decimal("0.15")

#: عدد الزيارات المتوقَّع قبل بلوغ المكافأة. المكافأة التي تُبلَغ
#: من زيارتين لا تبني عادة، والتي تحتاج عشرين تُيئِس.
TARGET_VISITS = 6

WEEKDAY_NAMES = [
    "الاثنين",
    "الثلاثاء",
    "الأربعاء",
    "الخميس",
    "الجمعة",
    "السبت",
    "الأحد",
]


def _confidence(sample: int, minimum: int) -> str:
    """
    ثلاث درجات لا نسبة مئوية.

    «٧٣٪ ثقة» رقم يُقرأ كدقّة وهو ليس كذلك — هو حجم عيّنة بثوب
    آخر. الكلمة تقول ما تعنيه بلا أن توحي بما لا تعنيه.
    """
    if sample >= minimum * 5:
        return "high"
    if sample >= minimum * 2:
        return "medium"
    return "low"


def suggested_reward_value(brand, *, days: int = WINDOW_DAYS) -> dict:
    """
    قيمة المكافأة المقترحة لكل برنامج في هذه العلامة.

    الحساب: متوسط الفاتورة × نسبة القطاع × عدد الزيارات المستهدفة،
    ثم يُترجَم إلى وحدات البرنامج نفسه — نقاط أو أختام أو زيارات —
    لأن التاجر يكتب التكلفة بالوحدة لا بالجنيه.

    ما لا يُفعَل هنا: اقتراح لبرنامج بلا قاعدة، أو لعلامة بلا
    فواتير كافية. الصمت أصدق من رقم مخترَع، والتاجر الذي يسعّر
    مكافأته على رقم مخترَع يكتشف الخطأ في التزامه القائم بعد شهر.
    """
    since = timezone.now() - timedelta(days=days)
    invoices = Transaction.objects.filter(
        terminal__branch__brand=brand,
        status=Transaction.STATUS_CONFIRMED,
        created_at__gte=since,
    ).aggregate(average=Avg("invoice_amount"), count=Count("id"))

    sample = invoices["count"] or 0
    average = invoices["average"]

    if sample < MIN_INVOICES or not average:
        return {
            "enough_data": False,
            "sample": sample,
            "needed": MIN_INVOICES,
            "window_days": days,
            "average_invoice": str(Decimal(average or 0).quantize(Decimal("0.01"))),
            "programs": [],
        }

    average = Decimal(average)
    programs = []

    for program in LoyaltyProgram.objects.filter(brand=brand, is_active=True).select_related(
        "rule"
    ):
        rule = getattr(program, "rule", None)
        if rule is None:
            # برنامج بلا قاعدة لا يمنح شيئًا، فلا معنى لاقتراح
            # تكلفة مكافأة عليه
            continue

        value = (average * REWARD_SHARE * TARGET_VISITS).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
        low = (average * REWARD_SHARE_LOW * TARGET_VISITS).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
        high = (average * REWARD_SHARE_HIGH * TARGET_VISITS).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )

        programs.append(
            {
                "program_id": str(program.id),
                "program_name": program.name,
                "program_type": program.type,
                "unit_label": program.unit_label,
                "cost_amount": str(_to_units(program, rule, value, average)),
                "cost_low": str(_to_units(program, rule, low, average)),
                "cost_high": str(_to_units(program, rule, high, average)),
                "reward_worth": str(value),
            }
        )

    return {
        "enough_data": True,
        "sample": sample,
        "needed": MIN_INVOICES,
        "window_days": days,
        "average_invoice": str(average.quantize(Decimal("0.01"))),
        "target_visits": TARGET_VISITS,
        "confidence": _confidence(sample, MIN_INVOICES),
        "programs": programs,
    }


def _to_units(program, rule, worth: Decimal, average_invoice: Decimal) -> Decimal:
    """
    قيمة المكافأة بالجنيه مترجَمة إلى وحدات البرنامج.

    الترجمة تختلف بنوع النموذج لأن الوحدة نفسها تختلف: النقطة
    تُكتسب لكل جنيه، والختم لكل زيارة، والاسترداد النقدي محسوب
    بالجنيه أصلًا. استعمال معادلة واحدة للجميع كان يعطي «٦ أختام»
    لبرنامج نقاط و«٤٢٠ نقطة» لبرنامج أختام.
    """
    rate = rule.earn_rate or Decimal("1")

    if program.type in (LoyaltyProgram.TYPE_STAMPS, LoyaltyProgram.TYPE_VISITS):
        # ختم لكل زيارة: التكلفة هي عدد الزيارات المستهدف
        return Decimal(TARGET_VISITS)

    if program.type == LoyaltyProgram.TYPE_CASHBACK:
        # الرصيد بالجنيه — القيمة كما هي
        return worth.quantize(Decimal("0.01"))

    if program.type == LoyaltyProgram.TYPE_GIFTS:
        # الهدية تُمنح بوحدة واحدة بقرار التاجر
        return Decimal("1")

    # نقاط ومكافآت: النقاط المكتسبة عبر الزيارات المستهدفة
    earned = average_invoice * rate * TARGET_VISITS
    return earned.quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def best_send_time(brand, *, days: int = WINDOW_DAYS) -> dict:
    """
    أفضل يوم وساعة لإرسال حملة، من تاريخ زيارات عملاء هذه العلامة.

    المنطق: الرسالة تصل حين يكون العميل على وشك السلوك الذي
    نريده. أكثر يوم وساعة يشتري فيهما عملاء هذا المتجر هو أقرب
    نافذة إلى ذلك السلوك.

    التوقيت يُقرأ بتوقيت القاهرة لا بـUTC: «الساعة ١٩» بتوقيت
    الخادم تعني ٢١ بتوقيت العميل، وحملة تصل بعد إغلاق المتجر
    بساعتين هي رسالة مدفوعة ضاعت.
    """
    since = timezone.now() - timedelta(days=days)
    rows = Transaction.objects.filter(
        terminal__branch__brand=brand,
        status=Transaction.STATUS_CONFIRMED,
        created_at__gte=since,
    ).values_list("created_at", flat=True)

    by_day: dict[int, int] = defaultdict(int)
    by_hour: dict[int, int] = defaultdict(int)
    sample = 0

    for moment in rows:
        local = timezone.localtime(moment)
        by_day[local.weekday()] += 1
        by_hour[local.hour] += 1
        sample += 1

    if sample < MIN_VISITS:
        return {
            "enough_data": False,
            "sample": sample,
            "needed": MIN_VISITS,
            "window_days": days,
            "days": [],
            "hours": [],
        }

    best_day = max(by_day, key=lambda d: by_day[d])
    best_hour = max(by_hour, key=lambda h: by_hour[h])

    return {
        "enough_data": True,
        "sample": sample,
        "needed": MIN_VISITS,
        "window_days": days,
        "confidence": _confidence(sample, MIN_VISITS),
        "best_day": best_day,
        "best_day_name": WEEKDAY_NAMES[best_day],
        # الساعة التي تسبق الذروة: الرسالة تحتاج وقتًا ليقرأها
        # العميل ويقرّر، ووصولها في الذروة نفسها يصل بعد أن قرّر
        "best_hour": (best_hour - 1) % 24,
        "peak_hour": best_hour,
        "days": [
            {"weekday": index, "name": WEEKDAY_NAMES[index], "visits": by_day.get(index, 0)}
            for index in range(7)
        ],
        "hours": [{"hour": hour, "visits": by_hour.get(hour, 0)} for hour in range(24)],
    }
