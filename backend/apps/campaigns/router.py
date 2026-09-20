"""
موجّه القنوات بالتكلفة.

القرار الوحيد هنا: **ما أرخص قناة تصل لهذا العميل فعلًا؟**

الترتيب push ← whatsapp ← sms ليس تفضيلًا جماليًا. الفرق بين
إشعار مجاني ورسالة نصية هو الفرق بين حملة تكلّف صفرًا وحملة تكلّف
مئات الجنيهات على نفس القائمة. تاجر يكتشف ذلك بعد الإرسال يلغي
اشتراكه — لذلك التكلفة تُحسب وتُعرض قبل الضغط على «إرسال».
"""

from dataclasses import dataclass
from decimal import Decimal

from .models import Channel

# التكلفة التقديرية للرسالة الواحدة بالجنيه.
# قيم مبدئية تُضبَط عند التعاقد مع المزوّد (القرار ٧ في decisions.md)
# — ولهذا تعيش هنا في مكان واحد لا مبعثرة في الكود.
CHANNEL_COST: dict[str, Decimal] = {
    Channel.PUSH: Decimal("0"),
    Channel.WHATSAPP: Decimal("0.35"),
    Channel.SMS: Decimal("0.60"),
}

DEFAULT_PRIORITY = [Channel.PUSH, Channel.WHATSAPP, Channel.SMS]


@dataclass(frozen=True)
class Route:
    """القناة المختارة لمستلم وتكلفتها."""

    channel: str | None
    cost: Decimal

    @property
    def reachable(self) -> bool:
        return self.channel is not None


def pick_channel(customer, priority: list[str] | None = None) -> Route:
    """
    أرخص قناة تصل لهذا العميل.

    `Route(None, 0)` تعني «لا يمكن الوصول إليه» — لا رسالة ولا
    تكلفة. إرسال إلى قناة غير متاحة يخصم رصيدًا مقابل لا شيء.
    """
    for channel in priority or DEFAULT_PRIORITY:
        if _can_reach(customer, channel):
            return Route(channel=channel, cost=CHANNEL_COST.get(channel, Decimal("0")))
    return Route(channel=None, cost=Decimal("0"))


def _can_reach(customer, channel: str) -> bool:
    if channel == Channel.PUSH:
        # اشتراك Web Push مخزَّن يعني متصفحًا ثبّت التطبيق فعلًا
        return bool(customer.push_subscription)
    if channel in (Channel.WHATSAPP, Channel.SMS):
        return bool(customer.phone) and not customer.phone.startswith("deleted-")
    return False


@dataclass(frozen=True)
class Estimate:
    """تقدير حملة قبل الإرسال."""

    recipients: int
    reachable: int
    unreachable: int
    cost: Decimal
    per_channel: dict[str, int]
    billable_messages: int

    def as_dict(self) -> dict:
        return {
            "recipients": self.recipients,
            "reachable": self.reachable,
            "unreachable": self.unreachable,
            "cost": str(self.cost),
            "billable_messages": self.billable_messages,
            "per_channel": {
                channel: {
                    "count": count,
                    "unit_cost": str(CHANNEL_COST.get(channel, Decimal("0"))),
                    "label": Channel(channel).label,
                }
                for channel, count in self.per_channel.items()
            },
        }


def estimate(memberships, priority: list[str] | None = None) -> Estimate:
    """
    يحسب تكلفة الحملة قبل إرسالها.

    يمر على المستلمين فعليًا لا بتقدير إحصائي: نسبة من ثبّت التطبيق
    تختلف اختلافًا حادًّا بين متجر وآخر، والتقدير المتوسط يعطي رقمًا
    خاطئًا بأضعاف.
    """
    per_channel: dict[str, int] = {}
    total_cost = Decimal("0")
    reachable = 0
    billable = 0
    recipients = 0

    for membership in memberships.select_related("customer").iterator(chunk_size=500):
        recipients += 1
        route = pick_channel(membership.customer, priority)

        if not route.reachable:
            continue

        reachable += 1
        per_channel[route.channel] = per_channel.get(route.channel, 0) + 1
        total_cost += route.cost
        if route.cost > 0:
            billable += 1

    return Estimate(
        recipients=recipients,
        reachable=reachable,
        unreachable=recipients - reachable,
        cost=total_cost,
        per_channel=per_channel,
        billable_messages=billable,
    )


def render(template: str, *, customer, brand, balance=None) -> str:
    """
    يملأ قالب الرسالة.

    `format_map` مع قاموس افتراضي لا `format`: متغيّر غير معروف في
    القالب يجب أن يظهر كما هو لا أن يُسقِط إرسال الحملة كلها.
    """

    class _Safe(dict):
        def __missing__(self, key):
            return "{" + key + "}"

    return template.format_map(
        _Safe(
            name=customer.full_name or "عميلنا العزيز",
            brand=brand.name,
            balance=balance if balance is not None else "",
        )
    )
