/**
 * السمة: فاتح، داكن، أو ما يقوله النظام.
 *
 * رموز الألوان في `tokens.css` تحمل الوضعين أصلًا — الداكن
 * معكوس يدويًا لا مقلوبًا آليًا. ما كان ناقصًا هو المفتاح: بلا
 * تبديل صريح يبقى المستخدم أسير إعداد نظام تشغيله، ومن يعمل على
 * جهاز مضبوط على الداكن لا يرى الوضع النهاري أبدًا.
 *
 * ثلاث حالات لا اثنتان. «يتبع النظام» ليست ترفًا: الجهاز الذي
 * يبدّل تلقائيًا عند الغروب يجب أن تبدّل معه الشاشة، وخيار ثنائي
 * كان يجمّدها على ما اختير ظهرًا.
 *
 * المخزن خارج React لنفس سبب اللغة — راجع `i18n/locale.ts`.
 */

export type Theme = "light" | "dark" | "system";

export const THEMES: readonly Theme[] = ["light", "dark", "system"];

/** مشترك بين التطبيقات الأربعة: نفس الأصل، نفس التفضيل. */
const KEY = "walaee.theme";

let current: Theme = read();
const listeners = new Set<() => void>();
let watcher: MediaQueryList | null = null;

function read(): Theme {
  try {
    const stored = localStorage.getItem(KEY);
    if (stored === "light" || stored === "dark" || stored === "system") return stored;
  } catch {
    // وضع التصفّح الخاص يرفض القراءة
  }
  return "system";
}

function systemPrefersDark(): boolean {
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ?? false;
}

export function getTheme(): Theme {
  return current;
}

/** ما يُرسم فعلًا — «يتبع النظام» تُحلّ هنا إلى فاتح أو داكن. */
export function resolvedTheme(): "light" | "dark" {
  if (current === "system") return systemPrefersDark() ? "dark" : "light";
  return current;
}

export function setTheme(theme: Theme): void {
  current = theme;
  try {
    localStorage.setItem(KEY, theme);
  } catch {
    // التفضيل لا يُحفظ، لكن الجلسة الحالية تعمل
  }
  applyTheme();
  listeners.forEach((fn) => fn());
}

export function subscribeTheme(fn: () => void): () => void {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

/**
 * يكتب `data-theme` على الجذر ويضبط `color-scheme`.
 *
 * `color-scheme` ليس تجميلًا: هو ما يجعل المتصفّح يرسم أشرطة
 * التمرير وحقول الإدخال الأصلية بالوضع نفسه. بدونه يظهر حقل
 * تاريخ أبيض ناصع وسط لوحة داكنة.
 */
export function applyTheme(): void {
  const root = document.documentElement;
  const resolved = resolvedTheme();

  root.setAttribute("data-theme", resolved);
  root.style.colorScheme = resolved;

  // متابعة النظام تُثبَّت مرة واحدة وتبقى: المستخدم قد يبدّل إعداد
  // جهازه والصفحة مفتوحة، وفي وضع «يتبع النظام» يجب أن تتبعه.
  if (watcher === null && window.matchMedia) {
    watcher = window.matchMedia("(prefers-color-scheme: dark)");
    watcher.addEventListener("change", () => {
      if (current === "system") {
        applyTheme();
        listeners.forEach((fn) => fn());
      }
    });
  }
}
