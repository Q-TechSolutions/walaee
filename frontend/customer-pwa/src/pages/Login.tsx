/**
 * الدخول بالهاتف وكود التحقق.
 *
 * خطوتان لا صفحتان: التنقّل بين مسارين يفقد الرقم المُدخل إذا ضغط
 * المستخدم رجوع، والدخول يجب أن يكون أقصر مسار في التطبيق كله.
 */

import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import {
  Button,
  ErrorBox,
  api,
  useAction,
  useCountdown,
  writeTokens,
} from "@walaee/shared";
import type { Customer } from "@walaee/shared";

const CONSENT_VERSION = "v1";
const RESEND_SECONDS = 60;

interface OtpRequestResponse {
  sent: boolean;
  expires_in: number;
  /** يصل لحسابات التجربة وحدها — الكود ثابت ومعلَن لها */
  demo?: boolean;
  code?: string;
  notice?: string;
}

interface VerifyResponse {
  access: string;
  refresh: string;
  is_new: boolean;
  customer: Customer;
}

export function Login() {
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: string } | null)?.from ?? "/";

  const [step, setStep] = useState<"phone" | "code">("phone");
  const [phone, setPhone] = useState("");
  const [code, setCode] = useState("");
  const [remaining, restartCountdown] = useCountdown(RESEND_SECONDS);
  const [demoNotice, setDemoNotice] = useState<string | null>(null);

  const codeInput = useRef<HTMLInputElement>(null);

  const requestOtp = useAction(async (value: string) =>
    api.anonymous.post<OtpRequestResponse>("/auth/otp/request", { phone: value }),
  );

  const verifyOtp = useAction(async (value: string, otp: string) => {
    return api.anonymous.post<VerifyResponse>("/auth/otp/verify", {
      phone: value,
      code: otp,
      consent_version: CONSENT_VERSION,
    });
  });

  // التركيز التلقائي على حقل الكود: المستخدم قادم من رسالة نصية
  // ويريد اللصق فورًا لا البحث عن الحقل
  useEffect(() => {
    if (step === "code") codeInput.current?.focus();
  }, [step]);

  async function submitPhone(event: React.FormEvent) {
    event.preventDefault();
    const trimmed = phone.trim();
    if (trimmed.length < 8) return;

    const result = await requestOtp.run(trimmed);
    if (result) {
      // حساب تجربة: الكود ثابت ولا يصل برسالة، فيُملأ تلقائيًا
      // بدل أن ينتظر المستخدم رسالة لن تأتي
      if (result.demo && result.code) {
        setCode(result.code);
        setDemoNotice(result.notice ?? "حساب تجربة — الكود مُدخَل تلقائيًا.");
      } else {
        setDemoNotice(null);
      }
      setStep("code");
      restartCountdown();
    }
  }

  async function submitCode(event: React.FormEvent) {
    event.preventDefault();
    if (code.trim().length < 4) return;

    const session = await verifyOtp.run(phone.trim(), code.trim());
    if (session) {
      writeTokens({ access: session.access, refresh: session.refresh });
      navigate(from, { replace: true });
    }
  }

  async function resend() {
    setCode("");
    const result = await requestOtp.run(phone.trim());
    if (result) {
      if (result.demo && result.code) setCode(result.code);
      restartCountdown();
    }
  }

  return (
    <div className="login">
      <div className="login-brand">
        <div className="login-mark" aria-hidden="true">
          ♥
        </div>
        <h1>ولائي</h1>
        <p className="muted">كلنا كسبانين</p>
      </div>

      {step === "phone" ? (
        <form className="login-card" onSubmit={submitPhone}>
          <h2>سجّل دخولك</h2>
          <p className="t-sm muted">
            أدخل رقم هاتفك وسنرسل لك كود تحقق من أربعة إلى ستة أرقام.
          </p>

          <div className="field">
            <label htmlFor="phone">رقم الهاتف</label>
            <input
              id="phone"
              className="input num"
              type="tel"
              inputMode="tel"
              autoComplete="tel"
              placeholder="01012345678"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              required
            />
          </div>

          {requestOtp.error != null && <ErrorBox error={requestOtp.error} />}

          <Button type="submit" size="lg" block loading={requestOtp.loading}>
            إرسال الكود
          </Button>

          <p className="t-xs faint center">
            بالمتابعة أنت توافق على تلقّي رسائل من المتاجر التي تنضم إليها.
            يمكنك إلغاء الموافقة في أي وقت من صفحة حسابك.
          </p>
        </form>
      ) : (
        <form className="login-card" onSubmit={submitCode}>
          <h2>أدخل الكود</h2>
          <p className="t-sm muted">
            أرسلنا كودًا إلى <span className="num">{phone}</span>
            {" · "}
            <button
              type="button"
              className="link"
              onClick={() => setStep("phone")}
            >
              تغيير الرقم
            </button>
          </p>

          <div className="field">
            <label htmlFor="code">كود التحقق</label>
            <input
              id="code"
              ref={codeInput}
              className="input code-input num"
              type="text"
              inputMode="numeric"
              autoComplete="one-time-code"
              maxLength={6}
              placeholder="······"
              value={code}
              onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
              required
            />
          </div>

          {demoNotice && (
            <p className="demo-notice">
              <span aria-hidden="true">◈</span> {demoNotice}
            </p>
          )}

          {verifyOtp.error != null && <ErrorBox error={verifyOtp.error} />}

          <Button type="submit" size="lg" block loading={verifyOtp.loading}>
            دخول
          </Button>

          {remaining > 0 ? (
            <p className="t-sm faint center">
              يمكنك طلب كود جديد بعد <span className="num">{remaining}</span> ثانية
            </p>
          ) : (
            <button type="button" className="link center" onClick={resend}>
              إرسال كود جديد
            </button>
          )}
        </form>
      )}
    </div>
  );
}
