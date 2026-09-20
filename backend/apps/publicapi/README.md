> ○ **مؤجّل.** خارج النطاق المبدئي (`docs/planning/scope.md`). المجلد موجود ليُستقبَل بلا إعادة بناء. يُفعَّل بـ `FEATURE_PUBLIC_API=1`.
>
> المرجع: `docs/architecture/`

# `apps/publicapi` — الواجهات البرمجية العامة و Webhooks

**الحالة:** ○ مؤجّل — يُفعَّل بمفتاح FEATURE_PUBLIC_API

## ما سيُبنى هنا

- ApiKey — مفاتيح مُجزّأة بصلاحيات
- WebhookEndpoint — الوجهات والأحداث
- توقيع HMAC-SHA256 وإعادة المحاولة بتراجع أسّي
- بيئة تجريب Sandbox

## الملفات المتوقّعة

```
publicapi/
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

`docs/architecture/` — قسم ٧.٣
