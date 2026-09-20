"""عقد مزوّدي القنوات."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class SentMessage:
    phone: str
    body: str
    provider_msg_id: str = ""
    cost: Decimal = Decimal("0")


class ChannelProvider(ABC):
    """
    كل مزوّد يلتزم بهذا العقد.

    `cost` مطلوب لأن الموجّه يقرّر على أساس التكلفة: push مجاني ←
    whatsapp ← sms. بلا تكلفة معروفة لا يمكن التوجيه ولا عرض رقم
    للتاجر قبل الإرسال.
    """

    key: str = "abstract"
    channel: str = ""

    @abstractmethod
    def send(self, *, phone: str, body: str) -> SentMessage:
        """يرسل رسالة واحدة ويُرجع نتيجتها."""

    def estimate_cost(self, *, count: int) -> Decimal:
        from apps.campaigns.router import CHANNEL_COST

        return CHANNEL_COST.get(self.channel, Decimal("0")) * count


class SmsProvider(ChannelProvider):
    """مزوّد رسائل نصية — يُستخدم أيضًا في إرسال أكواد OTP."""

    channel = "sms"


# اسم قديم أبقيناه لأن apps.accounts.services يستورده
SmsMessage = SentMessage
