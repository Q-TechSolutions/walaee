<div align="center">

# walaee · ولائي

**كلنا كسبانين**

منصة إدارة برامج الولاء — متعددة المتاجر

`Django 5` · `DRF` · `PostgreSQL 16` · `Redis 7` · `Celery` · `Vite PWA`

</div>

---

> 🛠 **هذا مستودع المنتج — الكود الفعلي.**
> العرض التقديمي والنموذج التفاعلي والتقارير في مستودع منفصل:
> **[github.com/mohamedN2018/walaee-demo](https://github.com/mohamedN2018/walaee-demo)**

---

## الهيكلة

```
walaee/
├── backend/                  Django 5 + DRF
│   ├── config/                 الإعدادات · التوجيه · Celery
│   │   └── settings/           base · dev · prod · test
│   ├── apps/                   تقسيم بالمجال لا بالنوع
│   │   ├── common/             أسس مشتركة — نماذج قاعدية · أخطاء · ترقيم
│   │   ├── accounts/           المصادقة · OTP · الصلاحيات · الخصوصية
│   │   ├── tenancy/            مؤسسة ← علامة ← فرع ← نقطة بيع ← كاشير
│   │   ├── loyalty/            النماذج الستة · القواعد · المكافآت · الرصيد
│   │   ├── ledger/       ◆◆    القلب المالي — القيود append-only
│   │   ├── pos/                رموز QR · المسح · التأكيد الذرّي
│   │   ├── fraud/              كشف الشذوذ · السقوف · المراجعة
│   │   ├── audit/              سجل التدقيق غير القابل للحذف
│   │   ├── campaigns/    ⬜    الحملات — المرحلة الثانية
│   │   ├── billing/      ⬜    الاشتراكات — المرحلة الثانية
│   │   ├── publicapi/    ○     API + Webhooks — مؤجّل بمفتاح ميزة
│   │   └── insights/     ○     التحليلات الذكية — مؤجّل بمفتاح ميزة
│   ├── requirements/           base · dev · prod
│   └── manage.py
│
├── frontend/                 ويب فقط — لا سطح مكتب ولا Electron
│   ├── customer-pwa/           تطبيق العميل — PWA · قراءة QR
│   ├── merchant-dashboard/     لوحة صاحب المتجر
│   ├── admin-panel/            لوحة إدارة المنصة
│   └── shared/                 ui · api-client · tokens · utils
│
├── infra/                    البنية والنشر للإنتاج
├── docs/
│   ├── architecture/           ◆ عقد البناء المُلزِم
│   └── planning/               القرارات والنطاق المعتمد
│
├── .env.example
├── docker-compose.yml        بيئة التطوير المحلية
└── Makefile
```

◆◆ الأخطر — تغطية اختبارات ١٠٠٪ إلزامية · ○ خارج النطاق المبدئي

---

## البدء

```bash
cp .env.example .env       # ثم املأ القيم
make up                    # PostgreSQL + Redis
make install               # تثبيت الاعتماديات
make migrate
make seed                  # بيانات تجريبية
make run                   # http://localhost:8000
```

`make help` يعرض كل الأوامر.

**المنافذ المحلية:** PostgreSQL على `5433` و Redis على `6380` — مُزاحة عمدًا
تفاديًا للتعارض مع خدمات أخرى على الجهاز.

---

## القواعد الملزمة أثناء البناء

كسر أي منها يعني إعادة بناء، لا إصلاحًا:

1. **الرصيد يُعدَّل من مكان واحد:** `apps.ledger.services.apply_entry()`.
2. **`LedgerEntry` بنمط append-only** — التصحيح بقيد عكسي لا بتعديل أو حذف.
3. **`select_for_update()` على الرصيد** — بدونه ضغطتان متزامنتان تمنحان النقاط مرتين.
4. **التسلسل الهرمي كامل من اليوم الأول** حتى لو لم يُستخدم.
5. **منطق الأعمال في `services.py` فقط** — الـView يستقبل ويتحقق ويستدعي.
6. **تغطية `apps/ledger` = ١٠٠٪** شرط للدمج، مع اختبار تزامن صريح.
7. **RTL كامل** ولا تباعد حروف على النص العربي.
8. **توكنات التصميم من مصدر واحد** — `frontend/shared/tokens/`.

التفاصيل الكاملة في [`docs/architecture/`](docs/architecture/).

---

## أين أجد ماذا

| أبحث عن | المسار |
|---|---|
| **عقد البناء المُلزِم** | [`docs/architecture/`](docs/architecture/) |
| نموذج البيانات — ٢١ جدولًا | [`docs/architecture/data-model.md`](docs/architecture/data-model.md) |
| عقد API — ٤٧ نقطة | [`docs/architecture/api-contract.md`](docs/architecture/api-contract.md) |
| تعريف الجداول | `backend/apps/*/models.py` |
| منطق الأعمال | `backend/apps/*/services.py` |
| المسارات | `backend/config/urls.py` + `backend/apps/*/urls.py` |
| الصلاحيات | `backend/apps/*/permissions.py` |
| النشر للإنتاج | `infra/` |
| القرارات المفتوحة | [`docs/planning/decisions.md`](docs/planning/decisions.md) |

---

## الحالة

| المرحلة | الحالة |
|---|---|
| التحليل والتخطيط والتصميم | ✅ منتهٍ — في مستودع `walaee-demo` |
| فصل مستودع المنتج | ✅ منتهٍ |
| **المرحلة ١ — الأساس** | 🔨 قيد التنفيذ |
| المرحلة ٢ — الحملات والفوترة | ⬜ |
| المرحلة ٣ — الواجهات الثلاث | ⬜ |
| الإنتاج | ⬜ |

**⚠ قرارات مفتوحة تُحسم قبل المرحلة ٢:** القطاع والبقعة الجغرافية · مزوّد الرسائل المحلي ·
بوابة الدفع. التفاصيل في [`docs/planning/decisions.md`](docs/planning/decisions.md).

---

<div align="center">

**ولائي… كلنا كسبانين.**

</div>
