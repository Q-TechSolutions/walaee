/**
 * إيصال عملية واحدة.
 *
 * هذه الشاشة تُفتح عند الشكّ: «دفعت وما اتسجّلش ليه؟». فتُعرض
 * العملية بكل ما يثبتها — رقم الفاتورة وقيمتها والفرع والكاشير
 * ووقت التأكيد — لأن الربط بهذه الأربعة هو ما يجعل المنح قابلًا
 * للدفاع عنه أمام التاجر وأمام العميل معًا.
 *
 * وحين لا يوجد قيد، يُقال السبب صراحةً. فاتورة تحت الحد الأدنى
 * سبب مشروع، وصمت الشاشة عنه يجعل العميل يظن أن النظام أكل نقاطه
 * — وهي أول خطوة نحو حذف التطبيق.
 *
 * الشكل إيصال بثقبين جانبيين لأن ما حلّ محلّه إيصال ورقي، فيُقرأ
 * بلا شرح.
 */

import { Link, useParams } from "react-router-dom";

import { ErrorBox, Icon, Loading, fmt, t, useApi } from "@walaee/shared";

import { queries } from "../lib/queries";

export function Receipt() {
  const { id = "" } = useParams();
  const receipt = useApi((signal) => queries.receipt(id, signal), [id]);

  if (receipt.loading) return <Loading />;
  if (receipt.error != null)
    return (
      <div className="pad">
        <ErrorBox error={receipt.error} onRetry={receipt.reload} />
      </div>
    );
  if (!receipt.data) return null;

  const data = receipt.data;
  const earned = data.entries.filter((entry) => Number(entry.delta) > 0);

  return (
    <>
      <header className="topbar">
        <Link to="/activity" className="iconbtn" aria-label={t("رجوع إلى سجل النشاط")}>
          <Icon name="chevronRight" size={19} />
        </Link>
        <h2>{t("تفاصيل العملية")}</h2>
      </header>

      <div className="pad section">
        <div className="center">
          <span
            className={`ibox ${data.entries.length > 0 ? "g" : "a"}`}
            style={{ width: 58, height: 58, borderRadius: 19, margin: "0 auto 10px" }}
            aria-hidden="true"
          >
            <Icon name={data.entries.length > 0 ? "checkCircle" : "info"} size={28} />
          </span>
          <p className="t-lg w-8">{t(data.status_label)}</p>
          <p className="t-sm muted">
            {data.brand_name} · {data.branch_name}
          </p>
        </div>

        <div className="rcpt">
          <div className="center">
            <p className="t-2xl w-8 num">{fmt.money(data.invoice_amount)}</p>
            <p className="t-xs muted">{t("قيمة الفاتورة")}</p>
          </div>

          <div className="dash" />

          <div className="rl">
            <span className="muted">{t("التاريخ")}</span>
            <b>{fmt.dateTime(data.confirmed_at ?? data.created_at)}</b>
          </div>
          <div className="rl">
            <span className="muted">{t("رقم الفاتورة")}</span>
            {/* المعرّفات لاتينية: الكاشير يطابقها بورقة مطبوعة */}
            <b className="num" style={{ direction: "ltr" }}>
              {data.invoice_no}
            </b>
          </div>
          {data.cashier_name && (
            <div className="rl">
              <span className="muted">{t("الكاشير")}</span>
              <b>{data.cashier_name}</b>
            </div>
          )}

          {earned.length > 0 && <div className="dash" />}

          {data.entries.map((entry) => (
            <div key={entry.id} className="rl">
              <span className="muted">{t(entry.reason_label)}</span>
              <b className={Number(entry.delta) > 0 ? "c-green" : "c-orange"}>
                {Number(entry.delta) > 0 ? "+" : ""}
                <span className="num">{fmt.number(entry.delta)}</span>{" "}
                {fmt.unit(entry.delta, entry.unit_label)}
              </b>
            </div>
          ))}

          {data.entries.length > 0 && (
            <div className="rl">
              <span className="muted">{t("رصيدك بعدها")}</span>
              <b>
                <span className="num">{fmt.number(data.entries[0]!.balance_after)}</span>{" "}
                {fmt.unit(data.entries[0]!.balance_after, data.entries[0]!.unit_label)}
              </b>
            </div>
          )}
        </div>

        {data.nothing_earned_reason && (
          <div className="card card-p tint-a row-t">
            <span className="ibox a" aria-hidden="true">
              <Icon name="info" size={20} />
            </span>
            <div className="grow">
              <p className="w-7 t-md">{t("لم يُسجَّل رصيد على هذه العملية")}</p>
              <p className="t-sm muted">{data.nothing_earned_reason}</p>
            </div>
          </div>
        )}

        <div className="card card-p tint-g row-t">
          <span className="ibox g" aria-hidden="true">
            <Icon name="shield" size={20} />
          </span>
          <div className="grow">
            <p className="w-7 t-md">{t("عملية موثّقة")}</p>
            <p className="t-sm muted">
              {t("مربوطة برقم الفاتورة وقيمتها والفرع، ومسجّلة في سجل لا يُعدَّل.")}
            </p>
          </div>
        </div>

        <Link to={`/cards/${data.brand_id}`} className="link center">
          {t("افتح بطاقة")} {data.brand_name}
        </Link>
      </div>
    </>
  );
}
