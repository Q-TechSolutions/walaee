import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";
import { VitePWA } from "vite-plugin-pwa";

import { devProxy, sharedAliases } from "../vite.shared";

export default defineConfig({
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
        start_url: "/",
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
        navigateFallbackDenylist: [/^\/api/],
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
