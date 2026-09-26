import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { LocaleBoundary, applyPreferences, clearTokens, configureApi } from "@walaee/shared";

import "@walaee/shared/tokens.css";
import "@walaee/shared/base.css";
import "@walaee/shared/components.css";
import "./styles.css";

import { App } from "./App";

configureApi({
  // يفصل تخزين التوكن عن التطبيقين الآخرين على نفس الأصل
  appId: "admin",
  onUnauthenticated: () => {
    clearTokens();
    window.location.reload();
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
    <LocaleBoundary>
        <App />
      </LocaleBoundary>
  </StrictMode>,
);
