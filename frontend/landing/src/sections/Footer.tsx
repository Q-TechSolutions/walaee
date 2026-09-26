/**
 * الدعوة الأخيرة والتذييل.
 *
 * الدعوة تكرّر البابين لا بابًا واحدًا: من وصل إلى نهاية الصفحة
 * قرأ كل شيء، وإجباره على التمرير لأعلى ليجد مدخله هو أسهل طريقة
 * لخسارته بعد أن اقتنع.
 */

import { Icon, Logo, t } from "@walaee/shared";

import { APP, SECTIONS } from "../links";

export function Footer({ merchants }: { merchants: number }) {
  return (
    <>
      <section className="cta">
        <div className="cta-art" aria-hidden="true">
          <span className="auth-grid" />
        </div>

        <div className="wrap cta-in">
          <h2>{t("ابدأ النهارده. مش محتاج أكتر من ربع ساعة.")}</h2>
          <p>
            {merchants > 0
              ? t("انضم لـ{n} متجرًا شغّالين على المنصة دلوقتي.", { n: merchants })
              : t("برنامج ولاء كامل، من غير أجهزة ولا عقود.")}
          </p>

          <div className="cta-buttons">
            <a href={APP.merchant} className="btn btn-lg cta-primary">
              {t("ابدأ كتاجر")}
              <Icon name="arrowLeft" size={18} />
            </a>
            <a href={APP.customer} className="btn btn-lg cta-ghost">
              {t("ادخل كعميل")}
            </a>
          </div>
        </div>
      </section>

      <footer className="foot">
        <div className="wrap foot-in">
          <div className="foot-brand">
            <Logo size={38} tagline />
            <p>
              {t("منصة مصرية لإدارة برامج الولاء متعدّدة المتاجر. مبنية بالعربية وبالجنيه من أول سطر.")}
            </p>
          </div>

          <nav className="foot-nav" aria-label={t("روابط الصفحة")}>
            <h3>{t("الصفحة")}</h3>
            {SECTIONS.map((section) => (
              <a key={section.id} href={`#${section.id}`}>
                {t(section.label)}
              </a>
            ))}
          </nav>

          <nav className="foot-nav" aria-label={t("تطبيقات المنصة")}>
            <h3>{t("الدخول")}</h3>
            <a href={APP.customer}>{t("تطبيق العملاء")}</a>
            <a href={APP.merchant}>{t("لوحة المتجر")}</a>
            <a href={APP.admin}>{t("إدارة المنصة")}</a>
          </nav>
        </div>

        <div className="wrap foot-base">
          <p className="num">© {new Date().getFullYear()} {t("ولائي")}</p>
          <p>{t("كلنا كسبانين")}</p>
        </div>
      </footer>
    </>
  );
}
