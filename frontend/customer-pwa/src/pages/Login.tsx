/**
 * الدخول بالهاتف وكود التحقق.
 *
 * خطوتان لا صفحتان: التنقّل بين مسارين يفقد الرقم المُدخل إذا ضغط
 * المستخدم رجوع، والدخول يجب أن يكون أقصر مسار في التطبيق كله.
 *
 * الشاشة نصفان — `AuthLayout`. لوح الهوية هنا يعرض أرقام الشبكة
 * الحقيقية لا وعودًا: من يفتح التطبيق لأول مرة يريد أن يعرف إن
 * كانت متاجره موجودة فيه قبل أن يعطي رقم هاتفه.
 */

import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import {
  AuthLayout,
  AuthPoint,
  Button,
  DemoAccountsPanel,
  ErrorBox,
  Icon,
  api,
  fetchNetwork,
  fmt,
  t,
  useAction,
  useApi,
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

  // الشبكة للوح الهوية وحده — فشلها لا يمنع الدخول
  const network = useApi((signal) => fetchNetwork(signal), []);

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

  /** دخول بضغطة من منتقي حسابات التجربة. */
  async function pickDemo(account: { phone: string; secret: string }) {
    setPhone(account.phone);
    const result = await requestOtp.run(account.phone);
    if (result?.code) {
      setCode(result.code);
      setDemoNotice(result.notice ?? t("حساب تجربة — الكود مُدخَل تلقائيًا."));
      setStep("code");
      restartCountdown();
    }
  }

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
        setDemoNotice(result.notice ?? t("حساب تجربة — الكود مُدخَل تلقائيًا."));
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

  const stats = network.data?.stats;

  return (
    <AuthLayout
      headline={t("بطاقات ولائك كلها في محفظة واحدة")}
      subline={t("لا كروت ورق تضيع ولا تطبيق لكل متجر. رقم هاتفك هو بطاقتك في كل متجر متعاقد.")}
      aside={
        <ul>
          <AuthPoint title={t("اجمع من غير ما تعمل حاجة")}>
            {t("قول رقمك عند الكاشير، والنقاط تتسجّل في ثانية.")}
          </AuthPoint>
          <AuthPoint title={t("رصيدك واضح دايمًا")}>
            {t("تعرف كام باقي على المكافأة القادمة، ومتى ينتهي رصيدك.")}
          </AuthPoint>
          <AuthPoint title={t("متاجر في كل محافظة")}>
            {stats
              ? t("{branches} فرعًا لـ{brands} متجرًا في {govs} محافظة.", {
                  branches: fmt.number(stats.branches),
                  brands: fmt.number(stats.brands),
                  govs: fmt.number(stats.governorates),
                })
              : t("شبكة تكبر كل شهر بمتاجر جديدة قريبة منك.")}
          </AuthPoint>
        </ul>
      }
      footer={<DemoAccountsPanel app="customer" onPick={pickDemo} />}
    >
      {step === "phone" ? (
        <form className="auth-fields" onSubmit={submitPhone}>
          <h2>{t("سجّل دخولك")}</h2>
          <p className="auth-lede">
            {t("أدخل رقم هاتفك وسنرسل لك كود تحقق من أربعة إلى ستة أرقام.")}
          </p>

          <div className="field">
            <label htmlFor="phone">{t("رقم الهاتف")}</label>
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
            {t("إرسال الكود")}
          </Button>

          <p className="auth-fine">
            {t("بالمتابعة أنت توافق على تلقّي رسائل من المتاجر التي تنضم إليها. يمكنك إلغاء الموافقة في أي وقت من صفحة حسابك.")}
          </p>
        </form>
      ) : (
        <form className="auth-fields" onSubmit={submitCode}>
          <h2>{t("أدخل الكود")}</h2>
          <p className="auth-lede">
            {t("أرسلنا كودًا إلى")} <span className="num">{phone}</span>
          </p>

          <div className="field">
            <label htmlFor="code">{t("كود التحقق")}</label>
            <input
              id="code"
              ref={codeInput}
              className="input auth-code num"
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
            <p className="auth-note">
              <Icon name="info" size={16} />
              <span>{demoNotice}</span>
            </p>
          )}

          {verifyOtp.error != null && <ErrorBox error={verifyOtp.error} />}

          <Button type="submit" size="lg" block loading={verifyOtp.loading}>
            {t("دخول")}
          </Button>

          <p className="auth-switch">
            <button type="button" onClick={() => setStep("phone")}>
              {t("تغيير الرقم")}
            </button>
            <span aria-hidden="true">·</span>
            {remaining > 0 ? (
              <span>
                {t("كود جديد بعد")} <span className="num">{remaining}</span> {t("ثانية")}
              </span>
            ) : (
              <button type="button" onClick={resend}>
                {t("إرسال كود جديد")}
              </button>
            )}
          </p>
        </form>
      )}
    </AuthLayout>
  );
}
