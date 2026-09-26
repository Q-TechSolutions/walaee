/**
 * المكوّنات المشتركة بين التطبيقات الثلاثة.
 *
 * ما يدخل هنا: كل ما يظهر بنفس الشكل في أكثر من تطبيق. ما لا يدخل:
 * أي شيء يخص مجالًا بعينه — شاشة الكاشير تبقى في لوحة التاجر.
 */

import type { ReactNode } from "react";

import { Icon } from "./icons";
import type { IconName } from "./icons";
import { t } from "../i18n/locale";

/* ══════════════ الحالات ══════════════ */

export function Spinner({ size = 20 }: { size?: number }) {
  return (
    <span
      className="wl-spinner"
      style={{ width: size, height: size }}
      role="status"
      aria-label={t("جارٍ التحميل")}
    />
  );
}

export function Loading({ label = t("جارٍ التحميل…") }: { label?: string }) {
  return (
    <div className="empty">
      <Spinner size={26} />
      <p className="muted">{label}</p>
    </div>
  );
}

export function Empty({
  icon = "layers",
  title,
  hint,
  action,
}: {
  icon?: IconName;
  title: string;
  hint?: string;
  action?: ReactNode;
}) {
  return (
    <div className="empty">
      <div className="empty-icon">
        <Icon name={icon} size={30} weight={1.5} />
      </div>
      <p style={{ fontWeight: 700, color: "var(--ink)" }}>{title}</p>
      {hint && <p className="t-sm muted">{hint}</p>}
      {action}
    </div>
  );
}

/**
 * عرض خطأ.
 *
 * يعرض رسالة الخادم لا نصًّا عامًّا: الخلفية تُرجع رسائل عربية
 * مكتوبة للمستخدم النهائي («الرصيد غير كافٍ» لا «422»)، وإخفاؤها
 * خلف «حدث خطأ» يضيّع المعلومة الوحيدة المفيدة.
 */
export function ErrorBox({
  error,
  onRetry,
}: {
  error: unknown;
  onRetry?: () => void;
}) {
  const message =
    error instanceof Error ? error.message : t("تعذّر إتمام العملية.");

  return (
    <div className="wl-error" role="alert">
      <Icon name="alert" size={18} />
      <span className="grow">{message}</span>
      {onRetry && (
        <button type="button" className="btn btn-ghost" onClick={onRetry}>
          {t("إعادة المحاولة")}
        </button>
      )}
    </div>
  );
}

/* ══════════════ العرض ══════════════ */

export function Card({
  children,
  className = "",
  padded = true,
}: {
  children: ReactNode;
  className?: string;
  padded?: boolean;
}) {
  return (
    <div className={`card ${padded ? "wl-card-p" : ""} ${className}`}>
      {children}
    </div>
  );
}

export function Stat({
  label,
  value,
  hint,
  tone = "default",
}: {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  tone?: "default" | "good" | "warn" | "bad";
}) {
  return (
    <div className={`wl-stat wl-stat-${tone}`}>
      <p className="t-sm muted">{label}</p>
      <p className="wl-stat-value num">{value}</p>
      {hint && <p className="t-sm faint">{hint}</p>}
    </div>
  );
}

const TONES = {
  violet: "badge-violet",
  green: "badge-green",
  orange: "badge-orange",
  red: "badge-red",
  amber: "badge-amber",
  blue: "badge-blue",
  muted: "badge-muted",
} as const;

export function Badge({
  children,
  tone = "muted",
}: {
  children: ReactNode;
  tone?: keyof typeof TONES;
}) {
  return <span className={`badge ${TONES[tone]}`}>{children}</span>;
}

export function Skeleton({
  height = 16,
  width = "100%",
}: {
  height?: number;
  width?: number | string;
}) {
  return <div className="skeleton" style={{ height, width }} />;
}

/* ══════════════ التفاعل ══════════════ */

export function Button({
  children,
  variant = "primary",
  size = "md",
  block = false,
  loading = false,
  disabled = false,
  type = "button",
  onClick,
}: {
  children: ReactNode;
  variant?: "primary" | "ghost" | "danger";
  size?: "md" | "lg";
  block?: boolean;
  loading?: boolean;
  disabled?: boolean;
  type?: "button" | "submit";
  onClick?: () => void;
}) {
  return (
    <button
      type={type}
      className={[
        "btn",
        `btn-${variant}`,
        size === "lg" ? "btn-lg" : "",
        block ? "btn-block" : "",
      ]
        .filter(Boolean)
        .join(" ")}
      // التعطيل أثناء التحميل يمنع الضغط المزدوج — وهو أول سبب
      // لتأكيد عملية مرتين عند الصندوق
      disabled={disabled || loading}
      onClick={onClick}
    >
      {loading && <Spinner size={15} />}
      {children}
    </button>
  );
}

export function Field({
  label,
  hint,
  error,
  children,
}: {
  label: string;
  hint?: string;
  error?: string;
  children: ReactNode;
}) {
  return (
    <div className="field">
      <label>{label}</label>
      {children}
      {error ? (
        <p className="t-sm" style={{ color: "var(--red-600)" }}>
          {error}
        </p>
      ) : (
        hint && <p className="t-sm faint">{hint}</p>
      )}
    </div>
  );
}

export function Modal({
  open,
  title,
  onClose,
  children,
  footer,
}: {
  open: boolean;
  title: string;
  onClose: () => void;
  children: ReactNode;
  footer?: ReactNode;
}) {
  if (!open) return null;

  return (
    <div className="wl-overlay" role="dialog" aria-modal="true" aria-label={title}>
      {/* النقر على الخلفية يغلق — سلوك متوقّع، لكن لا يغلق عند
          النقر داخل النافذة نفسها */}
      <div className="wl-overlay-bg" onClick={onClose} />
      <div className="wl-modal">
        <div className="wl-modal-hd">
          <h3>{title}</h3>
          <button type="button" onClick={onClose} aria-label={t("إغلاق")}>
            <Icon name="close" size={18} />
          </button>
        </div>
        <div className="wl-modal-body">{children}</div>
        {footer && <div className="wl-modal-ft">{footer}</div>}
      </div>
    </div>
  );
}

export function PageHeader({
  title,
  subtitle,
  actions,
}: {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
}) {
  return (
    <header className="wl-page-hd">
      <div className="grow">
        <h1>{title}</h1>
        {subtitle && <p className="t-sm muted">{subtitle}</p>}
      </div>
      {actions && <div className="row">{actions}</div>}
    </header>
  );
}

/* ══════════════ حلقة التقدّم ══════════════ */

/**
 * التقدّم كحلقة — للأرصدة التي لا تُعدّ.
 *
 * الأختام تُرسَم شبكةً لأن العميل يعدّها كما كان يعدّ أختام الكرت
 * الورقي. أما «٨٢٠ من ١٠٠٠ نقطة» فلا يُعدّ، ويهمّ فيه القرب من
 * الهدف — والحلقة تقول القرب بنظرة واحدة، والرقم الكبير في وسطها
 * يقول الرصيد بلا سطر ثانٍ.
 *
 * `children` هو ما يُكتب في المنتصف: يُمرَّر من الخارج لأن
 * الحلقة لا تعرف وحدة الرصيد ولا كيف يُنسَّق رقمه في كل لغة.
 */
export function Ring({
  value,
  size = 148,
  stroke = 12,
  color = "var(--violet-700)",
  children,
}: {
  /** بين ٠ و١ */
  value: number;
  size?: number;
  stroke?: number;
  color?: string;
  children?: ReactNode;
}) {
  const safe = Math.min(Math.max(value, 0), 1);
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;

  return (
    <div className="wl-ring" style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} aria-hidden="true">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="var(--line-2)"
          strokeWidth={stroke}
        />
        {/* يبدأ من أعلى الحلقة لا من يمينها: الدوران يجعل الامتلاء
            يُقرأ كعقرب ساعة، وهو ما يتوقّعه العين */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={circumference * (1 - safe)}
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
          className="wl-ring-fill"
        />
      </svg>
      <div className="wl-ring-mid">{children}</div>
    </div>
  );
}
