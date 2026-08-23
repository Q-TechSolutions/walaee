> ⚠️ مجلد هيكلي — لم يبدأ التنفيذ بعد. المرجع: `docs/demo/architecture/`


# `tests/` — اختبارات عابرة للتطبيقات

اختبارات الوحدة تعيش داخل كل تطبيق (`apps/*/tests/`).
هنا ما يعبر أكثر من تطبيق:

| ملف متوقّع | يغطّي |
|---|---|
| `test_earn_flow.py` | الدورة كاملة: رمز ← مسح ← تأكيد ← قيد |
| `test_permissions_matrix.py` | كل دور × كل نقطة API |
| `test_concurrency.py` | التأكيد المزدوج والمنح المتوازي |
| `test_api_contract.py` | مطابقة OpenAPI عبر schemathesis |

**معيار الإطلاق:** لا يُنشر إصدار وتغطية `apps/ledger` أقل من ١٠٠٪،
أو واختبار التزامن راسب.

المرجع: `docs/demo/architecture/` — قسم ١٢.
