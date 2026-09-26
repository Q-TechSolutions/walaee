/**
 * الاشتراك والفواتير.
 *
 * الاستهلاك أولًا ثم الباقات: التاجر يفتح هذه الشاشة ليعرف «هل
 * قربت أخلّص؟» لا ليتصفّح الأسعار. وضع جدول الباقات فوق يجعلها
 * تبدو صفحة بيع لا صفحة حساب.
 */

import {
  Badge,
  Empty,
  ErrorBox,
  Icon,
  Loading,
  fmt,
  t,
  useApi,
} from "@walaee/shared";

import { queries } from "../lib/queries";


/**
 * الباقات كما تفرضها الخلفية.
 *
 * الأرقام هنا يجب أن تطابق `PLAN_LIMITS` في
 * `backend/apps/billing/models.py`. مصدر الحقيقة هناك لأن الحدّ
 * يُفرَض في الخلفية، وشاشة تَعِد بخمسة فروع بينما النظام يرفض
 * السادس أسوأ من شاشة بلا أسعار: التاجر يكتشف الفرق بعد أن يدفع.
 */
const PLANS = [
  {
    key: "free",
    name: "مجانية",
    price: 0,
    note: "للأبد",
    limits: ["فرع واحد · نقطة بيع واحدة", "برنامج ولاء واحد", "حتى ٢٠٠ عميل"],
  },
  {
    key: "starter",
    name: "أساسية",
    price: 450,
    note: "شهريًا",
    limits: [
      "فرع واحد · ٣ نقاط بيع",
      "برنامجا ولاء",
      "حتى ٢٬٠٠٠ عميل",
      "٥٠٠ رسالة شهريًا",
    ],
  },
  {
    key: "growth",
    name: "نمو",
    price: 1200,
    note: "شهريًا",
    popular: true,
    limits: [
      "٥ فروع · ١٥ نقطة بيع",
      "٤ برامج ولاء",
      "حتى ٢٠٬٠٠٠ عميل",
      "٣٬٠٠٠ رسالة شهريًا",
    ],
  },
  {
    key: "chain",
    name: "سلاسل",
    price: 3000,
    note: "شهريًا",
    limits: [
      "فروع ونقاط بيع بلا حد",
      "برامج وعملاء بلا حد",
      "١٠٬٠٠٠ رسالة شهريًا",
      "دعم مخصّص",
    ],
  },
];

const LIMIT_LABELS: Record<string, string> = {
  max_branches: "الفروع",
  max_terminals: "نقاط البيع",
  max_staff: "الموظفون",
  max_programs: "البرامج",
  max_customers: "العملاء",
};

const USAGE_KEYS: Record<string, string> = {
  max_branches: "branches",
  max_terminals: "terminals",
  max_staff: "staff",
  max_programs: "programs",
  max_customers: "customers",
};

export function Billing() {
  const subscription = useApi((signal) => queries.subscription(signal), []);
  const invoices = useApi((signal) => queries.invoices(signal), []);
  const wallet = useApi((signal) => queries.wallet(signal), []);

  if (subscription.loading) return <Loading />;
  if (subscription.error != null)
    return <ErrorBox error={subscription.error} onRetry={subscription.reload} />;
  if (!subscription.data) return null;

  const data = subscription.data;

  return (
    <div className="billing-split">
      <div className="stack gap-lg">
        <section className="card">
          <div className="card-hd">
            <h3>{t("الباقات")}</h3>
            <Badge tone="violet"> {t("باقتك:")} {t(data.plan_label)}</Badge>
          </div>

          <div className="card-p">
            <div className="plans">
              {PLANS.map((plan) => {
                const current = plan.key === data.plan;
                return (
                  <article
                    key={plan.key}
                    className={`plan ${current ? "cur" : ""} ${
                      plan.popular && !current ? "pop" : ""
                    }`}
                  >
                    {plan.popular && !current && (
                      <span className="tag">{t("الأكثر اختيارًا")}</span>
                    )}

                    <b className="t-md">{t(plan.name)}</b>
                    <p className="pr num">
                      {plan.price === 0 ? t("مجانًا") : fmt.number(plan.price)}
                    </p>
                    <p className="t-xs muted">{t(plan.note)}</p>

                    <ul className="mt-2">
                      {plan.limits.map((line) => (
                        <li key={line}>
                          <Icon name="check" size={15} />
                          <span>{t(line)}</span>
                        </li>
                      ))}
                    </ul>

                    <button
                      type="button"
                      className={`btn btn-block btn-sm mt-3 ${
                        current ? "btn-line" : plan.popular ? "btn-primary" : "btn-soft"
                      }`}
                      disabled={current}
                    >
                      {current ? t("باقتك الحالية") : t("تواصل للترقية")}
                    </button>
                  </article>
                );
              })}
            </div>

            <div className="card card-p tint-v mt-3">
              <div className="row-t">
                <span className="ibox v" style={{ background: "#fff" }}>
                  <Icon name="bolt" size={20} />
                </span>
                <div className="grow">
                  <b className="t-sm">{t("تغيير الباقة يمرّ بفريق ولائي")}</b>
                  <p className="t-xs muted mt-1">
                    {t("الترقية فورية، أما التخفيض فيحتاج مراجعة: باقة أصغر قد لا تتّسع لفروعك أو موظفيك الحاليين، وتنفيذه آليًا كان سيعطّل نقاط بيع تعمل الآن.")}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="card">
          <div className="card-hd">
            <h3>{t("الفواتير")}</h3>
          </div>

          <div className="card-p">
            {invoices.data?.length === 0 && (
              <Empty icon="receipt" title={t("لا توجد فواتير بعد")} />
            )}

            {invoices.data?.map((invoice) => (
              <div key={invoice.id} className="li">
                <span className="ibox v" aria-hidden="true">
                  <Icon name="receipt" size={18} />
                </span>
                <div className="grow">
                  <p className="li-t num">{invoice.number}</p>
                  <p className="li-s">
                    {fmt.date(invoice.period_start)} —{" "}
                    {fmt.date(invoice.period_end)}
                  </p>
                </div>
                <span className="li-v num">{fmt.money(invoice.total)}</span>
                <Badge tone={invoice.status === "paid" ? "green" : "amber"}>
                  {t(invoice.status_label)}
                </Badge>
              </div>
            ))}
          </div>
        </section>
      </div>

      <div className="stack gap-lg">
        <section className="card">
          <div className="card-hd">
            <h3>{t("استهلاكك الحالي")}</h3>
          </div>

          <div className="card-p">
            {Object.entries(LIMIT_LABELS).map(([key, label]) => {
              const raw = data.limits[key];
              const used = data.usage[USAGE_KEYS[key] ?? ""] ?? 0;
              const cap = raw === null || raw === undefined ? null : Number(raw);
              const ratio = cap ? Math.min(100, (used / cap) * 100) : 0;

              return (
                <div key={key} className="usage">
                  <span className="t-sm w-7" style={{ width: "5.5rem" }}>
                    {t(label)}
                  </span>
                  <span className={`bar ${ratio >= 90 ? "o" : ""}`}>
                    <i style={{ width: `${cap ? Math.max(ratio, 2) : 6}%` }} />
                  </span>
                  <span className="t-xs muted num nowrap">
                    {fmt.number(used)}
                    {cap === null ? ` / ${t("بلا حد")}` : ` / ${fmt.number(cap)}`}
                  </span>
                </div>
              );
            })}
          </div>
        </section>

        <section className="card">
          <div className="card-hd">
            <h3>{t("رصيد الرسائل")}</h3>
            <span className="t-lg w-8 num">
              {fmt.number(data.message_balance)}
            </span>
          </div>

          <div className="card-p">
            <p className="t-sm muted mb-2">
              {t("الإشعارات داخل التطبيق لا تُخصَم من الرصيد — يُخصَم منه ما يخرج إلى شبكة الاتصالات وحده.")}
            </p>

            {wallet.data?.history.slice(0, 8).map((line) => (
              <div key={line.id} className="row between t-sm usage">
                <span className="grow">{t(line.reason_label)}</span>
                <span
                  className="num w-7"
                  style={{
                    color:
                      line.delta > 0 ? "var(--green-600)" : "var(--red-600)",
                  }}
                >
                  {line.delta > 0 ? "+" : ""}
                  {fmt.number(line.delta)}
                </span>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
