# نشر ولائي على Dokploy

نموذج العرض ثابت بالكامل (HTML/CSS/JS) — الصورة عبارة عن `nginx:alpine` بحجم ~**60 ميجابايت**
واستهلاك ذاكرة أقل من **20 ميجابايت**.

---

## الملفات

| الملف | الغرض |
|---|---|
| `Dockerfile` | يبني صورة nginx ويضع فيها `demo/` والتقارير |
| `nginx.conf` | ضغط، كاش، رؤوس أمان، فحص صحي، تحويلات نسبية |
| `docker-compose.yml` | تعريف الخدمة لـ Dokploy |
| `.dockerignore` | يستبعد ما لا يلزم من سياق البناء |

---

## الطريقة الأولى — Dokploy عبر Compose (موصى بها)

1. ارفع المشروع على مستودع Git (GitHub / GitLab / Gitea).
2. في Dokploy: **Create → Compose**.
3. اربط المستودع، والفرع، وحدّد **Compose Path**: `docker-compose.yml`.
4. من تبويب **Domains** أضف نطاقك واختر:
   - **Service:** `web`
   - **Container Port:** `80`
   - فعّل **HTTPS** (Let's Encrypt) — Dokploy يصدر الشهادة تلقائيًا.
5. اضغط **Deploy**.

## الطريقة الثانية — Dokploy عبر Dockerfile

1. **Create → Application**.
2. **Build Type:** `Dockerfile` · **Dockerfile Path:** `Dockerfile`.
3. **Port:** `80`.
4. أضف النطاق وفعّل HTTPS، ثم **Deploy**.

---

## تشغيل محلي للتجربة

```bash
docker compose up -d --build
# لو فعّلت ports في docker-compose.yml:
#   http://localhost:3000
```

أو مباشرة:

```bash
docker build -t walaee-demo .
docker run -d --name walaee -p 8080:80 walaee-demo
# http://localhost:8080
```

---

## المسارات بعد النشر

| المسار | المحتوى |
|---|---|
| `/` | يحوّل تلقائيًا إلى `/demo/` |
| `/demo/` | معرض الواجهات |
| `/demo/present/` | **العرض التقديمي 3D** |
| `/demo/customer/` | تطبيق العميل |
| `/demo/merchant/` | لوحة صاحب المتجر |
| `/demo/admin/` | لوحة إدارة المنصة |
| `/demo/plan/` | خطة التطوير والباقات |
| `/demo/architecture/` | المخطط البرمجي والمعماري |
| `/Walaee_Analysis_Report_AR.pdf` | التحليل الشامل |
| `/healthz` | فحص صحي (يرجع `ok`) |

---

## ملاحظات تشغيلية

**`X-Frame-Options: SAMEORIGIN` — لا تغيّره إلى `DENY`.**
العرض التقديمي يضمّن الواجهات داخل `iframe` من نفس الأصل؛ `DENY` ستُظهر إطارات فارغة.

**التحويلات نسبية** (`absolute_redirect off`) حتى لا يفقد التحويل النطاق أو المنفذ خلف بروكسي Traefik.

**خط Cairo** يُحمَّل من Google Fonts. لو الخادم بلا إنترنت خارجي سيقع النظام تلقائيًا على
`Segoe UI` / `Tahoma` والتصميم يبقى سليمًا. لتضمين الخط محليًا: نزّل ملفات `woff2` إلى
`demo/assets/fonts/` واستبدل سطر `@import` في `demo/assets/css/theme.css` بقاعدة `@font-face`.

**الكاش:** ملفات HTML بلا كاش (تحديث فوري بعد كل نشر)، والأصول 7 أيام.
لو حدّثت CSS أو JS ولم يظهر التغيير، افتح بـ Hard Refresh أو أضف بصمة للاسم.

**الموارد:** الحد في `docker-compose.yml` هو `0.5 CPU / 128MB` — كافٍ لآلاف الزيارات.
احذف قسم `deploy.resources` لو سيرفرك محدود ولا يدعم القيود.

---

## التحقق بعد النشر

```bash
curl -I https://your-domain.com/healthz
curl -I https://your-domain.com/demo/ | grep -i x-frame-options   # لازم SAMEORIGIN
```

---

## لاحقًا — نشر المنتج الحقيقي

هذا الملف يخص **نموذج العرض** فقط. تركيبة الإنتاج الكاملة
(Django + PostgreSQL + Redis + Celery + Nginx) موثّقة بالتفصيل في
**`demo/architecture/index.html`** — قسم «البنية على Docker».
