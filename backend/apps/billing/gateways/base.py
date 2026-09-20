"""
عقد بوابة الدفع.

القرار ٨ في docs/planning/decisions.md (Paymob أو Fawry) لم يُحسم.
البناء لم يتوقف عليه: الفوترة كاملة خلف هذا العقد، وإضافة بوابة
فعلية لاحقًا = ملف جديد هنا وتغيير متغيّر بيئة واحد.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class PaymentIntent:
    """نية دفع: ما يُعرض على التاجر ليسدّد."""

    reference: str
    amount: Decimal
    instructions: str
    checkout_url: str = ""
    expires_at: str = ""


class PaymentGateway(ABC):
    key: str = "abstract"
    label: str = ""

    @abstractmethod
    def create_intent(self, *, invoice) -> PaymentIntent:
        """يُنشئ نية دفع لفاتورة."""

    @abstractmethod
    def verify_callback(self, payload: dict) -> tuple[str, bool]:
        """
        يتحقق من إشعار البوابة.

        يُرجع (مرجع الفاتورة، هل نجح السداد).
        التحقق من التوقيع مسؤولية كل بوابة: قبول إشعار بلا تحقق
        يعني أن أي طرف يستطيع تعليم فواتيره كمسدّدة.
        """
