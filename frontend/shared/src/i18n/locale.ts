/**
 * اللغة والاتجاه — مخزن واحد خارج React.
 *
 * لماذا خارج React: النصوص لا تعيش كلها داخل مكوّنات. ثوابت على
 * مستوى الوحدة (`const RANGES = [{ label: "٣٠ يومًا" }]`) تُقيَّم
 * مرة واحدة عند الاستيراد، قبل أن يُركَّب أي مكوّن. دالة ترجمة
 * على هيئة خطّاف (hook) لا تصلها، فتتجمّد تلك النصوص على لغة
 * واحدة مهما بدّل المستخدم.
 *
 * الحل: `t()` دالة عادية تقرأ لغةً على مستوى الوحدة، ويُعيد
 * `useLocale()` رسم الشجرة عند التبديل. الثابت يبقى بالعربية —
 * وهي **مفتاحه** — ويُترجَم عند عرضه لا عند تعريفه.
 *
 * ولماذا المفتاح نصّ عربي لا `"nav.dashboard"`: هذا مشروع عربي
 * الأصل. مفاتيح مخترَعة كانت تعني ملفًا ثالثًا يجب أن يبقى
 * متّسقًا مع الشاشة والقاموس معًا، وأول ما ينحرف منها ينتج نصًّا
 * مفقودًا في الإنتاج. بالنصّ الأصلي مفتاحًا — كما يفعل gettext —
 * تكون الترجمة الناقصة عربيةً صحيحة لا مفتاحًا مكشوفًا.
 */

import { EN } from "./en";

export type Locale = "ar" | "en";

export const LOCALES: readonly Locale[] = ["ar", "en"];

/** مشترك بين التطبيقات الأربعة: نفس الأصل، نفس التفضيل. */
const KEY = "walaee.locale";

const LABELS: Record<Locale, string> = { ar: "العربية", en: "English" };

let current: Locale = read();
const listeners = new Set<() => void>();

function read(): Locale {
  try {
    const stored = localStorage.getItem(KEY);
    if (stored === "ar" || stored === "en") return stored;
  } catch {
    // وضع التصفّح الخاص يرفض القراءة — العربية هي الأصل
  }
  return "ar";
}

export function getLocale(): Locale {
  return current;
}

export function localeLabel(locale: Locale): string {
  return LABELS[locale];
}

export function setLocale(locale: Locale): void {
  if (locale === current) return;
  current = locale;
  try {
    localStorage.setItem(KEY, locale);
  } catch {
    // التفضيل لا يُحفظ، لكن الجلسة الحالية تعمل
  }
  applyDocument();
  listeners.forEach((fn) => fn());
}

export function subscribeLocale(fn: () => void): () => void {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

/**
 * يضبط `lang` و`dir` على جذر المستند.
 *
 * `dir` هنا لا في CSS: كل التنسيقات مكتوبة بخصائص منطقية
 * (`margin-inline-start` لا `margin-left`)، فالمتصفّح وحده يقلب
 * التخطيط حين يتغيّر الاتجاه — بلا ورقة أنماط ثانية للإنجليزية.
 */
export function applyDocument(): void {
  const root = document.documentElement;
  root.lang = current;
  root.dir = current === "ar" ? "rtl" : "ltr";
}

/**
 * الترجمة. المفتاح هو النصّ العربي.
 *
 * `vars` تستبدل `{name}` — تُستخدم حيث يتغيّر ترتيب الكلمات بين
 * اللغتين، فلا يصحّ تركيب الجملة بالجمع في موضع الاستدعاء.
 */
export function t(msgid: string, vars?: Record<string, string | number>): string {
  let text = current === "ar" ? msgid : (EN[msgid] ?? msgid);

  if (vars) {
    for (const [key, value] of Object.entries(vars)) {
      text = text.replaceAll(`{${key}}`, String(value));
    }
  }
  return text;
}

/** اختيار بين صيغتين حسب اللغة — للحالات التي لا يكفي فيها قاموس. */
export function pick<T>(arabic: T, english: T): T {
  return current === "ar" ? arabic : english;
}
