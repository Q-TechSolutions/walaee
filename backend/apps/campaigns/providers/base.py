"""عقد مزوّد الرسائل."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class SmsMessage:
    phone: str
    body: str
    provider_msg_id: str = ""
    cost: Decimal = Decimal("0")


class SmsProvider(ABC):
    """
    كل مزوّد يلتزم بهذا العقد.

    `cost` مطلوب لأن موجّه القنوات يقرّر على أساس التكلفة:
    push مجاني ← whatsapp ← sms. بلا تكلفة معروفة لا يمكن التوجيه.
    """

    key: str = "abstract"

    @abstractmethod
    def send(self, *, phone: str, body: str) -> SmsMessage:
        """يرسل رسالة واحدة ويُرجع نتيجتها بتكلفتها."""

    def estimate_cost(self, *, count: int) -> Decimal:
        return Decimal("0")
