/**
 * لوحة التاجر.
 *
 * ترتيب المؤشرات مقصود: الالتزام القائم أولًا لا الإيراد.
 *
 * الإيراد رقم يعرفه التاجر من نظام الكاشير أصلًا. الالتزام القائم
 * هو الرقم الذي لا يستطيع معرفته بدوننا: كم وعدًا بخصم مستقبلي
 * أصدره، وكم يكلّفه لو جاء الجميع ليصرفوه غدًا.
 */

import { useState } from "react";
import { Link } from "react-router-dom";

import { Badge, ErrorBox, Loading, Stat, fmt, useApi } from "@walaee/shared";
import type { SeriesPoint } from "@walaee/shared";

import { queries } from "../lib/queries";
import { atLeast } from "../lib/session";

const RANGES = [
  { days: 7, label: "٧ أيام" },
  { days: 30, label: "٣٠ يومًا" },
  { days: 90, label: "٩٠ يومًا" },
];

export function Dashboard() {
  const [days, setDays] = useState(30);

  const board = useApi((signal) => queries.dashboard(days, signal), [days]);
  const series = useApi((signal) => queries.series(days, signal), [days]);

  if (board.loading) return <Loading />;
  if (board.error != null)
    return <ErrorBox error={board.error} onRetry={board.reload} />;
  if (!board.data) return null;

  const data = board.data;

  return (
    <div className="stack gap-lg">
      <header className="row between wrap">
        <div>
          <h1>نظرة عامة</h1>
          <p className="t-sm muted">آخر {RANGES.find((r) => r.days === days)?.label}</p>
        </div>

        <div className="range-switch" role="group" aria-label="الفترة">
          {RANGES.map((range) => (
            <button
              key={range.days}
              type="button"
              className={days === range.days ? "active" : ""}
              onClick={() => setDays(range.days)}
            >
              {range.label}
            </button>
          ))}
        </div>
      </header>

      {data.open_fraud_signals > 0 && atLeast("owner") && (
        <Link to="/fraud" className="alert-strip">
          <span aria-hidden="true">⚠</span>
          <span className="grow">
            <span className="num w-8">{data.open_fraud_signals}</span> عملية
            تحتاج مراجعتك
          </span>
          <span aria-hidden="true">‹</span>
        </Link>
      )}

      {atLeast("owner") && (
        <section className="liability">
          <div className="row between wrap">
            <div>
              <p className="t-sm">الالتزام القائم</p>
              <p className="liability-value num">
                {fmt.money(data.liability.estimated_value)}
              </p>
              <p className="t-sm">
                <span className="num">
                  {fmt.number(data.liability.total_units)}
                </span>{" "}
                وحدة غير مستبدَلة
              </p>
            </div>

            <div className="liability-breakdown">
              {data.liability.by_program.map((line) => (
                <div key={line.program_id} className="row between">
                  <span className="t-sm">{line.program_name}</span>
                  <span className="t-sm num w-7">
                    {fmt.money(line.estimated_value)}
                  </span>
                </div>
              ))}
            </div>
          </div>
          <p className="t-xs liability-note">{data.liability.note}</p>
        </section>
      )}

      <div className="stats-grid">
        <Stat
          label="العمليات"
          value={fmt.number(data.transactions.count)}
          hint={<Change value={data.transactions.change_pct} />}
        />
        <Stat
          label="الإيراد"
          value={fmt.money(data.revenue.total)}
          hint={<Change value={data.revenue.change_pct} />}
        />
        <Stat
          label="متوسط الفاتورة"
          value={fmt.money(data.revenue.average_invoice)}
        />
        <Stat
          label="العملاء"
          value={fmt.number(data.customers.total)}
          hint={`${fmt.number(data.customers.new)} جديد في الفترة`}
        />
        <Stat
          label="العملاء العائدون"
          value={`${fmt.number(data.customers.repeat_rate_pct, 1)}٪`}
          tone={data.customers.repeat_rate_pct >= 25 ? "good" : "warn"}
          hint={`${fmt.number(data.customers.repeat)} من ${fmt.number(
            data.customers.active,
          )} نشط`}
        />
        <Stat label="الاستبدالات" value={fmt.number(data.redemptions)} />
      </div>

      <section className="card wl-card-p">
        <h2 className="mb-sm">حركة العمليات</h2>
        {series.loading && <Loading />}
        {series.data && <Sparkline points={series.data.series} />}
      </section>
    </div>
  );
}

function Change({ value }: { value: number | null }) {
  if (value === null) return <span className="faint">لا مقارنة متاحة</span>;

  const tone = value > 0 ? "green" : value < 0 ? "red" : "muted";
  return <Badge tone={tone}>{fmt.percent(value)}</Badge>;
}

/**
 * رسم بياني بسيط بـSVG.
 *
 * بلا مكتبة رسم: مخطط خطّي واحد لا يبرّر ٩٠ ك.ب إضافية على لوحة
 * تُفتح من جهاز في متجر قد يكون على شبكة بطيئة.
 */
function Sparkline({ points }: { points: SeriesPoint[] }) {
  if (points.length === 0) {
    return <p className="muted t-sm">لا توجد بيانات في هذه الفترة.</p>;
  }

  const width = 100;
  const height = 34;
  const max = Math.max(...points.map((p) => p.transactions), 1);

  // النقاط تُرسم من اليمين لليسار لتتبع اتجاه القراءة العربي:
  // مخطط يبدأ من اليسار يجعل التاجر يقرأ الزمن معكوسًا
  const step = points.length > 1 ? width / (points.length - 1) : 0;
  const path = points
    .map((point, index) => {
      const x = width - index * step;
      const y = height - (point.transactions / max) * (height - 4) - 2;
      return `${index === 0 ? "M" : "L"}${x.toFixed(2)},${y.toFixed(2)}`;
    })
    .join(" ");

  const total = points.reduce((sum, p) => sum + p.transactions, 0);
  const peak = points.reduce((best, p) =>
    p.transactions > best.transactions ? p : best,
  );

  return (
    <div className="stack gap">
      <svg
        viewBox={`0 0 ${width} ${height}`}
        preserveAspectRatio="none"
        className="sparkline"
        role="img"
        aria-label={`${total} عملية خلال الفترة`}
      >
        <path d={path} fill="none" stroke="var(--violet-600)" strokeWidth="1.2" />
      </svg>

      <div className="row between t-sm muted">
        <span>
          الإجمالي <span className="num w-7">{fmt.number(total)}</span> عملية
        </span>
        <span>
          الذروة <span className="num w-7">{fmt.number(peak.transactions)}</span>{" "}
          يوم {fmt.date(peak.date)}
        </span>
      </div>
    </div>
  );
}
