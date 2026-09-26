/**
 * ما تحصل عليه كتاجر.
 *
 * ستّ بطاقات، كل واحدة تجيب اعتراضًا سمعناه فعلًا لا ميزة نحبّها:
 * «هيسرق الكاشير النقاط»، «هتبقى فلوس ملزومة عليّ»، «عندي فروع
 * كتير»، «مش هعرف أقيس». الميزة بلا اعتراض تردّه تصير سطرًا
 * يتخطّاه القارئ.
 *
 * البطاقة الأولى أعرض من غيرها عمدًا: دفتر القيود هو ما يميّز
 * المنصة فعلًا، وتسويته ببقية البطاقات يخفي أهم ما فيها.
 */

import { Icon, t } from "@walaee/shared";
import type { IconName } from "@walaee/shared";

import { APP } from "../links";

interface Feature {
  icon: IconName;
  title: string;
  body: string;
  wide?: boolean;
}

const FEATURES: Feature[] = [
  {
    icon: "receipt",
    title: "كل نقطة ليها قيد",
    body:
      "الأرصدة مش رقم في خانة يتعدّل. كل منح وكل صرف وكل عكس له قيد ثابت لا يتغيّر ولا يُحذَف، ورصيد العميل مجموعها. يعني أي خلاف مع عميل يتحسم في دقيقة، وأي رقم في تقاريرك يقدر يتراجع لمصدره.",
    wide: true,
  },
  {
    icon: "shield",
    title: "حماية من الاحتيال الداخلي",
    body:
      "سقف يومي لكل عميل، وحساب مستقل لكل كاشير، ومراجعة تلقائية للأنماط الغريبة — زي منح متكرّر لنفس الرقم في نفس الوردية.",
  },
  {
    icon: "coins",
    title: "تعرف التزامك بالجنيه",
    body:
      "النقاط اللي لسه في جيب عملائك ليها تكلفة عليك. اللوحة بتحسبها بسعر المكافأة الحقيقي، مش بعدد النقاط.",
  },
  {
    icon: "building",
    title: "فروع وصلاحيات",
    body:
      "كل فرع بنقاط بيعه وموظفيه. المالك يشوف الكل، المدير يشوف فرعه، والكاشير يشوف شاشته بس.",
  },
  {
    icon: "clock",
    title: "صلاحية للرصيد",
    body:
      "تحدّد مدة صلاحية النقاط، والمنصة بتنبّه العميل قبل ما تنتهي — فبيرجع يصرفها عندك بدل ما تتبخّر وهو زعلان.",
  },
  {
    icon: "message",
    title: "حملات موجّهة",
    body:
      "ابعت لعملاء غابوا ٣٠ يوم، أو لأصحاب رصيد قارب ينتهي. مش رسائل جماعية — شرائح محدّدة برصيدها وسلوكها.",
  },
];

export function ForMerchants() {
  return (
    <section className="section merchants" id="merchants">
      <div className="wrap">
        <header className="section-head">
          <span className="eyebrow">
            <Icon name="store" size={15} />
            {t("للتجّار")}
          </span>
          <h2>{t("برنامج ولاء تقدر تدافع عن أرقامه")}</h2>
          <p className="section-lede">
            {t("أي حد يقدر يوزّع نقاط. الصعب إنك تعرف إن النقاط دي رجّعت عميل فعلًا، وإن محدش بيلعب فيها.")}
          </p>
        </header>

        <ul className="features">
          {FEATURES.map((feature) => (
            <li
              key={feature.title}
              className={`feature ${feature.wide ? "is-wide" : ""}`}
            >
              <span className="feature-icon">
                <Icon name={feature.icon} size={21} />
              </span>
              <strong>{t(feature.title)}</strong>
              <p>{t(feature.body)}</p>
            </li>
          ))}
        </ul>

        <div className="merchants-cta">
          <p>
            {t("عايز تشوفها شغّالة قبل ما تقرّر؟ لوحة التجربة مفتوحة بحسابات جاهزة — مالك ومدير وكاشير.")}
          </p>
          <a href={APP.merchant} className="btn btn-primary btn-lg">
            {t("افتح لوحة المتجر")}
            <Icon name="arrowLeft" size={18} />
          </a>
        </div>
      </div>
    </section>
  );
}
