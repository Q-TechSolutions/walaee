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
  Icon,
  Modal,
  fmt,
  t,
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
    <>
      <section className="card card-p tint-v mb-3">
        <div className="row-t">
          <span className="ibox v" style={{ background: "#fff" }}>
            <Icon name="bolt" size={20} />
          </span>
          <div className="grow">
            <b>{t("هذه هي الإجابة على سؤال «كيف تُثبَت عملية الشراء؟»")}</b>
            <p className="t-sm muted mt-1">
              {t("رمز متغيّر كل ٣٠ ثانية على شاشتك — العميل يمسحه ويُدخل قيمة الفاتورة، وأنت تؤكّد. لا أجهزة إضافية، ولا يمكن إعادة استخدام الرمز.")}
            </p>
          </div>
        </div>
      </section>

      <div className="pos">
        <section>
          {code.data ? (
            <QrPanel data={code.data} onRotate={code.reload} />
          ) : code.error != null ? (
            <ErrorBox error={code.error} onRetry={code.reload} />
          ) : (
            <div className="pos-qr skeleton" style={{ minHeight: 420 }} />
          )}

          <div className="cashier-actions mt-3">
            <Button variant="ghost" block onClick={() => setManualOpen(true)}>
              <Icon name="phone" size={16} />
              {t("تسجيل يدوي")}
            </Button>
            <Button variant="ghost" block onClick={() => setRedeemOpen(true)}>
              <Icon name="gift" size={16} />
              {t("صرف كود مكافأة")}
            </Button>
          </div>
        </section>

        <div className="stack gap">
          <ShiftCard />

          <section className="card grow">
            <div className="card-hd">
              <div className="row">
                <h3>{t("بانتظار التأكيد")}</h3>
                <span className="live">
                  <i />
                  {t("مباشر")}
                </span>
              </div>
              {pending.data && pending.data.length > 0 && (
                <Badge tone="orange">{fmt.number(pending.data.length)}</Badge>
              )}
            </div>

            <div className="card-p">
              {pending.error != null && (
                <ErrorBox error={pending.error} onRetry={pending.reload} />
              )}

              {pending.data?.length === 0 && (
                <Empty
                  icon="checkCircle"
                  title={t("لا توجد عمليات معلّقة")}
                  hint={t("اطلب من العميل مسح الرمز وإدخال قيمة الفاتورة.")}
                />
              )}

              <div className="stack gap">
                {pending.data?.map((txn) => (
                  <PendingRow key={txn.id} txn={txn} onDone={pending.reload} />
                ))}
              </div>
            </div>
          </section>
        </div>
      </div>

      <ManualModal
        open={manualOpen}
        onClose={() => setManualOpen(false)}
        onDone={pending.reload}
      />
      <RedeemModal open={redeemOpen} onClose={() => setRedeemOpen(false)} />
    </>
  );
}

/**
 * مناوبة اليوم.
 *
 * أرقام الكاشير نفسه لا أرقام الفرع: من يقف خلف الصندوق ثماني
 * ساعات يحتاج أن يرى أثره هو. الرقم يأتي من `/merchant/shift`
 * محسوبًا بالتقويم المحلي — «اليوم» يعني ورديته لا آخر ٢٤ ساعة.
 */
function ShiftCard() {
  const shift = useApi((signal) => queries.shift(signal), []);

  if (shift.error != null || !shift.data) return null;
  const data = shift.data;

  return (
    <section className="card card-p">
      <div className="row between mb-2">
        <b className="t-md">{t("مناوبة اليوم")}</b>
        <span className="badge bg-g">
          <span className="dot" style={{ background: "currentColor" }} />
          {t("نشطة")}
        </span>
      </div>

      <div className="row">
        <span className="av g" aria-hidden="true">
          {(data.staff_name || t("؟")).trim().charAt(0)}
        </span>
        <div className="grow">
          <b className="t-sm">{data.staff_name}</b>
          <p className="t-xs muted">
            {t(data.role_label)} · {data.branch_name}
          </p>
        </div>
      </div>

      <div className="grid g3 mt-3">
        <div className="shift-tile">
          <p className="t-xl w-8 num">{fmt.number(data.transactions)}</p>
          <p className="t-xs muted">{t("عملية اليوم")}</p>
        </div>
        <div className="shift-tile">
          <p className="t-xl w-8 num">{fmt.number(data.customers)}</p>
          <p className="t-xs muted">{t("عميل")}</p>
        </div>
        <div className="shift-tile">
          <p className="t-xl w-8 num">{fmt.money(data.revenue)}</p>
          <p className="t-xs muted">{t("إجمالي")}</p>
        </div>
      </div>
    </section>
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
        width: 240,
        margin: 1,
        color: { dark: "#14142b", light: "#ffffff" },
      }).catch(() => undefined);
    });

    return () => {
      cancelled = true;
    };
  }, [data.code]);

  return (
    <div className="pos-qr">
      <p className="t-sm w-7" style={{ opacity: 0.75 }}>
        {t("اعرض هذا الرمز للعميل —")} {data.label}
      </p>

      <div className="qrbox">
        <canvas ref={canvasRef} className="qr-canvas" />
      </div>

      <p className="pos-code num">{data.code}</p>

      <p className="pos-timer">
        <span className="ring" aria-hidden="true" />
        {t("يتجدّد تلقائيًا كل")} <span className="num">{t("٣٠")}</span> {t("ثانية")}
      </p>

      <div className="row gap-sm mt-3" style={{ justifyContent: "center" }}>
        <button
          type="button"
          className="btn btn-sm pos-ghost"
          disabled={rotate.loading}
          onClick={async () => {
            await rotate.run();
            onRotate();
          }}
        >
          <Icon name="refresh" size={14} />
          {t("تجديد فوري")}
        </button>
      </div>
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
          {txn.customer_name || t("عميل")} ·{" "}
          <span className="num">{fmt.phone(txn.customer_phone)}</span>
        </p>
        <p className="t-xs faint">
          {t("فاتورة")} <span className="num">{txn.invoice_no}</span> ·{" "}
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
            {t("إعادة المحاولة")}
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
          {t("تأكيد ومنح النقاط")}
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
      title={t("تسجيل عملية يدويًا")}
      onClose={() => {
        reset();
        onClose();
      }}
    >
      {result ? (
        <div className="manual-done">
          <p className="manual-done-icon">
            <Icon name="check" size={28} weight={2.4} />
          </p>
          <p className="w-7">{t("تمّت العملية ومُنحت النقاط")}</p>
          <p className="t-sm muted num">{fmt.money(result.invoice_amount)}</p>
          <Button
            block
            onClick={() => {
              reset();
              onDone();
            }}
          >
            {t("تسجيل عملية أخرى")}
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
          <Field label={t("رقم هاتف العميل")} hint={t("سيُنشأ حساب تلقائيًا إن لم يكن موجودًا")}>
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

          <Field label={t("قيمة الفاتورة")}>
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

          <Field label={t("رقم الفاتورة")} hint={t("اختياري")}>
            <input
              className="input num"
              value={invoiceNo}
              onChange={(e) => setInvoiceNo(e.target.value)}
            />
          </Field>

          {submit.error != null && <ErrorBox error={submit.error} />}

          <Button type="submit" size="lg" block loading={submit.loading}>
            {t("تسجيل ومنح النقاط")}
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
      title={t("صرف كود مكافأة")}
      onClose={() => {
        setCode("");
        setDone(null);
        use.reset();
        onClose();
      }}
    >
      {done ? (
        <div className="manual-done">
          <p className="manual-done-icon">
            <Icon name="check" size={28} weight={2.4} />
          </p>
          <p className="w-7">{t("صُرفت المكافأة")}</p>
          <p className="t-sm muted">{done}</p>
          <Button
            block
            onClick={() => {
              setCode("");
              setDone(null);
            }}
          >
            {t("صرف كود آخر")}
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
          <Field label={t("الكود")} hint={t("ثمانية محارف يعرضها العميل على شاشته")}>
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
            {t("صرف المكافأة")}
          </Button>
        </form>
      )}
    </Modal>
  );
}
