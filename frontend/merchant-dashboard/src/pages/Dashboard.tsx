/**
 * لوحة التاجر.
 *
 * التخطيط مطابق للعرض المعتمد: شبكة مؤشرات كل واحد منها يحمل
 * أيقونته ورسمه المصغّر وفرقه عن الفترة السابقة، ثم مخطط أعمدة
 * للحركة. كل رقم من `/merchant/dashboard` و`/merchant/series`.
 *
 * ترتيب المؤشرات مقصود: الالتزام القائم أولًا لا الإيراد.
 * الإيراد رقم يعرفه التاجر من نظام الكاشير أصلًا. الالتزام القائم
 * هو الرقم الذي لا يستطيع معرفته بدوننا: كم وعدًا بخصم مستقبلي
 * أصدره، وكم يكلّفه لو جاء الجميع ليصرفوه غدًا.
 *
 * الرسم المصغّر داخل كل بطاقة ليس زينة: الرقم وحده لا يقول إن
 * العمليات تتراجع منذ أسبوع، والفرق المئوي وحده لا يقول إن
 * التراجع مستمر أم قفزة يوم واحد. الثلاثة معًا تُقرأ في ثانية.
 */

import { useState } from "react";
import { Link } from "react-router-dom";

import {
  ErrorBox,
  Icon,
  Loading,
  fmt,
  t,
  useApi,
  useInterval,
} from "@walaee/shared";
import type { Dashboard as DashboardData, IconName, SeriesPoint } from "@walaee/shared";

import { queries } from "../lib/queries";
import { atLeast } from "../lib/session";

const RANGES = [
  { days: 7, label: "٧ أيام" },
  { days: 30, label: "٣٠ يومًا" },
  { days: 90, label: "٩٠ يومًا" },
];

type Tone = "v" | "g" | "o" | "r" | "b" | "a";

export function Dashboard() {
  const [days, setDays] = useState(30);

  const board = useApi((signal) => queries.dashboard(days, signal), [days]);
  const series = useApi((signal) => queries.series(days, signal), [days]);

  if (board.loading) return <Loading />;
  if (board.error != null)
    return <ErrorBox error={board.error} onRetry={board.reload} />;
  if (!board.data) return null;

  const data = board.data;
  const points = series.data?.series ?? [];
  const rangeLabel = t(RANGES.find((r) => r.days === days)?.label ?? "");

  return (
    <div className="stack gap-lg">
      <div className="row between wrap-f">
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

        <Link to="/cashier" className="btn btn-primary btn-sm">
          <Icon name="scan" size={15} />
          {t("افتح شاشة الكاشير")}
        </Link>
      </div>

      {data.open_fraud_signals > 0 && atLeast("owner") && (
        <Link to="/fraud" className="alert-strip">
          <Icon name="alert" size={18} />
          <span className="grow">
            <span className="num w-8">{fmt.number(data.open_fraud_signals)}</span>{" "}
            {t("عملية تحتاج مراجعتك")}
          </span>
          <Icon name="chevronLeft" size={18} />
        </Link>
      )}

      <div className="grid g3">
        <Kpi
          tone="v"
          icon="users"
          label={t("عملاء جدد في الفترة")}
          value={fmt.number(data.customers.new)}
          sub={t("من {n} عميل مسجّل", { n: fmt.number(data.customers.total) })}
          range={rangeLabel}
          points={points}
          field="transactions"
        />
        <Kpi
          tone="g"
          icon="refresh"
          label={t("العملاء العائدون")}
          value={fmt.percent(data.customers.repeat_rate_pct).replace("+", "")}
          sub={t("{repeat} من {active} نشط", {
            repeat: fmt.number(data.customers.repeat),
            active: fmt.number(data.customers.active),
          })}
          range={rangeLabel}
          points={points}
          field="transactions"
        />
        <Kpi
          tone="b"
          icon="trendingUp"
          label={t("معدل تكرار الشراء")}
          value={fmt.number(frequency(data), 1)}
          sub={t("عملية لكل عميل نشط في الفترة")}
          delta={data.transactions.change_pct}
          range={rangeLabel}
          points={points}
          field="transactions"
        />
        <Kpi
          tone="o"
          icon="gift"
          label={t("مكافآت مُستبدلة")}
          value={fmt.number(data.redemptions)}
          sub={t("ما صرفه عملاؤك فعلًا")}
          range={rangeLabel}
          points={points}
          field="transactions"
        />
        {atLeast("owner") ? (
          <Kpi
            tone="a"
            icon="wallet"
            label={t("الالتزام القائم")}
            value={fmt.money(data.liability.estimated_value)}
            sub={t("{n} وحدة غير مستبدَلة", {
              n: fmt.number(data.liability.total_units),
            })}
            range={rangeLabel}
            points={points}
            field="transactions"
          />
        ) : (
          <Kpi
            tone="a"
            icon="coins"
            label={t("الإيراد المسجّل")}
            value={fmt.money(data.revenue.total)}
            sub={t("فواتير مرّت على برنامج الولاء")}
            delta={data.revenue.change_pct}
            range={rangeLabel}
            points={points}
            field="revenue"
          />
        )}
        <Kpi
          tone="r"
          icon="shield"
          label={t("عمليات تحتاج مراجعة")}
          value={fmt.number(data.open_fraud_signals)}
          sub={t("كشف شذوذ آلي")}
          range={rangeLabel}
          points={points}
          field="transactions"
        />
      </div>

      <div className="dash-split">
        <section className="card">
          <div className="card-hd">
            <div>
              <h3>{t("حركة العمليات")}</h3>
              <p className="t-sm muted"> {t("آخر")} {rangeLabel}</p>
            </div>
          </div>

          <div className="card-p">
            {series.loading && <Loading />}
            {series.error != null && (
              <ErrorBox error={series.error} onRetry={series.reload} />
            )}
            {series.data && <Bars points={points} />}
          </div>
        </section>

        <AtRisk />
      </div>

      <LiveActivity />
    </div>
  );
}

/* ══════════════ عملاء معرّضون للفقدان ══════════════ */

/**
 * الشريحة الوحيدة التي تستحق فعلًا اليوم.
 *
 * وجودها بجوار المخطط مقصود: المخطط يقول «الزيارات نزلت»،
 * وهذه تقول **مَن** نزل تحديدًا وتضع زر الحملة في نفس النظرة.
 * فصلهما يجعل التاجر يرى المشكلة في شاشة والحل في أخرى.
 */
function AtRisk() {
  const risky = useApi(
    (signal) => queries.customers({ segment: "at_risk", page: 1 }, signal),
    [],
  );

  const rows = risky.data?.results ?? [];

  return (
    <section className="card">
      <div className="card-hd">
        <h3>{t("عملاء معرّضون للفقدان")}</h3>
        {rows.length > 0 && (
          <span className="badge bg-r num">
            {fmt.plural(risky.data?.count ?? 0, {
              zero: t("لا أحد"),
              one: t("عميل واحد"),
              two: t("عميلان"),
              few: t("عملاء"),
              many: t("عميلًا"),
            })}
          </span>
        )}
      </div>

      <div className="card-p">
        <p className="t-sm muted mb-2">
          {t("لم يعودوا خلال ضعف متوسط فترة زيارتهم المعتادة.")}
        </p>

        {risky.loading && <Loading />}
        {risky.error != null && (
          <ErrorBox error={risky.error} onRetry={risky.reload} />
        )}

        {!risky.loading && rows.length === 0 && (
          <p className="t-sm muted">{t("لا أحد في هذه الشريحة الآن — خبر جيّد.")}</p>
        )}

        {rows.slice(0, 4).map((row) => (
          <div key={row.id} className="li">
            <span
              className="av av-sm"
              style={{
                background: "var(--red-100)",
                color: "var(--red-600)",
              }}
              aria-hidden="true"
            >
              {(row.full_name || t("؟")).trim().charAt(0)}
            </span>
            <div className="grow">
              <p className="li-t">{row.full_name || t("عميل")}</p>
              <p className="li-s">
                {t("عضو منذ")} {fmt.date(row.joined_at)}
              </p>
            </div>
          </div>
        ))}

        {rows.length > 0 && (
          <Link to="/campaigns" className="btn btn-orange btn-block mt-3">
            <Icon name="message" size={16} />
            {t("أطلق حملة استرجاع")}
          </Link>
        )}
      </div>
    </section>
  );
}

/* ══════════════ أحدث العمليات ══════════════ */

const STATUS_BADGE: Record<string, { tone: string; label: string }> = {
  confirmed: { tone: "bg-g", label: "مؤكدة" },
  pending: { tone: "bg-a", label: "بانتظار التأكيد" },
  rejected: { tone: "bg-r", label: "مرفوضة" },
  reversed: { tone: "bg-n", label: "معكوسة" },
};

/**
 * ما يحدث عند الصندوق الآن.
 *
 * يُحدَّث كل عشرين ثانية لا كل ثانية: الجدول يُقرأ بالنظر لا
 * بالمراقبة، والتحديث المستمر يقفز بالصفوف تحت عين القارئ ويستهلك
 * بطارية الجهاز الموضوع بجوار الصندوق طوال اليوم. الخطّاف يوقف
 * التحديث تلقائيًا حين يكون التبويب مخفيًا.
 */
function LiveActivity() {
  const feed = useApi((signal) => queries.activity(signal), []);
  useInterval(() => feed.reload(), 20_000);

  const rows = feed.data?.activity ?? [];

  return (
    <section className="card">
      <div className="card-hd">
        <div className="row">
          <h3>{t("أحدث العمليات")}</h3>
          <span className="live">
            <i />
            {t("مباشر")}
          </span>
        </div>
        <Link to="/cashier" className="btn btn-line btn-sm">
          <Icon name="qr" size={14} />
          {t("فتح وضع الكاشير")}
        </Link>
      </div>

      {feed.loading && rows.length === 0 && <Loading />}
      {feed.error != null && <ErrorBox error={feed.error} onRetry={feed.reload} />}

      {!feed.loading && rows.length === 0 ? (
        <p className="card-p muted t-sm">{t("لا توجد عمليات بعد.")}</p>
      ) : (
        <div className="table-wrap">
          <table className="tbl">
            <thead>
              <tr>
                <th>{t("الوقت")}</th>
                <th>{t("العميل")}</th>
                <th>{t("الفرع")}</th>
                <th>{t("الكاشير")}</th>
                <th>{t("الفاتورة")}</th>
                <th>{t("الأثر")}</th>
                <th>{t("الحالة")}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => {
                const badge = STATUS_BADGE[row.status] ?? {
                  tone: "bg-n",
                  label: row.status,
                };
                const delta = Number(row.delta);
                return (
                  <tr key={row.id}>
                    <td className="num muted">{fmt.clock(row.at)}</td>
                    <td className="w-7">{row.customer}</td>
                    <td className="muted">{row.branch}</td>
                    <td className="muted">{row.cashier}</td>
                    <td className="num w-7">{fmt.money(row.amount)}</td>
                    <td className={`num w-8 ${delta > 0 ? "c-green" : "muted"}`}>
                      {delta > 0 ? "+" : ""}
                      {fmt.number(row.delta)}
                    </td>
                    <td>
                      <span className={`badge ${badge.tone}`}>{t(badge.label)}</span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

/**
 * معدل تكرار الشراء: عمليات الفترة ÷ العملاء النشطين فيها.
 *
 * يُحسب في الواجهة لا في الخلفية لأنه قسمة بين رقمين معروضين على
 * البطاقتين المجاورتين — القارئ يستطيع التحقق منه بعينه.
 */
function frequency(data: DashboardData): number {
  if (!data.customers.active) return 0;
  return data.transactions.count / data.customers.active;
}

/* ══════════════ بطاقة مؤشر ══════════════ */

function Kpi({
  tone,
  icon,
  label,
  value,
  sub,
  delta,
  range,
  points,
  field,
}: {
  tone: Tone;
  icon: IconName;
  label: string;
  value: string;
  sub: string;
  delta?: number | null;
  range: string;
  points: SeriesPoint[];
  field: "transactions" | "revenue";
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

      <Spark points={points} field={field} tone={tone} />

      <div className="row between">
        <Delta value={delta} />
        <span className="t-xs faint"> {t("آخر")} {range}</span>
      </div>
    </article>
  );
}

function Delta({ value }: { value?: number | null }) {
  if (value === null || value === undefined) {
    return <span className="t-xs faint">{t("لا مقارنة متاحة")}</span>;
  }

  const kind = value > 0 ? "up" : value < 0 ? "dn" : "flat";
  return (
    <span className={`delta ${kind}`}>
      <Icon name={value >= 0 ? "trendingUp" : "chart"} size={11} />
      <span className="num">{fmt.percent(value)}</span>
    </span>
  );
}

const TONE_COLORS: Record<Tone, string> = {
  v: "var(--violet-600)",
  g: "var(--green-600)",
  o: "var(--orange-600)",
  r: "var(--red-600)",
  b: "var(--blue-600)",
  a: "var(--amber-600)",
};

/**
 * رسم مصغّر داخل بطاقة المؤشر.
 *
 * بلا مكتبة رسم: مخطط خطّي واحد لا يبرّر ٩٠ ك.ب إضافية على لوحة
 * تُفتح من جهاز في متجر قد يكون على شبكة بطيئة.
 */
function Spark({
  points,
  field,
  tone,
}: {
  points: SeriesPoint[];
  field: "transactions" | "revenue";
  tone: Tone;
}) {
  if (points.length < 2) return <div className="spk-empty" />;

  const width = 100;
  const height = 30;
  const values = points.map((p) =>
    field === "revenue" ? Number(p.revenue) : p.transactions,
  );
  const max = Math.max(...values, 1);

  // من اليمين إلى اليسار ليتبع اتجاه القراءة العربي: مخطط يبدأ من
  // اليسار يجعل التاجر يقرأ الزمن معكوسًا
  const step = width / (points.length - 1);
  const yOf = (value: number) => height - (value / max) * (height - 4) - 2;

  const path = values
    .map((value, index) => {
      const x = width - index * step;
      return `${index === 0 ? "M" : "L"}${x.toFixed(2)},${yOf(value).toFixed(2)}`;
    })
    .join(" ");

  const color = TONE_COLORS[tone];

  return (
    <svg
      className="spk"
      viewBox={`0 0 ${width} ${height}`}
      preserveAspectRatio="none"
      role="img"
      aria-label={`اتجاه ${field === "revenue" ? t("الإيراد") : t("العمليات")}`}
    >
      <path d={`${path} L0,${height} L${width},${height} Z`} fill={color} opacity="0.12" />
      {/* non-scaling-stroke إلزامي مع preserveAspectRatio="none":
          الإطار يُمدّ أفقيًا أضعافًا ورأسيًا أقلّ، فيتشوّه سمك الخط
          مع الميل حتى يكاد يختفي في المقاطع الأفقية. */}
      <path
        d={path}
        fill="none"
        stroke={color}
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  );
}

/* ══════════════ مخطط الأعمدة ══════════════ */

/**
 * أعمدة لا خط.
 *
 * البيانات هنا عدّ يومي منفصل لا قياس متّصل: الخط بين يومين يرسم
 * قيمًا وسيطة لم تحدث، والعمود يقول «هذا اليوم كذا» وحسب. ولأن
 * أغلب أيام متجر صغير أصفار، فالأعمدة تُظهر الفراغ صراحةً بدل أن
 * يمسح الخط فوقه.
 */
function Bars({ points }: { points: SeriesPoint[] }) {
  const total = points.reduce((sum, p) => sum + p.transactions, 0);

  if (points.length === 0 || total === 0) {
    return <p className="muted t-sm">{t("لا توجد عمليات في هذه الفترة.")}</p>;
  }

  const max = Math.max(...points.map((p) => p.transactions), 1);
  const peak = points.reduce((best, p) =>
    p.transactions > best.transactions ? p : best,
  );
  const revenue = points.reduce((sum, p) => sum + Number(p.revenue), 0);

  // الأحدث يمينًا: اتجاه قراءة الصفحة نفسه
  const ordered = [...points].reverse();
  // عند مدى طويل لا تتّسع كل التسميات — تُعرض واحدة كل خمس
  const labelEvery = points.length > 14 ? 5 : 1;

  return (
    <>
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

      <div className="grid g3 mt-3">
        <div>
          <p className="t-xs muted">{t("إجمالي العمليات")}</p>
          <p className="t-lg w-8 num">{fmt.number(total)}</p>
        </div>
        <div>
          <p className="t-xs muted">{t("إجمالي الإيراد")}</p>
          <p className="t-lg w-8 num">{fmt.money(revenue)}</p>
        </div>
        <div>
          <p className="t-xs muted">{t("أعلى يوم")}</p>
          <p className="t-lg w-8">{fmt.date(peak.date)}</p>
        </div>
      </div>
    </>
  );
}
