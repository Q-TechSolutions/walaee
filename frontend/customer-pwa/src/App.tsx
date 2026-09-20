import { Navigate, Route, Routes, useLocation } from "react-router-dom";

import { isAuthenticated } from "@walaee/shared";

import { TabBar } from "./components/TabBar";
import { Activity } from "./pages/Activity";
import { CardDetail } from "./pages/CardDetail";
import { Cards } from "./pages/Cards";
import { Login } from "./pages/Login";
import { Profile } from "./pages/Profile";
import { Rewards } from "./pages/Rewards";
import { Scan } from "./pages/Scan";
import { Stores } from "./pages/Stores";

/**
 * حارس المسارات.
 *
 * يفحص وجود توكن لا صلاحيته: التحقق الحقيقي في الخلفية، وأي فحص
 * هنا يستطيع المستخدم تزويره. الغرض تجربة مستخدم — ألا تظهر شاشة
 * فارغة ثم تُعيد التوجيه بعد أول نداء فاشل.
 */
function Guard({ children }: { children: React.ReactNode }) {
  const location = useLocation();

  if (!isAuthenticated()) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  return <>{children}</>;
}

export function App() {
  const location = useLocation();
  const onLogin = location.pathname.startsWith("/login");

  return (
    <div className="app">
      <main className={onLogin ? "" : "app-main"}>
        <Routes>
          <Route path="/login" element={<Login />} />

          <Route
            path="/"
            element={
              <Guard>
                <Cards />
              </Guard>
            }
          />
          <Route
            path="/cards/:brandId"
            element={
              <Guard>
                <CardDetail />
              </Guard>
            }
          />
          <Route
            path="/scan"
            element={
              <Guard>
                <Scan />
              </Guard>
            }
          />
          <Route
            path="/rewards"
            element={
              <Guard>
                <Rewards />
              </Guard>
            }
          />
          <Route
            path="/activity"
            element={
              <Guard>
                <Activity />
              </Guard>
            }
          />
          <Route
            path="/stores"
            element={
              <Guard>
                <Stores />
              </Guard>
            }
          />
          <Route
            path="/profile"
            element={
              <Guard>
                <Profile />
              </Guard>
            }
          />

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>

      {!onLogin && <TabBar />}
    </div>
  );
}
