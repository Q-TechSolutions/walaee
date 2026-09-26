/**
 * التغطية — الخريطة ودليل المتاجر.
 *
 * هذا هو قسم البرهان في الصفحة. كل ما قبله كلام، وهذا ما يثبته.
 * لذلك لا يحمل رقمًا واحدًا مكتوبًا في الكود: كله من
 * `/public/network`، وإن سقط النداء يظهر سبب الفشل بدل أن تُعرَض
 * تغطية لا وجود لها.
 *
 * الخريطة والقائمة متصلتان في الاتجاهين: الضغط على محافظة يصفّي
 * القائمة، والضغط على محافظة في شريط المرشّحات يُبرزها على
 * الخريطة. الفصل بينهما كان سيجعل الخريطة زينة — ومن يفتح صفحة
 * تغطية يريد أن يعرف «هل أنتم عندي؟» لا أن يرى رسمًا جميلًا.
 */

import { useMemo, useState } from "react";

import {
  Badge,
  EgyptMap,
  Icon,
  categoryIcon,
  fmt,
  t,
} from "@walaee/shared";
import type { PublicNetwork } from "@walaee/shared";

const PROGRAM_LABELS: Record<string, string> = {
  points: "نقاط",
  stamps: "أختام",
  visits: "زيارات",
  cashback: "استرداد نقدي",
  rewards: "مكافآت",
  gifts: "هدايا",
};

export function Coverage({ network }: { network: PublicNetwork }) {
  const [governorate, setGovernorate] = useState<string | null>(null);
  const [category, setCategory] = useState<string | null>(null);

  const covered = useMemo(
    () =>
      network.governorates
        .filter((item) => item.branch_count > 0)
        .sort((a, b) => b.branch_count - a.branch_count),
    [network.governorates],
  );

  const brands = useMemo(() => {
    return network.brands
      .filter((brand) => !category || brand.category === category)
      .filter((brand) => !governorate || brand.governorates.includes(governorate))
      .sort((a, b) => b.branch_count - a.branch_count);
  }, [network.brands, category, governorate]);

  const chosen = covered.find((item) => item.code === governorate) ?? null;

  /** عدد فروع المتجر داخل المحافظة المختارة وحدها. */
  function reachOf(slug: string): number {
    if (!governorate) {
      return network.brands.find((b) => b.slug === slug)?.branch_count ?? 0;
    }
    return network.branches.filter(
      (branch) => branch.brand_slug === slug && branch.governorate === governorate,
    ).length;
  }

  return (
    <section className="section coverage" id="coverage">
      <div className="wrap">
        <header className="section-head">
          <span className="eyebrow">
            <Icon name="map" size={15} />
            {t("التغطية")}
          </span>
          <h2>{t("فين تلاقينا؟")}</h2>
          <p className="section-lede">
            {t("كل نقطة على الخريطة فرع شغّال فعلًا ببرنامج ولاء على المنصة. اضغط على أي محافظة تشوف متاجرها.")}
          </p>
        </header>

        <div className="coverage-grid">
          <div className="coverage-map card">
            <EgyptMap
              governorates={network.governorates}
              branches={network.branches}
              selected={governorate}
              onSelect={setGovernorate}
            />

            <footer className="coverage-legend">
              <span>
                <b className="num">{fmt.number(network.stats.branches)}</b> {t("فرعًا")}
              </span>
              <span aria-hidden="true">·</span>
              <span>
                <b className="num">{fmt.number(network.stats.cities)}</b> {t("مدينة")}
              </span>
              <span aria-hidden="true">·</span>
              <span>
                <b className="num">{fmt.number(network.stats.governorates)}</b> {t("محافظة من")} <span className="num">27</span>
              </span>
            </footer>
          </div>

          <aside className="coverage-side">
            <h3>{t("أكثر المحافظات تغطية")}</h3>
            <ol className="gov-list">
              {covered.slice(0, 10).map((item) => {
                const share = Math.round(
                  (item.branch_count / network.stats.branches) * 100,
                );
                return (
                  <li key={item.code}>
                    <button
                      type="button"
                      className={`gov-row ${governorate === item.code ? "is-on" : ""}`}
                      aria-pressed={governorate === item.code}
                      onClick={() =>
                        setGovernorate(governorate === item.code ? null : item.code)
                      }
                    >
                      <span className="gov-name">{t(item.name)}</span>
                      {/* الشريط نسبة لا عدد: «١٢ فرعًا» لا تعني شيئًا
                          وحدها، و«١٤٪ من الشبكة» تعني */}
                      <span className="gov-bar" aria-hidden="true">
                        <span style={{ width: `${Math.max(share, 3)}%` }} />
                      </span>
                      <span className="gov-count num">{item.branch_count}</span>
                    </button>
                  </li>
                );
              })}
            </ol>
          </aside>
        </div>

        {/* ── الدليل ── */}
        <div className="dir">
          <div className="dir-head">
            <h3>
              {chosen
                ? t("متاجر {gov}", { gov: t(chosen.name) })
                : t("المتاجر المتعاقدة")}
              <span className="dir-count num">{brands.length}</span>
            </h3>

            <div className="chips" role="group" aria-label={t("تصفية حسب الفئة")}>
              <button
                type="button"
                className={`chip ${!category ? "is-on" : ""}`}
                aria-pressed={!category}
                onClick={() => setCategory(null)}
              >
                {t("الكل")}
              </button>
              {network.categories.map((name) => (
                <button
                  key={name}
                  type="button"
                  className={`chip ${category === name ? "is-on" : ""}`}
                  aria-pressed={category === name}
                  onClick={() => setCategory(category === name ? null : name)}
                >
                  <Icon name={categoryIcon(name)} size={15} />
                  {t(name)}
                </button>
              ))}
            </div>
          </div>

          {(governorate || category) && (
            <button type="button" className="dir-clear" onClick={() => {
              setGovernorate(null);
              setCategory(null);
            }}>
              <Icon name="close" size={14} />
              {t("إزالة التصفية")}
            </button>
          )}

          {brands.length === 0 ? (
            <p className="dir-empty">
              {t("مفيش متجر بالمواصفات دي لسه. جرّب محافظة تانية أو شيل التصفية.")}
            </p>
          ) : (
            <ul className="dir-grid">
              {brands.map((brand) => (
                <li
                  key={brand.slug}
                  className="merchant"
                  style={{ "--brand": brand.color } as React.CSSProperties}
                >
                  <span className="merchant-icon">
                    <Icon name={categoryIcon(brand.category)} size={20} />
                  </span>

                  <div className="grow">
                    <p className="merchant-name">{brand.name}</p>
                    <p className="merchant-tag">{brand.tagline || brand.category}</p>

                    <div className="merchant-meta">
                      <span>
                        <Icon name="store" size={14} />
                        <span className="num">{reachOf(brand.slug)}</span> {t("فرع")}
                        {governorate ? ` ${t("في {gov}", { gov: t(chosen?.name ?? "") })}` : ""}
                      </span>
                      {brand.program_type && (
                        <Badge tone="violet">
                          {t(PROGRAM_LABELS[brand.program_type] ?? brand.program_type)}
                        </Badge>
                      )}
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </section>
  );
}
