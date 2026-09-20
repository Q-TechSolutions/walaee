/** المكافآت المتاحة وأكواد الاستبدال الفعّالة. */

import { Empty, ErrorBox, Badge, Loading, fmt, useApi } from "@walaee/shared";

import { queries } from "../lib/queries";

export function Rewards() {
  const rewards = useApi((signal) => queries.rewards(signal), []);
  const redemptions = useApi((signal) => queries.redemptions(signal), []);

  const pending = redemptions.data?.filter((r) => r.status === "pending") ?? [];

  return (
    <div className="page">
      <h1 className="mb">المكافآت</h1>

      {pending.length > 0 && (
        <section className="section">
          <h2>أكواد بانتظار الصرف</h2>
          <div className="stack gap">
            {pending.map((item) => (
              <div key={item.id} className="code-card">
                <div className="grow">
                  <p className="w-7">{item.reward_title}</p>
                  <p className="t-sm muted">{item.brand_name}</p>
                </div>
                <div className="code-card-code">
                  <span className="num">{item.code}</span>
                  <span className="t-xs faint">
                    ينتهي {fmt.relativeTime(item.expires_at)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      <section className="section">
        <h2>متاح لك</h2>

        {rewards.loading && <Loading />}
        {rewards.error != null && (
          <ErrorBox error={rewards.error} onRetry={rewards.reload} />
        )}

        {rewards.data?.length === 0 && (
          <Empty
            icon="🎁"
            title="لا توجد مكافآت"
            hint="انضم لمتجر وابدأ تجميع نقاطك."
          />
        )}

        <div className="stack gap">
          {rewards.data?.map((reward) => (
            <div key={reward.id} className="reward-row">
              <div className="grow">
                <p className="w-7">{reward.title}</p>
                <p className="t-sm muted">{reward.brand_name}</p>
              </div>
              <div className="stack" style={{ alignItems: "flex-end", gap: 4 }}>
                <span className="num w-7">{fmt.number(reward.cost_amount)}</span>
                {reward.stock !== null && reward.stock <= 5 && (
                  <Badge tone="orange">
                    باقي {fmt.number(reward.stock)}
                  </Badge>
                )}
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
