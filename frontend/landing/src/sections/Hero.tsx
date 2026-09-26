/**
 * القسم الأول.
 *
 * العنوان يخاطب التاجر لا العميل. هذا قرار تجاري لا ذوقي: التاجر
 * هو من يدفع، والعميل يصل إلى المنصة من متجره لا من هذه الصفحة.
 * لكن باب العميل يبقى ظاهرًا في الترويسة وفي قسم «كيف تعمل»، لأن
 * من يبحث عن رصيده سيصل إلى هنا أيضًا ويجب ألّا يضيع.
 *
 * الأرقام في الشريط حقيقية من `/public/network`. لو تعذّر جلبها
 * يختفي الشريط ولا يُستبدل بأرقام تقريبية: رقم مكتوب في الكود
 * يبقى بعد أن يتغيّر الواقع، ويصير الصفحة تكذب بلا أن ينتبه أحد.
 */

import { Icon, fmt, t } from "@walaee/shared";
import type { PublicBrand, NetworkStats } from "@walaee/shared";

import { APP } from "../links";

/**
 * أرقام البطاقة المعروضة في القسم الأول.
 *
 * **توضيحية لا حقيقية**، وهذا مقصود ومحدود: رصيد أي عميل بعينه
 * بيانات خاصة لا تُعرض على صفحة عامة. فالمعروض هنا متجر حقيقي
 * بلونه واسمه وعدد فروعه — كلها من `/public/network` — وأرقام
 * تقدّم توضيحية تريك شكل البطاقة لا رصيد أحد.
 *
 * القيم ثابتة ومنخفضة عمدًا: بطاقة تقول «٩٨٪ من الهدف» توحي بأن
 * المكافأة قريبة دائمًا، وهي رسالة تسويقية غير صادقة.
 */
const SAMPLE = [
  { value: "٧", goal: "١٠ أختام", reward: "قهوة مجانية", pct: 70 },
  { value: "٨٢٠", goal: "١٬٠٠٠ نقطة", reward: "خصم ٥٠ ج", pct: 82 },
  { value: "٣", goal: "٦ زيارات", reward: "طبق جانبي", pct: 50 },
];

export function Hero({
  stats,
  brands,
}: {
  stats: NetworkStats | null;
  brands: PublicBrand[];
}) {
  /**
   * ثلاث بطاقات من ثلاث فئات مختلفة.
   *
   * ثلاث فقط: المكدّس أكثر من ذلك يتحوّل إلى ضجيج، وأقل منه لا
   * يقرأ «متاجر كثيرة».
   *
   * ومن فئات مختلفة لأن لون البطاقة لون علامتها: أكبر ثلاث علامات
   * قد تكون كلها خضراء فيبدو المكدّس بطاقة واحدة سميكة. اختلاف
   * الفئة يضمن اختلاف اللون بلا أن نختار الألوان يدويًا.
   */
  const cards: PublicBrand[] = [];
  const seen = new Set<string>();
  for (const brand of brands) {
    if (seen.has(brand.category)) continue;
    seen.add(brand.category);
    cards.push(brand);
    if (cards.length === 3) break;
  }

  return (
    <section className="hero" id="top">
      <div className="hero-art" aria-hidden="true">
        <span className="hero-orb hero-orb-a" />
        <span className="hero-orb hero-orb-b" />
        <span className="hero-rule" />
      </div>

      <div className="wrap hero-in">
        <div className="hero-copy">
          <span className="eyebrow">
            <Icon name="mapPin" size={15} />
            {t("منصة مصرية — تعمل بالجنيه وبالعربية")}
          </span>

          <h1>
            {t("خلّي عميلك يرجع تاني،")}
            <br />
            {t("وبرهن إن ده بيحصل.")}
          </h1>

          <p className="hero-lede">
            {t("ولائي منصة لإدارة برامج الولاء للمتاجر: نقاط، أختام، زيارات، واسترداد نقدي. تشتغل من الصندوق برقم تليفون العميل — من غير جهاز جديد، ومن غير ما يحمّل تطبيق.")}
          </p>

          <div className="hero-cta">
            <a href={APP.merchant} className="btn btn-primary btn-lg">
              {t("ابدأ كتاجر")}
              <Icon name="arrowLeft" size={18} />
            </a>
            <a href={APP.customer} className="btn btn-ghost btn-lg">
              {t("أنا عميل — افتح محفظتي")}
            </a>
          </div>

          <ul className="hero-marks">
            <li>
              <Icon name="check" size={16} /> {t("بلا عقد سنوي")}
            </li>
            <li>
              <Icon name="check" size={16} /> {t("بلا أجهزة")}
            </li>
            <li>
              <Icon name="check" size={16} /> {t("تشغيل في نفس اليوم")}
            </li>
          </ul>
        </div>

        <div className="hero-visual">
          {/* البطاقة كما يراها العميل في تطبيقه — نفس المكوّن ونفس
              الأنماط من @walaee/shared، مبنية من متاجر الشبكة
              الحقيقية بألوانها. رسم توضيحي مخترَع كان سيكون أول ما
              يكشف أن الصفحة تعرض منتجًا لا يعمل. */}
          <div className="stack-cards" aria-hidden="true">
            {cards.map((brand, index) => (
              <article
                key={brand.slug}
                className="lcard"
                style={
                  {
                    "--brand": brand.color,
                    "--i": index,
                  } as React.CSSProperties
                }
              >
                <div className="lc-top">
                  <span className="lc-logo">{brand.name.trim().charAt(0)}</span>
                  <div className="grow">
                    <p className="lc-name">{brand.name}</p>
                    <p className="lc-cat">{brand.category}</p>
                  </div>
                </div>

                <div className="lc-mid">
                  <div>
                    <p className="lc-val num">{t(SAMPLE[index]?.value ?? "")}</p>
                    <p className="lc-unit"> {t("من")} {t(SAMPLE[index]?.goal ?? "")}</p>
                  </div>
                  <span className="lc-rew">{t(SAMPLE[index]?.reward ?? "")}</span>
                </div>

                <div className="lc-bar">
                  <i style={{ width: `${SAMPLE[index]?.pct ?? 0}%` }} />
                </div>
                <div className="lc-foot">
                  <span>
                    <span className="num">{fmt.number(SAMPLE[index]?.pct ?? 0)}{t("٪")}</span>{" "}
                    {t("من الهدف")}
                  </span>
                  <span>
                    <span className="num">{fmt.number(brand.branch_count)}</span>{" "}
                    {t("فرعًا")}
                  </span>
                </div>
              </article>
            ))}
          </div>

          {stats && (
            <dl className="hero-stats">
              <div>
                <dt>{t("متجر متعاقد")}</dt>
                <dd className="num">{fmt.number(stats.brands)}</dd>
              </div>
              <div>
                <dt>{t("فرع")}</dt>
                <dd className="num">{fmt.number(stats.branches)}</dd>
              </div>
              <div>
                <dt>{t("محافظة")}</dt>
                <dd className="num">{fmt.number(stats.governorates)}</dd>
              </div>
            </dl>
          )}
        </div>
      </div>
    </section>
  );
}
