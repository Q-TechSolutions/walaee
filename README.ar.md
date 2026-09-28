<div align="center">

# walaee · ولائي

**كلنا كسبانين**

منصة إدارة برامج الولاء — متعددة المتاجر

`Django 5` · `DRF` · `PostgreSQL 16` · `Redis 7` · `Celery` · `Vite PWA`

</div>

<div align="center">

<a href="README.md">English</a> · <a href="https://walaee.deplois.net"><b>عرض حيّ</b></a>

</div>

---

## 🔗 مباشر

| | الرابط |
|---|---|
| **المنصة** | <https://walaee.deplois.net> |
| تطبيق العميل | <https://walaee.deplois.net/app/> |
| لوحة المتجر | <https://walaee.deplois.net/merchant/> |
| لوحة المنصة | <https://walaee.deplois.net/admin/> |
| **النموذج التفاعلي** | <https://walaee.deplois.net/demo/> |
| الدليل العام (API) | <https://walaee.deplois.net/api/v1/public/network> |

الدخول بحسابات معلنة — الجدول في [docs/DEPLOY.md](docs/DEPLOY.md#الحسابات).
هذا **نشر عرض** لا إنتاج بعملاء حقيقيين.

---

## الفروع

| الفرع | ماذا يحوي | يُنشَر على |
|---|---|---|
| **`main`** | 🛠 **الإنتاج** — backend · frontend · infra · `docs/demo` | `walaee.deplois.net` |
| **`demo`** | 📘 العرض الكامل — النموذج والتقارير والتحليل | نطاق داخلي |
| **`client`** | 👁 العرض المصغّر — ما يراه العميل فقط | نطاق العميل |

`main` يحوي **نسخة من النموذج التفاعلي وحده** في `docs/demo/`، تُخدَم على
`/demo/` من نفس الحاوية. هو التصميم المعتمد الذي تُقاس عليه الشاشات، ومن
يفتح رابط المشروع يحتاج أن يرى الاثنين جنبًا إلى جنب بلا نشر ثانٍ.

ما يبقى على فرع `demo` وحده: التقارير والتحليل والخطة والتسعير والفريق —
أي شيء ليس واجهة. ولا يحوي فرعا العرض سطر كود منتج:

```bash
git ls-tree --name-only main     # backend frontend infra docs …
git ls-tree --name-only demo     # docs Dockerfile nginx.conf …
git ls-tree --name-only client   # docs Dockerfile nginx.conf
```

`client` **مولَّد آليًا** من `demo` ولا يُعدَّل يدويًا:

```bash
git checkout demo
bash scripts/make-client-branch.sh
git push -f origin client
```

السكربت يحذف الخطة والمعمارية والفريق والحلول والتحليل الشامل، ثم
**يفشل** إن بقيت أي إشارة إليها.

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
│   ├── landing/                 الصفحة العامة · خريطة التغطية · 5172
│   ├── customer-pwa/           تطبيق العميل — PWA · قراءة QR · 5173
│   ├── merchant-dashboard/     لوحة صاحب المتجر · شاشة الكاشير · 5174
│   ├── admin-panel/            لوحة إدارة المنصة · 5175
│   └── shared/                 توكنات · عميل API · مكوّنات · تنسيق عربي
│
├── infra/                    البنية والنشر للإنتاج
│   ├── docker/                 صور الخلفية والواجهات + compose الإنتاج
│   ├── nginx/                  الحافة — تمرير /api وخدمة الواجهات
│   ├── postgres/               الامتدادات وحارس append-only
│   └── scripts/                نقطة الدخول
├── docs/
│   ├── architecture/           ◆ عقد البناء المُلزِم
│   └── planning/               القرارات والنطاق المعتمد
│
├── .env.local            # للتطوير
├── .env.production       # للنشر
├── docker-compose.yml        بيئة التطوير المحلية
└── Makefile
```

◆◆ الأخطر — تغطية اختبارات ١٠٠٪ إلزامية · ○ خارج النطاق المبدئي

---

## البدء

```bash
make venv install          # البيئة والاعتماديات
make env                   # .env من القالب — راجع القيم
make up                    # PostgreSQL + Redis
make migrate
make seed                  # بيانات تجريبية جاهزة للتصفّح
make run                   # http://127.0.0.1:8000

make web-install           # اعتماديات الواجهات
make web-landing           # الصفحة العامة على 5172
make web-merchant          # لوحة المتجر على 5174
```

`make help` يعرض كل الأوامر.

### التشغيل على Docker كما في الإنتاج

```bash
cp .env.local .env         # يعمل كما هو — لا قيمة تحتاج تغييرًا
make prod-build && make prod-up
```

ثم التهيئة مرة واحدة:

```bash
docker compose --env-file .env -f docker-compose.yml   exec api python manage.py bootstrap_platform     --admin-phone 01000000000 --org "مؤسستك"     --brand "علامتك" --owner-phone 01011111111
```

سبع حاويات على منفذ واحد: `/` الصفحة العامة · `/app/` تطبيق العميل ·
`/merchant/` لوحة المتجر · `/admin/` إدارة المنصة · `/api/v1/` الواجهات.
**دليل النشر الكامل:** [`docs/DEPLOY.md`](docs/DEPLOY.md)

| العنوان | ماذا |
|---|---|
| `/healthz` | فحص صحي يتحقق من قاعدة البيانات فعليًا |
| `/api/v1/docs/` | توثيق تفاعلي — Swagger UI |
| `/api/v1/schema/` | مخطط OpenAPI |
| `/django-admin/` | أداة تشغيلية للفريق التقني |

**حسابات البذرة** — كلمة المرور `walaee123`:
مدير المنصة `+201000000000` · مالك `+201000000001` ·
مدير `+201000000002` · كاشير `+201000000003`.
عملاء التطبيق يدخلون بـ OTP، والكود يُطبع في سجل الخادم.

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
| **المرحلة ١ — الأساس** | ✅ **منتهية** |
| **المرحلة ٢ — الحملات والفوترة والتقارير** | ✅ **منتهية** |
| **المرحلة ٣ — الواجهات الثلاث** | ✅ **منتهية** |
| **النشر على Docker** | ✅ **منتهٍ ومُختبَر** |
| التعاقد على المزوّدين والإطلاق | ⬜ |

**١** المصادقة بـ OTP · التسلسل التنظيمي · نماذج الولاء الستة · محرك القيود
append-only · رموز نقطة البيع والتأكيد الذرّي · كشف الاحتيال · سجل التدقيق.

**٢** الاشتراكات والباقات وحدودها · الفواتير · رصيد الرسائل بسجل append-only ·
محرك الشرائح · موجّه القنوات بالتكلفة · لوحة التاجر والالتزام القائم ·
مراجعة الاحتيال · مهام انتهاء الصلاحية والفوترة.

**٣** تطبيق العميل PWA · لوحة المتجر وشاشة الكاشير · لوحة إدارة المنصة ·
مكتبة مشتركة بتوكنات تصميم واحدة وعميل API واحد.

**النشر** سبع حاويات: الحافة · الخلفية · عاملان معزولان · مجدول ·
PostgreSQL · Redis. الهجرات تلقائية عند الإقلاع، وأمر `bootstrap_platform`
يهيّئ أول نشر بكلمات مرور مولَّدة.

**٣٣٩ اختبارًا** · تغطية ١٠٠٪ على محرك القيود · اختبارات تزامن على الرصيد
وعلى رصيد الرسائل · مخطط OpenAPI بلا تحذيرات.

**⚠ قرارات مفتوحة تُحسم قبل المرحلة ٢:** القطاع والبقعة الجغرافية · مزوّد الرسائل المحلي ·
بوابة الدفع. التفاصيل في [`docs/planning/decisions.md`](docs/planning/decisions.md).

---

<div align="center">

**ولائي… كلنا كسبانين.**

</div>
