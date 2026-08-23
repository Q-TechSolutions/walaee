# هيكلة مشروع ولائي

فصل كامل بين **مرحلة التخطيط** (منتهية) و**المشروع الفعلي** (لم يبدأ بعد).
كل ما في `docs/` مرجع لا يُعدَّل أثناء البناء. وكل ما في `backend/` و`frontend/` هو ما سيُبنى.

> الهيكلة مشتقّة حرفيًا من **`docs/demo/architecture/`** القسم ٣ — لم يُغيَّر شيء في التخطيط أو المعمارية.

---

## الخريطة العامة

```
walaee/
│
├── docs/ ─────────────────────── ① التخطيط والتوثيق والعرض  (مرجع · منتهٍ)
│   ├── demo/                     النموذج التفاعلي (٢٤ شاشة + العرض التقديمي)
│   ├── reports/                  التقارير PDF ومصادرها
│   ├── planning/                 مراجع التخطيط ونقاط القرار
│   └── DEPLOY-DEMO.md            نشر موقع العرض
│
├── backend/ ──────────────────── ② الخلفية  (Django + DRF)
├── frontend/ ─────────────────── ③ الواجهات  (٣ تطبيقات ويب)
├── infra/ ────────────────────── ④ البنية والنشر
├── .github/workflows/ ────────── ⑤ التكامل والنشر المستمر
│
├── Dockerfile · nginx.conf · docker-compose.yml    نشر موقع العرض (docs/demo)
└── README.md · PROJECT_STRUCTURE.md
```

---

## ① `docs/` — التخطيط والتوثيق والعرض

كل مخرجات مرحلة التخطيط. **لا يُبنى منها شيء — تُقرأ فقط.**

```
docs/
├── demo/                          النموذج التفاعلي — يُخدَم على /demo/
│   ├── index.html                 فهرس المشروع
│   ├── present/                   العرض التقديمي — ١٨ شريحة ثلاثية الأبعاد
│   ├── preview/                   تصفّح الواجهات داخل إطارات أجهزة
│   ├── customer/                  تطبيق العميل — ١٢ شاشة
│   ├── merchant/                  لوحة صاحب المتجر — ١١ شاشة
│   ├── admin/                     لوحة إدارة المنصة — ٧ شاشات
│   ├── solutions/                 من المشكلة إلى الشاشة — ١٦ حلًّا
│   ├── pricing/                   عرض السعر والباقات
│   ├── plan/                      خطة التطوير — ٦ مراحل ومعايير قبول
│   ├── architecture/              ◆ المخطط المعماري — مرجع البناء الأساسي
│   ├── team/                      دليل الفريق ودورة التطوير (داخلي)
│   └── assets/                    نظام التصميم — css · js · icons
│
├── reports/
│   ├── Walaee_Analysis_Report_AR.pdf          التحليل الشامل — ٢٦ صفحة
│   ├── Walaee_Analysis_Report_AR.html         مصدر التقرير
│   ├── Walaee_Pricing_Proposal_AR.pdf         عرض السعر — ٧ صفحات
│   └── Walaee_Executive_Brief_Book_Mobile.pdf الوثيقة الأصلية
│
├── planning/
│   ├── decisions.md               قرارات المرحلة صفر وحالتها
│   └── scope.md                   النطاق المعتمد وما أُجِّل
│
└── DEPLOY-DEMO.md
```

**أين تجد ماذا في التخطيط**

| تريد | افتح |
|---|---|
| طبقات النظام | `docs/demo/architecture/` — قسم ١ |
| الحزمة التقنية بإصداراتها | قسم ٢ |
| بنية المشروع البرمجي | قسم ٣ |
| **نموذج البيانات (٢١ جدولًا)** | قسم ٤ |
| تدفق تنفيذ العملية الحرجة | قسم ٥ |
| الكود الحرج — محرك القيود | قسم ٦ |
| **واجهات API (٤٧ نقطة)** | قسم ٧ |
| المهام غير المتزامنة | قسم ٨ |
| الأمان والصلاحيات | قسم ٩ |
| Docker والنشر | قسم ١٠ |
| متغيرات البيئة | قسم ١١ |
| استراتيجية الاختبار | قسم ١٢ |
| المراحل ومعايير القبول | `docs/demo/plan/` |
| الأدوار ونقاط التسليم | `docs/demo/team/` |
| المشاكل وحلولها | `docs/demo/solutions/` |

---

## ② `backend/` — الخلفية

Django 5 + DRF. تقسيم بالمجال لا بالنوع — كل تطبيق يملك نماذجه وخدماته واختباراته.

```
backend/
├── config/                        إعدادات المشروع
│   ├── settings/                  base · dev · prod
│   ├── urls.py                    توجيه الجذر
│   ├── celery.py                  المهام غير المتزامنة
│   └── asgi.py · wsgi.py
│
├── apps/
│   ├── accounts/    ◆ المصادقة والصلاحيات  User · Customer · OTP · الموافقة
│   ├── tenancy/     ◆ الهيكل التنظيمي      Organization → Brand → Branch → Terminal → StaffUser
│   ├── loyalty/     ◆ نظام الولاء          LoyaltyProgram · ProgramRule · Reward · Membership · Balance
│   ├── ledger/      ◆◆ القلب المالي        Transaction · LedgerEntry (append-only) · Redemption
│   ├── pos/         ◆ نقطة البيع           تدوير رموز QR · resolve · confirm · المسار اليدوي
│   ├── fraud/       ◆ كشف الاحتيال         محرك القواعد · FraudSignal · المراجعة
│   ├── campaigns/   ◆ الحملات              Campaign · MessageJob · موجّه القنوات بالتكلفة
│   ├── billing/     ◆ الاشتراكات           Subscription · Invoice · MessageCredit · الجدار المجاني
│   ├── audit/       ◆ سجل التدقيق          AuditLog + middleware
│   ├── publicapi/   ○ واجهات عامة          ApiKey · Webhook   — تطوير مستقبلي
│   └── insights/    ○ التحليلات الذكية     AiInsight          — تطوير مستقبلي
│
├── requirements/                  base · dev · prod
├── tests/                         اختبارات شاملة عابرة للتطبيقات
├── static/ · media/ · locale/
└── manage.py                      (يُولَّد في مرحلة البناء)
```

◆ ضمن النطاق المعتمد · ○ مؤجّل للتطوير المستقبلي (مفاتيح ميزات، نفس قاعدة الكود)

**قاعدة معمارية غير قابلة للكسر:** كل تعديل على الرصيد يمر عبر
`backend/apps/ledger/services.py → apply_entry()`. لا يوجد في المشروع كله سطر آخر
يكتب في جدول `Balance` مباشرة.

### قاعدة البيانات

| ماذا | أين |
|---|---|
| تعريف الجداول | `backend/apps/*/models.py` |
| الهجرات | `backend/apps/*/migrations/` |
| مخطط ERD المرجعي | `docs/demo/architecture/` — قسم ٤ |
| إعداد الخادم محليًا | `infra/docker/` + `docker-compose.dev.yml` |
| سكربتات التهيئة | `infra/postgres/` |
| النسخ الاحتياطي | `infra/scripts/` |

### واجهات API

| ماذا | أين |
|---|---|
| المسارات | `backend/config/urls.py` + `backend/apps/*/urls.py` |
| العرض والتسلسل | `backend/apps/*/views.py` · `serializers.py` |
| منطق الأعمال | `backend/apps/*/services.py` |
| التوثيق التلقائي | `/api/schema/` عبر drf-spectacular |
| العقد المرجعي | `docs/demo/architecture/` — قسم ٧ |

### المصادقة والصلاحيات

| ماذا | أين |
|---|---|
| هوية العميل والتاجر | `backend/apps/accounts/models.py` |
| تسجيل الدخول بالهاتف و OTP | `backend/apps/accounts/services.py` |
| توكنات JWT | `backend/config/settings/base.py` |
| صلاحيات الأدوار الخمسة | `backend/apps/*/permissions.py` |
| عزل بيانات العلامات | `backend/apps/tenancy/managers.py` |

---

## ③ `frontend/` — الواجهات

ثلاثة تطبيقات ويب مستقلة تشترك في مكتبة واحدة. **ويب فقط — لا يوجد تطبيق سطح مكتب ولا Electron.**

```
frontend/
├── customer-pwa/          تطبيق العميل — PWA · Service Worker · قراءة QR
├── merchant-dashboard/    لوحة صاحب المتجر — الكاشير · العملاء · الحملات · الحوكمة
├── admin-panel/           لوحة إدارة المنصة — الإيراد · المتاجر · مؤشرات الصحة
└── shared/
    ├── ui/                مكوّنات مشتركة
    ├── api-client/        عميل API مولّد من OpenAPI
    ├── tokens/            توكنات التصميم — مصدرها docs/demo/assets/css/theme.css
    └── utils/             تنسيق · تواريخ · أرقام عربية · RTL
```

**لوحة الإدارة موجودة في مكانين مختلفين ومقصودين:**
`frontend/admin-panel/` لوحة أعمال لمالك المنصة (الإيراد والمؤشرات) ·
Django Admin على `/django-admin/` أداة تشغيلية للفريق التقني فقط.

---

## ④ `infra/` — البنية والنشر

```
infra/
├── docker/        Dockerfile للخلفية والواجهات + compose الإنتاج
├── nginx/         الوكيل العكسي وتوجيه /api
├── postgres/      تهيئة قاعدة البيانات
├── scripts/       نقطة الدخول · النسخ الاحتياطي · الاسترجاع
└── ci/            فحوص الجودة
```

> ملفات `Dockerfile` و`nginx.conf` و`docker-compose.yml` **في الجذر** تخص
> **موقع العرض فقط** (`docs/demo`) وهي التي ينشرها Dokploy حاليًا. لا تخلطها ببنية الإنتاج.

---

## كيف ترتبط الأجزاء

```
                     ┌──────────────── المتصفح ────────────────┐
                     │                                          │
        customer-pwa           merchant-dashboard          admin-panel
        (العميل)                 (التاجر)                   (المنصة)
             │                        │                        │
             └────────── HTTPS · JSON ─┴────────────────────────┘
                                  │
                            infra/nginx
                    ملفات ثابتة · TLS · تحديد المعدل
                                  │  /api/*
                                  ▼
                    backend/config/urls.py
                                  │
              ┌───────────────────┼───────────────────┐
              ▼                   ▼                   ▼
        apps/accounts        apps/pos           apps/loyalty
        (مصادقة وصلاحية)   (رمز · مسح · تأكيد)   (قواعد المنح)
              │                   │                   │
              └───────────────────┼───────────────────┘
                                  ▼
                    apps/ledger/services.apply_entry()
                       ◆ المكان الوحيد لتعديل الرصيد
                                  │
              ┌───────────────────┼───────────────────┐
              ▼                   ▼                   ▼
        LedgerEntry           apps/audit          apps/fraud
        (append-only)         (سجل تدقيق)        (كشف الشذوذ)
              │
              ▼
        PostgreSQL ◄──── Redis (رموز QR · كاش · طوابير)
                              │
                              ▼
                    Celery worker + beat
        إشعارات · Webhooks · انتهاء الصلاحية · تقارير · فوترة
```

**مسار العملية الحرجة عبر الطبقات**

| # | الخطوة | المكوّن |
|---|---|---|
| ١ | توليد رمز كل ٣٠ ثانية | `apps/pos` + Celery beat → Redis |
| ٢ | العميل يمسح الرمز | `customer-pwa` → `POST /scan/resolve` |
| ٣ | إدخال قيمة الفاتورة | `apps/pos` → عملية بحالة `pending` |
| ٤ | التاجر يؤكّد | `merchant-dashboard` → `apps/pos.confirm_transaction()` |
| ٥ | **منح النقاط ذرّيًا** | `apps/ledger.apply_entry()` داخل معاملة واحدة |
| ٦ | ما بعد التأكيد | Celery: إشعار · Webhook · تحديث المؤشرات |

المرجع الكامل: `docs/demo/architecture/` — قسم ٥.

---

## حالة المشروع

| الجزء | الحالة |
|---|---|
| التحليل والجدوى | ✅ منتهٍ — `docs/reports/` |
| المخطط المعماري | ✅ منتهٍ — `docs/demo/architecture/` |
| تصميم الواجهات | ✅ منتهٍ — `docs/demo/` ٢٤ شاشة |
| خطة التنفيذ والتسعير | ✅ منتهٍ — `docs/demo/plan/` · `pricing/` |
| **هيكلة المشروع** | ✅ **جاهزة — هذا الملف** |
| الخلفية | ⬜ لم تبدأ |
| الواجهات | ⬜ لم تبدأ |
| البنية والنشر للإنتاج | ⬜ لم تبدأ |

**الخطوة التالية:** المرحلة صفر — حسم القرارات في `docs/planning/decisions.md` قبل أول سطر كود.
