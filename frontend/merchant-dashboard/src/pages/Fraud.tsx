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
  Loading,
  Modal,
  fmt,
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
      <header className="row between wrap">
        <div>
          <h1>مراجعة العمليات</h1>
          <p className="t-sm muted">
            النظام يرفع راية على الأنماط غير المعتادة — والقرار لك
          </p>
        </div>

        <div className="range-switch" role="group" aria-label="الحالة">
          {[
            { key: "open", label: "بانتظار المراجعة" },
            { key: "all", label: "الكل" },
          ].map((option) => (
            <button
              key={option.key}
              type="button"
              className={status === option.key ? "active" : ""}
              onClick={() => setStatus(option.key)}
            >
              {option.label}
            </button>
          ))}
        </div>
      </header>

      {signals.loading && <Loading />}
      {signals.error != null && (
        <ErrorBox error={signals.error} onRetry={signals.reload} />
      )}

      {signals.data?.length === 0 && (
        <Empty
          icon="✓"
          title="لا شيء يحتاج مراجعتك"
          hint="كل العمليات ضمن الأنماط المعتادة لمتجرك."
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
              {SEVERITY[signal.severity].label}
            </Badge>
            <div className="grow" style={{ textAlign: "start" }}>
              <p className="w-7">{signal.rule_label}</p>
              <p className="t-sm muted">
                فاتورة <span className="num">{signal.invoice_no}</span> ·{" "}
                <span className="num">{fmt.money(signal.invoice_amount)}</span> ·{" "}
                {signal.branch_name}
              </p>
              <p className="t-xs faint">
                {signal.staff_name ?? "—"} · {fmt.relativeTime(signal.created_at)}
              </p>
            </div>
            {signal.status !== "open" && (
              <Badge tone={signal.status === "accepted" ? "green" : "red"}>
                {signal.status === "accepted" ? "قُبلت" : "عُكست"}
              </Badge>
            )}
          </button>
        ))}
      </div>

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
    <Modal open title={signal.rule_label} onClose={onClose}>
      <div className="stack gap">
        <dl className="detail-list">
          <div>
            <dt>الفاتورة</dt>
            <dd className="num">{signal.invoice_no}</dd>
          </div>
          <div>
            <dt>المبلغ</dt>
            <dd className="num">{fmt.money(signal.invoice_amount)}</dd>
          </div>
          <div>
            <dt>الفرع</dt>
            <dd>{signal.branch_name}</dd>
          </div>
          <div>
            <dt>الكاشير</dt>
            <dd>{signal.staff_name ?? "—"}</dd>
          </div>
          <div>
            <dt>العميل</dt>
            <dd className="num">{fmt.phone(signal.customer_phone)}</dd>
          </div>
          <div>
            <dt>الوقت</dt>
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
            روجعت هذه الإشارة في {fmt.dateTime(signal.reviewed_at)}.
          </p>
        ) : (
          <>
            <p className="t-sm muted">
              «العملية سليمة» تغلق الإشارة بلا أي تغيير على الرصيد.
              «مخالفة» تعكس النقاط الممنوحة بقيود مضادة — والقيود الأصلية
              تبقى في السجل.
            </p>

            <div className="row gap">
              <Button
                loading={resolve.loading}
                onClick={async () => {
                  const done = await resolve.run(signal.id, "accept");
                  if (done) onDone();
                }}
              >
                العملية سليمة
              </Button>
              <Button
                variant="danger"
                loading={resolve.loading}
                onClick={async () => {
                  const done = await resolve.run(signal.id, "reject");
                  if (done) onDone();
                }}
              >
                مخالفة — اعكس النقاط
              </Button>
            </div>
          </>
        )}
      </div>
    </Modal>
  );
}
