/**
 * ما وصل العميل من المنصة.
 *
 * الصندوق مطابق لهاتفه: يعرض ما أُرسل فعلًا، لا ما كان يمكن أن
 * يُرسل. حملة فشل إرسالها أو تُخطّيت موجودة في القاعدة كصف كامل،
 * وعرضها هنا يجعل العميل يسأل عن عرض لم يُعرض عليه — أو يطالب
 * بخصم لم يُمنح له عند الكاشير.
 *
 * ومعها تنبيه الرصيد المقارب للانتهاء، وهو الإشعار الوحيد الذي
 * تولّده المنصة لا التاجر. يُبنى عند القراءة لا يُخزَّن، فلا يبقى
 * يقول «ينتهي ٢٠٠ نقطة» بعد أن صُرفت.
 */

import { Link } from "react-router-dom";

import { Empty, ErrorBox, Icon, Loading, fmt, t, useApi } from "@walaee/shared";

import { queries } from "../lib/queries";
import type { Notification } from "../lib/queries";

export function Notifications() {
  const inbox = useApi((signal) => queries.notifications(signal), []);

  const rows = inbox.data?.results ?? [];
  const unread = inbox.data?.unread ?? 0;

  return (
    <>
      <header className="topbar">
        <Link to="/" className="iconbtn" aria-label={t("رجوع إلى بطاقاتي")}>
          <Icon name="chevronRight" size={19} />
        </Link>
        <h2>{t("الإشعارات")}</h2>
        {unread > 0 && (
          <span className="badge bg-o">
            <span className="num">{fmt.number(unread)}</span> {t("جديدة")}
          </span>
        )}
      </header>

      <div className="pad section">
        {inbox.loading && <Loading />}
        {inbox.error != null && <ErrorBox error={inbox.error} onRetry={inbox.reload} />}

        {inbox.data && rows.length === 0 && (
          <Empty
            icon="bell"
            title={t("لا إشعارات بعد")}
            hint={t("هنبّهك أول ما تجهز مكافأة أو يقرب رصيدك على الانتهاء.")}
          />
        )}

        <div className="stack gap">
          {rows.map((row) => (
            <NotificationRow key={row.id} row={row} />
          ))}
        </div>
      </div>
    </>
  );
}

function NotificationRow({ row }: { row: Notification }) {
  const expiry = row.kind === "expiry";

  return (
    <article className={`ntf ${row.read ? "" : "unread"}`}>
      <span className={`ibox ${expiry ? "a" : "v"}`} aria-hidden="true">
        <Icon name={expiry ? "clock" : "message"} size={18} />
      </span>

      <div className="grow">
        <p className="nb">{expiry ? t(row.title) : row.title}</p>
        <p className="ns">{expiry ? row.body : row.body}</p>
        <p className="t-xs faint mt-1">
          {row.brand_name} · {t(row.channel_label)}
        </p>
      </div>

      <span className="nt">{fmt.relativeTime(row.created_at)}</span>
    </article>
  );
}
