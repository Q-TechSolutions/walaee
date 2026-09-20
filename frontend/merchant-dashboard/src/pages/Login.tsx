/** دخول الموظفين بالهاتف وكلمة المرور. */

import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { Button, ErrorBox, Field, useAction } from "@walaee/shared";

import { actions } from "../lib/queries";
import { saveSession } from "../lib/session";

export function Login() {
  const navigate = useNavigate();
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");

  const login = useAction(actions.login);

  return (
    <div className="auth">
      <form
        className="auth-card"
        onSubmit={async (event) => {
          event.preventDefault();
          const session = await login.run(phone.trim(), password);
          if (session) {
            saveSession(session);
            // الكاشير يبدأ من شاشته مباشرة: هي الشاشة الوحيدة
            // التي يستخدمها، وإجباره على المرور باللوحة إهدار وقت
            navigate(
              session.roles[0]?.role === "cashier" ? "/cashier" : "/",
              { replace: true },
            );
          }
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
      </form>
    </div>
  );
}
