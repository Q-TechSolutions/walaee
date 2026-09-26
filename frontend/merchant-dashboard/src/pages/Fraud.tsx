/**
 * مراجعة إشارات الشذوذ.
 *
 * النظام يرفع راية ولا يحكم. الشاشة تعرض السياق كاملًا — الفاتورة
 * والكاشير والفرع — لأن القرار بشري ويحتاج ما يكفي لاتخاذه.
 *
 * «رفض» يعكس القيود بقيود مضادة لا يحذفها: التاريخ يبقى كاملًا.
 */

import { useState } from "react";

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
import type { FraudSignal } from "@walaee/shared";

const SEVERITY: Record<FraudSignal["severity"], { tone: "red" | "amber" | "muted"; label: string }> = {
  high: { tone: "red", label: "خطورة عالية" },
  medium: { tone: "amber", label: "متوسطة" },
  low: { tone: "muted", label: "منخفضة" },
};

import { actions, queries } from "../lib/queries";

export function Fraud() {
  const [status, setStatus] = useState("open");
  const signals = useApi((signal) => queries.fraudSignals(status, signal), [status]);
  const [reviewing, setReviewing] = useState<FraudSignal | null>(null);

  return (
    <div className="stack gap-lg">
      <FraudIntro />

      <div className="row between wrap-f">
        <div className="tabs" role="group" aria-label={t("الحالة")}>
          {[
            { key: "open", label: t("بانتظار المراجعة") },
            { key: "all", label: t("الكل") },
          ].map((option) => (
            <button
              key={option.key}
              type="button"
              className={status === option.key ? "on" : ""}
              onClick={() => setStatus(option.key)}
            >
              {t(option.label)}
            </button>
          ))}
        </div>
      </div>

      {signals.loading && <Loading />}
      {signals.error != null && (
        <ErrorBox error={signals.error} onRetry={signals.reload} />
      )}

      {signals.data?.length === 0 && (
        <Empty
          icon="shield"
          title={t("لا شيء يحتاج مراجعتك")}
          hint={t("كل العمليات ضمن الأنماط المعتادة لمتجرك.")}
        />
      )}

      <div className="stack gap">
        {signals.data?.map((signal) => (
          <button
            key={signal.id}
            type="button"
            className="signal-row"
            onClick={() => setReviewing(signal)}
          >
            <Badge tone={SEVERITY[signal.severity].tone}>
              {t(SEVERITY[signal.severity].label)}
            </Badge>
            <div className="grow" style={{ textAlign: "start" }}>
              <p className="w-7">{t(signal.rule_label)}</p>
              <p className="t-sm muted">
                {t("فاتورة")} <span className="num">{signal.invoice_no}</span> ·{" "}
                <span className="num">{fmt.money(signal.invoice_amount)}</span> ·{" "}
                {signal.branch_name}
              </p>
              <p className="t-xs faint">
                {signal.staff_name ?? "—"} · {fmt.relativeTime(signal.created_at)}
              </p>
            </div>
            {signal.status !== "open" && (
              <Badge tone={signal.status === "accepted" ? "green" : "red"}>
                {signal.status === "accepted" ? t("قُبلت") : t("عُكست")}
              </Badge>
            )}
          </button>
        ))}
      </div>

      <FraudControls />

      <ReviewModal
        signal={reviewing}
        onClose={() => setReviewing(null)}
        onDone={() => {
          setReviewing(null);
          signals.reload();
        }}
      />
    </div>
  );
}

function ReviewModal({
  signal,
  onClose,
  onDone,
}: {
  signal: FraudSignal | null;
  onClose: () => void;
  onDone: () => void;
}) {
  const resolve = useAction(actions.resolveSignal);

  if (!signal) return null;

  const closed = signal.status !== "open";

  return (
    <Modal open title={t(signal.rule_label)} onClose={onClose}>
      <div className="stack gap">
        <dl className="detail-list">
          <div>
            <dt>{t("الفاتورة")}</dt>
            <dd className="num">{signal.invoice_no}</dd>
          </div>
          <div>
            <dt>{t("المبلغ")}</dt>
            <dd className="num">{fmt.money(signal.invoice_amount)}</dd>
          </div>
          <div>
            <dt>{t("الفرع")}</dt>
            <dd>{signal.branch_name}</dd>
          </div>
          <div>
            <dt>{t("الكاشير")}</dt>
            <dd>{signal.staff_name ?? "—"}</dd>
          </div>
          <div>
            <dt>{t("العميل")}</dt>
            <dd className="num">{fmt.phone(signal.customer_phone)}</dd>
          </div>
          <div>
            <dt>{t("الوقت")}</dt>
            <dd>{fmt.dateTime(signal.created_at)}</dd>
          </div>
        </dl>

        {Object.keys(signal.details).length > 0 && (
          <div className="detail-json">
            {Object.entries(signal.details).map(([key, value]) => (
              <div key={key} className="row between t-sm">
                <span className="muted">{key}</span>
                <span className="num">{String(value)}</span>
              </div>
            ))}
          </div>
        )}

        {resolve.error != null && <ErrorBox error={resolve.error} />}

        {closed ? (
          <p className="t-sm muted">
            {t("روجعت هذه الإشارة في")} {fmt.dateTime(signal.reviewed_at)}.
          </p>
        ) : (
          <>
            <p className="t-sm muted">
              {t("«العملية سليمة» تغلق الإشارة بلا أي تغيير على الرصيد. «مخالفة» تعكس النقاط الممنوحة بقيود مضادة — والقيود الأصلية تبقى في السجل.")}
            </p>

            <div className="row gap">
              <Button
                loading={resolve.loading}
                onClick={async () => {
                  const done = await resolve.run(signal.id, "accept");
                  if (done) onDone();
                }}
              >
                {t("العملية سليمة")}
              </Button>
              <Button
                variant="danger"
                loading={resolve.loading}
                onClick={async () => {
                  const done = await resolve.run(signal.id, "reject");
                  if (done) onDone();
                }}
              >
                {t("مخالفة — اعكس النقاط")}
              </Button>
            </div>
          </>
        )}
      </div>
    </Modal>
  );
}

/**
 * لماذا هذه الشاشة موجودة.
 *
 * أي نظام ولاء بلا ضوابط يُستغَل خلال أسابيع — كاشير يمنح نقاطًا
 * لرقمه أو لأصدقائه. الشرح هنا لا في التوثيق لأن من يفتح هذه
 * الشاشة أول مرة يظن أنها تتّهم موظفيه، وسطران يمنعان ذلك.
 */
function FraudIntro() {
  return (
    <section className="card card-p tint-r">
      <div className="row-t">
        <span className="ibox r" style={{ background: "#fff" }}>
          <Icon name="shield" size={20} />
        </span>
        <div className="grow">
          <b>{t("ضوابط تحمي بياناتك وثقتك")}</b>
          <p className="t-sm muted mt-1">
            {t("النظام يربط كل منح برقم الفاتورة وقيمتها، ويكشف الشذوذ آليًا، ويحتفظ بسجل تدقيق غير قابل للحذف. ما يظهر هنا اقتراح للمراجعة لا اتهامًا — والقرار لك.")}
          </p>
        </div>
      </div>
    </section>
  );
}

/** الضوابط المفعّلة — سياسات النظام لا إعدادات لهذا المتجر. */
const CONTROLS: [string, string][] = [
  ["سقف يومي لكل عميل", "يضبطه كل برنامج في قواعده"],
  ["ربط المنح برقم الفاتورة وقيمتها", "إلزامي — لا منح بلا فاتورة"],
  ["رفض إعادة استخدام نفس الرمز", "الرمز صالح لمرة واحدة وثوانٍ معدودة"],
  ["حساب مستقل لكل كاشير", "شرط نسبة أي نمط إلى شخص بعينه"],
  ["سجل تدقيق غير قابل للحذف", "العكس يُسجَّل قيدًا جديدًا ولا يمحو القديم"],
];

function FraudControls() {
  return (
    <section className="card">
      <div className="card-hd">
        <h3>{t("الضوابط المفعّلة")}</h3>
      </div>
      <div className="card-p">
        {CONTROLS.map(([title, note]) => (
          <div key={title} className="li">
            <span className="ibox g" aria-hidden="true">
              <Icon name="lock" size={18} />
            </span>
            <div className="grow">
              <p className="li-t">{t(title)}</p>
              <p className="li-s">{t(note)}</p>
            </div>
            <Icon name="checkCircle" size={18} className="c-green" />
          </div>
        ))}
      </div>
    </section>
  );
}
