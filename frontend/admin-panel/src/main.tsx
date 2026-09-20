import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { clearTokens, configureApi } from "@walaee/shared";

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

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
