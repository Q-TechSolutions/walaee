import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";
import { VitePWA } from "vite-plugin-pwa";

import { devProxy, sharedAliases } from "../vite.shared";

/**
 * تطبيق العميل انتقل من الجذر إلى `/app/`.
 *
 * الجذر صار للصفحة العامة: من يسمع باسم المنصة لأول مرة يكتب
 * الدومين، ولا يجوز أن يستقبله نموذج دخول.
 *
 * `base` هنا و`basename` في الموجّه يجب أن يتطابقا — تغيير أحدهما
 * وحده يعطي صفحة بيضاء بلا أي خطأ في السجل.
 */
const BASE = process.env.VITE_BASE ?? "/app/";

export default defineConfig({
  base: BASE,
  plugins: [
    react(),
    VitePWA({
      registerType: "autoUpdate",
      includeAssets: ["favicon.svg"],
      manifest: {
        name: "ولائي",
        short_name: "ولائي",
        description: "بطاقات الولاء كلها في مكان واحد",
        lang: "ar",
        dir: "rtl",
        theme_color: "#4b1e9e",
        background_color: "#f6f4fc",
        display: "standalone",
        orientation: "portrait",
        start_url: "/app/",
        // النطاق يحصر عامل الخدمة في التطبيق: بلا حصره يعترض
        // طلبات الصفحة العامة و/merchant/ ويخدمها من ذاكرته
        scope: "/app/",
        id: "/app/",
        icons: [
          { src: "icon-192.png", sizes: "192x192", type: "image/png" },
          { src: "icon-512.png", sizes: "512x512", type: "image/png" },
          {
            src: "icon-512.png",
            sizes: "512x512",
            type: "image/png",
            purpose: "maskable",
          },
        ],
      },
      workbox: {
        // نداءات API لا تُخزَّن إطلاقًا: رصيد نقاط مخزَّن مؤقتًا
        // يعني عميلًا يرى رصيدًا صرفه بالفعل ثم يُرفض عند الكاشير.
        // والمسارات خارج `/app/` ليست لنا — تخزينها يجعل التطبيق
        // يخدم صفحة قديمة بدل الصفحة العامة أو لوحة التاجر.
        navigateFallback: "/app/index.html",
        navigateFallbackDenylist: [
          /^\/api/,
          /^\/merchant\//,
          /^\/admin\//,
          /^\/django-admin\//,
        ],
        runtimeCaching: [
          {
            urlPattern: /^https:\/\/fonts\.(googleapis|gstatic)\.com\//,
            handler: "CacheFirst",
            options: {
              cacheName: "fonts",
              expiration: { maxEntries: 20, maxAgeSeconds: 60 * 60 * 24 * 365 },
            },
          },
        ],
      },
    }),
  ],
  resolve: { alias: sharedAliases(import.meta.url) },

  server: {
    port: 5173,
    proxy: devProxy,
  },
});
