<div align="center">

# walaee · ولائي

**كلنا كسبانين**

منصة إدارة برامج الولاء — متعددة المتاجر

</div>

---

## المستودع مقسوم إلى جزأين

| | | |
|---|---|---|
| 📘 **`docs/`** | التخطيط والتوثيق والعرض | ✅ منتهٍ — مرجع لا يُعدَّل |
| 🛠 **`backend/` · `frontend/` · `infra/`** | المشروع الفعلي | ⬜ الهيكلة جاهزة · البناء لم يبدأ |

**الخريطة الكاملة والتفصيلية:** [`PROJECT_STRUCTURE.md`](PROJECT_STRUCTURE.md)

---

## الهيكلة

```
walaee/
├── docs/                     ① التخطيط · التوثيق · العرض
│   ├── demo/                   النموذج التفاعلي — ٣٠ شاشة + العرض التقديمي
│   ├── reports/                التقارير PDF ومصادرها
│   ├── planning/               القرارات والنطاق المعتمد
│   └── DEPLOY-DEMO.md
│
├── backend/                  ② الخلفية — Django + DRF
│   ├── config/                 الإعدادات والتوجيه والمهام
│   ├── apps/                   ١١ تطبيقًا مقسّمة بالمجال
│   ├── requirements/
│   └── tests/
│
├── frontend/                 ③ الواجهات — ويب فقط
│   ├── customer-pwa/           تطبيق العميل
│   ├── merchant-dashboard/     لوحة صاحب المتجر
│   ├── admin-panel/            لوحة إدارة المنصة
│   └── shared/                 مكوّنات · عميل API · توكنات
│
├── infra/                    ④ البنية والنشر للإنتاج
├── .github/workflows/        ⑤ التكامل والنشر المستمر
│
├── Dockerfile                نشر موقع العرض (docs/demo) — لا يخص الإنتاج
├── nginx.conf
├── docker-compose.yml
└── PROJECT_STRUCTURE.md
```

---

## أين أجد ماذا

| أبحث عن | المسار |
|---|---|
| النموذج التفاعلي والعرض | `docs/demo/` |
| **المخطط المعماري ونموذج البيانات** | `docs/demo/architecture/` |
| خطة التنفيذ ومعايير القبول | `docs/demo/plan/` |
| عرض السعر والباقات | `docs/demo/pricing/` |
| التقارير PDF | `docs/reports/` |
| القرارات المفتوحة | `docs/planning/decisions.md` |
| **بداية المشروع الحقيقي** | `backend/` و `frontend/` |
| قاعدة البيانات | `backend/apps/*/models.py` + `migrations/` |
| واجهات API | `backend/apps/*/views.py` + `config/urls.py` |
| المصادقة والصلاحيات | `backend/apps/accounts/` + `*/permissions.py` |
| لوحة الإدارة | `frontend/admin-panel/` + Django Admin |
| النشر للإنتاج | `infra/` |

---

## تشغيل موقع العرض

```bash
docker build -t walaee-demo .
docker run -d -p 8090:80 walaee-demo
# http://localhost:8090/demo/
```

المسارات بعد النشر لم تتغيّر: `/demo/` · `/Walaee_Analysis_Report_AR.pdf` وغيرها.
التفاصيل في [`docs/DEPLOY-DEMO.md`](docs/DEPLOY-DEMO.md).

---

## القرارات المعمارية غير الرجعية

مأخوذة من التخطيط ومُلزمة أثناء البناء:

1. **`LedgerEntry` بنمط append-only** — لا تعديل ولا حذف. أي تصحيح بقيد عكسي.
2. **`select_for_update()` على الرصيد** — بدونه ضغطتان متزامنتان تمنحان النقاط مرتين.
3. **التسلسل الهرمي من اليوم صفر** — مؤسسة ← علامة ← فرع ← نقطة بيع ← كاشير.
4. **رصيد منفصل لكل علامة** — يتجنّب تحوّل المنصة إلى نظام مقاصة مالية.
5. **مفاتيح ميزات حسب الباقة** — الباقات الثلاث من قاعدة كود واحدة.

التفاصيل: `docs/demo/architecture/` و `docs/planning/decisions.md`.

---

## الحالة

| المرحلة | الحالة |
|---|---|
| التحليل والجدوى | ✅ منتهٍ |
| تصميم الواجهات — ٣٠ شاشة | ✅ منتهٍ |
| المخطط المعماري | ✅ منتهٍ |
| خطة التنفيذ والتسعير | ✅ منتهٍ |
| **فصل الهيكلة** | ✅ **منتهٍ** |
| الخلفية · الواجهات · الإنتاج | ⬜ لم تبدأ |

**الخطوة التالية:** حسم القرارات المتبقية في `docs/planning/decisions.md` (البنود ٦ · ٧ · ٨)، ثم بدء المرحلة الأولى.

---

<div align="center">

**ولائي… كلنا كسبانين.**

</div>
