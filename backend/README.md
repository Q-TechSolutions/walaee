> ⚠️ مجلد هيكلي — لم يبدأ التنفيذ بعد. المرجع: `docs/architecture/`


# الخلفية — Django + DRF

## البنية

```
backend/
├── config/           إعدادات المشروع والتوجيه والمهام
│   ├── settings/     base.py · dev.py · prod.py
│   ├── urls.py       توجيه الجذر
│   ├── celery.py     المهام غير المتزامنة
│   └── asgi.py · wsgi.py
├── apps/             أحد عشر تطبيقًا مقسّمة بالمجال — لكل واحد README
├── requirements/     base.txt · dev.txt · prod.txt
├── tests/            اختبارات عابرة للتطبيقات
├── static/ media/ locale/
└── manage.py         (يُولَّد في مرحلة البناء)
```

## قواعد ملزمة

1. **منطق الأعمال في `services.py` فقط** — لا في `views.py` ولا `models.py`.
   الـView يستقبل ويتحقق ويستدعي الخدمة. هذا يجعل نفس المنطق قابلًا للاستدعاء
   من API ومن Celery ومن أوامر الإدارة بلا تكرار.

2. **الرصيد يُعدَّل من مكان واحد:** `apps/ledger/services.apply_entry()`.
   لا يوجد في المشروع كله سطر آخر يكتب في `Balance`.

3. **`LedgerEntry` بنمط append-only** — لا `UPDATE` ولا `DELETE`.
   التصحيح بقيد عكسي جديد عبر `reverse_entry()`.

4. **التسلسل الهرمي كامل من اليوم الأول** حتى لو لم يُستخدم —
   تعديله لاحقًا يكلّف ٣–٦ أشهر ترحيل بيانات.

5. **تغطية اختبارات `apps/ledger` = ١٠٠٪** شرط للدمج، مع اختبار تزامن صريح.

## المرجع

- المعمارية الكاملة: `docs/architecture/`
- المراحل ومعايير القبول: مستودع العرض walaee-demo → `docs/demo/plan/`
- الأدوار ونقاط التسليم: مستودع العرض walaee-demo → `docs/demo/team/`
