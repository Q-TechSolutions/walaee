import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";

import { configureApi, hardRedirect, isAt } from "@walaee/shared";

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

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>,
);
