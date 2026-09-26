/**
 * لوحة إدارة المنصة.
 *
 * تعرض صحة الأعمال لا بيانات العملاء. المؤشر الذي يقود كل قرار
 * هنا هو **آخر نشاط لكل مؤسسة**: متجر توقّف عن التسجيل أسبوعين هو
 * متجر على وشك الإلغاء، واستدراكه أرخص من استعادته.
 */

import { useState } from "react";

import {
  AuthLayout,
  AuthPoint,
  Badge,
  Button,
  DemoAccountsPanel,
  Empty,
  ErrorBox,
  Field,
  Icon,
  Loading,
  LogoMark,
  Modal,
  PreferenceBar,
  clearTokens,
  fetchNetwork,
  fmt,
  isAuthenticated,
  t,
  useAction,
  useApi,
  writeTokens,
} from "@walaee/shared";

import { Config } from "./pages/Config";
import { Health } from "./pages/Health";
import { Ops } from "./pages/Ops";
import { Users } from "./pages/Users";

import { actions, queries } from "./lib/queries";
import type { MerchantRow, UnpaidInvoice } from "./lib/queries";
import type { IconName } from "@walaee/shared";

type Tab =
  | "overview"
  | "health"
  | "merchants"
  | "invoices"
  | "users"
  | "ops"
  | "config";

interface NavItem {
  key: Tab;
  label: string;
  title: string;
  crumb: string;
  icon: IconName;
}

interface NavGroup {
  title: string;
  items: NavItem[];
}

/**
 * التنقّل مجمَّعًا — نفس هيكل لوحة التاجر.
 *
 * التطابق مقصود: من يعمل في فريق المنصة يفتح لوحة التاجر أيضًا
 * ليتابع شكوى أو يشرح ميزة، واختلاف الهيكل بين الاثنين يجعله
 * يبحث عن كل شيء مرتين.
 */
const NAV: NavGroup[] = [
  {
    title: "المنصة",
    items: [
      {
        key: "overview",
        label: "نظرة عامة",
        title: "نظرة عامة",
        crumb: "أداء المنصة بالكامل",
        icon: "chart",
      },
      {
        key: "health",
        label: "مؤشرات الصحة",
        title: "مؤشرات الصحة",
        crumb: "كل مؤشر مقابل هدفه",
        icon: "target",
      },
    ],
  },
  {
    title: "الإدارة",
    items: [
      {
        key: "merchants",
        label: "المتاجر",
        title: "المتاجر",
        crumb: "المؤسسات المشتركة وآخر نشاط لكل واحدة",
        icon: "store",
      },
      {
        key: "invoices",
        label: "الاشتراكات والفواتير",
        title: "الاشتراكات والفواتير",
        crumb: "ما لم يُسدَّد بعد",
        icon: "receipt",
      },
      {
        key: "users",
        label: "المستخدمون",
        title: "المستخدمون والصلاحيات",
        crumb: "من يملك صلاحية على ماذا",
        icon: "users",
      },
    ],
  },
  {
    title: "التشغيل",
    items: [
      {
        key: "ops",
        label: "التشغيل والمراقبة",
        title: "التشغيل والمراقبة",
        crumb: "الخدمات والمهام الدورية وسلامة الأرصدة",
        icon: "bolt",
      },
      {
        key: "config",
        label: "إعدادات المنصة",
        title: "إعدادات المنصة",
        crumb: "الامتثال ونموذج النقاط والباقات",
        icon: "settings",
      },
    ],
  },
];

const ALL_ITEMS = NAV.flatMap((group) => group.items);

export function App() {
  const [authed, setAuthed] = useState(isAuthenticated());
  const [tab, setTab] = useState<Tab>("overview");

  if (!authed) return <Login onDone={() => setAuthed(true)} />;

  const page = ALL_ITEMS.find((item) => item.key === tab) ?? ALL_ITEMS[0]!;

  return (
    <div className="shell">
      <aside className="side side-admin">
        <div className="side-brand">
          <LogoMark size={34} inverted />
          <div className="grow">
            <p className="side-brand-name">{t("ولائي")}</p>
            <p className="side-brand-sub">{t("لوحة إدارة المنصة")}</p>
          </div>
        </div>

        <nav>
          {NAV.map((group) => (
            <div key={group.title}>
              <p className="grp-t">{t(group.title)}</p>
              {group.items.map((item) => (
                <button
                  key={item.key}
                  type="button"
                  role="tab"
                  aria-selected={tab === item.key}
                  className={`nav-i ${tab === item.key ? "on" : ""}`}
                  onClick={() => setTab(item.key)}
                >
                  <Icon name={item.icon} size={18} />
                  <span>{t(item.label)}</span>
                </button>
              ))}
            </div>
          ))}
        </nav>

        <div className="side-foot">
          <span className="av av-sm" aria-hidden="true">
            <Icon name="shield" size={15} />
          </span>
          <div className="grow">
            <p className="t-sm w-7">{t("فريق ولائي")}</p>
            <p className="t-xs">{t("إدارة المنصة")}</p>
          </div>
          <button
            type="button"
            className="iconbtn-dark"
            aria-label={t("تسجيل الخروج")}
            onClick={() => {
              clearTokens();
              setAuthed(false);
            }}
          >
            <Icon name="logout" size={17} />
          </button>
        </div>
      </aside>

      <div className="main">
        <header className="topnav">
          <div className="grow">
            <h1>{t(page.title)}</h1>
            <p className="crumb">{t(page.crumb)}</p>
          </div>
          <PreferenceBar />
        </header>

        <main className="content">
          {tab === "overview" && <Overview />}
          {tab === "health" && <Health />}
          {tab === "merchants" && <Merchants />}
          {tab === "invoices" && <Invoices />}
          {tab === "users" && <Users />}
          {tab === "ops" && <Ops />}
          {tab === "config" && <Config />}
        </main>
      </div>
    </div>
  );
}

/**
 * دخول فريق المنصة — نصفان مثل بقية التطبيقات.
 *
 * لوح الهوية هنا يعرض حجم الشبكة الفعلي لا وعدًا تسويقيًا: هذه
 * شاشة داخلية، ومن يفتحها يريد أن يعرف حالة المنصة قبل أن يدخل.
 */
function Login({ onDone }: { onDone: () => void }) {
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const login = useAction(actions.login);
  const network = useApi((signal) => fetchNetwork(signal), []);

  async function signIn(phoneValue: string, passwordValue: string) {
    const session = await login.run(phoneValue.trim(), passwordValue);
    if (session) {
      writeTokens({ access: session.access, refresh: session.refresh });
      onDone();
    }
  }

  const stats = network.data?.stats;

  return (
    <AuthLayout
      badge={t("إدارة المنصة")}
      headline={t("حالة الشبكة في لوحة واحدة")}
      subline={t("الإيراد المتكرّر، والمتاجر المتوقّفة عن النشاط، والفواتير المتأخرة — قبل أن تتحوّل إلى إلغاءات.")}
      aside={
        <ul>
          <AuthPoint title={t("الشبكة الآن")}>
            {stats
              ? t("{brands} متجرًا · {branches} فرعًا · {govs} محافظة", {
                  brands: fmt.number(stats.brands),
                  branches: fmt.number(stats.branches),
                  govs: fmt.number(stats.governorates),
                })
              : t("الأرقام تُحمَّل من الدليل العام.")}
          </AuthPoint>
          <AuthPoint title={t("آخر نشاط لكل مؤسسة")}>
            {t("متجر توقّف أسبوعين هو متجر على وشك الإلغاء — واستدراكه أرخص من استعادته.")}
          </AuthPoint>
          <AuthPoint title={t("بيانات أعمال لا بيانات عملاء")}>
            {t("هذه اللوحة لا ترى أرصدة العملاء ولا عملياتهم.")}
          </AuthPoint>
        </ul>
      }
      footer={
        <DemoAccountsPanel
          app="admin"
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
        <h2>{t("دخول الفريق")}</h2>
        <p className="auth-lede">
          {t("هذه الشاشة لفريق ولائي وحده. حسابات التجّار والعملاء لا تعمل هنا.")}
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
      </form>
    </AuthLayout>
  );
}

/**
 * بطاقة مؤشر — نفس مكوّن لوحة التاجر شكلًا.
 *
 * بلا رسم مصغّر هنا: لوحة المنصة لا تملك سلسلة زمنية لكل مؤشر،
 * ورسم خطّ من نقطتين يوحي باتجاه لا تسنده بيانات.
 */
function AdminKpi({
  tone,
  icon,
  label,
  value,
  sub,
}: {
  tone: "v" | "g" | "o" | "r" | "b" | "a";
  icon: IconName;
  label: string;
  value: string;
  sub: string;
}) {
  return (
    <article className="kpi">
      <div className="row between">
        <div className="grow">
          <p className="kt">{label}</p>
          <p className="kv num">{value}</p>
          <p className="ks">{sub}</p>
        </div>
        <span className={`ibox ${tone}`} aria-hidden="true">
          <Icon name={icon} size={20} />
        </span>
      </div>
    </article>
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
        <p className="t-sm">{t("الإيراد الشهري المتكرّر")}</p>
        <p className="mrr-value num">{fmt.money(board.mrr)}</p>
        <p className="t-sm">
          <span className="num">{fmt.number(board.organizations.paying)}</span>{" "}
          {t("مؤسسة مشتركة من")}{" "}
          <span className="num">{fmt.number(board.organizations.total)}</span>
          {board.organizations.past_due > 0 && (
            <>
              {" · "}
              <span className="num">
                {fmt.number(board.organizations.past_due)}
              </span>{" "}
              {t("متأخرة السداد")}
            </>
          )}
        </p>
      </section>

      <div className="grid g3">
        <AdminKpi
          tone="v"
          icon="store"
          label={t("العلامات المفعّلة")}
          value={fmt.number(board.brands)}
          sub={t("{n} فرعًا", { n: fmt.number(board.branches) })}
        />
        <AdminKpi
          tone="b"
          icon="users"
          label={t("عملاء نهائيون")}
          value={fmt.number(board.customers.total)}
          sub={t("{n} جديد في ٣٠ يومًا", {
            n: fmt.number(board.customers.new_30d),
          })}
        />
        <AdminKpi
          tone="g"
          icon="card"
          label={t("العضويات")}
          value={fmt.number(board.memberships)}
          sub={t("بطاقة نشطة عبر كل العلامات")}
        />
        <AdminKpi
          tone="a"
          icon="receipt"
          label={t("العمليات — ٣٠ يومًا")}
          value={fmt.number(board.transactions_30d)}
          sub={t("{n} قيدًا في الدفتر", { n: fmt.number(board.entries_30d) })}
        />
        <AdminKpi
          tone="o"
          icon="coins"
          label={t("قيمة المبيعات — ٣٠ يومًا")}
          value={fmt.money(board.gmv_30d)}
          sub={t("إجمالي فواتير المتاجر لا إيراد المنصة")}
        />
        <AdminKpi
          tone={board.unpaid_invoices > 0 ? "r" : "g"}
          icon="alert"
          label={t("فواتير غير مسدّدة")}
          value={fmt.number(board.unpaid_invoices)}
          sub={board.unpaid_invoices > 0 ? t("تحتاج متابعة") : t("لا شيء متأخر")}
        />
      </div>

      <section className="card">
        <div className="card-hd">
          <h3>{t("التوزيع على الباقات")}</h3>
        </div>
        <div className="card-p stack gap">
          {Object.entries(board.by_plan).map(([plan, count]) => {
            const total = Object.values(board.by_plan).reduce(
              (sum, n) => sum + n,
              0,
            );
            const share = total > 0 ? (count / total) * 100 : 0;
            return (
              <div key={plan} className="usage">
                <span className="t-sm w-7" style={{ width: "5.5rem" }}>
                  {t(PLAN_LABELS[plan] ?? plan)}
                </span>
                <span className="bar">
                  <i style={{ width: `${Math.max(share, 2)}%` }} />
                </span>
                <span className="t-sm num w-7">{fmt.number(count)}</span>
              </div>
            );
          })}
        </div>
      </section>

      <p className="t-xs faint">
        {t("لا تعرض هذه اللوحة بيانات شراء أي فرد. بيانات العملاء ملك التاجر وعميله، والمنصة وسيط — راجع مصفوفة الأدوار في التوثيق.")}
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
    return <Empty icon="building" title={t("لا توجد مؤسسات بعد")} />;
  }

  return (
    <div className="stack gap">
      <div className="notice">
        {t("«آخر نشاط» هو مؤشر الخطر الأول: مؤسسة بلا عملية منذ أسبوعين على وشك الإلغاء، والتدخل قبل ذلك أرخص من استعادتها.")}
      </div>

      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr>
              <th>{t("المؤسسة")}</th>
              <th>{t("الباقة")}</th>
              <th>{t("الإيراد")}</th>
              <th>{t("عمليات ٣٠ يومًا")}</th>
              <th>{t("آخر نشاط")}</th>
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
        <p className="t-xs muted">{row.brand_names.join(t("، ")) || t("بلا علامات")}</p>
      </td>
      <td>
        <Badge tone={row.plan === "free" ? "muted" : "violet"}>
          {t(row.plan_label)}
        </Badge>
        {row.subscription_status === "past_due" && (
          <Badge tone="red">{t("متأخرة")}</Badge>
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
          <span className="c-red">{t("لا نشاط إطلاقًا")}</span>
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
      <Empty icon="checkCircle" title={t("كل الفواتير مسدّدة")} hint={t("لا شيء يحتاج متابعة.")} />
    );
  }

  return (
    <div className="stack gap">
      <div className="notice">
        {t("السداد بالتحويل البنكي يُعلَّم يدويًا بعد مطابقة كشف الحساب — وهذا ما يستخدمه عملاء المنصة الأوائل فعلًا.")}
      </div>

      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr>
              <th>{t("الفاتورة")}</th>
              <th>{t("المؤسسة")}</th>
              <th>{t("المبلغ")}</th>
              <th>{t("صدرت")}</th>
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
                    {t("تعليم كمسدّدة")}
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
      title={t("سداد {number}", { number: invoice.number })}
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
            {t("تأكيد السداد")}
          </Button>
          <Button variant="ghost" onClick={onClose}>
            {t("تراجع")}
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
          label={t("مرجع التحويل")}
          hint={t("رقم العملية في كشف الحساب — يُحفظ للمراجعة")}
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
