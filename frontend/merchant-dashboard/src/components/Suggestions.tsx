/**
 * التوصيتان الإحصائيتان: كم تساوي المكافأة، ومتى تُرسَل الحملة.
 *
 * حسابُ متوسطات لا تعلّم آلي، وتُسمّى هنا بما هي: «اقتراح» لا
 * «توقّع». التسمية ليست تواضعًا — التاجر الذي يقرأ «توقّع» يأخذ
 * الرقم كما هو، والذي يقرأ «اقتراح» يراجعه.
 *
 * والامتناع جزء من الواجهة لا استثناء فيها: تحت عتبة العيّنة
 * يُعرض ما ينقص بدل رقم. توصية على سبع فواتير تُعرض بنفس خطّ
 * توصية على سبعة آلاف، والتاجر يسعّر مكافأته عليها.
 */

import { Badge, Icon, Loading, fmt, t } from "@walaee/shared";

import type { RewardValueSuggestion, SendTimeSuggestion } from "../lib/queries";

const CONFIDENCE_LABELS: Record<string, string> = {
  low: "عيّنة محدودة",
  medium: "عيّنة معقولة",
  high: "عيّنة قوية",
};

const CONFIDENCE_TONES: Record<string, "muted" | "amber" | "green"> = {
  low: "muted",
  medium: "amber",
  high: "green",
};

function Confidence({ level }: { level?: string }) {
  if (!level) return null;
  return (
    <Badge tone={CONFIDENCE_TONES[level] ?? "muted"}>
      {t(CONFIDENCE_LABELS[level] ?? level)}
    </Badge>
  );
}

function NotEnough({
  sample,
  needed,
  what,
}: {
  sample: number;
  needed: number;
  what: string;
}) {
  return (
    <div className="card card-p tint-a row-t">
      <span className="ibox a" aria-hidden="true">
        <Icon name="info" size={20} />
      </span>
      <div className="grow">
        <p className="w-7 t-md">{t("لسه بدري على اقتراح")}</p>
        <p className="t-sm muted">
          {t("عندك {n} {what} من {m} مطلوبة. الاقتراح على عيّنة أقل يتحرّك بحالة شاذّة واحدة.", {
            n: fmt.number(sample),
            m: fmt.number(needed),
            what: t(what),
          })}
        </p>
      </div>
    </div>
  );
}

/* ══════════════ قيمة المكافأة ══════════════ */

export function RewardValueCard({
  data,
  loading,
  rewards = [],
}: {
  data?: RewardValueSuggestion;
  loading?: boolean;
  /** المكافآت القائمة — تُقارَن بالحد الأعلى للاقتراح */
  rewards?: { id: string; title: string; cost_amount: string; program_id?: string }[];
}) {
  if (loading) return <Loading />;
  if (!data) return null;

  if (!data.enough_data) {
    return <NotEnough sample={data.sample} needed={data.needed} what="فاتورة" />;
  }

  // الأعلى من حدّ برنامجه — لا من حدّ عامّ: المكافأة تُقاس بوحدة
  // برنامجها، ومقارنة أختام بسقف نقاط لا تعني شيئًا
  const ceilings = new Map(
    data.programs.map((program) => [program.program_id, Number(program.cost_high)]),
  );
  const over = rewards.filter((reward) => {
    const ceiling = reward.program_id ? ceilings.get(reward.program_id) : undefined;
    return ceiling !== undefined && Number(reward.cost_amount) > ceiling;
  });

  return (
    <section className="card">
      <div className="card-hd">
        <h3>{t("قيمة المكافأة المقترحة")}</h3>
        <Confidence level={data.confidence} />
      </div>

      <div className="card-p">
        <p className="t-sm muted mb-2">
          {t(
            "محسوبة من متوسط فاتورتك {avg} خلال {days} يومًا، على أن يبلغها العميل في {visits} زيارات.",
            {
              avg: fmt.money(data.average_invoice),
              days: fmt.number(data.window_days),
              visits: fmt.number(data.target_visits ?? 0),
            },
          )}
        </p>

        {data.programs.map((program) => (
          <div key={program.program_id} className="li">
            <div className="grow">
              <p className="li-t">{program.program_name}</p>
              <p className="li-s">
                {t("المدى")}{" "}
                <span className="num">{fmt.number(program.cost_low)}</span>
                {" – "}
                <span className="num">{fmt.number(program.cost_high)}</span>{" "}
                {fmt.unit(program.cost_high, program.unit_label)}
              </p>
            </div>
            <div style={{ textAlign: "end" }}>
              <p className="li-v num">
                {fmt.number(program.cost_amount)}{" "}
                {fmt.unit(program.cost_amount, program.unit_label)}
              </p>
              <p className="t-xs muted">
                {t("تساوي")} {fmt.money(program.reward_worth)}
              </p>
            </div>
          </div>
        ))}

        {over.length > 0 && (
          /* المقارنة بما هو قائم فعلًا: الاقتراح وحده يُقرأ ويُنسى،
             وأسماء المكافآت الخارجة عن المدى تُفتح وتُعدَّل */
          <p className="t-sm mt-2 c-orange w-7">
            {over.length === 1
              ? t("«{title}» أعلى من المدى الموصى به.", { title: over[0]!.title })
              : t("{n} مكافآت أعلى من المدى الموصى به: {names}", {
                  n: fmt.number(over.length),
                  names: over.slice(0, 3).map((reward) => reward.title).join(" · "),
                })}
          </p>
        )}

        <p className="t-sm muted mt-2">
          {t("الأقل من المدى لا يُشعِر العميل بشيء، والأعلى منه يأكل هامشك.")}
        </p>
      </div>
    </section>
  );
}

/* ══════════════ وقت الإرسال ══════════════ */

export function SendTimeCard({
  data,
  loading,
}: {
  data?: SendTimeSuggestion;
  loading?: boolean;
}) {
  if (loading) return <Loading />;
  if (!data) return null;

  if (!data.enough_data) {
    return <NotEnough sample={data.sample} needed={data.needed} what="زيارة" />;
  }

  const busiest = Math.max(...data.days.map((day) => day.visits), 1);

  return (
    <section className="card">
      <div className="card-hd">
        <h3>{t("أفضل وقت لإرسال الحملة")}</h3>
        <Confidence level={data.confidence} />
      </div>

      <div className="card-p">
        <div className="card card-p tint-v mb-2">
          <b className="t-md">
            {t("{day} الساعة {hour}", {
              day: t(data.best_day_name ?? ""),
              hour: fmt.number(data.best_hour ?? 0),
            })}
          </b>
          <p className="t-sm muted mt-1">
            {t(
              "ذروة شرائك الساعة {peak}. الإرسال قبلها بساعة يعطي العميل وقتًا ليقرأ ويقرّر.",
              { peak: fmt.number(data.peak_hour ?? 0) },
            )}
          </p>
        </div>

        {/* التوزيع الذي بُنيت عليه التوصية: التاجر يصدّقها حين
            يرى الأعمدة لا حين يُقال له الرقم */}
        {data.days.map((day) => (
          <div key={day.weekday} className="usage">
            <div style={{ width: 62 }}>
              <b className="t-sm">{t(day.name)}</b>
            </div>
            <span className={`bar ${day.weekday === data.best_day ? "" : "g"}`}>
              <i style={{ width: `${(day.visits / busiest) * 100}%` }} />
            </span>
            <div className="t-xs muted w-7 num nowrap">{fmt.number(day.visits)}</div>
          </div>
        ))}
      </div>
    </section>
  );
}
