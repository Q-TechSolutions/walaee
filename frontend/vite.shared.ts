/**
 * إعداد Vite المشترك بين التطبيقات الثلاثة.
 *
 * الأسماء المستعارة مرتّبة من الأخص إلى الأعم: Vite يطابق البادئة،
 * فلو جاء `@walaee/shared` أولًا لابتلع `@walaee/shared/tokens.css`
 * وحوّله إلى مسار داخل ملف — وهو عطل بناء لا يشرح نفسه.
 */

import { fileURLToPath } from "node:url";

import type { AliasOptions } from "vite";

const from = (relative: string, base: string) =>
  fileURLToPath(new URL(relative, base));

export function sharedAliases(importMetaUrl: string): AliasOptions {
  return [
    {
      find: "@walaee/shared/tokens.css",
      replacement: from("../shared/src/tokens/tokens.css", importMetaUrl),
    },
    {
      find: "@walaee/shared/base.css",
      replacement: from("../shared/src/tokens/base.css", importMetaUrl),
    },
    {
      find: "@walaee/shared/components.css",
      replacement: from("../shared/src/ui/components.css", importMetaUrl),
    },
    {
      find: "@walaee/shared",
      replacement: from("../shared/src/index.ts", importMetaUrl),
    },
  ];
}

/** وكيل التطوير — يجعل الواجهة والـAPI على أصل واحد كما في الإنتاج. */
export const devProxy = {
  "/api": { target: "http://127.0.0.1:8000", changeOrigin: true },
};
