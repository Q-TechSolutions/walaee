import { NavLink, Navigate, Route, Routes, useLocation } from "react-router-dom";

import { Icon, LogoMark, PreferenceBar, hardRedirect, isAuthenticated, t } from "@walaee/shared";
import type { IconName } from "@walaee/shared";

import {
  activeRole,
  atLeast,
  endSession,
  readSession,
  setActiveRole,
} from "./lib/session";
import type { Role } from "./lib/session";
import { Campaigns } from "./pages/Campaigns";
import { Cashier } from "./pages/Cashier";
import { Customers } from "./pages/Customers";
import { Dashboard } from "./pages/Dashboard";
import { Fraud } from "./pages/Fraud";
import { Login } from "./pages/Login";
import { Branches } from "./pages/Branches";
import { Billing } from "./pages/Billing";
import { Programs } from "./pages/Programs";
import { Reports } from "./pages/Reports";
import { Rewards } from "./pages/Rewards";
import { Settings } from "./pages/Settings";

interface NavItem {
  to: string;
  label: string;
  title: string;
  crumb: string;
  icon: IconName;
  minRole: Role;
}

interface NavGroup {
  title: string;
  items: NavItem[];
}

/**
 * التنقّل حسب الدور، مجمَّعًا حسب الغرض.
 *
 * الكاشير يرى عنصرًا واحدًا: شاشته. إخفاء ما لا يستطيع فتحه ليس
 * أمانًا — الخلفية تفرض ذلك — بل احترام لوقته: قائمة من ثمانية
 * عناصر كلها مرفوضة إلا واحد هي قائمة سيئة.
 *
 * والتجميع ليس ترتيبًا جماليًا: المالك يفتح اللوحة بسؤال في ذهنه
 * («إيه اللي حصل النهاردة؟» أو «أظبط برنامجي إزاي؟»)، والعناوين
 * تنقله إلى القسم بلا قراءة كل العناصر.
 *
 * `title` و`crumb` يعيشان مع الصفحة لا داخلها: الشريط العلوي
 * يعرضهما، وتكرارهما في كل شاشة كان يجعل عنوانًا يتغيّر في مكان
 * وينسى في آخر.
 */
const NAV: NavGroup[] = [
  {
    title: "التشغيل اليومي",
    items: [
      {
        to: "/",
        label: "لوحة المعلومات",
        title: "لوحة المعلومات",
        crumb: "نظرة سريعة على أداء برنامج الولاء",
        icon: "chart",
        minRole: "manager",
      },
      {
        to: "/cashier",
        label: "وضع الكاشير",
        title: "وضع الكاشير",
        crumb: "الشاشة التي تعمل عند نقطة البيع",
        icon: "qr",
        minRole: "cashier",
      },
      {
        to: "/customers",
        label: "العملاء",
        title: "العملاء",
        crumb: "قاعدة عملائك وشرائحهم",
        icon: "users",
        minRole: "manager",
      },
    ],
  },
  {
    title: "برنامج الولاء",
    items: [
      {
        to: "/programs",
        label: "إعداد البرنامج",
        title: "إعداد برنامج الولاء",
        crumb: "اختر النموذج واضبط قواعده",
        icon: "star",
        minRole: "manager",
      },
      {
        to: "/rewards",
        label: "المكافآت",
        title: "المكافآت",
        crumb: "ما الذي يحصل عليه عميلك",
        icon: "gift",
        minRole: "manager",
      },
      {
        to: "/campaigns",
        label: "الحملات",
        title: "الحملات",
        crumb: "تواصل مع شرائح محدّدة بتكلفة واضحة",
        icon: "message",
        minRole: "manager",
      },
    ],
  },
  {
    title: "التحليل والحوكمة",
    items: [
      {
        to: "/reports",
        label: "التقارير",
        title: "التقارير",
        crumb: "أثر برنامج الولاء على نشاطك",
        icon: "trendingUp",
        minRole: "manager",
      },
      {
        to: "/fraud",
        label: "المراجعة والاحتيال",
        title: "المراجعة والاحتيال",
        crumb: "ضوابط تحمي بياناتك وثقتك",
        icon: "shield",
        minRole: "owner",
      },
      {
        to: "/branches",
        label: "الفروع والكاشيرين",
        title: "الفروع والكاشيرين",
        crumb: "مؤسسة ← علامة ← فرع ← كاشير",
        icon: "building",
        minRole: "owner",
      },
    ],
  },
  {
    title: "الحساب",
    items: [
      {
        to: "/billing",
        label: "الاشتراك والفواتير",
        title: "الاشتراك والفواتير",
        crumb: "باقتك واستهلاكك",
        icon: "wallet",
        minRole: "owner",
      },
      {
        to: "/settings",
        label: "الإعدادات",
        title: "الإعدادات",
        crumb: "بيانات المتجر والخصوصية",
        icon: "settings",
        minRole: "owner",
      },
    ],
  },
];

const ALL_ITEMS = NAV.flatMap((group) => group.items);

/**
 * مبدّل الفرع/العلامة في ترويسة الشريط الجانبي.
 *
 * يظهر كقائمة فقط حين يملك الموظف أكثر من دور. الدور الواحد —
 * وهو الحال الغالب للكاشير — يُعرض كنص ثابت: زرّ قائمة بخيار
 * واحد يوحي بوجود ما يُختار ولا يوجد.
 *
 * التبديل يعيد تحميل الصفحة عمدًا. الأنظف نظريًا إبطال كل ما هو
 * مجلوب وإعادة جلبه، لكن كل شاشة هنا تحمل حالتها الخاصة (مرشّحات
 * ونطاقات زمنية وصفوف مفتوحة)، وتركها كما هي بعد تغيير العلامة
 * يعني لوحة تعرض مرشّح «فرع المعادي» فوق بيانات علامة أخرى.
 * إعادة التحميل تضمن أن كل ما على الشاشة من مصدر واحد.
 */
function BranchSwitcher() {
  const session = readSession();
  const role = activeRole();
  const roles = session?.roles ?? [];

  return (
    <div className="side-brand">
      <LogoMark size={34} inverted />

      <div className="grow">
        {roles.length > 1 ? (
          <>
            <label className="sr-only" htmlFor="branch-switch">
              {t("الفرع الحالي")}
            </label>
            <select
              id="branch-switch"
              className="branch-switch"
              value={role?.id ?? ""}
              onChange={(event) => {
                setActiveRole(event.target.value);
                window.location.reload();
              }}
            >
              {roles.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.brand_name} — {item.branch_name}
                </option>
              ))}
            </select>
          </>
        ) : (
          <p className="side-brand-name">{role?.brand_name ?? t("ولائي")}</p>
        )}

        {/* اسم الفرع تحت الاسم حين لا يوجد مبدّل. مع المبدّل يكون
            مذكورًا داخل الخيار نفسه، وتكراره يضيّق عرضًا ضيقًا
            أصلًا فيُقصّ الاسم في الاثنين معًا. */}
        {roles.length <= 1 && (
          <p className="side-brand-sub">{role?.branch_name}</p>
        )}
      </div>
    </div>
  );
}

function Guard({
  children,
  minRole,
}: {
  children: React.ReactNode;
  minRole: Role;
}) {
  const location = useLocation();

  if (!isAuthenticated()) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  if (!atLeast(minRole)) {
    // الكاشير يُحوَّل لشاشته بدل رسالة رفض: هي وجهته الوحيدة
    return <Navigate to="/cashier" replace />;
  }
  return <>{children}</>;
}

export function App() {
  const location = useLocation();

  if (location.pathname === "/login") {
    return <Login />;
  }

  if (!isAuthenticated()) {
    return <Navigate to="/login" replace />;
  }

  const session = readSession();
  const role = activeRole();

  // الصفحة الحالية تحدّد عنوان الشريط العلوي. الأطول مسارًا أولًا
  // حتى لا يبتلع «/» كل شيء.
  const page =
    [...ALL_ITEMS]
      .sort((a, b) => b.to.length - a.to.length)
      .find((item) =>
        item.to === "/"
          ? location.pathname === "/"
          : location.pathname.startsWith(item.to),
      ) ?? ALL_ITEMS[0]!;

  return (
    <div className="shell">
      <aside className="side">
        <BranchSwitcher />

        <nav>
          {NAV.map((group) => {
            const items = group.items.filter((item) => atLeast(item.minRole));
            if (items.length === 0) return null;

            return (
              <div key={group.title}>
                <p className="grp-t">{t(group.title)}</p>
                {items.map((item) => (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    end={item.to === "/"}
                    className={({ isActive }) => `nav-i ${isActive ? "on" : ""}`}
                  >
                    <Icon name={item.icon} size={18} />
                    <span>{t(item.label)}</span>
                  </NavLink>
                ))}
              </div>
            );
          })}
        </nav>

        <div className="side-foot">
          <span className="av av-sm" aria-hidden="true">
            {(session?.user.full_name ?? t("؟")).trim().charAt(0)}
          </span>
          <div className="grow">
            <p className="t-sm w-7">{session?.user.full_name}</p>
            <p className="t-xs">{t(role?.role_label ?? "")}</p>
          </div>
          <button
            type="button"
            className="iconbtn-dark"
            aria-label={t("تسجيل الخروج")}
            onClick={() => {
              endSession();
              hardRedirect("/login");
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
        <Routes>
          <Route
            path="/"
            element={
              <Guard minRole="manager">
                <Dashboard />
              </Guard>
            }
          />
          <Route
            path="/cashier"
            element={
              <Guard minRole="cashier">
                <Cashier />
              </Guard>
            }
          />
          <Route
            path="/customers"
            element={
              <Guard minRole="manager">
                <Customers />
              </Guard>
            }
          />
          <Route
            path="/campaigns"
            element={
              <Guard minRole="manager">
                <Campaigns />
              </Guard>
            }
          />
          <Route
            path="/programs"
            element={
              <Guard minRole="manager">
                <Programs />
              </Guard>
            }
          />
          <Route
            path="/fraud"
            element={
              <Guard minRole="owner">
                <Fraud />
              </Guard>
            }
          />
          <Route
            path="/settings"
            element={
              <Guard minRole="owner">
                <Settings />
              </Guard>
            }
          />
          <Route
            path="/rewards"
            element={
              <Guard minRole="manager">
                <Rewards />
              </Guard>
            }
          />
          <Route
            path="/reports"
            element={
              <Guard minRole="manager">
                <Reports />
              </Guard>
            }
          />
          <Route
            path="/branches"
            element={
              <Guard minRole="owner">
                <Branches />
              </Guard>
            }
          />
          <Route
            path="/billing"
            element={
              <Guard minRole="owner">
                <Billing />
              </Guard>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
        </main>
      </div>
    </div>
  );
}
