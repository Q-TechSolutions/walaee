/**
 * مؤشرات الصحة مقابل أهدافها.
 *
 * ليست «نظرة عامة» ثانية. تلك تقول ما حدث، وهذه تقول هل ما حدث
 * كافٍ — ولذلك لا يُعرض رقم هنا بلا هدفه وحكمه: «انسحاب ٤٪» تُقرأ
 * جيدة أو كارثية حسب الهدف، وشاشة تعرض الرقم وحده تترك القارئ
 * يخمّن ثم يمضي.
 *
 * وما هو خارج هدفه يُرفع إلى أعلى الشاشة في قسمه الخاص. مؤشر
 * يستدعي قرارًا مدفونًا بين خمسة سليمة يُقرأ بعد أسبوع.
 */

import { ErrorBox, Icon, Loading, fmt, t, useApi } from "@walaee/shared";

import { queries } from "../lib/queries";
import type { HealthMetric } from "../lib/queries";

export function Health() {
  const health = useApi((signal) => queries.health(signal), []);

  if (health.loading) return <Loading />;
  if (health.error != null)
    return <ErrorBox error={health.error} onRetry={health.reload} />;
  if (!health.data) return null;

  const { metrics, off_target: missed } = health.data;

  return (
    <>
      <section className="card card-p tint-v mb">
        <div className="row-t">
          <span className="ibox v" aria-hidden="true">
            <Icon name="target" size={20} />
          </span>
          <div className="grow">
            <b>{t("هذه الأرقام هي ما يقرر إن كان المشروع يستحق الاستثمار")}</b>
            <p className="t-sm muted mt-1">
              {t("تُقاس منذ اليوم الأول وتُراجع أسبوعيًا. أي مؤشر خارج هدفه يستدعي قرارًا، لا تفسيرًا.")}
            </p>
          </div>
        </div>
      </section>

      {missed.length > 0 && (
        <section className="card card-p tint-r mb">
          <div className="row-t">
            <span className="ibox r" aria-hidden="true">
              <Icon name="alert" size={20} />
            </span>
            <div className="grow">
              <b>
                <span className="num">{fmt.number(missed.length)}</span>{" "}
                {fmt.plural(missed.length, {
                  zero: t("مؤشر خارج هدفه"),
                  one: t("مؤشر خارج هدفه"),
                  two: t("مؤشران خارج هدفيهما"),
                  few: t("مؤشرات خارج أهدافها"),
                  many: t("مؤشرًا خارج هدفه"),
                })}
              </b>
              <p className="t-sm muted mt-1">
                {missed.map((metric) => t(metric.label)).join(" · ")}
              </p>
            </div>
          </div>
        </section>
      )}

      <div className="grid g2">
        {metrics.map((metric) => (
          <MetricCard key={metric.key} metric={metric} />
        ))}
      </div>
    </>
  );
}

/** يحوّل خانات الخادم إلى أرقام بنظام اللغة — والمبلغ بعملته. */
function formatVars(vars: Record<string, string>): Record<string, string> {
  const out: Record<string, string> = {};
  for (const [name, value] of Object.entries(vars)) {
    out[name] = name === "amount" ? fmt.money(value) : fmt.number(value);
  }
  return out;
}

function MetricCard({ metric }: { metric: HealthMetric }) {
  // النسبة من الهدف تُحصر عند مئة: شريط يتجاوز خانته لا يقول
  // «تفوّقنا» بل يبدو مكسورًا
  const reached =
    metric.direction === "up"
      ? Math.min((metric.value / Math.max(metric.target, 1)) * 100, 100)
      : Math.min((metric.target / Math.max(metric.value, 0.1)) * 100, 100);

  return (
    <section className="card card-p">
      <div className="row between mb-2">
        <div className="grow">
          <p className="t-sm w-7 muted">{t(metric.label)}</p>
          <p className={`t-2xl w-8 num mt-1 ${metric.on_target ? "c-green" : "c-red"}`}>
            {fmt.share(metric.value, 1)}
          </p>
          <p className="t-xs muted w-6">
            {t("الهدف")}{" "}
            {metric.direction === "up" ? t("لا يقلّ عن") : t("لا يزيد على")}{" "}
            <span className="num">{fmt.share(metric.target)}</span>
          </p>
        </div>
        <span
          className={`ibox ${metric.on_target ? "g" : "r"}`}
          aria-label={metric.on_target ? t("في الهدف") : t("خارج الهدف")}
        >
          <Icon name={metric.on_target ? "checkCircle" : "alert"} size={20} />
        </span>
      </div>

      <span className={`bar ${metric.on_target ? "g" : "o"}`}>
        <i style={{ width: `${reached}%` }} />
      </span>

      {/* الأرقام تُنسَّق هنا لا في الخادم: خانة لاتينية وسط جملة
          عربية تقطعها، والقالب يُترجَم كاملًا */}
      <p className="t-sm muted mt-2">
        {t(metric.hint, formatVars(metric.hint_vars))}
      </p>
    </section>
  );
}
