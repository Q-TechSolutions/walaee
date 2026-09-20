/**
 * محفظة البطاقات — الشاشة الأولى.
 *
 * البطاقة تعرض الرصيد بحجم كبير وبلا تفاصيل: العميل يفتح التطبيق
 * وهو واقف عند الصندوق ليجيب سؤالًا واحدًا — «عندي كام؟».
 */

import { Link } from "react-router-dom";

import { Empty, ErrorBox, Loading, Skeleton, fmt, useApi } from "@walaee/shared";

import { queries } from "../lib/queries";
import type { Card } from "../lib/queries";

export function Cards() {
  const cards = useApi((signal) => queries.cards(signal), []);
  const summary = useApi((signal) => queries.summary(signal), []);

  return (
    <div className="page">
      <header className="home-hd">
        <div>
          <p className="t-sm muted">محفظتي</p>
          <h1>بطاقاتي</h1>
        </div>
        {summary.data ? (
          <div className="home-chip">
            <span className="num w-8">{summary.data.cards}</span>
            <span className="t-xs">
              {summary.data.cards === 1 ? "متجر" : "متاجر"}
            </span>
          </div>
        ) : (
          <Skeleton height={44} width={64} />
        )}
      </header>

      {summary.data && summary.data.pending_redemptions > 0 && (
        <Link to="/rewards" className="alert-strip">
          <span aria-hidden="true">🎁</span>
          <span className="grow">
            لديك{" "}
            <span className="num w-8">{summary.data.pending_redemptions}</span>{" "}
            كود استبدال بانتظار الصرف
          </span>
          <span aria-hidden="true">‹</span>
        </Link>
      )}

      {cards.loading && <Loading label="جارٍ تحميل بطاقاتك…" />}

      {cards.error != null && (
        <ErrorBox error={cards.error} onRetry={cards.reload} />
      )}

      {cards.data?.length === 0 && (
        <Empty
          icon="🪪"
          title="لا توجد بطاقات بعد"
          hint="امسح رمز أي متجر مشترك لتبدأ تجميع نقاطك."
          action={
            <Link to="/scan" className="btn btn-primary">
              امسح رمزًا
            </Link>
          }
        />
      )}

      <div className="cards">
        {cards.data?.map((card) => (
          <CardTile key={card.brand_id} card={card} />
        ))}
      </div>
    </div>
  );
}

function CardTile({ card }: { card: Card }) {
  const primary = card.balances[0];

  return (
    <Link
      to={`/cards/${card.brand_id}`}
      className="loyalty-card"
      // لون العلامة يأتي من بياناتها لا من ثابت: البطاقة يجب أن
      // تبدو كالمتجر لا كالتطبيق، وإلا لم يتعرّف عليها العميل بنظرة
      style={{ "--brand": card.primary_color } as React.CSSProperties}
    >
      <div className="loyalty-card-top">
        <span className="loyalty-card-name">{card.brand_name}</span>
        {card.tier && <span className="loyalty-card-tier">{card.tier}</span>}
      </div>

      {primary ? (
        <div className="loyalty-card-balance">
          <span className="num">{fmt.number(primary.amount)}</span>
          <span className="loyalty-card-unit">{primary.unit_label}</span>
        </div>
      ) : (
        <div className="loyalty-card-balance">
          <span className="num">0</span>
          <span className="loyalty-card-unit">نقطة</span>
        </div>
      )}

      <div className="loyalty-card-foot">
        {card.balances.length > 1 && (
          <span className="t-xs">
            +{card.balances.length - 1} برنامج آخر
          </span>
        )}
        <span className="grow" />
        <span className="t-xs">
          {card.last_activity
            ? fmt.relativeTime(card.last_activity)
            : "لم تستخدمها بعد"}
        </span>
      </div>

      {primary?.expires_at && <ExpiryHint at={primary.expires_at} />}
    </Link>
  );
}

/**
 * تنبيه انتهاء الصلاحية.
 *
 * يظهر قبل ٣٠ يومًا فقط: تنبيه دائم يصبح جزءًا من الخلفية ولا
 * يقرؤه أحد حين يهمّ فعلًا.
 */
function ExpiryHint({ at }: { at: string }) {
  const days = Math.ceil((new Date(at).getTime() - Date.now()) / 86_400_000);
  if (days > 30 || days < 0) return null;

  return (
    <div className="loyalty-card-expiry">
      تنتهي خلال <span className="num">{days}</span> يومًا
    </div>
  );
}
