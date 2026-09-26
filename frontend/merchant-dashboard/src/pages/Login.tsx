/**
 * دخول الموظفين بالهاتف وكلمة المرور.
 *
 * الشاشة نصفان — `AuthLayout`. لوح الهوية يقول ماذا تجد خلف
 * الباب: الكاشير الذي يفتحها أول مرة يحتاج أن يتأكّد أنها شاشته
 * لا شاشة العميل، والثلاثة على نفس الدومين.
 */

import { useState } from "react";
import { useNavigate } from "react-router-dom";

import {
  AuthLayout,
  AuthPoint,
  Button,
  DemoAccountsPanel,
  ErrorBox,
  Field,
  t,
  useAction,
} from "@walaee/shared";

import { actions } from "../lib/queries";
import { saveSession } from "../lib/session";

export function Login() {
  const navigate = useNavigate();
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");

  const login = useAction(actions.login);

  /** دخول مباشر بحساب تجربة — بلا كتابة. */
  async function signIn(phoneValue: string, passwordValue: string) {
    const session = await login.run(phoneValue.trim(), passwordValue);
    if (session) {
      saveSession(session);
      // الكاشير يبدأ من شاشته: هي الشاشة الوحيدة التي يستخدمها
      navigate(session.roles[0]?.role === "cashier" ? "/cashier" : "/", {
        replace: true,
      });
    }
  }

  return (
    <AuthLayout
      badge={t("لوحة المتجر")}
      headline={t("برنامج ولائك، تحت سيطرتك")}
      subline={t("امنح النقاط، اصرف المكافآت، واعرف مَن عاد ومَن غاب — من شاشة واحدة.")}
      aside={
        <ul>
          <AuthPoint title={t("شاشة كاشير في خطوتين")}>
            {t("رقم العميل ثم قيمة الفاتورة. لا تدريب ولا جهاز إضافي.")}
          </AuthPoint>
          <AuthPoint title={t("تقارير تقول ما الذي نجح")}>
            {t("أي مكافأة تُصرف فعلًا، وكم يكلّفك الالتزام القائم.")}
          </AuthPoint>
          <AuthPoint title={t("صلاحيات لكل دور")}>
            {t("الكاشير يؤكّد العمليات ولا يرى التقارير ولا يضيف موظفين.")}
          </AuthPoint>
        </ul>
      }
      footer={
        <DemoAccountsPanel
          app="merchant"
          onPick={({ phone: p, secret }) => {
            setPhone(p);
            setPassword(secret);
            void signIn(p, secret);
          }}
        />
      }
    >
      <form
        className="auth-fields"
        onSubmit={async (event) => {
          event.preventDefault();
          await signIn(phone, password);
        }}
      >
        <h2>{t("دخول الموظفين")}</h2>
        <p className="auth-lede">
          {t("استخدم الرقم الذي سجّله مالك المتجر لك. لكل موظف حساب مستقل.")}
        </p>

        <Field label={t("رقم الهاتف")}>
          <input
            className="input num"
            type="tel"
            inputMode="tel"
            autoComplete="username"
            placeholder="01012345678"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            required
          />
        </Field>

        <Field label={t("كلمة المرور")}>
          <input
            className="input"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </Field>

        {login.error != null && <ErrorBox error={login.error} />}

        <Button type="submit" size="lg" block loading={login.loading}>
          {t("دخول")}
        </Button>

        <p className="auth-fine">
          {t("نسيت كلمة المرور؟ مالك المتجر يستطيع إعادة ضبطها لك من صفحة الموظفين.")}
        </p>
      </form>
    </AuthLayout>
  );
}
