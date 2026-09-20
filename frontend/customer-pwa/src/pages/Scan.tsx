/**
 * المسح وإدخال الفاتورة.
 *
 * ثلاث خطوات: امسح ← أدخل المبلغ ← انتظر تأكيد الكاشير.
 *
 * الخطوة الثالثة ليست تجميلية. العميل يجب أن يفهم أن النقاط لم
 * تُمنح بعد، وإلا أغلق التطبيق قبل أن يؤكّد الكاشير ثم عاد يشتكي
 * أن نقاطه ضاعت.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { Button, ErrorBox, Field, fmt, useAction } from "@walaee/shared";
import type { ScanResult } from "@walaee/shared";

import { actions } from "../lib/queries";

type Stage = "scan" | "amount" | "waiting";

export function Scan() {
  const navigate = useNavigate();
  const [stage, setStage] = useState<Stage>("scan");
  const [code, setCode] = useState("");
  const [resolved, setResolved] = useState<ScanResult | null>(null);
  const [amount, setAmount] = useState("");
  const [invoiceNo, setInvoiceNo] = useState("");

  const resolve = useAction(actions.resolveCode);
  const create = useAction(actions.createTransaction);

  const handleResolve = useCallback(
    async (value: string) => {
      const result = await resolve.run(value.trim().toUpperCase());
      if (result) {
        setCode(value.trim().toUpperCase());
        setResolved(result);
        setStage("amount");
      }
    },
    [resolve],
  );

  async function submitAmount(event: React.FormEvent) {
    event.preventDefault();
    const value = Number(amount);
    if (!Number.isFinite(value) || value <= 0) return;

    const txn = await create.run({
      code,
      invoice_no: invoiceNo.trim() || `C-${Date.now()}`,
      invoice_amount: amount,
    });

    if (txn) setStage("waiting");
  }

  function restart() {
    setStage("scan");
    setResolved(null);
    setCode("");
    setAmount("");
    setInvoiceNo("");
    resolve.reset();
    create.reset();
  }

  return (
    <div className="page">
      <h1 className="mb">امسح رمز المتجر</h1>

      {stage === "scan" && (
        <>
          <QrReader onCode={handleResolve} busy={resolve.loading} />

          <ManualCode onSubmit={handleResolve} busy={resolve.loading} />

          {resolve.error != null && <ErrorBox error={resolve.error} />}
        </>
      )}

      {stage === "amount" && resolved && (
        <form className="stack gap" onSubmit={submitAmount}>
          <div
            className="scan-brand"
            style={{ "--brand": resolved.brand.primary_color } as React.CSSProperties}
          >
            <p className="t-sm">أنت في</p>
            <h2>{resolved.brand.name}</h2>
            <p className="t-sm">
              {resolved.branch.name} · {resolved.terminal.label}
            </p>

            {resolved.is_member && resolved.balances.length > 0 && (
              <p className="scan-balance">
                رصيدك الحالي{" "}
                <span className="num w-8">
                  {fmt.number(resolved.balances[0]!.amount)}
                </span>{" "}
                {resolved.balances[0]!.unit}
              </p>
            )}
            {!resolved.is_member && (
              <p className="scan-balance">أول زيارة لك — أهلًا بك 👋</p>
            )}
          </div>

          <Field label="قيمة الفاتورة" hint="كما هي على الإيصال، بالجنيه">
            <input
              className="input num amount-input"
              type="number"
              inputMode="decimal"
              min="0.01"
              step="0.01"
              autoFocus
              placeholder="0.00"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              required
            />
          </Field>

          <Field label="رقم الفاتورة" hint="اختياري — يساعد التاجر على المطابقة">
            <input
              className="input num"
              type="text"
              inputMode="numeric"
              placeholder="مثال: 10428"
              value={invoiceNo}
              onChange={(e) => setInvoiceNo(e.target.value)}
            />
          </Field>

          {create.error != null && <ErrorBox error={create.error} />}

          <Button type="submit" size="lg" block loading={create.loading}>
            إرسال للكاشير
          </Button>
          <button type="button" className="link center" onClick={restart}>
            إلغاء والمسح من جديد
          </button>
        </form>
      )}

      {stage === "waiting" && (
        <div className="waiting">
          <div className="waiting-pulse" aria-hidden="true" />
          <h2>بانتظار تأكيد الكاشير</h2>
          <p className="muted">
            أرسلنا الفاتورة إلى شاشة الكاشير. ستُضاف نقاطك فور تأكيده — لا
            تغلق التطبيق قبل ذلك.
          </p>
          <p className="t-sm faint">
            المبلغ <span className="num">{fmt.money(amount)}</span>
          </p>

          <div className="stack gap w-full">
            <Button size="lg" block onClick={() => navigate("/")}>
              عودة لبطاقاتي
            </Button>
            <button type="button" className="link" onClick={restart}>
              مسح فاتورة أخرى
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * قارئ الكاميرا.
 *
 * المكتبة تُحمَّل عند الحاجة لا مع التطبيق: ٤٠ ك.ب لا يحتاجها من
 * يفتح التطبيق ليرى رصيده فقط.
 */
function QrReader({
  onCode,
  busy,
}: {
  onCode: (code: string) => void;
  busy: boolean;
}) {
  const [state, setState] = useState<"idle" | "starting" | "running" | "denied">(
    "idle",
  );
  const containerId = "qr-reader";
  const scannerRef = useRef<{ stop: () => Promise<void> } | null>(null);

  useEffect(() => {
    return () => {
      // إيقاف الكاميرا عند مغادرة الشاشة: تركها مضاءة يستهلك
      // البطارية ويقلق المستخدم بحق
      scannerRef.current?.stop().catch(() => undefined);
    };
  }, []);

  async function start() {
    setState("starting");
    try {
      const { Html5Qrcode } = await import("html5-qrcode");
      const scanner = new Html5Qrcode(containerId);
      scannerRef.current = scanner;

      await scanner.start(
        { facingMode: "environment" },
        { fps: 10, qrbox: { width: 230, height: 230 } },
        (decoded: string) => {
          scanner.stop().catch(() => undefined);
          setState("idle");
          onCode(decoded);
        },
        () => undefined,
      );
      setState("running");
    } catch {
      setState("denied");
    }
  }

  return (
    <div className="qr">
      <div id={containerId} className={state === "running" ? "qr-live" : "qr-idle"}>
        {state !== "running" && (
          <div className="qr-placeholder">
            <span aria-hidden="true">⬚</span>
            <p className="t-sm muted">
              {state === "denied"
                ? "تعذّر فتح الكاميرا — استخدم الإدخال اليدوي بالأسفل"
                : "وجّه الكاميرا نحو الرمز على شاشة الكاشير"}
            </p>
          </div>
        )}
      </div>

      {state !== "running" && (
        <Button
          block
          size="lg"
          loading={state === "starting" || busy}
          onClick={start}
        >
          فتح الكاميرا
        </Button>
      )}
    </div>
  );
}

/**
 * الإدخال اليدوي.
 *
 * ليس مسارًا احتياطيًا نادرًا: الكاميرا تُرفض على http وفي متصفحات
 * قديمة وفي أجهزة بعدسة معطوبة. بدونه يفقد المتجر عميلًا بلا سبب
 * يفهمه أحد.
 */
function ManualCode({
  onSubmit,
  busy,
}: {
  onSubmit: (code: string) => void;
  busy: boolean;
}) {
  const [value, setValue] = useState("");

  return (
    <form
      className="manual-code"
      onSubmit={(e) => {
        e.preventDefault();
        if (value.trim().length >= 6) onSubmit(value);
      }}
    >
      <p className="t-sm muted center">أو اكتب الرمز الظاهر على الشاشة</p>
      <div className="row">
        <input
          className="input num code-input grow"
          type="text"
          maxLength={12}
          placeholder="ABCD2345"
          value={value}
          onChange={(e) => setValue(e.target.value.toUpperCase())}
        />
        <Button type="submit" loading={busy}>
          تأكيد
        </Button>
      </div>
    </form>
  );
}
