> ⚠️ مجلد هيكلي — لم يبدأ التنفيذ بعد. المرجع: `docs/demo/architecture/`


# الواجهات — ثلاثة تطبيقات ويب

**ويب فقط.** لا يوجد تطبيق سطح مكتب ولا Electron ولا تطبيق أصلي.
تطبيق العميل PWA يغطّي الهاتف بلا متجر تطبيقات.

```
frontend/
├── customer-pwa/          تطبيق العميل        → docs/demo/customer/
├── merchant-dashboard/    لوحة صاحب المتجر    → docs/demo/merchant/
├── admin-panel/           لوحة إدارة المنصة   → docs/demo/admin/
└── shared/                ui · api-client · tokens · utils
```

## قواعد ملزمة

1. **دعم RTL كامل** من اليوم الأول — لا `left/right` بل `inline-start/end`.
2. **لا تباعد حروف على النص العربي** — يكسر اتصال الحروف.
3. **حالات التحميل والخطأ والفراغ لكل شاشة** — ليست اختيارية.
4. **توكنات التصميم من مصدر واحد** — `shared/tokens/` مشتقّة من
   `docs/demo/assets/css/theme.css`. لا ألوان أو مسافات خارجها.
5. **عميل API مولّد** من مخطط OpenAPI لا مكتوب يدويًا.

## معايير القبول

- يعمل على iOS 15 و Android 9 بشبكة 3G
- أول محتوى في أقل من ثانيتين
- Lighthouse: الأداء والإتاحة فوق ٩٠
