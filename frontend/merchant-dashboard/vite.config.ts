import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

import { devProxy, sharedAliases } from "../vite.shared";

export default defineConfig({
  plugins: [react()],
  resolve: { alias: sharedAliases(import.meta.url) },
  server: { port: 5174, proxy: devProxy },
});
