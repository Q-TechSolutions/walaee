# استراتيجية الاختبار

| الطبقة | الأداة | التغطية المطلوبة | ماذا تحمي |
|---|---|---|---|
| وحدة — محرك القيود | `pytest` | **١٠٠٪ إلزامي** | صحة كل جنيه في النظام |
| تزامن | `pytest` + خيوط متوازية | سيناريوهات محددة | التأكيد المزدوج والمنح المتوازي |
| تكامل — دورة المنح | `pytest-django` | المسارات الكاملة | رمز ← مسح ← تأكيد ← قيد |
| عقد API | `schemathesis` | كل النقاط | عدم كسر العملاء المرتبطين |
| صلاحيات | `pytest` | كل دور × كل نقطة | تسريب بيانات بين العلامات |
| حِمل | `locust` | قبل كل توسّع | ثبات الأداء تحت الضغط |
| ميداني | بشري + ساعة إيقاف | كل إصدار | أقل من ١٠ ثوانٍ عند الكاشير |

---

## الاختبار الذي لا يُتنازل عنه

`backend/apps/ledger/tests/test_concurrency.py`

```python
def test_double_confirm_grants_points_once(txn, cashier):
    """ضغطتان متزامنتان على «تأكيد» = منح واحد فقط."""
    errors = []

    def worker():
        try:
            confirm_transaction(txn.id, staff_user=cashier)
        except LedgerError as e:
            errors.append(e)

    threads = [Thread(target=worker) for _ in range(2)]
    [t.start() for t in threads]
    [t.join() for t in threads]

    assert LedgerEntry.objects.filter(transaction=txn).count() == 1
    assert len(errors) == 1                      # الثانية رُفضت
    assert Balance.objects.get(...).amount == expected_once
```

---

## معيار الإطلاق

> لا يُنشر أي إصدار وتغطية `apps/ledger` أقل من **١٠٠٪**، أو واختبار التزامن أعلاه راسب.

خطأ واحد في الرصيد يساوي فقدان ثقة التاجر نهائيًا — وهي خسارة لا تُسترد بإصلاح لاحق.

**ملاحظة تشغيلية:** اختبارات التزامن تحتاج قاعدة بيانات حقيقية لا SQLite،
وتُشغَّل بـ `--no-cov` منفصلة لأن قياس التغطية عبر الخيوط غير موثوق.
