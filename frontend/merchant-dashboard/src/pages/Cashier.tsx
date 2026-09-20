/**
 * شاشة الكاشير — أهم شاشة في المنتج كله.
 *
 * تعمل على جهاز ثابت بجوار الصندوق طول اليوم، ويستخدمها شخص
 * مستعجل وأمامه طابور. كل قرار تصميم هنا يخدم هدفًا واحدًا:
 * **أقل من عشر ثوانٍ من وصول العميل إلى منحه نقاطه.**
 *
 * ولذلك:
 *   · الرمز كبير ودائم على الشاشة بلا ضغطة.
 *   · العمليات المعلّقة تصل باستطلاع كل ثلاث ثوانٍ لا بزر تحديث.
 *   · زر التأكيد كبير ويُعطَّل أثناء التنفيذ — الضغط المزدوج هو
 *     أول سبب لمنح النقاط مرتين.
 */

import { useEffect, useRef, useState } from "react";

import {
  Badge,
  Button,
  Empty,
  ErrorBox,
  Field,
  Modal,
  fmt,
  useAction,
  useApi,
  useInterval,
} from "@walaee/shared";
import type { TerminalCode, Transaction } from "@walaee/shared";

import { actions, queries } from "../lib/queries";

const POLL_MS = 3_000;
const ROTATE_MS = 30_000;

export function Cashier() {
  const code = useApi((signal) => queries.terminalCode(signal), []);
  const pending = useApi((signal) => queries.pendingTransactions(signal), []);

  const [manualOpen, setManualOpen] = useState(false);
  const [redeemOpen, setRedeemOpen] = useState(false);

  // الاستطلاع والتدوير مستقلان: الرمز يتغيّر كل ٣٠ ثانية، والعمليات
  // تصل خلال ثوانٍ من ضغط العميل
  useInterval(() => pending.reload(), POLL_MS);
  useInterval(() => code.reload(), ROTATE_MS);

  return (
    <div className="cashier">
      <section className="cashier-code">
        {code.data ? (
          <QrPanel data={code.data} onRotate={code.reload} />
        ) : code.error != null ? (
          <ErrorBox error={code.error} onRetry={code.reload} />
        ) : (
          <div className="qr-box skeleton" style={{ aspectRatio: "1" }} />
        )}

        <div className="cashier-actions">
          <Button variant="ghost" block onClick={() => setManualOpen(true)}>
            تسجيل يدوي
          </Button>
          <Button variant="ghost" block onClick={() => setRedeemOpen(true)}>
            صرف كود مكافأة
          </Button>
        </div>
      </section>

      <section className="cashier-queue">
        <header className="row between">
          <h2>بانتظار التأكيد</h2>
          {pending.data && pending.data.length > 0 && (
            <Badge tone="orange">{fmt.number(pending.data.length)}</Badge>
          )}
        </header>

        {pending.error != null && (
          <ErrorBox error={pending.error} onRetry={pending.reload} />
        )}

        {pending.data?.length === 0 && (
          <Empty
            icon="✓"
            title="لا توجد عمليات معلّقة"
            hint="اطلب من العميل مسح الرمز وإدخال قيمة الفاتورة."
          />
        )}

        <div className="stack gap">
          {pending.data?.map((txn) => (
            <PendingRow key={txn.id} txn={txn} onDone={pending.reload} />
          ))}
        </div>
      </section>

      <ManualModal
        open={manualOpen}
        onClose={() => setManualOpen(false)}
        onDone={pending.reload}
      />
      <RedeemModal open={redeemOpen} onClose={() => setRedeemOpen(false)} />
    </div>
  );
}

/**
 * لوحة الرمز.
 *
 * الرمز مرسوم كـQR وبالنص معًا: الكاميرا تفشل أحيانًا، والنص
 * يبقي المسار مفتوحًا بلا أن ينادي الكاشير على أحد.
 */
function QrPanel({
  data,
  onRotate,
}: {
  data: TerminalCode;
  onRotate: () => void;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const rotate = useAction(actions.rotateCode);

  useEffect(() => {
    let cancelled = false;

    // مكتبة الرسم تُحمَّل عند الحاجة: لا يحتاجها من يفتح التقارير
    import("qrcode").then((QR) => {
      if (cancelled || !canvasRef.current) return;
      QR.toCanvas(canvasRef.current, data.code, {
        width: 280,
        margin: 1,
        color: { dark: "#14142b", light: "#ffffff" },
      }).catch(() => undefined);
    });

    return () => {
      cancelled = true;
    };
  }, [data.code]);

  return (
    <div className="qr-box">
      <p className="t-sm muted">{data.label}</p>
      <canvas ref={canvasRef} className="qr-canvas" />
      <p className="qr-code num">{data.code}</p>
      <p className="t-xs faint">يتغيّر الرمز تلقائيًا كل ٣٠ ثانية</p>
      <Button
        variant="ghost"
        loading={rotate.loading}
        onClick={async () => {
          await rotate.run();
          onRotate();
        }}
      >
        تجديد الآن
      </Button>
    </div>
  );
}

function PendingRow({ txn, onDone }: { txn: Transaction; onDone: () => void }) {
  const confirm = useAction(actions.confirmTransaction);

  return (
    <div className="pending-row">
      <div className="grow">
        <p className="pending-amount num">{fmt.money(txn.invoice_amount)}</p>
        <p className="t-sm muted">
          {txn.customer_name || "عميل"} ·{" "}
          <span className="num">{fmt.phone(txn.customer_phone)}</span>
        </p>
        <p className="t-xs faint">
          فاتورة <span className="num">{txn.invoice_no}</span> ·{" "}
          {fmt.relativeTime(txn.created_at)}
        </p>
      </div>

      {confirm.error != null ? (
        <div className="stack" style={{ gap: 6, maxWidth: 220 }}>
          <ErrorBox error={confirm.error} />
          <Button
            size="lg"
            loading={confirm.loading}
            onClick={async () => {
              const done = await confirm.run(txn.id);
              if (done) onDone();
            }}
          >
            إعادة المحاولة
          </Button>
        </div>
      ) : (
        <Button
          size="lg"
          loading={confirm.loading}
          onClick={async () => {
            const done = await confirm.run(txn.id);
            if (done) onDone();
          }}
        >
          تأكيد ومنح النقاط
        </Button>
      )}
    </div>
  );
}

/**
 * المسار اليدوي.
 *
 * ليس استثناءً نادرًا: نسبة معتبرة من العملاء لن تحمل التطبيق
 * أبدًا، ورفضهم يعني خسارة التاجر لجزء من قاعدته — وهو أول سبب
 * لإلغاء الاشتراك.
 */
function ManualModal({
  open,
  onClose,
  onDone,
}: {
  open: boolean;
  onClose: () => void;
  onDone: () => void;
}) {
  const [phone, setPhone] = useState("");
  const [amount, setAmount] = useState("");
  const [invoiceNo, setInvoiceNo] = useState("");
  const [result, setResult] = useState<Transaction | null>(null);

  const submit = useAction(actions.manualTransaction);

  function reset() {
    setPhone("");
    setAmount("");
    setInvoiceNo("");
    setResult(null);
    submit.reset();
  }

  return (
    <Modal
      open={open}
      title="تسجيل عملية يدويًا"
      onClose={() => {
        reset();
        onClose();
      }}
    >
      {result ? (
        <div className="manual-done">
          <p className="manual-done-icon" aria-hidden="true">
            ✓
          </p>
          <p className="w-7">تمّت العملية ومُنحت النقاط</p>
          <p className="t-sm muted num">{fmt.money(result.invoice_amount)}</p>
          <Button
            block
            onClick={() => {
              reset();
              onDone();
            }}
          >
            تسجيل عملية أخرى
          </Button>
        </div>
      ) : (
        <form
          className="stack gap"
          onSubmit={async (event) => {
            event.preventDefault();
            const txn = await submit.run({
              phone: phone.trim(),
              invoice_amount: amount,
              invoice_no: invoiceNo.trim() || `M-${Date.now()}`,
            });
            if (txn) {
              setResult(txn);
              onDone();
            }
          }}
        >
          <Field label="رقم هاتف العميل" hint="سيُنشأ حساب تلقائيًا إن لم يكن موجودًا">
            <input
              className="input num"
              type="tel"
              inputMode="tel"
              placeholder="01012345678"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              required
              autoFocus
            />
          </Field>

          <Field label="قيمة الفاتورة">
            <input
              className="input num"
              type="number"
              min="0.01"
              step="0.01"
              placeholder="0.00"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              required
            />
          </Field>

          <Field label="رقم الفاتورة" hint="اختياري">
            <input
              className="input num"
              value={invoiceNo}
              onChange={(e) => setInvoiceNo(e.target.value)}
            />
          </Field>

          {submit.error != null && <ErrorBox error={submit.error} />}

          <Button type="submit" size="lg" block loading={submit.loading}>
            تسجيل ومنح النقاط
          </Button>
        </form>
      )}
    </Modal>
  );
}

function RedeemModal({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const [code, setCode] = useState("");
  const [done, setDone] = useState<string | null>(null);

  const use = useAction(actions.useRedemption);

  return (
    <Modal
      open={open}
      title="صرف كود مكافأة"
      onClose={() => {
        setCode("");
        setDone(null);
        use.reset();
        onClose();
      }}
    >
      {done ? (
        <div className="manual-done">
          <p className="manual-done-icon" aria-hidden="true">
            ✓
          </p>
          <p className="w-7">صُرفت المكافأة</p>
          <p className="t-sm muted">{done}</p>
          <Button
            block
            onClick={() => {
              setCode("");
              setDone(null);
            }}
          >
            صرف كود آخر
          </Button>
        </div>
      ) : (
        <form
          className="stack gap"
          onSubmit={async (event) => {
            event.preventDefault();
            const result = await use.run(code.trim().toUpperCase());
            if (result) setDone(result.reward_title);
          }}
        >
          <Field label="الكود" hint="ثمانية محارف يعرضها العميل على شاشته">
            <input
              className="input num code-input"
              maxLength={10}
              placeholder="ABCD2345"
              value={code}
              onChange={(e) => setCode(e.target.value.toUpperCase())}
              required
              autoFocus
            />
          </Field>

          {use.error != null && <ErrorBox error={use.error} />}

          <Button type="submit" size="lg" block loading={use.loading}>
            صرف المكافأة
          </Button>
        </form>
      )}
    </Modal>
  );
}
