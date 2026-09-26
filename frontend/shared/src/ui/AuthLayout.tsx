/**
 * هيكل شاشات الدخول — نصفان لا عمود واحد.
 *
 * النصف الأول (يمين، في اتجاه العربية) لوح الهوية: من نحن وما هذا
 * المكان. النصف الثاني النموذج نفسه.
 *
 * لماذا نصفان: شاشة الدخول في عمود واحد وسط صفحة فارغة تضع
 * النموذج في المنتصف البصري وتترك ثلثي الشاشة بلا عمل. الأسوأ أنها
 * لا تقول شيئًا — والداخل إلى لوحة تاجر لأول مرة يحتاج أن يعرف
 * أنه في المكان الصحيح قبل أن يكتب رقمه.
 *
 * لوح الهوية يختلف بين التطبيقات الثلاثة (`aside`): العميل يرى ما
 * يكسبه، والتاجر يرى ما يديره، والمنصة ترى شبكتها. نفس الهيكل
 * ومحتوى مختلف — لا ثلاث شاشات دخول تنحرف كل منها عن الأخرى.
 *
 * ── على الهاتف ──
 * ينهار إلى عمود واحد ويختفي لوح الهوية إلا ترويسته. إبقاؤه كاملًا
 * يعني تمرير شاشة كاملة قبل الوصول إلى حقل الرقم — وشاشة الدخول
 * يجب أن تكون أقصر مسار في التطبيق لا أطوله.
 */

import type { ReactNode } from "react";

import { Logo } from "./Logo";

export interface AuthLayoutProps {
  /** ما يظهر في لوح الهوية تحت العنوان */
  aside?: ReactNode;
  headline: string;
  /** سطر تحت العنوان — يقول أين نحن بالضبط */
  subline: string;
  /** شارة صغيرة أعلى العنوان: «لوحة التاجر»، «إدارة المنصة» */
  badge?: string;
  children: ReactNode;
  /** أسفل عمود النموذج — عادةً منتقي حسابات التجربة */
  footer?: ReactNode;
}

export function AuthLayout({
  aside,
  headline,
  subline,
  badge,
  children,
  footer,
}: AuthLayoutProps) {
  return (
    <div className="auth">
      <section className="auth-brand">
        {/* الطبقة الزخرفية مفصولة عن المحتوى: وضعها خلفية على
            العنصر نفسه كان يجعلها تُقصّ مع النص عند التمرير */}
        <div className="auth-brand-art" aria-hidden="true">
          <span className="auth-orb auth-orb-1" />
          <span className="auth-orb auth-orb-2" />
          <span className="auth-grid" />
        </div>

        <div className="auth-brand-body">
          <Logo size={44} inverted tagline />

          <div className="auth-brand-copy">
            {badge && <span className="auth-badge">{badge}</span>}
            <h1>{headline}</h1>
            <p>{subline}</p>
          </div>

          {aside && <div className="auth-aside">{aside}</div>}
        </div>
      </section>

      <section className="auth-form">
        {/* ترويسة الهاتف: نسخة مصغّرة من لوح الهوية تظهر حين
            يختفي اللوح نفسه، فلا تصير الشاشة الصغيرة بلا هوية */}
        <header className="auth-mobile-head">
          <Logo size={32} />
          {badge && <span className="auth-badge auth-badge-light">{badge}</span>}
        </header>

        <div className="auth-form-body">{children}</div>

        {footer && <div className="auth-form-foot">{footer}</div>}
      </section>
    </div>
  );
}

/**
 * نقطة في قائمة لوح الهوية.
 *
 * ثلاث نقاط لا أكثر: اللوح ليس صفحة تسويق، ومن وصل إلى شاشة
 * الدخول قرّر بالفعل.
 */
export function AuthPoint({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <li className="auth-point">
      <span className="auth-point-dot" aria-hidden="true" />
      <div>
        <strong>{title}</strong>
        <p>{children}</p>
      </div>
    </li>
  );
}
