/**
 * الباقات.
 *
 * الأرقام هنا يجب أن تطابق `PLAN_LIMITS` في
 * `backend/apps/billing/models.py` حرفًا بحرف. مصدر الحقيقة هناك
 * لأن الحدّ يُفرَض في الخلفية، وصفحة تَعِد بخمسة فروع بينما النظام
 * يرفض السادس هي أسوأ من صفحة بلا أسعار: التاجر يكتشف الفرق بعد
 * أن يدفع.
 *
 * لم تُجلَب من واجهة لأن الأسعار ليست بيانات حيّة تتغيّر في اليوم
 * مرّات — وطلب شبكة إضافي لصفحة عامة له ثمن أول رسم. التبعية
 * مكتوبة هنا ليجدها من يغيّر الأسعار.
 */

import { Icon, fmt, t } from "@walaee/shared";

import { APP } from "../links";

interface Plan {
  key: string;
  name: string;
  price: number;
  pitch: string;
  lines: string[];
  featured?: boolean;
}

const PLANS: Plan[] = [
  {
    key: "free",
    name: "مجانية",
    price: 0,
    pitch: "تجرّب بيها على فرع واحد",
    lines: [
      "فرع واحد · نقطة بيع واحدة",
      "برنامج ولاء واحد",
      "حتى 200 عميل",
      "موظفان",
      "بدون حملات رسائل",
    ],
  },
  {
    key: "starter",
    name: "أساسية",
    price: 450,
    pitch: "لمتجر واحد شغّال",
    lines: [
      "فرع واحد · 3 نقاط بيع",
      "برنامجا ولاء",
      "حتى 2,000 عميل",
      "5 موظفين",
      "500 رسالة شهريًا",
      "تصدير التقارير",
    ],
  },
  {
    key: "growth",
    name: "نمو",
    price: 1200,
    pitch: "لما تبقى أكتر من فرع",
    featured: true,
    lines: [
      "5 فروع · 15 نقطة بيع",
      "4 برامج ولاء",
      "حتى 20,000 عميل",
      "25 موظفًا",
      "3,000 رسالة شهريًا",
      "تصدير التقارير",
    ],
  },
  {
    key: "chain",
    name: "سلاسل",
    price: 3000,
    pitch: "للسلاسل والمجموعات",
    lines: [
      "فروع ونقاط بيع بلا حد",
      "برامج ولاء بلا حد",
      "عملاء بلا حد",
      "موظفون بلا حد",
      "10,000 رسالة شهريًا",
      "دعم مخصّص",
    ],
  },
];

export function Pricing() {
  return (
    <section className="section pricing" id="pricing">
      <div className="wrap">
        <header className="section-head">
          <span className="eyebrow">
            <Icon name="tag" size={15} />
            {t("الأسعار")}
          </span>
          <h2>{t("ادفع على حجمك، مش على وعد")}</h2>
          <p className="section-lede">
            {t("كل الأسعار بالجنيه المصري شهريًا. تقدر تغيّر باقتك أو توقفها في أي وقت، وبياناتك بتفضل معاك.")}
          </p>
        </header>

        <div className="plans">
          {PLANS.map((plan) => (
            <article
              key={plan.key}
              className={`plan ${plan.featured ? "is-featured" : ""}`}
            >
              {plan.featured && <span className="plan-flag">{t("الأكثر اختيارًا")}</span>}

              <h3>{t(plan.name)}</h3>
              <p className="plan-pitch">{t(plan.pitch)}</p>

              <p className="plan-price">
                {plan.price === 0 ? (
                  <b>{t("مجانًا")}</b>
                ) : (
                  <>
                    <b className="num">{fmt.number(plan.price)}</b>
                    <span>{t("جنيه / شهر")}</span>
                  </>
                )}
              </p>

              <ul>
                {plan.lines.map((line) => (
                  <li key={line}>
                    <Icon name="check" size={15} />
                    <span>{t(line)}</span>
                  </li>
                ))}
              </ul>

              <a
                href={APP.merchant}
                className={`btn btn-block ${plan.featured ? "btn-primary" : "btn-ghost"}`}
              >
                {plan.price === 0 ? t("ابدأ مجانًا") : t("اختر الباقة")}
              </a>
            </article>
          ))}
        </div>

        <p className="pricing-note">
          <Icon name="info" size={15} />
          {t("الرسائل تُحسب بالفعلي المُرسَل. تجاوز الحد بيوقف الحملات بس — ما بيوقفش تسجيل النقاط ولا صرف المكافآت عند الصندوق.")}
        </p>
      </div>
    </section>
  );
}
