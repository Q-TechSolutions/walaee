# النشر

دليل تشغيل المنصة على خادم. مكتوب لمن سينشرها ويشغّلها، لا لمن كتبها.

---

## ما الذي يُنشَر

حاوية واحدة مكشوفة (`web`) وستّ خلفها:

```
الإنترنت ──▶ Traefik (TLS)  ──▶  web : nginx
                                   │
                    ┌──────────────┼───────────────┐
                    ▼              ▼               ▼
              /  ·  /merchant/  ·  /admin/      /api/ ──▶ api : Django
                 (ملفات ثابتة مبنية)                        │
                                                            ▼
                              worker-realtime · worker-default · beat
                                                            │
                                              postgres  ·  redis
```

| المسار | ماذا |
|---|---|
| `/` | تطبيق العميل — PWA |
| `/merchant/` | لوحة المتجر وشاشة الكاشير |
| `/admin/` | لوحة إدارة المنصة — `noindex` |
| `/api/v1/` | واجهات البرمجة |
| `/api/v1/docs/` | توثيق تفاعلي |
| `/django-admin/` | أداة تشغيلية للفريق التقني |
| `/healthz` | فحص صحي يتحقق من قاعدة البيانات فعليًا |

---

## متطلبات الخادم

| | الحد الأدنى | المريح |
|---|---|---|
| المعالج | نواتان | ٤ أنوية |
| الذاكرة | ٤ جيجا | ٨ جيجا |
| القرص | ٢٠ جيجا | ٤٠ جيجا |

Docker 24+ و Compose v2.

---

## أولًا: ملف البيئة

```bash
cp .env.example .env
```

ثم املأ **ما لا غنى عنه**:

```bash
DJANGO_SETTINGS_MODULE=config.settings.prod
DEBUG=0
SECRET_KEY=<٥٠ محرفًا عشوائيًا>
ALLOWED_HOSTS=walaee.example.com,web,api
CSRF_TRUSTED_ORIGINS=https://walaee.example.com

POSTGRES_PASSWORD=<كلمة مرور قوية>
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2

WEB_PORT=8080
```

لتوليد المفتاح:

```bash
python -c "import secrets,string;print(''.join(secrets.choice(string.ascii_letters+string.digits) for _ in range(50)))"
```

> **لا تضف `DATABASE_URL`.** كلمة المرور في متغيّر واحد فقط، ونقطة الدخول
> تبني الرابط منه. وجودها مرتين يعني نسختين تنحرفان بصمت — وقد حدث ذلك
> فعلًا أثناء التطوير فظل الخادم عالقًا على «انتظار قاعدة البيانات» بلا
> أي رسالة تشرح السبب.

**`ALLOWED_HOSTS` يجب أن يشمل `web` و `api`**: الفحوص الصحية تأتي من داخل
الشبكة بهذين الاسمين، وغيابهما يجعل كل فحص يفشل بـ400.

---

## ثانيًا: التشغيل

```bash
make prod-build
make prod-up
make prod-logs        # للمتابعة
```

أو مباشرةً:

```bash
docker compose --env-file .env \
  -f infra/docker/docker-compose.prod.yml up -d --build
```

> `--env-file .env` إلزامي. Compose يقرأ متغيرات التداخل `${...}` من الملف
> **المجاور لملف compose** لا من جذر المستودع، فبدونه يفشل التشغيل برسالة
> عن متغيّر ناقص وملف `.env` موجود أمامك.

الهجرات و`collectstatic` تعملان تلقائيًا في نقطة دخول حاوية `api` —
لا في وقت البناء، لأن جهاز البناء قد لا يرى قاعدة الإنتاج أصلًا.

---

## ثالثًا: التهيئة — مرة واحدة

```bash
docker compose --env-file .env -f infra/docker/docker-compose.prod.yml \
  exec api python manage.py bootstrap_platform \
    --admin-phone 01000000000 \
    --org "اسم المؤسسة" \
    --brand "اسم العلامة" \
    --owner-phone 01011111111 \
    --owner-name "اسم المالك" \
    --plan growth
```

يُنشئ حساب فريق المنصة وأول مؤسسة بعلامتها وفرعها ونقطة بيعها وبرنامج
نقاط افتراضي. **كلمات المرور تُطبع مرة واحدة** — احفظها فورًا ثم غيّرها
من `/django-admin/`.

> `seed_demo` بيانات تطوير بكلمة مرور معروفة، ولا يعمل خارج التطوير إلا
> بـ`--force`. لا تستخدمه على خادم حقيقي.

---

## رابعًا: تشديد قاعدة البيانات

بعد أول `migrate` ناجح:

```bash
make harden-db
```

يضيف حارسًا على مستوى PostgreSQL يرفض `UPDATE` و`DELETE` على جدولَي
القيود وسجل التدقيق — حتى من `psql` مباشرةً. الحارس في بايثون يمنع الخطأ
البرمجي، وهذا يمنع ما لا يستطيع بايثون منعه.

⚠ لا تطبّقه على قاعدة تطوير تُستخدم فيها `seed_demo --reset`.

---

## Dokploy

### التطبيق

| الحقل | القيمة |
|---|---|
| النوع | Docker Compose |
| المستودع | `github.com/mohamedN2018/walaee` |
| الفرع | `main` |
| مسار Compose | `infra/docker/docker-compose.prod.yml` |
| النطاق | نطاقك → الخدمة `web` → المنفذ `80` |

### متغيرات البيئة

الصقها في لوحة Dokploy كما هي في `.env` أعلاه. Dokploy يمرّرها إلى
Compose كملف بيئة، فينتفي شرط `--env-file` هناك.

### بعد أول نشر

١. افتح طرفية حاوية `api` من Dokploy ونفّذ `bootstrap_platform`.
٢. نفّذ تشديد قاعدة البيانات.
٣. افتح `https://نطاقك/healthz` — يجب أن يردّ `{"status":"ok","database":"ok"}`.

---

## أعطال نشر شائعة وأسبابها

| العرَض | السبب | الحل |
|---|---|---|
| حلقة تحويل لا تنتهي على `/api/` | nginx يكتب `X-Forwarded-Proto: http` فوق ما أرسله Traefik، فيرى Django طلبًا غير آمن ويحوّله | مُعالَج بـ`map` في `infra/nginx/walaee.conf` — لا تستبدله بـ`$scheme` |
| Dokploy يتراجع عن نشر سليم | فحص الحاوية يستخدم `localhost` فيُحلّ إلى `::1` بينما nginx يربط IPv4 وحده | مُعالَج: الفحص يستخدم `127.0.0.1` ونginx يسمع على الاثنين |
| `PermissionError: /app/staticfiles` | الحاوية تعمل بمستخدم غير جذري والحجم المسمّى أُنشئ بملكية root | المجلدان يُنشآن في الصورة بملكية التطبيق — لا تحذفهما من `Dockerfile.backend` |
| عالق على «انتظار قاعدة البيانات» | كلمة المرور مختلفة بين `POSTGRES_PASSWORD` و`DATABASE_URL` | لا تضف `DATABASE_URL` إطلاقًا |
| صفحة بيضاء على `/merchant/` بلا خطأ | `base` في Vite و`basename` في الموجّه غير متطابقين | يتحددان من `VITE_BASE` — لا تغيّر أحدهما وحده |
| كل فحص صحي يردّ 400 | `ALLOWED_HOSTS` لا يشمل `web` و`api` | أضفهما |
| نقاط تُمنح مرتين | نسختان من `beat` | `replicas: 1` — إلزامي |
| ‏502 على `/api/` بعد كل نشر بينما الخلفية «صحيّة» | nginx يحلّ اسم الخلفية مرة واحدة عند الإقلاع، والحاوية الجديدة تأخذ عنوانًا آخر | مُعالَج بـ`resolver 127.0.0.11` و`proxy_pass` عبر متغيّر — لا تُعِد كتلة `upstream` الثابتة |
| الخلفية عالقة على «انتظار قاعدة البيانات» محليًا | `.env` يحمل قيم التطوير (`127.0.0.1:5433`) بينما الحاويات تحتاج `postgres:5432` | احتفظ بنسختين: `.env.dev.local` و`.env.prod.local`، وانسخ المطلوبة إلى `.env` |

---

## التشغيل اليومي

```bash
make prod-logs                    # السجلات
docker compose --env-file .env -f infra/docker/docker-compose.prod.yml ps
```

### نسخة احتياطية

```bash
make backup                              # إلى backups/
bash infra/scripts/backup.sh /mnt/backups
```

السكربت يكتب إلى ملف مؤقت ثم يعيد تسميته، ويتحقق من سلامة الضغط ومن أن
الحجم معقول قبل اعتماد النسخة: انقطاع في المنتصف يترك ملفًا ناقصًا يبدو
سليمًا، ويُكتشف يوم الاسترجاع لا قبله. ويحذف ما تجاوز `BACKUP_KEEP_DAYS`
(افتراضيًا ١٤ يومًا).

**الجدولة على الخادم:**

```cron
0 1 * * * cd /path/to/walaee && bash infra/scripts/backup.sh >> /var/log/walaee-backup.log 2>&1
```

**قاعدة غير قابلة للتفاوض:** النسخة غير المختبَرة ليست نسخة احتياطية.
جرّب الاسترجاع على خادم اختبار مرة شهريًا على الأقل.

### الاسترجاع

```bash
make restore FILE=backups/walaee-2026-09-20_0100.sql.gz
```

يوقف التطبيق والعمّال أولًا — استرجاع بينما عامل يكتب يعطي قاعدة نصفها
قديم ونصفها جديد — ثم يسترجع، ثم **يدقّق سلامة الأرصدة تلقائيًا** قبل
إعادة الفتح. التأكيد بكتابة اسم القاعدة لا بـ«نعم».

### التحديث

```bash
git pull
make prod-build
make prod-up
```

الهجرات تُطبَّق تلقائيًا. راجع سجل `api` بعد كل تحديث.

### تدقيق سلامة الأرصدة

```bash
docker compose --env-file .env -f infra/docker/docker-compose.prod.yml \
  exec api python -c "
import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings.prod'); django.setup()
from apps.ledger.tasks import verify_integrity
print(verify_integrity())
"
```

أو الأمر المخصّص:

```bash
make verify-ledger
```

يخرج برمز `1` عند أي انحراف — صالح للاستخدام في مراقبة آلية. يعمل ليليًا
أيضًا كمهمة مجدولة. أي انحراف يعني مسارًا يكتب في الرصيد خارج المحرك:
**أوقف النشر وابحث عنه قبل أي شيء آخر.** التصحيح بـ`--fix-snapshots`
متاح لكنه يخفي العطل إن استُخدم قبل فهم سببه.

### المهام الدورية

تُثبَّت تلقائيًا عند إقلاع `api`. لإعادة تثبيتها يدويًا:

```bash
make schedule
```

المواعيد قابلة للتعديل من `/django-admin/` بلا نشر جديد.

---

## قبل الإطلاق الحقيقي

هذه ليست تفاصيل تُؤجَّل:

- [ ] `DEBUG=0` و`SECRET_KEY` فريد لهذا الخادم
- [ ] `ALLOWED_HOSTS` بنطاقك الفعلي + `web` + `api`
- [ ] شهادة TLS فعّالة (Traefik يتولاها)
- [ ] `make harden-db` مُطبَّق
- [ ] نسخة احتياطية مجدولة **ومُختبَرة استرجاعها**
- [ ] `SENTRY_DSN` مضبوط — بدونه تكتشف الأعطال من شكوى تاجر
- [ ] مزوّد رسائل فعلي بدل `console` — القرار ٧
- [ ] بوابة دفع أو تأكيد الاكتفاء بالتحويل اليدوي — القرار ٨
- [ ] تغيير كلمات مرور التهيئة
- [ ] `make schedule` مثبَّت والمهام السبع ظاهرة في `/django-admin/`
- [ ] `make verify-ledger` يخرج بـ`✓ سليم`
