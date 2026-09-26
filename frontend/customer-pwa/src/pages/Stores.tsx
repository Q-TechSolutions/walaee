/**
 * المتاجر — تصفّح أولًا، ثم «قريب مني» عند الطلب.
 *
 * الترتيب هنا انعكس عن النسخة السابقة، وهذا هو التغيير المهم:
 * الشاشة كانت تفتح فارغة إلى أن يمنح المستخدم إذن الموقع. من
 * يرفض — وأغلب الناس ترفض إذنًا يُطلب بلا سبب ظاهر — كان يرى
 * شاشة بيضاء ويستنتج أن المنصة بلا متاجر.
 *
 * الآن تفتح الشاشة على بطاقاته ثم الخريطة والدليل كاملين بلا أي
 * إذن. زر الموقع يبقى لمن يريده، ورفضه يكلّف ترتيبًا بالمسافة لا
 * محتوى الشاشة كله.
 *
 * كل صف يحمل حرف علامته بلونها لا أيقونة متجر موحّدة: دليل من
 * تسعين صفًّا بأيقونة واحدة مكرّرة لا يُمسَح بالعين، والعميل الذي
 * يبحث عن متجر يعرف لونه في محفظته لا يجد ما يربط بينهما.
 */

import { useDeferredValue, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import {
  Badge,
  EgyptMap,
  Empty,
  ErrorBox,
  Icon,
  Loading,
  fetchNetwork,
  fmt,
  t,
  useApi,
} from "@walaee/shared";

import { queries } from "../lib/queries";
import type { NearbyStore } from "../lib/queries";

type Near =
  | { kind: "off" }
  | { kind: "locating" }
  | { kind: "ready"; stores: NearbyStore[] }
  | { kind: "error"; error: unknown };

export function Stores() {
  const network = useApi((signal) => fetchNetwork(signal), []);
  const cards = useApi((signal) => queries.cards(signal), []);
  const [governorate, setGovernorate] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [near, setNear] = useState<Near>({ kind: "off" });

  // البحث يُؤجَّل عن الكتابة: تصفية تسعين علامة عند كل ضغطة زر
  // تجعل الحقل يتلعثم على هاتف متوسط
  const needle = useDeferredValue(query).trim().toLowerCase();

  function locate() {
    if (!("geolocation" in navigator)) {
      setNear({
        kind: "error",
        error: new Error(t("متصفحك لا يدعم تحديد الموقع.")),
      });
      return;
    }

    setNear({ kind: "locating" });

    navigator.geolocation.getCurrentPosition(
      async (position) => {
        try {
          const stores = await queries.nearby(
            position.coords.latitude,
            position.coords.longitude,
          );
          setNear({ kind: "ready", stores });
        } catch (error) {
          setNear({ kind: "error", error });
        }
      },
      () => {
        setNear({
          kind: "error",
          error: new Error(
            t("تعذّر تحديد موقعك. فعّل إذن الموقع من إعدادات المتصفح ثم حاول مجددًا."),
          ),
        });
      },
      { enableHighAccuracy: false, timeout: 10_000, maximumAge: 60_000 },
    );
  }

  const branches = useMemo(() => {
    if (!network.data) return [];
    return network.data.branches.filter(
      (branch) => !governorate || branch.governorate === governorate,
    );
  }, [network.data, governorate]);

  /** الفئة تعيش على العلامة لا على الفرع — تُجلب من قائمة العلامات. */
  const categoryOf = useMemo(() => {
    const map = new Map<string, string>();
    for (const brand of network.data?.brands ?? []) map.set(brand.slug, brand.category);
    return map;
  }, [network.data]);

  /** الفروع مجمّعة تحت علامتها — صفّان لنفس المتجر في نفس المدينة ضجيج. */
  const grouped = useMemo(() => {
    const map = new Map<
      string,
      { name: string; color: string; category: string; cities: string[] }
    >();
    for (const branch of branches) {
      const entry = map.get(branch.brand_slug) ?? {
        name: branch.brand_name,
        color: branch.color,
        category: categoryOf.get(branch.brand_slug) ?? "",
        cities: [],
      };
      if (!entry.cities.includes(branch.city || branch.governorate_name)) {
        entry.cities.push(branch.city || branch.governorate_name);
      }
      map.set(branch.brand_slug, entry);
    }

    const rows = [...map.entries()].sort(
      (a, b) => b[1].cities.length - a[1].cities.length,
    );

    if (!needle) return rows;
    // البحث يشمل الفئة والمدن: من يكتب «قهوة» أو «أسيوط» يقصد
    // متاجرها، لا متجرًا اسمه كذلك
    return rows.filter(
      ([, brand]) =>
        brand.name.toLowerCase().includes(needle) ||
        brand.category.toLowerCase().includes(needle) ||
        brand.cities.some((city) => city.toLowerCase().includes(needle)),
    );
  }, [branches, categoryOf, needle]);

  const chosen =
    network.data?.governorates.find((item) => item.code === governorate) ?? null;

  return (
    <>
      <header className="mhead">
        <div className="grow">
          <h1>{t("المتاجر")}</h1>
          <p className="sub">{t("متاجر تقبل ولائي في كل محافظة")}</p>
        </div>
      </header>

      <div className="pad section">
        {/* ── البحث ── */}
        <div className="searchbox">
          <Icon name="search" size={18} />
          <input
            className="input"
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder={t("ابحث عن متجر أو فئة أو مدينة…")}
            aria-label={t("ابحث عن متجر أو فئة أو مدينة…")}
          />
        </div>

        {/* ── قريب مني ── */}
        <section className="near">
          {near.kind === "off" && (
            <button type="button" className="near-cta" onClick={locate}>
              <Icon name="mapPin" size={20} />
              <span className="grow">
                <b>{t("اعرف الأقرب لك")}</b>
                <span className="t-sm muted">
                  {" "}
                  {t("— نستخدم موقعك ولا نحتفظ به")}
                </span>
              </span>
              <Icon name="chevronLeft" size={18} />
            </button>
          )}

          {near.kind === "locating" && <Loading label={t("جارٍ تحديد موقعك…")} />}

          {near.kind === "error" && <ErrorBox error={near.error} onRetry={locate} />}

          {near.kind === "ready" && (
            <>
              <div className="sec-t">
                <h3>{t("الأقرب إليك")}</h3>
              </div>
              {near.stores.length === 0 ? (
                <p className="muted t-sm">
                  {t("لا توجد فروع قريبة. تصفّح الخريطة بالأسفل.")}
                </p>
              ) : (
                <div className="card card-p">
                  {near.stores.map((store) => (
                    <Link
                      key={store.branch_id}
                      to={store.is_member ? `/cards/${store.brand_id}` : "/scan"}
                      className="li"
                      style={
                        { "--brand": store.primary_color } as React.CSSProperties
                      }
                    >
                      <span className="av brandav" aria-hidden="true">
                        {store.brand_name.trim().charAt(0)}
                      </span>
                      <div className="grow">
                        <p className="li-t">{store.brand_name}</p>
                        {/* المسافة أولًا: الفاصل «·» بجوار رقم
                            عربي-هندي يُقرأ صفرًا زائدًا */}
                        <p className="li-s">
                          <span className="num">
                            {fmt.number(store.distance_km, 1)}
                          </span>{" "}
                          {t("كم")} · {store.branch_name}
                        </p>
                      </div>
                      {store.is_member ? (
                        <Badge tone="green">{t("عضو")}</Badge>
                      ) : (
                        <Badge tone="violet">{t("جديد")}</Badge>
                      )}
                    </Link>
                  ))}
                </div>
              )}
            </>
          )}
        </section>

        {/* ── بطاقاتك النشطة ── */}
        {cards.data && cards.data.length > 0 && !needle && (
          <>
            <div className="sec-t">
              <h3>{t("بطاقاتك النشطة")}</h3>
              <Link to="/">{t("المحفظة")}</Link>
            </div>

            <div className="card card-p">
              {cards.data.map((card) => {
                const balance =
                  card.balances.find(
                    (b) => b.next_reward?.id === card.next_reward?.id,
                  ) ?? card.balances[0];

                return (
                  <Link
                    key={card.brand_id}
                    to={`/cards/${card.brand_id}`}
                    className="li"
                    style={
                      { "--brand": card.primary_color } as React.CSSProperties
                    }
                  >
                    <span className="av brandav" aria-hidden="true">
                      {card.brand_name.trim().charAt(0)}
                    </span>
                    <div className="grow">
                      <p className="li-t">{card.brand_name}</p>
                      {/* الكسر نصّ واحد لا عنصرين: فصلهما يقطع مقطع
                          الأرقام فيعكس المتصفّح ترتيبه، و«٣٤٠ من
                          ٤٥٠» تُعرض «٤٥٠/٣٤٠» */}
                      <p className="li-s">
                        <span className="num">
                          {card.next_reward
                            ? `${fmt.number(balance?.amount ?? 0)}/${fmt.number(card.next_reward.cost_amount)}`
                            : fmt.number(balance?.amount ?? 0)}
                        </span>{" "}
                        {fmt.unit(
                          card.next_reward?.cost_amount ?? balance?.amount ?? 0,
                          balance?.unit_label ?? "",
                        )}
                        {card.category && ` · ${t(card.category)}`}
                      </p>
                    </div>
                    <Icon name="chevronLeft" size={18} />
                  </Link>
                );
              })}
            </div>
          </>
        )}

        {/* ── الشبكة كلها ── */}
        {network.loading && <Loading label={t("جارٍ تحميل الشبكة…")} />}

        {network.error != null && (
          <ErrorBox error={network.error} onRetry={network.reload} />
        )}

        {network.data && (
          <section className="net">
            <div className="sec-t">
              <h3>{t("شبكة ولائي")}</h3>
            </div>
            <p className="t-sm muted mb">
              <span className="num">{fmt.number(network.data.stats.branches)}</span>{" "}
              {t("فرعًا في")}{" "}
              <span className="num">
                {fmt.number(network.data.stats.governorates)}
              </span>{" "}
              {t("محافظة. اضغط على محافظة لعرض متاجرها.")}
            </p>

            <div className="card wl-card-p mb">
              <EgyptMap
                governorates={network.data.governorates}
                branches={network.data.branches}
                selected={governorate}
                onSelect={setGovernorate}
                compact
              />
            </div>

            <div className="row between mb">
              {/* العدد في عنصره لا خلف فاصل: «كل المحافظات · ١٥» كان
                  يُقرأ «١٥٠» لأن «·» بجوار رقم عربي-هندي يشبه صفرًا */}
              <h3 className="w-7">
                {chosen ? t(chosen.name) : t("كل المحافظات")}
                <span className="muted t-sm">
                  {" — "}
                  <span className="num">{fmt.number(grouped.length)}</span>{" "}
                  {t("متجرًا")}
                </span>
              </h3>
              {(governorate || needle) && (
                <button
                  type="button"
                  className="link"
                  onClick={() => {
                    setGovernorate(null);
                    setQuery("");
                  }}
                >
                  {t("عرض الكل")}
                </button>
              )}
            </div>

            {grouped.length === 0 ? (
              <Empty
                icon="search"
                title={t("لا يوجد متجر بهذا الاسم")}
                hint={t("جرّب اسم فئة أو مدينة، أو اعرض الكل.")}
              />
            ) : (
              <div className="card card-p">
                {grouped.map(([slug, brand]) => (
                  <div
                    key={slug}
                    className="li"
                    style={{ "--brand": brand.color } as React.CSSProperties}
                  >
                    <span className="av brandav" aria-hidden="true">
                      {brand.name.trim().charAt(0)}
                    </span>
                    <div className="grow">
                      <p className="li-t">{brand.name}</p>
                      <p className="li-s">
                        {/* ثلاث مدن ثم «و٤ غيرها»: القائمة الكاملة تكسر
                            السطر على الهاتف وتدفن اسم المتجر */}
                        {brand.cities
                          .slice(0, 3)
                          .map((city) => t(city))
                          .join(" · ")}
                        {brand.cities.length > 3 &&
                          ` ${t("و{n} غيرها", { n: fmt.number(brand.cities.length - 3) })}`}
                      </p>
                    </div>
                    <span className="li-v num muted">
                      {fmt.number(brand.cities.length)}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </section>
        )}
      </div>
    </>
  );
}
