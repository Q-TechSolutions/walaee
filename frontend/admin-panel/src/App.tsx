/**
 * لوحة إدارة المنصة.
 *
 * تعرض صحة الأعمال لا بيانات العملاء. المؤشر الذي يقود كل قرار
 * هنا هو **آخر نشاط لكل مؤسسة**: متجر توقّف عن التسجيل أسبوعين هو
 * متجر على وشك الإلغاء، واستدراكه أرخص من استعادته.
 */

import { useState } from "react";

import {
  Badge,
  Button,
  Empty,
  ErrorBox,
  Field,
  Loading,
  Modal,
  Stat,
  clearTokens,
  fmt,
  isAuthenticated,
  useAction,
  useApi,
  writeTokens,
} from "@walaee/shared";

import { actions, queries } from "./lib/queries";
import type { MerchantRow, UnpaidInvoice } from "./lib/queries";

type Tab = "overview" | "merchants" | "invoices";

const TABS: { key: Tab; label: string }[] = [
  { key: "overview", label: "نظرة عامة" },
  { key: "merchants", label: "المتاجر" },
  { key: "invoices", label: "الفواتير" },
];

export function App() {
  const [authed, setAuthed] = useState(isAuthenticated());
  const [tab, setTab] = useState<Tab>("overview");

  if (!authed) return <Login onDone={() => setAuthed(true)} />;

  return (
    <div className="admin">
      <header className="admin-hd">
        <div className="row" style={{ gap: 10 }}>
          <span className="admin-mark" aria-hidden="true">
            ♥
          </span>
          <div>
            <p className="w-8">إدارة المنصة</p>
            <p className="t-xs muted">ولائي</p>
          </div>
        </div>

        <nav className="range-switch" role="tablist">
          {TABS.map((option) => (
            <button
              key={option.key}
              type="button"
              role="tab"
              aria-selected={tab === option.key}
              className={tab === option.key ? "active" : ""}
              onClick={() => setTab(option.key)}
            >
              {option.label}
            </button>
          ))}
        </nav>

        <button
          type="button"
          className="link"
          onClick={() => {
            clearTokens();
            setAuthed(false);
          }}
        >
          خروج
        </button>
      </header>

      <main className="admin-body">
        {tab === "overview" && <Overview />}
        {tab === "merchants" && <Merchants />}
        {tab === "invoices" && <Invoices />}
      </main>
    </div>
  );
}

function Login({ onDone }: { onDone: () => void }) {
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
            writeTokens({ access: session.access, refresh: session.refresh });
            onDone();
          }
        }}
      >
        <div className="auth-brand">
          <div className="auth-mark" aria-hidden="true">
            ♥
          </div>
          <h1>إدارة المنصة</h1>
          <p className="t-sm muted">لفريق ولائي فقط</p>
        </div>

        <Field label="رقم الهاتف">
          <input
            className="input num"
            type="tel"
            autoComplete="username"
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

const PLAN_LABELS: Record<string, string> = {
  free: "مجانية",
  starter: "أساسية",
  growth: "نمو",
  chain: "سلاسل",
};

function Overview() {
  const data = useApi((signal) => queries.overview(signal), []);

  if (data.loading) return <Loading />;
  if (data.error != null)
    return <ErrorBox error={data.error} onRetry={data.reload} />;
  if (!data.data) return null;

  const board = data.data;

  return (
    <div className="stack gap-lg">
      <section className="mrr">
        <p className="t-sm">الإيراد الشهري المتكرّر</p>
        <p className="mrr-value num">{fmt.money(board.mrr)}</p>
        <p className="t-sm">
          <span className="num">{board.organizations.paying}</span> مؤسسة مشتركة
          من <span className="num">{board.organizations.total}</span>
          {board.organizations.past_due > 0 && (
            <>
              {" · "}
              <span className="num">{board.organizations.past_due}</span> متأخرة
              السداد
            </>
          )}
        </p>
      </section>

      <div className="stats-grid">
        <Stat label="العلامات" value={fmt.number(board.brands)} />
        <Stat label="الفروع" value={fmt.number(board.branches)} />
        <Stat
          label="العملاء"
          value={fmt.number(board.customers.total)}
          hint={`${fmt.number(board.customers.new_30d)} جديد في ٣٠ يومًا`}
        />
        <Stat label="العضويات" value={fmt.number(board.memberships)} />
        <Stat
          label="العمليات — ٣٠ يومًا"
          value={fmt.number(board.transactions_30d)}
        />
        <Stat
          label="قيمة المبيعات — ٣٠ يومًا"
          value={fmt.money(board.gmv_30d)}
          hint="إجمالي فواتير المتاجر لا إيراد المنصة"
        />
        <Stat label="القيود — ٣٠ يومًا" value={fmt.number(board.entries_30d)} />
        <Stat
          label="فواتير غير مسدّدة"
          value={fmt.number(board.unpaid_invoices)}
          tone={board.unpaid_invoices > 0 ? "warn" : "good"}
        />
      </div>

      <section className="card wl-card-p stack gap">
        <h2>التوزيع على الباقات</h2>
        {Object.entries(board.by_plan).map(([plan, count]) => (
          <div key={plan} className="row between t-sm">
            <span>{PLAN_LABELS[plan] ?? plan}</span>
            <span className="num w-7">{fmt.number(count)}</span>
          </div>
        ))}
      </section>

      <p className="t-xs faint">
        لا تعرض هذه اللوحة بيانات شراء أي فرد. بيانات العملاء ملك التاجر
        وعميله، والمنصة وسيط — راجع مصفوفة الأدوار في التوثيق.
      </p>
    </div>
  );
}

/** عدد الأيام منذ آخر نشاط، أو null إن لم يوجد نشاط قط. */
function daysSince(value: string | null): number | null {
  if (!value) return null;
  return Math.floor((Date.now() - new Date(value).getTime()) / 86_400_000);
}

function Merchants() {
  const merchants = useApi((signal) => queries.merchants(signal), []);

  if (merchants.loading) return <Loading />;
  if (merchants.error != null)
    return <ErrorBox error={merchants.error} onRetry={merchants.reload} />;

  if (merchants.data?.length === 0) {
    return <Empty icon="◻" title="لا توجد مؤسسات بعد" />;
  }

  return (
    <div className="stack gap">
      <div className="notice">
        «آخر نشاط» هو مؤشر الخطر الأول: مؤسسة بلا عملية منذ أسبوعين على وشك
        الإلغاء، والتدخل قبل ذلك أرخص من استعادتها.
      </div>

      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr>
              <th>المؤسسة</th>
              <th>الباقة</th>
              <th>الإيراد</th>
              <th>عمليات ٣٠ يومًا</th>
              <th>آخر نشاط</th>
            </tr>
          </thead>
          <tbody>
            {merchants.data?.map((row) => (
              <MerchantRowView key={row.id} row={row} />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function MerchantRowView({ row }: { row: MerchantRow }) {
  const idle = daysSince(row.last_activity);
  const atRisk = idle === null || idle >= 14;

  return (
    <tr className={atRisk ? "row-risk" : ""}>
      <td>
        <p className="w-7">{row.name}</p>
        <p className="t-xs muted">{row.brand_names.join("، ") || "بلا علامات"}</p>
      </td>
      <td>
        <Badge tone={row.plan === "free" ? "muted" : "violet"}>
          {row.plan_label}
        </Badge>
        {row.subscription_status === "past_due" && (
          <Badge tone="red">متأخرة</Badge>
        )}
      </td>
      <td className="num">{fmt.money(row.mrr)}</td>
      <td className="num">{fmt.number(row.transactions_30d)}</td>
      <td>
        {row.last_activity ? (
          <span className={atRisk ? "c-red" : ""}>
            {fmt.relativeTime(row.last_activity)}
          </span>
        ) : (
          <span className="c-red">لا نشاط إطلاقًا</span>
        )}
      </td>
    </tr>
  );
}

function Invoices() {
  const invoices = useApi((signal) => queries.invoices(signal), []);
  const [paying, setPaying] = useState<UnpaidInvoice | null>(null);

  if (invoices.loading) return <Loading />;
  if (invoices.error != null)
    return <ErrorBox error={invoices.error} onRetry={invoices.reload} />;

  if (invoices.data?.length === 0) {
    return (
      <Empty icon="✓" title="كل الفواتير مسدّدة" hint="لا شيء يحتاج متابعة." />
    );
  }

  return (
    <div className="stack gap">
      <div className="notice">
        السداد بالتحويل البنكي يُعلَّم يدويًا بعد مطابقة كشف الحساب — وهذا
        ما يستخدمه عملاء المنصة الأوائل فعلًا.
      </div>

      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr>
              <th>الفاتورة</th>
              <th>المؤسسة</th>
              <th>المبلغ</th>
              <th>صدرت</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {invoices.data?.map((invoice) => (
              <tr key={invoice.id}>
                <td className="num">{invoice.number}</td>
                <td>{invoice.organization}</td>
                <td className="num">{fmt.money(invoice.amount)}</td>
                <td className="t-sm muted">{fmt.date(invoice.issued_at)}</td>
                <td>
                  <button
                    type="button"
                    className="link"
                    onClick={() => setPaying(invoice)}
                  >
                    تعليم كمسدّدة
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <MarkPaidModal
        invoice={paying}
        onClose={() => setPaying(null)}
        onDone={() => {
          setPaying(null);
          invoices.reload();
        }}
      />
    </div>
  );
}

function MarkPaidModal({
  invoice,
  onClose,
  onDone,
}: {
  invoice: UnpaidInvoice | null;
  onClose: () => void;
  onDone: () => void;
}) {
  const [reference, setReference] = useState("");
  const mark = useAction(actions.markPaid);

  if (!invoice) return null;

  return (
    <Modal
      open
      title={`سداد ${invoice.number}`}
      onClose={onClose}
      footer={
        <>
          <Button
            loading={mark.loading}
            disabled={!reference.trim()}
            onClick={async () => {
              const done = await mark.run(invoice.id, reference.trim());
              if (done) {
                setReference("");
                onDone();
              }
            }}
          >
            تأكيد السداد
          </Button>
          <Button variant="ghost" onClick={onClose}>
            تراجع
          </Button>
        </>
      }
    >
      <div className="stack gap">
        <div className="row between">
          <span>{invoice.organization}</span>
          <span className="num w-7">{fmt.money(invoice.amount)}</span>
        </div>

        <Field
          label="مرجع التحويل"
          hint="رقم العملية في كشف الحساب — يُحفظ للمراجعة"
        >
          <input
            className="input num"
            value={reference}
            onChange={(e) => setReference(e.target.value)}
            autoFocus
          />
        </Field>

        {mark.error != null && <ErrorBox error={mark.error} />}
      </div>
    </Modal>
  );
}
