/**
 * الصفحة العامة.
 *
 * صفحة واحدة بلا موجّه: كل الأقسام مراسٍ داخلها (`#coverage`،
 * `#pricing`…). إضافة موجّه هنا تعني حزمة أكبر ومسارات تحتاج
 * إعدادًا في nginx مقابل لا شيء — الصفحة تُقرأ بالتمرير.
 *
 * نداء شبكة واحد يغذّي القسم الأول وقسم التغطية والتذييل معًا،
 * ويُخزَّن داخل المتصفّح في `fetchNetwork`. ثلاثة نداءات كانت
 * ستعطي ثلاثة أرقام مختلفة على نفس الصفحة لو تجدّد التخزين في
 * الخادم بينها.
 *
 * ── السلوك عند الفشل ──
 * الأقسام التي لا تعتمد على الشبكة تُعرض كاملة دائمًا. قسم التغطية
 * وحده يُخفى، ويظهر مكانه سبب الفشل مع زر إعادة محاولة. البديل —
 * إخفاء الصفحة كلها خلف شاشة تحميل — يجعل انقطاعًا في واجهة
 * ثانوية يُسقط صفحة التسويق بأكملها.
 */

import {
  Button,
  Icon,
  Spinner,
  byReach,
  fetchNetwork,
  t,
  useApi,
} from "@walaee/shared";

import { Coverage } from "./sections/Coverage";
import { Faq } from "./sections/Faq";
import { ForMerchants } from "./sections/ForMerchants";
import { Footer } from "./sections/Footer";
import { Header } from "./sections/Header";
import { Hero } from "./sections/Hero";
import { HowItWorks } from "./sections/HowItWorks";
import { Pricing } from "./sections/Pricing";

export function App() {
  const network = useApi((signal) => fetchNetwork(signal), []);
  const data = network.data;

  return (
    <>
      <a className="skip" href="#top">
        {t("تخطَّ إلى المحتوى")}
      </a>

      <Header />

      <main>
        <Hero
          stats={data?.stats ?? null}
          brands={data ? byReach(data.brands) : []}
        />

        {data ? (
          <Coverage network={data} />
        ) : (
          <section className="section coverage-fallback" id="coverage">
            <div className="wrap">
              {network.loading ? (
                <p className="coverage-loading">
                  <Spinner size={22} />
                  {t("جارٍ تحميل خريطة التغطية…")}
                </p>
              ) : (
                <div className="coverage-error">
                  <Icon name="alert" size={26} />
                  <h2>{t("تعذّر تحميل خريطة التغطية")}</h2>
                  <p>
                    {t("باقي الصفحة يعمل. جرّب مرة أخرى بعد لحظات، أو ادخل إلى التطبيق مباشرةً.")}
                  </p>
                  <Button onClick={network.reload}>{t("إعادة المحاولة")}</Button>
                </div>
              )}
            </div>
          </section>
        )}

        <HowItWorks />
        <ForMerchants />
        <Pricing />
        <Faq />
      </main>

      <Footer merchants={data?.stats.brands ?? 0} />
    </>
  );
}
