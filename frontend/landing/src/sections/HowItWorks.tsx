/**
 * كيف تعمل — مساران متجاوران.
 *
 * عمودان لا قائمة واحدة: رحلة العميل ورحلة التاجر مختلفتان تمامًا،
 * ودمجهما في «١، ٢، ٣» واحدة يجبر كل قارئ على تخطّي نصف الخطوات
 * ليصل إلى نصفه. وضعهما جنبًا إلى جنب يجعل العلاقة بينهما مرئية:
 * ما يفعله الكاشير في العمود الأيسر هو ما يراه العميل في الأيمن.
 */

import { Icon, t } from "@walaee/shared";
import type { IconName } from "@walaee/shared";

interface Step {
  icon: IconName;
  title: string;
  body: string;
}

const CUSTOMER: Step[] = [
  {
    icon: "phone",
    title: "قول رقمك عند الصندوق",
    body: "من غير كارت ولا كود ولا تطبيق. رقم تليفونك هو بطاقتك في كل متجر متعاقد.",
  },
  {
    icon: "stamp",
    title: "رصيدك يتسجّل في ثانية",
    body: "نقاط أو أختام أو زيارة، حسب برنامج المتجر. يوصلك تأكيد ويتحدّث رصيدك فورًا.",
  },
  {
    icon: "gift",
    title: "اصرف مكافأتك وانت واقف",
    body: "تختار المكافأة من التطبيق، يطلع كود قصير يقوله الكاشير، وخلاص.",
  },
];

const MERCHANT: Step[] = [
  {
    icon: "settings",
    title: "اختر برنامجك",
    body: "نقاط على الفاتورة، ختم على كل زيارة، استرداد نقدي… وحدّد الشروط: أقل فاتورة، سقف يومي، مدة صلاحية.",
  },
  {
    icon: "scan",
    title: "شغّل الصندوق",
    body: "شاشة الكاشير تفتح على أي متصفّح. رقم العميل، قيمة الفاتورة، تأكيد. ولا جهاز جديد ولا تدريب.",
  },
  {
    icon: "chart",
    title: "اقرأ الأرقام واتصرّف",
    body: "مين رجع ومين غاب، وكام مكافأة اتصرفت فعلًا، وكام الالتزام اللي عليك دلوقتي.",
  },
];

function Track({
  badge,
  title,
  steps,
  tone,
}: {
  badge: string;
  title: string;
  steps: Step[];
  tone: "customer" | "merchant";
}) {
  return (
    <article className={`track track-${tone}`}>
      <header>
        <span className="track-badge">{badge}</span>
        <h3>{title}</h3>
      </header>

      <ol className="steps">
        {steps.map((step, index) => (
          <li key={step.title}>
            {/* الرقم والأيقونة معًا: الرقم يقول «الترتيب مهم»
                والأيقونة تجعل الخطوة تُمسح بالعين بلا قراءة */}
            <span className="step-mark">
              <Icon name={step.icon} size={19} />
              <b className="num">{index + 1}</b>
            </span>
            <div>
              <strong>{t(step.title)}</strong>
              <p>{t(step.body)}</p>
            </div>
          </li>
        ))}
      </ol>
    </article>
  );
}

export function HowItWorks() {
  return (
    <section className="section how" id="how">
      <div className="wrap">
        <header className="section-head">
          <span className="eyebrow">
            <Icon name="layers" size={15} />
            {t("كيف تعمل")}
          </span>
          <h2>{t("نفس العملية، من الناحيتين")}</h2>
          <p className="section-lede">
            {t("الكاشير يعمل خطوة واحدة، والعميل يشوف نتيجتها على طول. مفيش وسيط ولا انتظار ولا «هيتحدّث بعدين».")}
          </p>
        </header>

        <div className="tracks">
          <Track
            badge={t("للعميل")}
            title={t("من غير ما تعمل أي حاجة")}
            steps={CUSTOMER}
            tone="customer"
          />
          <Track
            badge={t("للتاجر")}
            title={t("من غير ما تغيّر نظامك")}
            steps={MERCHANT}
            tone="merchant"
          />
        </div>
      </div>
    </section>
  );
}
