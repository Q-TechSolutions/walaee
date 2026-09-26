/**
 * المكافآت المتاحة وأكواد الاستبدال الفعّالة.
 *
 * الأكواد الفعّالة أولًا ثم المتاح: من يفتح هذه الشاشة وهو واقف
 * عند الكاشير يريد الكود الآن، والبحث عنه أسفل قائمة طويلة يعني
 * طابورًا ينتظره.
 *
 * الكود يُرسَم كإيصال بثقبين جانبيين — نفس شكل قسيمة الخصم
 * الورقية التي حلّ محلّه، فيفهم الكاشير ما يُعرض عليه بلا شرح.
 *
 * المتاح مقسوم قسمين: **جاهزة الآن** يقابلها زر استبدال، و**قريبة
 * منك** يقابلها ما ينقصها. قائمة واحدة بلا هذا الفصل كانت تعرض
 * عشرين صفًّا متطابقًا لا يفرّق فيها العميل بين ما يستطيع صرفه
 * الآن وما يحتاج ألف نقطة أخرى — فيقرأ الشاشة كلها كوعد مؤجّل.
 */

import { useState } from "react";
import { Link } from "react-router-dom";

import {
  Badge,
  Button,
  Empty,
  ErrorBox,
  Icon,
  Loading,
  Modal,
  fmt,
  t,
  useAction,
  useApi,
} from "@walaee/shared";

import { actions, queries } from "../lib/queries";
import type { AvailableReward } from "../lib/queries";

export function Rewards() {
  const rewards = useApi((signal) => queries.rewards(signal), []);
  const redemptions = useApi((signal) => queries.redemptions(signal), []);
  const [issued, setIssued] = useState<{ code: string; title: string } | null>(
    null,
  );

  const redeem = useAction(actions.redeem);

  const pending = redemptions.data?.filter((r) => r.status === "pending") ?? [];
  const ready = rewards.data?.filter((r) => r.ready) ?? [];
  const soon = rewards.data?.filter((r) => !r.ready) ?? [];

  async function onRedeem(reward: AvailableReward) {
    const result = await redeem.run(reward.id);
    if (result) {
      setIssued({ code: result.code, title: reward.title });
      rewards.reload();
      redemptions.reload();
    }
  }

  return (
    <>
      <header className="mhead">
        <div className="grow">
          <h1>{t("المكافآت")}</h1>
          <p className="sub">
            {pending.length > 0
              ? t("عندك كود جاهز — اعرضه على الكاشير")
              : ready.length > 0
                ? t("{n} جاهزة الآن و{m} قريبة", {
                    n: fmt.number(ready.length),
                    m: fmt.number(soon.length),
                  })
                : t("اللي تقدر تستبدله دلوقتي وقريبًا")}
          </p>
        </div>
      </header>

      <div className="pad section">
        {pending.length > 0 && (
          <>
            <div className="sec-t">
              <h3>{t("أكواد بانتظار الصرف")}</h3>
            </div>

            <div className="stack gap">
              {pending.map((item) => (
                <div key={item.id} className="rcpt">
                  <div className="row between">
                    <div className="grow">
                      <p className="w-8 t-md">{item.reward_title}</p>
                      <p className="t-sm muted">{item.brand_name}</p>
                    </div>
                    <span className="ibox g" aria-hidden="true">
                      <Icon name="gift" size={20} />
                    </span>
                  </div>

                  <div className="dash" />

                  <div className="row between">
                    <span className="code-card-code num c-violet">
                      {item.code}
                    </span>
                    <span className="t-sm muted">
                      {t("ينتهي")} {fmt.relativeTime(item.expires_at)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}

        {rewards.loading && <Loading />}
        {rewards.error != null && (
          <ErrorBox error={rewards.error} onRetry={rewards.reload} />
        )}
        {redeem.error != null && <ErrorBox error={redeem.error} />}

        {rewards.data?.length === 0 && (
          <Empty
            icon="gift"
            title={t("لا توجد مكافآت")}
            hint={t("انضم لمتجر وابدأ تجميع نقاطك.")}
          />
        )}

        {ready.length > 0 && (
          <>
            <div className="sec-t">
              <h3>{t("جاهزة للاستبدال")}</h3>
              <span className="badge bg-g num">{fmt.number(ready.length)}</span>
            </div>

            <div className="stack gap">
              {ready.map((reward) => (
                <RewardRow
                  key={reward.id}
                  reward={reward}
                  busy={redeem.loading}
                  onRedeem={() => onRedeem(reward)}
                />
              ))}
            </div>
          </>
        )}

        {soon.length > 0 && (
          <>
            <div className="sec-t">
              <h3>{t("قريبة منك")}</h3>
            </div>

            <div className="stack gap">
              {soon.map((reward) => (
                <RewardRow key={reward.id} reward={reward} />
              ))}
            </div>
          </>
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

/* ══════════════ صف مكافأة ══════════════ */

/**
 * الصف يحمل لون علامته لا لونًا موحّدًا.
 *
 * قائمة بعشرين أيقونة بنفسجية متطابقة تُخفي أن المكافآت من متاجر
 * مختلفة. حرف العلامة بلونها يعيد الربط بين الصف والبطاقة التي
 * رآها العميل في محفظته.
 */
function RewardRow({
  reward,
  busy,
  onRedeem,
}: {
  reward: AvailableReward;
  busy?: boolean;
  onRedeem?: () => void;
}) {
  const remaining = Number(reward.remaining);

  return (
    <div className={`rw ${reward.ready ? "ready" : ""}`}>
      <Link
        to={`/cards/${reward.brand_id}`}
        className="av brandav"
        style={{ "--brand": reward.primary_color } as React.CSSProperties}
        aria-label={reward.brand_name}
      >
        {reward.brand_name.trim().charAt(0)}
      </Link>

      <div className="grow">
        <p className="rw-t">{reward.title}</p>
        {/* التكلفة أولًا ثم اسم المتجر: الفاصل «·» لا يقع بجوار رقم
            أبدًا بهذا الترتيب. ملتصقًا برقم عربي-هندي يُقرأ صفرًا —
            «٥٠ ج» تصير «٥٠٠ ج»، وهو ثمن يصدّقه العميل */}
        <p className="rw-s">
          <span className="num">{fmt.number(reward.cost_amount)}</span>{" "}
          {fmt.unit(reward.cost_amount, reward.unit_label)} · {reward.brand_name}
          {!reward.ready && remaining > 0 && (
            <>
              {" · "}
              {t("باقي")} <span className="num">{fmt.number(remaining)}</span>
            </>
          )}
        </p>
      </div>

      {!reward.in_stock ? (
        <Badge tone="muted">{t("نفدت")}</Badge>
      ) : reward.ready && onRedeem ? (
        <Button size="md" loading={busy} onClick={onRedeem}>
          {t("استبدال")}
        </Button>
      ) : (
        <Badge tone="muted">{t("قريبًا")}</Badge>
      )}
    </div>
  );
}
