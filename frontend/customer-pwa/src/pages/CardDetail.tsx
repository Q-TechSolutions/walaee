/**
 * تفاصيل بطاقة واحدة.
 *
 * التخطيط مطابق للعرض المعتمد: بطاقة العلامة، ثم التقدّم، ثم
 * أرقام العلاقة، ثم تنبيه الصلاحية، ثم المكافآت، ثم النشاط.
 *
 * التقدّم يُرسَم بشكلين حسب نموذج البرنامج:
 * • **الأختام** شبكة خانات — العميل يعدّ ما جمعه بنظرة، وهو ما
 *   يفعله مع الكرت الورقي الذي حلّت محلّه البطاقة.
 * • **النقاط** حلقة — عدّ ثمانمئة خانة سخيف، والحلقة تقول القرب
 *   من الهدف وهو ما يهمّ هنا، والرصيد في وسطها.
 * استخدام شكل واحد للاثنين يجعل أحدهما خاطئًا دائمًا.
 *
 * المكافأة تعرض «ينقصك ٤٠ نقطة» لا «غير متاح»: الفرق بين إحباط
 * وهدف. هذا هو ما يجعل العميل يعود.
 */

import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import {
  Badge,
  Button,
  Empty,
  ErrorBox,
  Icon,
  Loading,
  Modal,
  Ring,
  fmt,
  t,
  useAction,
  useApi,
} from "@walaee/shared";

import { actions, queries } from "../lib/queries";
import type { BalanceRow, CardReward } from "../lib/queries";

/** فوق هذا العدد تصير شبكة الأختام جدارًا لا يُعدّ. */
const MAX_STAMPS = 20;

export function CardDetail() {
  const { brandId = "" } = useParams();
  const card = useApi((signal) => queries.card(brandId, signal), [brandId]);
  const [issued, setIssued] = useState<{ code: string; title: string } | null>(
    null,
  );

  const redeem = useAction(actions.redeem);

  if (card.loading) return <Loading />;
  if (card.error != null)
    return (
      <div className="pad">
        <ErrorBox error={card.error} onRetry={card.reload} />
      </div>
    );
  if (!card.data) return null;

  const data = card.data;
  const target = data.next_reward;
  const balance =
    data.balances.find((b) => b.next_reward?.id === target?.id) ??
    data.balances[0];
  const available = Number(balance?.amount ?? 0);

  async function onRedeem(reward: CardReward) {
    const result = await redeem.run(reward.id);
    if (result) {
      setIssued({ code: result.code, title: reward.title });
      card.reload();
    }
  }

  return (
    <>
      <header className="topbar">
        <Link to="/" className="iconbtn" aria-label={t("رجوع إلى بطاقاتي")}>
          <Icon name="chevronRight" size={19} />
        </Link>
        <h2>{data.brand_name}</h2>
      </header>

      <div className="pad section">
        {/* بطاقة العلامة — نفس شكلها في المحفظة فيعرف العميل أنه
            فتح نفس البطاقة لا شاشة أخرى */}
        <div
          className="lcard"
          style={{ "--brand": data.primary_color } as React.CSSProperties}
        >
          <div className="lc-top">
            <span className="lc-logo" aria-hidden="true">
              {data.brand_name.trim().charAt(0)}
            </span>
            <div className="grow">
              <p className="lc-name">{data.brand_name}</p>
              <p className="lc-cat">
                {data.category && `${t(data.category)} · `}
                {t("عضو منذ")} {fmt.date(data.joined_at)}
              </p>
            </div>
          </div>

          <div className="lc-mid">
            <div>
              <p className="lc-val num">{fmt.number(available)}</p>
              <p className="lc-unit">
              {fmt.unit(available, balance?.unit_label ?? "نقطة")}
            </p>
            </div>
            {target && <span className="lc-rew">{target.title}</span>}
          </div>

          {target && (
            <div className="lc-bar">
              <i style={{ width: `${Math.round(target.progress * 100)}%` }} />
            </div>
          )}
        </div>

        {balance && target && <Progress balance={balance} target={target} />}

        <Relationship data={data} />

        {balance?.expires_at && (
          <div className="card card-p tint-a row-t">
            <span className="ibox a" aria-hidden="true">
              <Icon name="clock" size={20} />
            </span>
            <div className="grow">
              <p className="w-7 t-md">
                {t("رصيدك صالح حتى")} {fmt.date(balance.expires_at)}
              </p>
              <p className="t-sm muted">
                {t("هننبّهك قبلها. الرصيد ده خاص بـ")}<b>{data.brand_name}</b> {t("وحده.")}
              </p>
            </div>
          </div>
        )}

        {redeem.error != null && <ErrorBox error={redeem.error} />}

        <div className="sec-t">
          <h3>{t("مكافآت هذا المتجر")}</h3>
        </div>

        {data.rewards.length === 0 ? (
          <Empty
            icon="gift"
            title={t("لا توجد مكافآت بعد")}
            hint={t("هذا المتجر لم يضف مكافآت حتى الآن.")}
          />
        ) : (
          <div className="stack gap">
            {data.rewards.map((reward) => {
              const cost = Number(reward.cost_amount);
              const short = cost - available;
              const ready = short <= 0 && reward.in_stock;

              return (
                <div key={reward.id} className={`rw ${ready ? "ready" : ""}`}>
                  <span
                    className={`ibox ${ready ? "g" : "v"}`}
                    aria-hidden="true"
                  >
                    <Icon name="gift" size={20} />
                  </span>

                  <div className="grow">
                    <p className="rw-t">{reward.title}</p>
                    <p className="rw-s">
                      <span className="num">{fmt.number(cost)}</span>{" "}
                      {fmt.unit(cost, reward.unit_label)}
                      {!ready && short > 0 && (
                        <>
                          {t(" · باقي ")}
                          <span className="num">{fmt.number(short)}</span>
                        </>
                      )}
                    </p>
                  </div>

                  {!reward.in_stock ? (
                    <Badge tone="muted">{t("نفدت")}</Badge>
                  ) : ready ? (
                    <Button
                      size="md"
                      loading={redeem.loading}
                      onClick={() => onRedeem(reward)}
                    >
                      {t("استبدال")}
                    </Button>
                  ) : (
                    <Badge tone="violet">{t("قريبًا")}</Badge>
                  )}
                </div>
              );
            })}
          </div>
        )}

        <div className="sec-t">
          <h3>{t("آخر النشاط")}</h3>
        </div>

        {data.activity.length === 0 ? (
          <Empty icon="clock" title={t("لا يوجد نشاط بعد")} />
        ) : (
          <div className="card card-p">
            {data.activity.map((line) => {
              const delta = Number(line.delta);
              return (
                <div key={line.id} className="li">
                  <span
                    className={`ibox ${delta > 0 ? "g" : "o"}`}
                    aria-hidden="true"
                  >
                    <Icon name={delta > 0 ? "plus" : "gift"} size={18} />
                  </span>
                  <div className="grow">
                    <p className="li-t">{t(line.reason_label)}</p>
                    <p className="li-s">
                      {line.program} · {fmt.relativeTime(line.created_at)}
                    </p>
                  </div>
                  <span
                    className={`li-v num ${delta > 0 ? "c-green" : "c-orange"}`}
                  >
                    {delta > 0 ? "+" : ""}
                    {fmt.number(line.delta)}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </div>

      <Modal
        open={issued !== null}
        title={t("كود الاستبدال")}
        onClose={() => setIssued(null)}
      >
        <div className="center">
          <p className="muted t-sm">{t("اعرض هذا الكود على الكاشير")}</p>
          <p className="code-card-code num">{issued?.code}</p>
          <p className="w-7">{issued?.title}</p>
          <p className="t-sm faint mt-2">
            {t("صالح لمدة ١٥ دقيقة ومرة واحدة فقط. تجده أيضًا في صفحة المكافآت.")}
          </p>
        </div>
      </Modal>
    </>
  );
}

/* ══════════════ التقدّم ══════════════ */

function Progress({
  balance,
  target,
}: {
  balance: BalanceRow;
  target: NonNullable<BalanceRow["next_reward"]>;
}) {
  const amount = Number(balance.amount);
  const cost = Number(target.cost_amount);
  const remaining = Math.max(cost - amount, 0);

  // الأختام شبكة، وما عداها حلقة — إلا حين يكون عدد الأختام
  // كبيرًا بما يجعل الشبكة جدارًا لا يُعدّ بنظرة
  const asGrid =
    balance.program_type === "stamps" &&
    Number.isInteger(cost) &&
    cost > 0 &&
    cost <= MAX_STAMPS;

  return (
    <section className="card card-p">
      <div className="row between mb-2">
        <h3 className="t-md w-8">{t("تقدّمك")}</h3>
        <span className={`badge ${remaining === 0 ? "bg-g" : "bg-n"}`}>
          {remaining === 0 ? (
            t("جاهزة للاستبدال")
          ) : (
            <>
              <span className="num">{fmt.number(remaining)}</span> {t("متبقية")}
            </>
          )}
        </span>
      </div>

      {asGrid ? (
        <div className="stamps">
          {Array.from({ length: cost }, (_, index) => {
            const filled = index < amount;
            const next = index === Math.floor(amount);
            return (
              <span
                key={index}
                className={`stamp ${filled ? "fill" : next ? "next" : ""}`}
              >
                <Icon name={filled ? "check" : "star"} size={21} />
              </span>
            );
          })}
        </div>
      ) : (
        <Ring value={target.progress} color="var(--violet-700)">
          <div>
            <p className="t-2xl w-8 num">{fmt.number(amount)}</p>
            <p className="t-xs muted w-7">
              {t("من {n} {unit}", {
                n: fmt.number(cost),
                unit: fmt.unit(cost, balance.unit_label),
              })}
            </p>
          </div>
        </Ring>
      )}

      <p className="t-sm muted mt-2">
        {asGrid
          ? t("كل زيارة = ختم.")
          : t("كل {unit} تقرّبك من المكافأة.", { unit: balance.unit_label })}{" "}
        {t("عند الاكتمال تحصل على")} <b>{target.title}</b>.
      </p>
    </section>
  );
}

/* ══════════════ أرقام العلاقة ══════════════ */

/**
 * ثلاثة أرقام تصف علاقة العميل بالمتجر.
 *
 * لا يوجد هنا «عدد العمليات»: الخادم يُرجع آخر عشرين قيدًا فقط،
 * وعدّها يعطي «٢٠» لمن عنده مئتان — رقم خاطئ يبدو صحيحًا تمامًا.
 * ما يُعرض محسوب من حقول كاملة لا من قائمة مقصوصة.
 */
function Relationship({
  data,
}: {
  data: { total_spend: string; total_visits: number; joined_at: string };
}) {
  return (
    <div className="grid g3 facts">
      <div className="card card-p center fact">
        <p className="t-xl w-8 num">{fmt.number(data.total_visits)}</p>
        <p className="t-sm muted">{t("زيارة")}</p>
      </div>
      <div className="card card-p center fact">
        {/* الرقم وحده والعملة في التسمية تحته: «٢٬٤٠٠٫٠٠ ج.م.‏»
            في خانة عرضها الثلث يلتفّ على سطرين فيرتفع مربعها وحده
            ويبدو الصف مكسورًا */}
        <p className="t-xl w-8 num">{fmt.number(data.total_spend)}</p>
        <p className="t-sm muted">{t("جنيهًا أنفقتها")}</p>
      </div>
      <div className="card card-p center fact">
        {/* السنة وحدها: «٢٥ سبتمبر ٢٠٢٦» ثلاث كلمات في ثلث العرض */}
        <p className="t-xl w-8 num">{fmt.year(data.joined_at)}</p>
        <p className="t-sm muted">{t("عضو منذ")}</p>
      </div>
    </div>
  );
}
