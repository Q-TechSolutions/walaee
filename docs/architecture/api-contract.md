# عقد الـAPI — ٤٧ نقطة

جميعها تحت `/api/v1/` وتُوثَّق تلقائيًا بـ OpenAPI عبر `drf-spectacular` على `/api/schema/`.

---

## ١ — تطبيق العميل

| الطريقة | المسار | الغرض | المصادقة |
|---|---|---|---|
| `POST` | `/auth/otp/request` | طلب كود تحقق — محدود بالمعدل | عام |
| `POST` | `/auth/otp/verify` | تأكيد الكود وإصدار JWT | عام |
| `GET` | `/me` · `/me/cards` | الملف الشخصي ومحفظة البطاقات | JWT |
| `GET` | `/me/cards/{brand_id}` | تفاصيل بطاقة علامة واحدة | JWT |
| `POST` | `/scan/resolve` | ترجمة رمز QR إلى نقطة بيع | JWT |
| `POST` | `/transactions` | إنشاء عملية بحالة معلّقة | JWT |
| `GET` | `/me/rewards` | المكافآت الجاهزة والقريبة | JWT |
| `POST` | `/redemptions` | استبدال مكافأة وتوليد كود | JWT |
| `GET` | `/me/activity` | سجل النشاط مع ترقيم | JWT |
| `GET` | `/stores/nearby?lat&lng` | متاجر قريبة — استعلام جغرافي | JWT |
| `POST` | `/me/push-subscription` | تسجيل اشتراك Web Push | JWT |
| `GET` | `/me/export` | تحميل نسخة من البيانات (م‑٠٩) | JWT |
| `DELETE` | `/me` | حذف الحساب — يتطلب OTP | JWT |

---

## ٢ — لوحة التاجر ونقطة البيع

| الطريقة | المسار | الغرض | الصلاحية |
|---|---|---|---|
| `GET` | `/pos/code` | الرمز الفعّال للطرفية | `cashier` |
| `POST` | `/pos/code/rotate` | تجديد فوري للرمز | `cashier` |
| `GET` | `/pos/pending` | العمليات المعلّقة — SSE أو استطلاع | `cashier` |
| `POST` | `/pos/transactions/{id}/confirm` | تأكيد ومنح النقاط | `cashier` |
| `POST` | `/pos/manual` | المسار اليدوي: هاتف + فاتورة | `cashier` |
| `POST` | `/pos/redemptions/{code}/use` | صرف كود استبدال | `cashier` |
| `GET` | `/merchant/dashboard` | المؤشرات الستة ومنها الالتزام القائم | `manager` |
| `GET` | `/merchant/customers?segment=` | العملاء وشرائحهم | `manager` |
| `GET` | `/merchant/liability` | قيمة النقاط غير المستبدلة | `owner` |
| `PUT` | `/merchant/programs/{id}/rule` | تعديل قواعد المنح والصلاحية | `owner` |
| `POST` | `/merchant/rewards` | إدارة المكافآت | `manager` |
| `GET` | `/merchant/fraud-signals` | عمليات تحتاج مراجعة | `owner` |
| `POST` | `/merchant/fraud-signals/{id}/resolve` | قبول أو إلغاء وعكس القيد | `owner` |
| `POST` | `/merchant/branches` · `/terminals` · `/staff` | الهيكل التنظيمي | `owner` |
| `POST` | `/merchant/campaigns` | إنشاء حملة — يُرجع التكلفة قبل الإرسال | `manager` |
| `GET` | `/merchant/reports/{kind}` | تقارير قابلة للتصدير | `manager` |

---

## ٣ — الواجهات العامة و Webhooks ○ مؤجّل

خارج النطاق المبدئي. يُفعَّل بـ `FEATURE_PUBLIC_API=1`.

| الطريقة | المسار / الحدث | الغرض |
|---|---|---|
| `GET` | `/public/v1/customers/{phone}/balance` | قراءة رصيد عميل من نظام خارجي |
| `POST` | `/public/v1/transactions` | تسجيل عملية من نظام نقاط بيع |
| `POST` | `/public/v1/redemptions/{code}/use` | صرف مكافأة من نظام خارجي |
| `GET` | `/public/v1/schema` | توثيق OpenAPI تفاعلي |
| ⇢ | `transaction.created` | عند تأكيد أي عملية |
| ⇢ | `reward.redeemed` | عند استبدال مكافأة |
| ⇢ | `customer.joined` | عند انضمام عميل جديد للعلامة |
| ⇢ | `balance.expiring` | قبل انتهاء الرصيد بثلاثين يومًا |

**أمان Webhooks:** كل طلب يحمل `X-Walaee-Signature` = HMAC‑SHA256 للجسم بمفتاح الوجهة،
مع `X-Walaee-Timestamp` لمنع إعادة التشغيل. إعادة المحاولة بتراجع أسّي حتى ٦ مرات،
ثم تعطيل الوجهة تلقائيًا.

---

## رموز الاستجابة المتفق عليها

| الرمز | متى |
|---|---|
| `410 Gone` | رمز QR غير موجود أو منتهٍ |
| `409 Conflict` | فاتورة مسجّلة مسبقًا على نفس الطرفية · تأكيد مزدوج |
| `422` | سقف يومي متجاوَز · رصيد غير كافٍ |
| `429` | تجاوز حد معدل OTP |
| `403` | كاشير من فرع آخر · دور غير كافٍ |
