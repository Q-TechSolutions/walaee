import { NavLink, Navigate, Route, Routes, useLocation } from "react-router-dom";

import { isAuthenticated } from "@walaee/shared";

import { activeRole, atLeast, endSession, readSession } from "./lib/session";
import type { Role } from "./lib/session";
import { Campaigns } from "./pages/Campaigns";
import { Cashier } from "./pages/Cashier";
import { Customers } from "./pages/Customers";
import { Dashboard } from "./pages/Dashboard";
import { Fraud } from "./pages/Fraud";
import { Login } from "./pages/Login";
import { Programs } from "./pages/Programs";
import { Settings } from "./pages/Settings";

interface NavItem {
  to: string;
  label: string;
  icon: string;
  minRole: Role;
}

/**
 * التنقّل حسب الدور.
 *
 * الكاشير يرى عنصرًا واحدًا: شاشته. إخفاء ما لا يستطيع فتحه ليس
 * أمانًا — الخلفية تفرض ذلك — بل احترام لوقته: قائمة من ثمانية
 * عناصر كلها مرفوضة إلا واحد هي قائمة سيئة.
 */
const NAV: NavItem[] = [
  { to: "/cashier", label: "شاشة الكاشير", icon: "▣", minRole: "cashier" },
  { to: "/", label: "نظرة عامة", icon: "◧", minRole: "manager" },
  { to: "/customers", label: "العملاء", icon: "◉", minRole: "manager" },
  { to: "/campaigns", label: "الحملات", icon: "✉", minRole: "manager" },
  { to: "/programs", label: "البرامج", icon: "◈", minRole: "manager" },
  { to: "/fraud", label: "المراجعة", icon: "⚠", minRole: "owner" },
  { to: "/settings", label: "الإعدادات", icon: "☰", minRole: "owner" },
];

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
  const visible = NAV.filter((item) => atLeast(item.minRole));

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <span className="sidebar-mark" aria-hidden="true">
            ♥
          </span>
          <div>
            <p className="w-8">{role?.brand_name ?? "ولائي"}</p>
            <p className="t-xs muted">{role?.branch_name}</p>
          </div>
        </div>

        <nav className="sidebar-nav">
          {visible.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) =>
                `sidebar-link ${isActive ? "active" : ""}`
              }
            >
              <span aria-hidden="true">{item.icon}</span>
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-foot">
          <p className="t-sm w-7">{session?.user.full_name}</p>
          <p className="t-xs muted">{role?.role_label}</p>
          <button
            type="button"
            className="link"
            onClick={() => {
              endSession();
              window.location.replace("/login");
            }}
          >
            تسجيل الخروج
          </button>
        </div>
      </aside>

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
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}
