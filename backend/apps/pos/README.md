> ⚠️ مجلد هيكلي — لم يبدأ التنفيذ بعد. المرجع: `docs/demo/architecture/`

# `apps/pos` — نقطة البيع وآلية إثبات الشراء

**الحالة:** ◆ ضمن النطاق

## ما سيُبنى هنا

- تدوير رموز QR كل ٣٠ ثانية في Redis بـ TTL
- scan/resolve — ترجمة الرمز إلى نقطة بيع
- confirm_transaction() — التأكيد الذرّي بقفل الصف
- المسار اليدوي البديل: هاتف + رقم فاتورة

## الملفات المتوقّعة

```
pos/
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

`docs/demo/architecture/` — قسم ٥
