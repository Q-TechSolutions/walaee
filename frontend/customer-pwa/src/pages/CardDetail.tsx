/**
 * تفاصيل بطاقة واحدة: الرصيد والمكافآت والنشاط.
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
  Loading,
  Modal,
  fmt,
  useAction,
  useApi,
} from "@walaee/shared";

import { actions, queries } from "../lib/queries";
import type { CardReward } from "../lib/queries";

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
      <div className="page">
        <ErrorBox error={card.error} onRetry={card.reload} />
      </div>
    );
  if (!card.data) return null;

  const data = card.data;
  const balance = data.balances[0];
  const available = Number(balance?.amount ?? 0);

  async function onRedeem(reward: CardReward) {
    const result = await redeem.run(reward.id);
    if (result) {
      setIssued({ code: result.code, title: reward.title });
      card.reload();
    }
  }

  return (
    <div className="page">
      <Link to="/" className="back-link">
        ‹ بطاقاتي
      </Link>

      <header
        className="detail-hero"
        style={{ "--brand": data.primary_color } as React.CSSProperties}
      >
        <p className="t-sm">{data.category || "متجر"}</p>
        <h1>{data.brand_name}</h1>

        <div className="detail-balances">
          {data.balances.map((row) => (
            <div key={row.program_id} className="detail-balance">
              <span className="num">{fmt.number(row.amount)}</span>
              <span className="t-sm">{row.unit_label}</span>
              <span className="t-xs detail-program">{row.program_name}</span>
            </div>
          ))}
          {data.balances.length === 0 && (
            <div className="detail-balance">
              <span className="num">0</span>
              <span className="t-sm">نقطة</span>
            </div>
          )}
        </div>

        <p className="t-xs detail-meta">
          عضو منذ {fmt.date(data.joined_at)} · أنفقت{" "}
          <span className="num">{fmt.money(data.total_spend)}</span>
        </p>
      </header>

      {redeem.error != null && <ErrorBox error={redeem.error} />}

      <section className="section">
        <h2>المكافآت</h2>

        {data.rewards.length === 0 ? (
          <Empty
            icon="🎁"
            title="لا توجد مكافآت بعد"
            hint="هذا المتجر لم يضف مكافآت حتى الآن."
          />
        ) : (
          <div className="stack gap">
            {data.rewards.map((reward) => {
              const cost = Number(reward.cost_amount);
              const short = cost - available;
              const ready = short <= 0 && reward.in_stock;

              return (
                <div key={reward.id} className="reward-row">
                  <div className="grow">
                    <p className="w-7">{reward.title}</p>
                    {reward.description && (
                      <p className="t-sm muted">{reward.description}</p>
                    )}
                    <p className="t-sm">
                      <span className="num w-7">{fmt.number(cost)}</span>{" "}
                      {reward.unit_label}
                      {!reward.in_stock && (
                        <>
                          {" · "}
                          <Badge tone="muted">نفدت الكمية</Badge>
                        </>
                      )}
                    </p>
                  </div>

                  {ready ? (
                    <Button
                      loading={redeem.loading}
                      onClick={() => onRedeem(reward)}
                    >
                      استبدل
                    </Button>
                  ) : (
                    <div className="reward-progress">
                      <div className="reward-bar">
                        <span
                          style={{
                            width: `${Math.min(100, (available / cost) * 100)}%`,
                          }}
                        />
                      </div>
                      <span className="t-xs faint">
                        ينقصك <span className="num">{fmt.number(short)}</span>
                      </span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </section>

      <section className="section">
        <h2>آخر النشاط</h2>

        {data.activity.length === 0 ? (
          <Empty icon="🕗" title="لا يوجد نشاط بعد" />
        ) : (
          <ul className="activity">
            {data.activity.map((line) => (
              <li key={line.id}>
                <span
                  className={`activity-delta ${
                    Number(line.delta) > 0 ? "plus" : "minus"
                  } num`}
                >
                  {Number(line.delta) > 0 ? "+" : ""}
                  {fmt.number(line.delta)}
                </span>
                <span className="grow">
                  <span className="w-7">{line.reason_label}</span>
                  <span className="t-xs faint"> · {line.program}</span>
                </span>
                <span className="t-xs faint">
                  {fmt.relativeTime(line.created_at)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <Modal
        open={issued !== null}
        title="كود الاستبدال"
        onClose={() => setIssued(null)}
      >
        <div className="redeem-result">
          <p className="muted">اعرض هذا الكود على الكاشير</p>
          <p className="redeem-code num">{issued?.code}</p>
          <p className="w-7">{issued?.title}</p>
          <p className="t-sm faint">
            صالح لمدة ١٥ دقيقة ومرة واحدة فقط. تجده أيضًا في صفحة المكافآت.
          </p>
        </div>
      </Modal>
    </div>
  );
}
