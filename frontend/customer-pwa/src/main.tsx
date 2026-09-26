import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";

import { LocaleBoundary, applyPreferences, configureApi, hardRedirect, isAt } from "@walaee/shared";

import "@walaee/shared/tokens.css";
import "@walaee/shared/base.css";
import "@walaee/shared/components.css";
import "./styles.css";

import { App } from "./App";

/**
 * انتهاء الجلسة يعيد إلى شاشة الدخول.
 *
 * `replace` لا `assign`: ترك شاشة منتهية الصلاحية في تاريخ التصفّح
 * يعني أن زر الرجوع يعيد المستخدم إليها فيرى بيانات لا يملكها.
 */
configureApi({
  // يفصل تخزين التوكن عن التطبيقين الآخرين على نفس الأصل
  appId: "customer",
  onUnauthenticated: () => {
    if (!isAt("/login")) {
      hardRedirect("/login");
    }
  },
});

/**
 * التفضيلات قبل أول رسم.
 *
 * `applyPreferences` يكتب `lang` و`dir` و`data-theme` على جذر
 * المستند من المحفوظ في هذا المتصفّح. تأجيلها إلى ما بعد التركيب
 * كان يُظهر ومضة بالوضع الخاطئ — كافية لتبدو الصفحة معطوبة على
 * جهاز مضبوط على الداكن.
 */
applyPreferences();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    {/* يجب أن يطابق `base` في vite.config.ts — راجع التعليق هناك */}
    <BrowserRouter basename={import.meta.env.BASE_URL}>
      <LocaleBoundary>
        <App />
      </LocaleBoundary>
    </BrowserRouter>
  </StrictMode>,
);
