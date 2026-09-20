import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

import { devProxy, sharedAliases } from "../vite.shared";

// تُخدَم تحت مسار فرعي على نفس الدومين. `base` و `basename` في
// الموجّه يجب أن يتطابقا: تغيير أحدهما وحده يعطي صفحة بيضاء بلا
// أي خطأ في السجل — وهو أصعب عطل نشر يُشخَّص.
const BASE = process.env.VITE_BASE ?? "/merchant/";

export default defineConfig({
  base: BASE,
  plugins: [react()],
  resolve: { alias: sharedAliases(import.meta.url) },
  server: { port: 5174, proxy: devProxy },
});
