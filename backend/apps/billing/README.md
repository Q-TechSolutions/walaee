> ⬜ **المرحلة الثانية.** مفاتيح الميزات تُقرأ حاليًا من متغيرات البيئة لا من `Subscription` — راجع `config/settings/base.py`.
>
> المرجع: `docs/architecture/`

# `apps/billing` — الاشتراكات والفوترة

**الحالة:** ◆ ضمن النطاق

## ما سيُبنى هنا

- Subscription — الباقات الأربع وحدودها
- Invoice — الفواتير الشهرية
- MessageCredit — رصيد الرسائل
- فرض الجدار المجاني على كل طلب

## الملفات المتوقّعة

```
billing/
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

`docs/architecture/` — قسم ٤.٤
