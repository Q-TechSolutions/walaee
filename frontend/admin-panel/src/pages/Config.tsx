/**
 * الإعدادات والامتثال ونموذج النقاط.
 *
 * كل بند هنا يُقرأ من الإعدادات أو من القاعدة، لا من قائمة مكتوبة
 * بيد: لوحة امتثال تعلن «مفعَّل» لحمايةٍ مطفأة تجعل قارئها يتوقّف
 * عن التحقق — وهو بالضبط ما تُشترى اللوحة لمنعه.
 *
 * ونموذج النقاط معروض لأنه القرار المعماري غير الرجعي الأهم:
 * «هل نحن نظام مقاصة مالية؟» سؤال يُطرح في كل اجتماع مع سلسلة،
 * وجوابه يجب ألا يُخمَّن.
 */

import { Badge, ErrorBox, Icon, Loading, fmt, t, useApi } from "@walaee/shared";

import { queries } from "../lib/queries";

const RETENTION_LABELS: Record<string, string> = {
  audit_months: "الاحتفاظ بسجل التدقيق (شهرًا)",
  default_expiry_months: "صلاحية الرصيد الافتراضية (شهرًا)",
  otp_ttl_seconds: "صلاحية كود التحقق (ثانية)",
  pos_code_ttl_seconds: "صلاحية رمز الكاشير (ثانية)",
};

const LIMIT_LABELS: Record<string, string> = {
  max_branches: "فروع",
  max_terminals: "نقاط بيع",
  max_staff: "موظفون",
  max_programs: "برامج",
  max_customers: "عملاء",
  monthly_messages: "رسائل شهريًا",
};

const STAGE_TONES: Record<string, "green" | "amber" | "muted"> = {
  active: "green",
  planned: "amber",
  blocked: "muted",
};

const STAGE_LABELS: Record<string, string> = {
  active: "مفعّلة الآن",
  planned: "مخططة",
  blocked: "تحتاج مراجعة تنظيمية",
};

export function Config() {
  const config = useApi((signal) => queries.config(signal), []);

  if (config.loading) return <Loading />;
  if (config.error != null) return <ErrorBox error={config.error} onRetry={config.reload} />;
  if (!config.data) return null;

  const { retention, privacy, network_model: network, features, plans } = config.data;

  return (
    <>
      <div className="grid g2 mb">
        <section className="card">
          <div className="card-hd">
            <h3>{t("الخصوصية والامتثال")}</h3>
          </div>
          <div className="card-p">
            {privacy.map((row) => (
              <div key={row.key} className="li">
                <span className={`ibox ${row.enabled ? "g" : "a"}`} aria-hidden="true">
                  <Icon name={row.enabled ? "shield" : "clock"} size={18} />
                </span>
                <div className="grow">
                  <p className="li-t">{t(row.label)}</p>
                  <p className="li-s">{row.detail}</p>
                </div>
                <Badge tone={row.enabled ? "green" : "amber"}>
                  {row.enabled ? t("مفعّل") : t("غير مفعّل")}
                </Badge>
              </div>
            ))}
          </div>
        </section>

        <section className="card">
          <div className="card-hd">
            <h3>{t("نموذج النقاط عبر الشبكة")}</h3>
            <Badge tone="violet">
              {t("المرحلة")} <span className="num">{fmt.number(network.phase)}</span>
            </Badge>
          </div>
          <div className="card-p">
            <div className="card card-p tint-v mb-2">
              <b className="t-sm">{t(network.label)}</b>
              <p className="t-xs muted mt-1">{t(network.detail)}</p>
            </div>
            {network.stages.map((stage) => (
              <div key={stage.stage} className="li">
                <div className="grow">
                  <p className="li-t">
                    {t("المرحلة")} <span className="num">{fmt.number(stage.stage)}</span>
                    {" — "}
                    {t(stage.label)}
                  </p>
                </div>
                <Badge tone={STAGE_TONES[stage.status] ?? "muted"}>
                  {t(STAGE_LABELS[stage.status] ?? stage.status)}
                </Badge>
              </div>
            ))}
          </div>
        </section>
      </div>

      <div className="grid g2 mb">
        <section className="card">
          <div className="card-hd">
            <h3>{t("الاحتفاظ والصلاحيات")}</h3>
          </div>
          <div className="card-p">
            {Object.entries(retention).map(([key, value]) => (
              <div key={key} className="li">
                <div className="grow">
                  <p className="li-t">{t(RETENTION_LABELS[key] ?? key)}</p>
                </div>
                <span className="li-v num">
                  {value === null ? t("بلا حد") : fmt.number(value)}
                </span>
              </div>
            ))}
          </div>
        </section>

        <section className="card">
          <div className="card-hd">
            <h3>{t("مفاتيح الميزات")}</h3>
          </div>
          <div className="card-p">
            {/* خارج النطاق المبدئي عمدًا — المجلدات موجودة في
                الهيكلة حتى لا تحتاج إعادة بناء عند التفعيل */}
            {features.map((feature) => (
              <div key={feature.key} className="li">
                <div className="grow">
                  <p
                    className="li-t num"
                    style={{ direction: "ltr", textAlign: "start" }}
                  >
                    {feature.key}
                  </p>
                  <p className="li-s">{t("تطوير مستقبلي خارج النطاق المبدئي")}</p>
                </div>
                <Badge tone={feature.enabled ? "green" : "muted"}>
                  {feature.enabled ? t("مفعّل") : t("مطفأ")}
                </Badge>
              </div>
            ))}
          </div>
        </section>
      </div>

      <section className="card">
        <div className="card-hd">
          <h3>{t("الباقات وحدودها")}</h3>
          <span className="t-xs muted">
            {t("الحدود في الكود لا في جدول — تغييرها يمرّ بمراجعة ونشر")}
          </span>
        </div>
        <div className="table-wrap">
          <table className="tbl">
            <thead>
              <tr>
                <th>{t("الباقة")}</th>
                <th>{t("الشهري")}</th>
                <th>{t("المشتركون")}</th>
                <th>{t("الحدود")}</th>
              </tr>
            </thead>
            <tbody>
              {plans.map((plan) => (
                <tr key={plan.code}>
                  <td className="w-7">{t(plan.name)}</td>
                  <td className="num w-7">{fmt.money(plan.monthly_price)}</td>
                  <td className="num">{fmt.number(plan.subscribers)}</td>
                  <td className="muted t-sm">
                    {Object.entries(plan.limits)
                      .map(
                        ([key, value]) =>
                          `${value === null ? t("بلا حد") : fmt.number(value)} ${t(
                            LIMIT_LABELS[key] ?? key,
                          )}`,
                      )
                      .join(" · ")}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}
