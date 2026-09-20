<div align="center">

# walaee-demo · العرض والتخطيط

**كلنا كسبانين**

النموذج التفاعلي · العرض التقديمي · التقارير · عرض السعر

</div>

---

> 📦 **هذا مستودع العرض فقط.**
> الكود الفعلي للمنصة في مستودع منفصل:
> **[github.com/mohamedN2018/walaee](https://github.com/mohamedN2018/walaee)**

---

## الفروع

| الفرع | المحتوى | يُخدَم على |
|---|---|---|
| `main` | كل شيء — العرض والتخطيط والتقارير الداخلية | `/demo/` |
| `client` | نسخة العميل المقصوصة — مولَّدة آليًا من `main` | `/` |

**فرع `client` لا يُعدَّل يدويًا.** عدّل `main` ثم أعد التوليد:

```bash
bash scripts/make-client-branch.sh
git push -f origin client
```

---

## المحتوى

```
docs/
├── demo/                    النموذج التفاعلي — ٣٠ شاشة
│   ├── index.html             الفهرس
│   ├── present/               العرض التقديمي — ١٨ شريحة
│   ├── preview/               تصفّح الواجهات داخل إطارات أجهزة
│   ├── customer/              تطبيق العميل — ١٢ شاشة
│   ├── merchant/              لوحة صاحب المتجر — ١١ شاشة
│   ├── admin/                 لوحة إدارة المنصة — ٧ شاشات
│   ├── architecture/          المخطط المعماري ونموذج البيانات
│   ├── plan/                  خطة التنفيذ — ٦ مراحل
│   ├── solutions/             من المشكلة إلى الشاشة — ١٦ حلًّا
│   ├── pricing/               عرض السعر والباقات
│   ├── team/                  دليل الفريق (داخلي)
│   └── assets/                نظام التصميم
│
├── reports/                 التقارير PDF ومصادرها
└── planning/                القرارات والنطاق المعتمد
```

---

## التشغيل محليًا

```bash
docker build -t walaee-demo .
docker run -d -p 8090:80 walaee-demo
# http://localhost:8090/demo/
```

بدون Docker — أي خادم ثابت:

```bash
python -m http.server 8090 --directory docs
# http://localhost:8090/demo/
```

---

## النشر على Dokploy

| | `main` | `client` |
|---|---|---|
| النطاق | `walaee.deplois.net` | `walae.deplois.net` |
| Path | `/` (يحوّل إلى `/demo/`) | `/` |
| Build | Dockerfile في الجذر | Dockerfile في الجذر |

التفاصيل في [`docs/DEPLOY-DEMO.md`](docs/DEPLOY-DEMO.md).

---

<div align="center">

**ولائي… كلنا كسبانين.**

</div>
