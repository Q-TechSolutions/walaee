/**
 * مفتاحا التفضيلات: السمة واللغة.
 *
 * الاثنان معًا في ملف واحد لأنهما يظهران معًا دائمًا — في ترويسة
 * اللوحة، وفي صفحة الملف الشخصي، وأسفل شاشة الدخول. فصلهما كان
 * سيعني استيرادين ومكوّن ثالث يجمعهما في كل تطبيق.
 *
 * `useSyncExternalStore` لا `useState`: المخزن خارج React (راجع
 * `i18n/locale.ts`)، وهذا الخطّاف هو الطريق المعتمد لقراءة مخزن
 * خارجي بلا تمزّق بين مكوّن رُسم قبل التبديل وآخر بعده.
 */

import { Fragment, useSyncExternalStore } from "react";
import type { ReactNode } from "react";

import {
  LOCALES,
  applyDocument,
  getLocale,
  localeLabel,
  setLocale,
  subscribeLocale,
  t,
} from "../i18n/locale";
import type { Locale } from "../i18n/locale";
import { Icon } from "./icons";
import type { IconName } from "./icons";
import { THEMES, applyTheme, getTheme, setTheme, subscribeTheme } from "./theme";
import type { Theme } from "./theme";

/* ══════════════ الخطّافات ══════════════ */

export function useLocale(): [Locale, (next: Locale) => void] {
  const locale = useSyncExternalStore(subscribeLocale, getLocale, () => "ar" as Locale);
  return [locale, setLocale];
}

export function useTheme(): [Theme, (next: Theme) => void] {
  const theme = useSyncExternalStore(subscribeTheme, getTheme, () => "system" as Theme);
  return [theme, setTheme];
}

/**
 * يُطبّق التفضيلين المحفوظين على المستند.
 *
 * يُستدعى من `main.tsx` قبل أول رسم. تأخيره إلى ما بعد التركيب
 * كان يُظهر وميضًا أبيض على جهاز داكن — نصف ثانية تكفي لتبدو
 * الصفحة معطوبة.
 */
export function applyPreferences(): void {
  applyDocument();
  applyTheme();
}

/* ══════════════ المفاتيح ══════════════ */

const THEME_ICON: Record<Theme, IconName> = {
  light: "sun",
  dark: "moon",
  system: "monitor",
};

const THEME_LABEL: Record<Theme, string> = {
  light: "نهاري",
  dark: "ليلي",
  system: "النظام",
};

/**
 * مفتاح السمة — ثلاثة أزرار لا زرّ دوّار.
 *
 * الزر الدوّار (اضغط فيتنقّل بين الحالات) يخفي الحالة الحالية
 * والتالية معًا، فيضغط المستخدم مرتين ليصل لما يريد ولا يعرف
 * أصلًا أن «يتبع النظام» موجود.
 */
export function ThemeToggle({ compact = false }: { compact?: boolean }) {
  const [theme, choose] = useTheme();

  return (
    <div className="pref-seg" role="group" aria-label={t("السمة")}>
      {THEMES.map((option) => (
        <button
          key={option}
          type="button"
          className={theme === option ? "on" : ""}
          aria-pressed={theme === option}
          title={t(THEME_LABEL[option])}
          onClick={() => choose(option)}
        >
          <Icon name={THEME_ICON[option]} size={15} />
          {!compact && <span>{t(THEME_LABEL[option])}</span>}
        </button>
      ))}
    </div>
  );
}

/**
 * مفتاح اللغة.
 *
 * كل لغة مكتوبة **باسمها فيها** — «العربية» و«English» — لا
 * مترجمةً إلى لغة الواجهة الحالية. من يبحث عن الإنجليزية لأنه لا
 * يقرأ العربية لن يتعرّف على كلمة «الإنجليزية».
 */
export function LocaleToggle({ compact = false }: { compact?: boolean }) {
  const [locale, choose] = useLocale();

  return (
    <div className="pref-seg" role="group" aria-label={t("اللغة")}>
      {LOCALES.map((option) => (
        <button
          key={option}
          type="button"
          className={locale === option ? "on" : ""}
          aria-pressed={locale === option}
          lang={option}
          onClick={() => choose(option)}
        >
          {compact ? option.toUpperCase() : localeLabel(option)}
        </button>
      ))}
    </div>
  );
}

/** الاثنان جنبًا إلى جنب — الشكل الذي يظهران به في أغلب المواضع. */
export function PreferenceBar({ compact = false }: { compact?: boolean }) {
  return (
    <div className="pref-bar">
      <LocaleToggle compact={compact} />
      <ThemeToggle compact />
    </div>
  );
}

/**
 * يُعيد بناء الشجرة عند تبديل اللغة.
 *
 * `t()` دالة عادية لا خطّاف، فلا تُعلِم React بشيء. المكوّن الذي
 * يستدعيها بلا اشتراك يبقى على لغته السابقة حتى يُرسم لسبب آخر —
 * فتظهر الشاشة نصفها عربي ونصفها إنجليزي.
 *
 * `key` على الجزء يُسقط الشجرة ويُعيد تركيبها. الثمن معروف: ما في
 * نموذج نصفَ مكتوب يضيع. وهو الثمن الصحيح — البديل اشتراكٌ في كل
 * مكوّن، وأول واحد يُنسى ينتج شاشة بلغتين ولا يكتشفه أحد. وتبديل
 * اللغة يحدث مرة في العمر لا في منتصف إدخال فاتورة.
 */
export function LocaleBoundary({ children }: { children: ReactNode }) {
  const [locale] = useLocale();
  return <Fragment key={locale}>{children}</Fragment>;
}
