/**
 * منتقي حسابات التجربة.
 *
 * يعرض **كل** الحسابات في كل شاشة دخول لا حسابات التطبيق الحالي
 * وحدها. السبب تجربة حقيقية: من يفتح شاشة ويرى ثلاثة حسابات فقط
 * لا يعرف أن هناك لوحة متجر ولوحة منصة أصلًا، فيجرّب رقم مدير
 * المنصة في تطبيق العميل ويفشل بلا أن يفهم السبب.
 *
 * حساب يخص هذا التطبيق  ← زر يُدخِل بضغطة.
 * حساب يخص تطبيقًا آخر  ← رابط ينقل إليه مباشرة.
 *
 * يختفي كليًا حين تردّ النقطة ٤٠٤، وهو ما يحدث على أي نشر لم
 * تُضبَط فيه متغيرات التجربة.
 */

import { useEffect, useState } from "react";

import { api } from "../api/client";

export type DemoApp = "customer" | "merchant" | "admin";

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
  apps: Record<DemoApp, string>;
  notice: string;
}

const APP_TITLES: Record<DemoApp, string> = {
  customer: "تطبيق العميل",
  merchant: "لوحة المتجر",
  admin: "إدارة المنصة",
};

const APP_ORDER: DemoApp[] = ["customer", "merchant", "admin"];

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

    api.anonymous
      .get<DemoAccountsPayload>("/auth/demo-accounts")
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

interface Row {
  phone: string;
  label: string;
  hint: string;
  secret: string;
}

export function DemoAccountsPanel({
  app,
  onPick,
}: {
  /** التطبيق الذي تعمل فيه هذه الشاشة */
  app: DemoApp;
  /** يملأ الحقول ويُرسل — الضغطة الواحدة هي الهدف كله */
  onPick: (account: { phone: string; secret: string }) => void;
}) {
  const data = useDemoAccounts();
  if (!data) return null;

  const grouped: Record<DemoApp, Row[]> = {
    customer: data.customers.map((c) => ({
      phone: c.phone,
      label: c.label,
      hint: `الكود ${c.code}`,
      secret: c.code,
    })),
    merchant: data.staff
      .filter((s) => s.app === "merchant")
      .map((s) => ({
        phone: s.phone,
        label: s.label,
        hint: s.phone,
        secret: s.password,
      })),
    admin: data.staff
      .filter((s) => s.app === "admin")
      .map((s) => ({
        phone: s.phone,
        label: s.label,
        hint: s.phone,
        secret: s.password,
      })),
  };

  const groups = APP_ORDER.filter((key) => grouped[key].length > 0);
  if (groups.length === 0) return null;

  return (
    <div className="wl-demo">
      <p className="wl-demo-title">
        <span aria-hidden="true">◈</span> حسابات تجربة
      </p>

      {groups.map((key) => {
        const current = key === app;
        return (
          <section key={key} className="wl-demo-group">
            <p className="wl-demo-group-title">
              {APP_TITLES[key]}
              {current ? (
                <span className="wl-demo-badge">هنا</span>
              ) : (
                <a className="wl-demo-link" href={data.apps[key]}>
                  انتقل إليه ›
                </a>
              )}
            </p>

            <div className="wl-demo-list">
              {grouped[key].map((row) =>
                current ? (
                  <button
                    key={row.phone}
                    type="button"
                    className="wl-demo-item"
                    onClick={() =>
                      onPick({ phone: row.phone, secret: row.secret })
                    }
                  >
                    <span className="wl-demo-label">{row.label}</span>
                    <span className="wl-demo-hint num">{row.hint}</span>
                  </button>
                ) : (
                  // حساب تطبيق آخر: يُعرض للعلم لا للضغط. الضغط
                  // عليه هنا كان سيحاول دخولًا يفشل دائمًا.
                  <a
                    key={row.phone}
                    className="wl-demo-item wl-demo-item-other"
                    href={data.apps[key]}
                  >
                    <span className="wl-demo-label">{row.label}</span>
                    <span className="wl-demo-hint num">{row.hint}</span>
                  </a>
                ),
              )}
            </div>
          </section>
        );
      })}

      <p className="wl-demo-note">{data.notice}</p>
    </div>
  );
}
