> ⚠️ مجلد هيكلي — لم يبدأ التنفيذ بعد. المرجع: `docs/architecture/`

# `apps/ledger` — القلب المالي — القيود والعمليات

**الحالة:** ◆◆ الأخطر — تغطية اختبارات ١٠٠٪ إلزامية

## ما سيُبنى هنا

- Transaction — العملية مرتبطة بالفاتورة والكاشير
- LedgerEntry — قيد append-only: لا تعديل ولا حذف أبدًا
- Redemption — الاستبدال وكود التحقق
- apply_entry() — المكان الوحيد الذي يعدّل الرصيد
- reverse_entry() — التصحيح الوحيد المسموح

## الملفات المتوقّعة

```
ledger/
├── models.py         النماذج والهجرات
├── serializers.py    تحويل البيانات
├── views.py          نقاط API — استقبال وتحقق فقط
├── services.py       ◆ منطق الأعمال كله هنا
├── permissions.py    صلاحيات الأدوار
├── tasks.py          مهام Celery
├── admin.py          تسجيل في Django Admin
├── urls.py           مسارات التطبيق
└── tests/            اختبارات الوحدة والتكامل
```

## المرجع

`docs/architecture/` — قسم ٤.٣ و ٦
