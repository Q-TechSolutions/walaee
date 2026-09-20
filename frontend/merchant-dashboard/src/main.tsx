import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";

import { configureApi, hardRedirect, isAt } from "@walaee/shared";

import "@walaee/shared/tokens.css";
import "@walaee/shared/base.css";
import "@walaee/shared/components.css";
import "./styles.css";

import { App } from "./App";
import { endSession } from "./lib/session";

configureApi({
  // يفصل تخزين التوكن عن التطبيقين الآخرين على نفس الأصل
  appId: "merchant",
  onUnauthenticated: () => {
    endSession();
    if (!isAt("/login")) {
      hardRedirect("/login");
    }
  },
});

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    {/* BASE_URL يأتي من Vite ويطابق `base` في إعداده */}
    <BrowserRouter basename={import.meta.env.BASE_URL}>
      <App />
    </BrowserRouter>
  </StrictMode>,
);
