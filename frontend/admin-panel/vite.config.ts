import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

import { devProxy, sharedAliases } from "../vite.shared";

// راجع التعليق في merchant-dashboard/vite.config.ts
const BASE = process.env.VITE_BASE ?? "/admin/";

export default defineConfig({
  base: BASE,
  plugins: [react()],
  resolve: { alias: sharedAliases(import.meta.url) },
  server: { port: 5175, proxy: devProxy },
});
