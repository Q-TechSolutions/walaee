
import { t } from "../i18n/locale";
/**
 * علامة «ولائي».
 *
 * الرمز بطاقة مثقوبة الحافتين تحمل ثلاث دوائر: اثنتان مفرَّغتان
 * وواحدة ممتلئة بالذهب. هذا هو المنتج في شكل واحد — بطاقة تُختَم،
 * والختم الأخير هو المكسب.
 *
 * لماذا ليس حرفًا ولا قلبًا: الحرف يحتاج خطًّا قد لا يُحمَّل فينهار
 * الشعار إلى مربّع فارغ، والقلب يُستخدم في كل تطبيق ولاء على وجه
 * الأرض فلا يميّز شيئًا. الثقوب الجانبية تُميّز الشكل حتى عند ١٦
 * بكسل في تبويب المتصفّح، وهو الحجم الذي تُختبَر فيه العلامات فعلًا.
 *
 * الذهب هنا الاستثناء الوحيد المسموح خارج سياق المكافأة، لأنه
 * يعني نفس الشيء تمامًا.
 */

export interface LogoProps {
  size?: number;
  /** يعكس الألوان — للاستعمال فوق خلفية داكنة */
  inverted?: boolean;
  className?: string;
}

export function LogoMark({ size = 36, inverted = false, className = "" }: LogoProps) {
  const body = inverted ? "#ffffff" : "var(--violet-700)";
  const hole = inverted ? "var(--violet-800)" : "var(--surface)";

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 40 40"
      fill="none"
      className={`wl-logo ${className}`}
      aria-hidden="true"
    >
      {/* البطاقة */}
      <rect x="3" y="8" width="34" height="24" rx="6" fill={body} />

      {/* الثقبان الجانبيان — يُرسمان بلون الخلفية لا بشفافية، لأن
          الشفافية تُظهر ما تحتها فيتّسخ الشكل فوق أي صورة */}
      <circle cx="3" cy="20" r="3.4" fill={hole} />
      <circle cx="37" cy="20" r="3.4" fill={hole} />

      {/* ختمان فارغان وختم مكتمل */}
      <circle cx="13" cy="20" r="3.1" stroke={hole} strokeWidth="1.8" />
      <circle cx="20" cy="20" r="3.1" stroke={hole} strokeWidth="1.8" />
      <circle cx="27" cy="20" r="3.6" fill="var(--gold-500)" />
    </svg>
  );
}

/** الشعار كاملًا: العلامة والاسم والشعار النصّي. */
export function Logo({
  size = 36,
  inverted = false,
  tagline = false,
  className = "",
}: LogoProps & { tagline?: boolean }) {
  return (
    <span className={`wl-logo-lockup ${className}`}>
      <LogoMark size={size} inverted={inverted} />
      <span className="wl-logo-text">
        <strong style={{ fontSize: size * 0.62 }}>{t("ولائي")}</strong>
        {tagline && <span className="wl-logo-tagline">{t("كلنا كسبانين")}</span>}
      </span>
    </span>
  );
}
