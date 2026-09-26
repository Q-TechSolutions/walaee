import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { LocaleBoundary, applyPreferences, configureApi } from "@walaee/shared";

import "@walaee/shared/tokens.css";
import "@walaee/shared/base.css";
import "@walaee/shared/components.css";
import "./styles.css";

import { App } from "./App";

/**
 * الصفحة العامة لا تسجّل دخول أحد ولا تحمل توكنًا.
 *
 * `appId` مضبوط رغم ذلك: لو لم يُضبط لاستخدمت المكتبة المساحة
 * الافتراضية `walaee.tokens.app`، وهي مساحة لا يملكها تطبيق بعينه
 * فتصير أرضًا مشاعًا تلتقط ما يكتبه غيرها.
 */
configureApi({ appId: "public" });

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
