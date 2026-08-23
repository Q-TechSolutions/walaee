# التخطيط والتوثيق والعرض

كل مخرجات مرحلة التخطيط. **مرجع لا يُعدَّل أثناء البناء.**

## النموذج التفاعلي — `demo/`

يُخدَم على `/demo/` بعد النشر.

| المسار | المحتوى |
|---|---|
| `demo/index.html` | فهرس المشروع — نقطة البداية |
| `demo/present/` | العرض التقديمي — ١٨ شريحة |
| `demo/preview/` | تصفّح الواجهات داخل إطارات أجهزة |
| `demo/customer/` · `merchant/` · `admin/` | الواجهات الثلاث — ٣٠ شاشة |
| **`demo/architecture/`** | **المخطط المعماري — مرجع البناء الأساسي** |
| `demo/plan/` | ٦ مراحل بمعايير قبول |
| `demo/pricing/` | عرض السعر والباقات |
| `demo/solutions/` | ١٦ مشكلة وحلولها |
| `demo/team/` | دليل الفريق (داخلي — لا يُعرض على العميل) |

## التقارير — `reports/`

| الملف | المحتوى |
|---|---|
| `Walaee_Analysis_Report_AR.pdf` | التحليل الشامل — ٢٦ صفحة |
| `Walaee_Pricing_Proposal_AR.pdf` | عرض السعر — ٧ صفحات |
| `Walaee_Executive_Brief_Book_Mobile.pdf` | الوثيقة الأصلية |
| `Walaee_Analysis_Report_AR.html` | مصدر التقرير — يُعاد توليد PDF منه |

## التخطيط — `planning/`

`decisions.md` — قرارات المرحلة صفر · `scope.md` — النطاق المعتمد.

## تشغيل موقع العرض محليًا

```bash
docker build -t walaee-demo .
docker run -d -p 8090:80 walaee-demo
# http://localhost:8090/demo/
```

التفاصيل في `DEPLOY-DEMO.md`.
