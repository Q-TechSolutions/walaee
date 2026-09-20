/** دخول الموظفين بالهاتف وكلمة المرور. */

import { useState } from "react";
import { useNavigate } from "react-router-dom";

import {
  Button,
  DemoAccountsPanel,
  ErrorBox,
  Field,
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
    <div className="auth">
      <form
        className="auth-card"
        onSubmit={async (event) => {
          event.preventDefault();
          await signIn(phone, password);
        }}
      >
        <div className="auth-brand">
          <div className="auth-mark" aria-hidden="true">
            ♥
          </div>
          <h1>لوحة المتجر</h1>
          <p className="muted t-sm">ولائي — كلنا كسبانين</p>
        </div>

        <Field label="رقم الهاتف">
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

        <Field label="كلمة المرور">
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
          دخول
        </Button>

        <DemoAccountsPanel
          app="merchant"
          onPick={({ phone: p, secret }) => {
            setPhone(p);
            setPassword(secret);
            void signIn(p, secret);
          }}
        />
      </form>
    </div>
  );
}
