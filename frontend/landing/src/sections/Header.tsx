/**
 * ترويسة الصفحة العامة.
 *
 * تلتصق بالأعلى بعد أول تمرير لا من البداية: ترويسة ثابتة فوق
 * القسم الأول تأكل من ارتفاعه على الهاتف بلا داعٍ — لا شيء فوقها
 * ليُرجَع إليه بعد.
 *
 * زرّان لا زر واحد: الصفحة تخاطب جمهورين. التاجر هو من يشتري،
 * فزرّه ممتلئ؛ والعميل يحتاج بابًا واضحًا لا أقل، فزرّه محدَّد
 * الإطار. إخفاء أحدهما خلف قائمة يعني نصف الزوّار يبحثون عن
 * مدخلهم في صفحة كُتبت للنصف الآخر.
 */

import { useEffect, useState } from "react";

import { Icon, Logo, PreferenceBar, t } from "@walaee/shared";

import { APP, SECTIONS } from "../links";

export function Header() {
  const [stuck, setStuck] = useState(false);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setStuck(window.scrollY > 24);
    onScroll();
    // passive: المتصفّح لا ينتظر ليعرف إن كنا سنمنع التمرير،
    // فيبقى التمرير ناعمًا على الأجهزة الضعيفة
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  // القائمة المفتوحة تقفل عند التنقّل: رابط داخلي لا يعيد تحميل
  // الصفحة، فتبقى القائمة مفتوحة فوق ما ذهب إليه المستخدم
  function go() {
    setOpen(false);
  }

  return (
    <header className={`nav ${stuck ? "is-stuck" : ""}`}>
      <div className="nav-in wrap">
        <a href="#top" className="nav-logo" aria-label={t("ولائي — الصفحة الرئيسية")}>
          <Logo size={34} />
        </a>

        <nav className={`nav-links ${open ? "is-open" : ""}`} aria-label={t("أقسام الصفحة")}>
          {SECTIONS.map((section) => (
            <a key={section.id} href={`#${section.id}`} onClick={go}>
              {t(section.label)}
            </a>
          ))}
        </nav>

        <div className="nav-cta">
          <PreferenceBar compact />
          <a href={APP.customer} className="btn btn-ghost">
            {t("دخول العملاء")}
          </a>
          <a href={APP.merchant} className="btn btn-primary">
            {t("لوحة المتجر")}
          </a>
        </div>

        <button
          type="button"
          className="nav-burger"
          aria-expanded={open}
          aria-label={open ? t("إغلاق القائمة") : t("فتح القائمة")}
          onClick={() => setOpen((value) => !value)}
        >
          <Icon name={open ? "close" : "menu"} size={22} />
        </button>
      </div>
    </header>
  );
}
