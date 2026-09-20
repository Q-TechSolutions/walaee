"""
تحويل بنكي يدوي — البوابة الافتراضية.

ليست بديلًا مؤقتًا بلا قيمة: أول عملاء المنصة في السوق المحلي
يسدّدون بالتحويل أو الإيداع فعلًا، والسداد يُعلَّم يدويًا من لوحة
إدارة المنصة بعد مطابقة كشف الحساب.
"""

from decimal import Decimal

from django.conf import settings

from .base import PaymentGateway, PaymentIntent


class ManualTransferGateway(PaymentGateway):
    key = "manual"
    label = "تحويل بنكي"

    def create_intent(self, *, invoice) -> PaymentIntent:
        account = getattr(settings, "BANK_ACCOUNT_DETAILS", "")
        return PaymentIntent(
            reference=invoice.number,
            amount=Decimal(invoice.total),
            instructions=(
                f"حوّل مبلغ {invoice.total} جنيهًا إلى:\n{account}\n"
                f"واكتب رقم الفاتورة {invoice.number} في خانة الملاحظات."
            ),
        )

    def verify_callback(self, payload: dict) -> tuple[str, bool]:
        # لا إشعار آلي في التحويل اليدوي — السداد يُعلَّم من اللوحة
        raise NotImplementedError("التحويل اليدوي لا يستقبل إشعارات. يُعلَّم السداد من لوحة الإدارة.")
