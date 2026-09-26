/**
 * التقارير — أثر برنامج الولاء على النشاط.
 *
 * الفرق بين هذه الشاشة و«لوحة المعلومات»: اللوحة تقول **ما يحدث
 * الآن**، والتقارير تقول **هل البرنامج يستحق ما تدفعه فيه**.
 * السؤال الثاني لا يُجاب عنه برقم واحد بل بمقارنات: فرع بفرع،
 * وبرنامج ببرنامج، وعميل عضو بعميل غير عضو.
 *
 * كل ما هنا من `/merchant/reports/*` و`/merchant/dashboard` — لا
 * رقم مشتق في الواجهة إلا ما يُحسب أمام القارئ من قيمتين
 * معروضتين، وما لا يسنده مصدر لا يُعرض أصلًا.
 */

import { useState } from "react";

import { ErrorBox, Icon, Loading, fmt, t, useApi } from "@walaee/shared";
import type { IconName, SeriesPoint } from "@walaee/shared";

import { queries } from "../lib/queries";

const RANGES = [
  { days: 30, label: "٣٠ يومًا" },
  { days: 90, label: "٩٠ يومًا" },
  { days: 365, label: "سنة" },
];

interface BranchRow {
  branch_id: string;
  branch_name: string;
  transactions: number;
  revenue: string;
  customers: number;
}

interface ProgramRow {
  program_id: string;
  name: string;
  type: string;
  granted: string;
  redeemed: string;
  expired: string;
  redemption_rate_pct: number;
}

export function Reports() {
  const [days, setDays] = useState(90);

  const board = useApi((signal) => queries.dashboard(days, signal), [days]);
  const series = useApi((signal) => queries.series(days, signal), [days]);
  const branches = useApi((signal) => queries.report("branches", signal), []);
  const programs = useApi((signal) => queries.report("programs", signal), []);
  const top = useApi((signal) => queries.report("top-customers", signal), []);

  if (board.loading) return <Loading />;
  if (board.error != null)
    return <ErrorBox error={board.error} onRetry={board.reload} />;
  if (!board.data) return null;

  const data = board.data;
  const rangeLabel = t(RANGES.find((r) => r.days === days)?.label ?? "");
  const branchRows = (branches.data?.rows ?? []) as unknown as BranchRow[];
  const programRows = (programs.data?.rows ?? []) as unknown as ProgramRow[];

  return (
    <div className="stack gap-lg">
      <div className="tabs" role="group" aria-label={t("الفترة")}>
        {RANGES.map((range) => (
          <button
            key={range.days}
            type="button"
            className={days === range.days ? "on" : ""}
            onClick={() => setDays(range.days)}
          >
            {t(range.label)}
          </button>
        ))}
      </div>

      <div className="grid g4">
        <Figure
          tone="g"
          icon="trendingUp"
          label={t("العملاء العائدون")}
          value={fmt.percent(data.customers.repeat_rate_pct).replace("+", "")}
          sub={t("{repeat} من {active} نشط", {
            repeat: fmt.number(data.customers.repeat),
            active: fmt.number(data.customers.active),
          })}
        />
        <Figure
          tone="v"
          icon="bolt"
          label={t("معدل تفعيل العميل")}
          value={fmt.percent(activation(data)).replace("+", "")}
          sub={t("انضموا وأتمّوا عملية واحدة على الأقل")}
        />
        <Figure
          tone="b"
          icon="coins"
          label={t("متوسط الفاتورة")}
          value={fmt.money(data.revenue.average_invoice)}
          sub={t("على {n} فاتورة", { n: fmt.number(data.transactions.count) })}
        />
        <Figure
          tone="o"
          icon="gift"
          label={t("مكافآت مُستبدلة")}
          value={fmt.number(data.redemptions)}
          sub={t("خلال {range}", { range: rangeLabel })}
        />
      </div>

      <section className="card">
        <div className="card-hd">
          <div>
            <h3>{t("حركة العمليات")}</h3>
            <p className="t-sm muted"> {t("آخر")} {rangeLabel}</p>
          </div>
        </div>
        <div className="card-p">
          {series.loading && <Loading />}
          {series.data && <Trend points={series.data.series} />}
        </div>
      </section>

      <section className="card">
        <div className="card-hd">
          <h3>{t("تفصيل حسب الفرع")}</h3>
          <span className="t-sm muted">
            {t("الفرع الذي لا يطبّق البرنامج يظهر هنا قبل أي مكان آخر")}
          </span>
        </div>

        {branches.loading && <Loading />}
        {branchRows.length === 0 && !branches.loading ? (
          <p className="card-p muted t-sm">{t("لا توجد عمليات مسجّلة بعد.")}</p>
        ) : (
          <div className="table-wrap">
            <table className="tbl">
              <thead>
                <tr>
                  <th>{t("الفرع")}</th>
                  <th>{t("العمليات")}</th>
                  <th>{t("العملاء")}</th>
                  <th>{t("الإيراد")}</th>
                  <th>{t("الحصة")}</th>
                </tr>
              </thead>
              <tbody>
                {branchRows.map((row) => {
                  const total = branchRows.reduce(
                    (sum, r) => sum + Number(r.revenue),
                    0,
                  );
                  const share = total > 0 ? (Number(row.revenue) / total) * 100 : 0;
                  return (
                    <tr key={row.branch_id}>
                      <td className="w-7">{row.branch_name}</td>
                      <td className="num">{fmt.number(row.transactions)}</td>
                      <td className="num">{fmt.number(row.customers)}</td>
                      <td className="num w-7">{fmt.money(row.revenue)}</td>
                      <td style={{ width: 170 }}>
                        <span className="bar">
                          <i style={{ width: `${Math.max(share, 2)}%` }} />
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <div className="grid g2">
        <section className="card">
          <div className="card-hd">
            <h3>{t("أداء البرامج")}</h3>
          </div>
          {programRows.length === 0 ? (
            <p className="card-p muted t-sm">{t("لا توجد برامج نشطة.")}</p>
          ) : (
            <div className="card-p stack gap">
              {programRows.map((row) => (
                <div key={row.program_id} className="usage">
                  <span className="t-sm w-7" style={{ width: "7rem" }}>
                    {row.name}
                  </span>
                  <span className="bar g">
                    <i
                      style={{
                        width: `${Math.max(row.redemption_rate_pct, 2)}%`,
                      }}
                    />
                  </span>
                  <span className="t-sm num w-7 nowrap">
                    {fmt.percent(row.redemption_rate_pct)}
                  </span>
                </div>
              ))}
              <p className="t-xs muted">
                {t("نسبة ما استُبدل إلى ما مُنح. المنخفض جدًا يعني مكافآت بعيدة المنال، والمرتفع جدًا يعني منحًا أكثر من اللازم.")}
              </p>
            </div>
          )}
        </section>

        <section className="card">
          <div className="card-hd">
            <h3>{t("أكثر العملاء إنفاقًا")}</h3>
          </div>
          {top.loading && <Loading />}
          {(top.data?.rows ?? []).length === 0 && !top.loading ? (
            <p className="card-p muted t-sm">{t("لا توجد بيانات كافية بعد.")}</p>
          ) : (
            <div className="card-p">
              {(top.data?.rows ?? []).slice(0, 6).map((row, index) => (
                <div key={String(row.customer_id ?? index)} className="li">
                  <span className="av av-sm" aria-hidden="true">
                    {String(row.name ?? t("؟")).trim().charAt(0)}
                  </span>
                  <div className="grow">
                    <p className="li-t">{String(row.name ?? t("عميل"))}</p>
                    <p className="li-s num">
                      {fmt.number(Number(row.visits ?? 0))} {t("زيارة")}
                    </p>
                  </div>
                  <span className="li-v num">
                    {fmt.money(String(row.total_spend ?? 0))}
                  </span>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

/**
 * معدل التفعيل: نسبة من سجّلوا وأتمّوا عملية.
 *
 * يُحسب هنا لا في الخلفية لأنه قسمة بين رقمين معروضين على نفس
 * الشاشة — القارئ يستطيع التحقق منه بعينه، وهو شرط عرض أي رقم
 * مشتق في الواجهة.
 */
function activation(data: {
  customers: { total: number; active: number };
}): number {
  if (!data.customers.total) return 0;
  return (data.customers.active / data.customers.total) * 100;
}

function Figure({
  tone,
  icon,
  label,
  value,
  sub,
}: {
  tone: "v" | "g" | "o" | "r" | "b" | "a";
  icon: IconName;
  label: string;
  value: string;
  sub: string;
}) {
  return (
    <article className="kpi">
      <div className="row between">
        <div className="grow">
          <p className="kt">{label}</p>
          <p className="kv num">{value}</p>
          <p className="ks">{sub}</p>
        </div>
        <span className={`ibox ${tone}`} aria-hidden="true">
          <Icon name={icon} size={20} />
        </span>
      </div>
    </article>
  );
}

/** مخطط أعمدة مبسّط — نفس منطق لوحة المعلومات. */
function Trend({ points }: { points: SeriesPoint[] }) {
  const total = points.reduce((sum, p) => sum + p.transactions, 0);
  if (points.length === 0 || total === 0) {
    return <p className="muted t-sm">{t("لا توجد عمليات في هذه الفترة.")}</p>;
  }

  const max = Math.max(...points.map((p) => p.transactions), 1);
  const ordered = [...points].reverse();
  const labelEvery = points.length > 14 ? Math.ceil(points.length / 10) : 1;

  return (
    <div className="bars" style={{ "--count": points.length } as React.CSSProperties}>
      {ordered.map((point, index) => (
        <div key={point.date} className="bar-col">
          <span
            className="bar-fill"
            style={{ height: `${Math.max((point.transactions / max) * 100, 2)}%` }}
            title={`${fmt.date(point.date)} — ${point.transactions}`}
          />
          <span className="bar-lbl">
            {index % labelEvery === 0 ? fmt.dayMonth(point.date) : ""}
          </span>
        </div>
      ))}
    </div>
  );
}
