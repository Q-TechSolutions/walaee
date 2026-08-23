> ⚠️ مجلد هيكلي — لم يبدأ التنفيذ بعد. المرجع: `docs/demo/architecture/`

# `apps/tenancy` — الهيكل التنظيمي متعدد المستويات

**الحالة:** ◆ ضمن النطاق

## ما سيُبنى هنا

- Organization → Brand → Branch → Terminal → StaffUser
- صلاحيات على كل مستوى وتقارير قابلة للتجميع
- BrandScopedQuerySet — عزل بيانات كل علامة
- حساب مستقل لكل كاشير

## الملفات المتوقّعة

```
tenancy/
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

`docs/demo/architecture/` — قسم ٤.١
