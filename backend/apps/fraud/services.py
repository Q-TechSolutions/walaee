"""
تقييم قواعد الشذوذ.

يُستدعى داخل معاملة تأكيد العملية. فشل قاعدة واحدة لا يُسقط العملية:
منع منح نقاط مستحقة بسبب خطأ في كاشف احتيال ضررُه أكبر من نفعه.
"""

import logging

from .models import FraudSignal
from .rules import RULES

logger = logging.getLogger(__name__)


def evaluate(txn) -> list[FraudSignal]:
    """يشغّل كل القواعد ويكتب إشارة لكل مخالفة."""
    signals = []

    for rule_code, rule_fn in RULES.items():
        try:
            result = rule_fn(txn)
        except Exception:  # pragma: no cover - حارس ضد خطأ في قاعدة
            logger.exception("fraud rule failed rule=%s txn=%s", rule_code, txn.pk)
            continue

        if not result:
            continue

        signal, created = FraudSignal.objects.get_or_create(
            transaction=txn,
            rule_code=rule_code,
            defaults={
                "severity": result["severity"],
                "details": result.get("details", {}),
            },
        )
        if created:
            signals.append(signal)
            logger.info(
                "fraud signal rule=%s severity=%s txn=%s",
                rule_code,
                signal.severity,
                txn.pk,
            )

    return signals
