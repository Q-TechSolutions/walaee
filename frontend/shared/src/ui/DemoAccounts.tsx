/**
 * منتقي حسابات التجربة.
 *
 * يظهر أسفل شاشة الدخول على النشر التجريبي وحده، فيدخل المجرّب
 * بضغطة واحدة. بدونه عليه أن يعرف الأرقام وكلمات المرور من مكان
 * آخر ويكتبها — وأول ما يحدث أن يُدخل رقم مدير المنصة في تطبيق
 * العميل فيفشل بلا أن يفهم السبب.
 *
 * يختفي تمامًا حين تردّ النقطة ٤٠٤، وهو ما يحدث على أي نشر لم
 * تُضبَط فيه متغيرات التجربة.
 */

import { useEffect, useState } from "react";

import { api } from "../api/client";

export interface DemoStaff {
  phone: string;
  label: string;
  role: string;
  app: "merchant" | "admin";
  password: string;
}

export interface DemoCustomer {
  phone: string;
  label: string;
  app: "customer";
  code: string;
}

interface DemoAccountsPayload {
  enabled: boolean;
  staff: DemoStaff[];
  customers: DemoCustomer[];
  notice: string;
}

/**
 * يجلب حسابات التجربة، أو null إن كان النشر غير تجريبي.
 *
 * لا يستخدم `useApi` لأن ٤٠٤ هنا نتيجة متوقّعة لا خطأ: عرض صندوق
 * خطأ أحمر على شاشة دخول إنتاجية لأن ميزة عرض غير مفعّلة هو
 * بالضبط ما نريد تجنّبه.
 */
export function useDemoAccounts(): DemoAccountsPayload | null {
  const [data, setData] = useState<DemoAccountsPayload | null>(null);

  useEffect(() => {
    let active = true;

    api
      .anonymous.get<DemoAccountsPayload>("/auth/demo-accounts")
      .then((payload) => {
        if (active && payload?.enabled) setData(payload);
      })
      .catch(() => {
        // ٤٠٤ أو شبكة مقطوعة: لا شيء يُعرض، والشاشة تعمل كالمعتاد
      });

    return () => {
      active = false;
    };
  }, []);

  return data;
}

export function DemoAccountsPanel({
  app,
  onPick,
}: {
  app: "customer" | "merchant" | "admin";
  /** يملأ الحقول ويُرسل — الضغطة الواحدة هي الهدف كله */
  onPick: (account: { phone: string; secret: string }) => void;
}) {
  const data = useDemoAccounts();
  if (!data) return null;

  const rows =
    app === "customer"
      ? data.customers.map((c) => ({
          phone: c.phone,
          label: c.label,
          hint: `الكود ${c.code}`,
          secret: c.code,
        }))
      : data.staff
          .filter((s) => s.app === app)
          .map((s) => ({
            phone: s.phone,
            label: s.label,
            hint: s.phone,
            secret: s.password,
          }));

  if (rows.length === 0) return null;

  return (
    <div className="wl-demo">
      <p className="wl-demo-title">
        <span aria-hidden="true">◈</span> حسابات تجربة — اضغط للدخول
      </p>

      <div className="wl-demo-list">
        {rows.map((row) => (
          <button
            key={row.phone}
            type="button"
            className="wl-demo-item"
            onClick={() => onPick({ phone: row.phone, secret: row.secret })}
          >
            <span className="wl-demo-label">{row.label}</span>
            <span className="wl-demo-hint num">{row.hint}</span>
          </button>
        ))}
      </div>

      <p className="wl-demo-note">{data.notice}</p>
    </div>
  );
}
