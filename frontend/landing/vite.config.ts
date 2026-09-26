import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

import { devProxy, sharedAliases } from "../vite.shared";

/**
 * الصفحة العامة تُخدَم من الجذر، وتطبيق العميل انتقل إلى `/app/`.
 *
 * السبب ليس ترتيبًا: الجذر هو ما يصل إليه من يسمع باسم المنصة
 * لأول مرة، ولا يجوز أن يستقبله نموذج دخول. `walaee.com` يشرح،
 * و`walaee.com/app` هو التطبيق — وهو التقسيم الذي يتوقّعه الزائر
 * أصلًا من أي منتج.
 */
export default defineConfig({
  base: "/",
  plugins: [react()],
  resolve: { alias: sharedAliases(import.meta.url) },
  server: { port: 5172, proxy: devProxy },
  build: {
    // صفحة واحدة بلا توجيه: التقسيم إلى أجزاء هنا يضيف نداء شبكة
    // قبل أول رسم بلا أي مكسب
    cssCodeSplit: false,
  },
});
