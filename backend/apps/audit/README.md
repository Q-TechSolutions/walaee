> ⚠️ مجلد هيكلي — لم يبدأ التنفيذ بعد. المرجع: `docs/architecture/`

# `apps/audit` — سجل التدقيق

**الحالة:** ◆ ضمن النطاق

## ما سيُبنى هنا

- AuditLog — سجل غير قابل للحذف
- Middleware يلتقط كل تغيير مع الفاعل والعنوان
- الاحتفاظ ٢٤ شهرًا

## الملفات المتوقّعة

```
audit/
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

`docs/architecture/` — قسم ٤.٣ و ٩
