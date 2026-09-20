# نموذج البيانات — ٢١ جدولًا

> أهم قرار في المشروع. بناؤه صحيحًا الآن يكلّف أيامًا؛ تعديله بعد الإطلاق يكلّف شهورًا.

`PK` مفتاح أساسي · `FK` مفتاح خارجي · `UQ` فريد · `IX` فهرس

---

## ١ — الهيكل التنظيمي والحسابات · `apps/tenancy` + `apps/accounts`

### `Organization` — المؤسسة

كيان التعاقد والفوترة. أعلى مستوى في الشجرة.

| حقل | نوع | ملاحظات |
|---|---|---|
| `id` | uuid | `PK` |
| `name` | varchar | |
| `legal_name` · `tax_id` | varchar | |
| `billing_email` | email | |
| `status` | enum | |
| `created_at` | timestamptz | |

### `Brand` — العلامة التجارية

**وحدة عزل البيانات.** عميل العلامة «أ» لا يظهر للعلامة «ب».

| حقل | نوع | ملاحظات |
|---|---|---|
| `id` | uuid | `PK` |
| `org_id` | → Organization | `FK` |
| `slug` | varchar | `UQ` |
| `name` · `logo` · `category` | | |
| `primary_color` | varchar(7) | |

### `Branch` — الفرع

| حقل | نوع | ملاحظات |
|---|---|---|
| `id` | uuid | `PK` |
| `brand_id` | → Brand | `FK` |
| `name` · `address` | | |
| `lat` · `lng` | decimal | `IX` — فهرس جغرافي لخاصية «متاجر قريبة منك» |
| `opening_hours` | jsonb | |
| `is_active` | bool | |

### `Terminal` — نقطة البيع

| حقل | نوع | ملاحظات |
|---|---|---|
| `id` | uuid | `PK` |
| `branch_id` | → Branch | `FK` |
| `label` | varchar | |
| `current_code` | varchar(12) | **نسخة للتدقيق فقط** — الرمز الفعّال يعيش في Redis بـ TTL |
| `code_expires_at` | timestamptz | |
| `is_active` | bool | |

### `StaffUser` — الكاشير والموظف

حساب مستقل لكل كاشير — **شرط كشف الاحتيال (م‑٠٧)**.

| حقل | نوع | ملاحظات |
|---|---|---|
| `id` | uuid | `PK` |
| `branch_id` | → Branch | `FK` |
| `user_id` | → User | `FK` |
| `role` | owner · manager · cashier | |
| `pin_hash` · `is_active` | | |

### `User` — حساب النظام

لأصحاب المتاجر وفريق المنصة — **منفصل عن `Customer`**.

| حقل | نوع | ملاحظات |
|---|---|---|
| `id` | uuid | `PK` |
| `phone` | varchar(20) | `UQ` |
| `email` · `password_hash` | | |
| `full_name` · `last_login` | | |
| `is_active` · `is_superuser` | bool | |

### `Customer` — العميل النهائي

هوية واحدة عبر المنصة كلها. `consent_*` مطلوب للامتثال (م‑٠٩).

| حقل | نوع | ملاحظات |
|---|---|---|
| `id` | uuid | `PK` |
| `phone` | varchar(20) | `UQ` |
| `full_name` · `birth_date` | | |
| `consent_at` · `consent_version` | | |
| `push_subscription` | jsonb | |
| `deleted_at` | timestamptz | حذف ناعم |

---

## ٢ — الولاء · `apps/loyalty`

### `LoyaltyProgram` — البرنامج

النماذج الستة. علامة واحدة قد تُشغّل أكثر من برنامج معًا.

| حقل | نوع | ملاحظات |
|---|---|---|
| `id` | uuid | `PK` |
| `brand_id` | → Brand | `FK` |
| `type` | points · stamps · visits · cashback · rewards · gifts | |
| `name` · `is_active` | | |
| `starts_at` · `ends_at` | | |

### `ProgramRule` — القواعد

`expiry_months` و `max_per_day` يعالجان **م‑٠٨** و **م‑٠٧**.

| حقل | نوع | ملاحظات |
|---|---|---|
| `id` | uuid | `PK` |
| `program_id` | → LoyaltyProgram | `FK` · 1:1 |
| `earn_rate` | decimal | |
| `min_invoice` · `max_per_day` | decimal | |
| `expiry_months` | int | |
| `reversal_policy` | enum | |
| `welcome_bonus` | int | |

### `Membership` — العضوية

جدول الربط N↔N. **هو ما يجعل الرصيد منفصلًا لكل علامة (م‑٠٢).**

| حقل | نوع | ملاحظات |
|---|---|---|
| `id` | uuid | `PK` |
| `customer_id` | → Customer | `FK` |
| `brand_id` | → Brand | `FK` |
| `(customer_id, brand_id)` | | `UQ` |
| `joined_at` · `status` · `tier` | | |

### `Balance` — الرصيد

**لقطة محسوبة فقط** — مصدر الحقيقة هو `LedgerEntry`.

| حقل | نوع | ملاحظات |
|---|---|---|
| `id` | uuid | `PK` |
| `membership_id` · `program_id` | | `FK` |
| `(membership_id, program_id)` | | `UQ` |
| `amount` | decimal(12,2) | |
| `expires_at` · `updated_at` | | |

### `Reward` — المكافأة

`merchant_cost` يُستخدم لحساب «الالتزام القائم» وعائد البرنامج.

| حقل | نوع | ملاحظات |
|---|---|---|
| `id` | uuid | `PK` |
| `program_id` | → LoyaltyProgram | `FK` |
| `title` · `cost_amount` · `cost_unit` | | |
| `merchant_cost` | decimal | |
| `stock` | int أو null | |
| `is_active` | bool | |

---

## ٣ — القيود والعمليات · `apps/ledger` ◆ append-only

### `Transaction` — العملية

| حقل | نوع | ملاحظات |
|---|---|---|
| `id` | uuid | `PK` |
| `terminal_id` · `staff_user_id` | | `FK` |
| `customer_id` | | `FK` · nullable |
| `(terminal_id, invoice_no)` | | `UQ` — **يمنع تسجيل نفس الفاتورة مرتين** |
| `invoice_amount` | decimal | |
| `code_used` | varchar(12) | |
| `status` | pending · confirmed · rejected · reversed | |
| `created_at` | | `IX` |

### `LedgerEntry` — قيد الرصيد

**لا `UPDATE` ولا `DELETE` أبدًا.** أي تصحيح بقيد عكسي جديد يشير عبر `reverses_id`.

| حقل | نوع | ملاحظات |
|---|---|---|
| `id` | uuid | `PK` |
| `transaction_id` | | `FK` · nullable |
| `membership_id` · `program_id` | | `FK` |
| `delta` | decimal(12,2) | |
| `reason` | earn · redeem · expire · reverse · adjust · welcome | |
| `reverses_id` | → self | `FK` |
| `balance_after` | decimal | |
| `created_at` | | `IX` |

### `Redemption` — الاستبدال

الكود صالح **١٥ دقيقة ومرة واحدة فقط**.

| حقل | نوع | ملاحظات |
|---|---|---|
| `id` | uuid | `PK` |
| `reward_id` · `membership_id` | | `FK` |
| `ledger_entry_id` | | `FK` |
| `code` | varchar(10) | `UQ` |
| `status` | pending · used · expired | |
| `expires_at` · `used_at` | | |
| `used_by_staff_id` | | `FK` |

### `AuditLog` — سجل التدقيق · `apps/audit`

صلاحيات قاعدة البيانات تمنع الحذف. يُحفظ ٢٤ شهرًا.

| حقل | نوع | ملاحظات |
|---|---|---|
| `id` | uuid | `PK` |
| `actor_type` · `actor_id` | | |
| `action` | varchar | |
| `entity_type` · `entity_id` | | `IX` |
| `before` · `after` | jsonb | |
| `ip` · `user_agent` | | |
| `created_at` | | `IX` |

---

## ٤ — التشغيل والفوترة والتكاملات

### `FraudSignal` · `apps/fraud`

تُولَّد **لحظيًا داخل نفس معاملة التأكيد** — لا تُؤجَّل.

| حقل | نوع | ملاحظات |
|---|---|---|
| `id` | uuid | `PK` |
| `transaction_id` | | `FK` |
| `rule_code` | varchar | |
| `severity` | low · medium · high | |
| `details` | jsonb | |
| `status` | open · accepted · rejected | |
| `reviewed_by` · `reviewed_at` | | `FK` |

### `Campaign` · `apps/campaigns`

التكلفة تُحسب وتُعرض **قبل** الإرسال (م‑١٠).

| حقل | نوع | ملاحظات |
|---|---|---|
| `id` | uuid | `PK` |
| `brand_id` · `created_by` | | `FK` |
| `name` · `message_template` | | |
| `segment_query` | jsonb | |
| `channel_priority` | text[] | |
| `status` · `scheduled_at` | | |
| `estimated_cost` | decimal | |

### `MessageJob` · `apps/campaigns`

تسلسل القنوات: **push (مجاني) ← whatsapp ← sms**.

| حقل | نوع | ملاحظات |
|---|---|---|
| `id` | uuid | `PK` |
| `campaign_id` · `customer_id` | | `FK` |
| `channel` | push · whatsapp · sms | |
| `status` | queued · sent · failed · read | |
| `cost` | decimal(8,4) | |
| `provider_msg_id` · `sent_at` | | |

### `Subscription` · `apps/billing`

حدود الجدار المجاني تُقرأ من الباقة عند كل طلب.

| حقل | نوع | ملاحظات |
|---|---|---|
| `id` | uuid | `PK` |
| `org_id` | → Organization | `FK` · 1:1 |
| `plan` | free · starter · growth · chain | |
| `status` · `mrr` | | |
| `current_period_start` / `_end` | | |
| `gateway_ref` | varchar | |

### `Invoice` · `MessageCredit` · `apps/billing`

رصيد الرسائل يُخصم لحظيًا عند كل `MessageJob` ناجح.

| حقل | نوع |
|---|---|
| `id` | uuid `PK` |
| `subscription_id` / `org_id` | `FK` |
| `amount` · `balance` | decimal |
| `status` · `issued_at` · `paid_at` | |
| `pdf_url` | varchar |

### `ApiKey` · `WebhookEndpoint` · `apps/publicapi` ○ مؤجّل

المفتاح يُخزَّن **مُجزّأً** ويُعرض مرة واحدة فقط عند الإنشاء.

| حقل | نوع |
|---|---|
| `id` | uuid `PK` |
| `org_id` | `FK` |
| `key_hash` | varchar(128) |
| `scopes` · `events` | text[] |
| `url` · `secret` · `last_used_at` · `revoked_at` | |

### `AiInsight` · `apps/insights` ○ مؤجّل

تُولَّد ليليًا. تبدأ بقواعد إحصائية ثم تتطور إلى نماذج (م‑١٢).

| حقل | نوع |
|---|---|
| `id` | uuid `PK` |
| `brand_id` | `FK` |
| `kind` | churn_risk · reward_value · best_time · segment |
| `payload` | jsonb |
| `confidence` | decimal |
| `generated_at` | |

---

## ٥ — خريطة العلاقات

| من | النوع | إلى | عند الحذف | الغرض |
|---|---|---|---|---|
| Organization | 1 — N | Brand | `PROTECT` | مؤسسة قد تملك أكثر من علامة |
| Brand | 1 — N | Branch | `CASCADE` | فروع العلامة |
| Branch | 1 — N | Terminal | `CASCADE` | نقاط البيع داخل الفرع |
| Branch | 1 — N | StaffUser | `CASCADE` | الكاشيرون |
| Brand | 1 — N | LoyaltyProgram | `CASCADE` | أكثر من نموذج ولاء معًا |
| LoyaltyProgram | 1 — 1 | ProgramRule | `CASCADE` | قواعد المنح والصلاحية |
| Customer ↔ Brand | N — N | **Membership** | `PROTECT` | **جوهر النموذج: رصيد منفصل لكل علامة** |
| Membership | 1 — N | Balance | `CASCADE` | رصيد لكل برنامج داخل العلامة |
| Transaction | 1 — N | LedgerEntry | `PROTECT` | عملية قد تنتج أكثر من قيد |
| LedgerEntry | 1 — 1 | LedgerEntry (self) | `PROTECT` | `reverses_id` — قيد عكسي للتصحيح |
| Reward | 1 — N | Redemption | `PROTECT` | سجل الاستبدالات |
| Transaction | 1 — N | FraudSignal | `CASCADE` | قد تُخالف أكثر من قاعدة |
| Campaign | 1 — N | MessageJob | `CASCADE` | رسالة لكل مستلم بتكلفتها |
| Organization | 1 — 1 | Subscription | `CASCADE` | باقة واحدة لكل مؤسسة |

**لماذا `PROTECT` على `LedgerEntry`؟**
لأن حذف عملية بعد منح نقاطها يجعل الرصيد غير قابل للتفسير. النظام يرفض الحذف
ويفرض التصحيح بقيد عكسي — وهذا بالضبط ما يجعل رقم «الالتزام القائم»
قابلًا للدفاع عنه أمام محاسب التاجر.
