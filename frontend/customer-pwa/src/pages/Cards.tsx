/**
 * الشاشة الرئيسية — محفظة البطاقات.
 *
 * التخطيط مطابق للعرض المعتمد: تحية، ثم شريط «أقرب مكافأة»، ثم
 * سلسلة الزيارات، ثم دعوة التثبيت، ثم البطاقات، ثم آخر نشاط.
 * لكن **كل رقم فيها من الخادم**: الأرصدة والأهداف من `/me/cards`،
 * والسلسلة من `/me/summary` محسوبة من العمليات المؤكَّدة.
 *
 * الشريط العلوي في العرض كان «مستواك». لا يوجد سلّم مستويات في
 * المنتج — `Membership.tier` حقل نصّي لا يحسبه شيء — فاخترعه هنا
 * كان سيعني وعدًا بمزايا غير موجودة. مكانه يشغله ما هو حقيقي
 * ويؤدّي نفس الوظيفة: أقرب مكافأة إلى الاكتمال عبر كل البطاقات،
 * وهي الإجابة على السؤال الذي يفتح العميل التطبيق من أجله.
 *
 * ما لا يوجد له مصدر حقيقي لا يُرسَم: دعوة التثبيت تظهر فقط حين
 * يعرضها المتصفّح فعلًا. عنصرٌ مزيّن برقم مخترَع يكشف نفسه في أول
 * عرض أمام عميل حقيقي.
 */

import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import {
  Empty,
  ErrorBox,
  Icon,
  Loading,
  fmt,
  t,
  useApi,
} from "@walaee/shared";

import { queries } from "../lib/queries";
import type { Card, WeekDay } from "../lib/queries";

/** عدد صفوف النشاط على الرئيسية — البقية خلف «الكل». */
const RECENT = 4;

/** مفتاح رفض دعوة التثبيت. لكل متصفّح على حدة — وهو المطلوب. */
const DISMISS_KEY = "walaee.a2hs.dismissed";

export function Cards() {
  const cards = useApi((signal) => queries.cards(signal), []);
  const summary = useApi((signal) => queries.summary(signal), []);
  const me = useApi((signal) => queries.me(signal), []);
  const activity = useApi((signal) => queries.activity(1, signal), []);
  const inbox = useApi((signal) => queries.notifications(signal), []);

  const firstName = (me.data?.full_name ?? "").trim().split(" ")[0];
  const pending = summary.data?.pending_redemptions ?? 0;
  const unread = inbox.data?.unread ?? 0;

  // أقرب هدف عبر كل البطاقات — أعلى نسبة اكتمال، لا أكبر رصيد:
  // من عنده ٩٠٠ نقطة على هدف ٥٠٠٠ أبعد ممن عنده ٩ أختام من ١٠
  const closest = (cards.data ?? [])
    .filter((card) => card.next_reward !== null)
    .sort((a, b) => (b.next_reward?.progress ?? 0) - (a.next_reward?.progress ?? 0))[0];

  return (
    <>
      <header className="mhead">
        <div className="grow">
          <h1>
            {firstName ? t("أهلًا {name}", { name: firstName }) : t("أهلًا بك")}
          </h1>
          <p className="sub">
            {pending > 0
              ? t("عندك {what}", {
                  what: fmt.plural(pending, {
                    zero: t("لا مكافآت جاهزة"),
                    one: t("مكافأة جاهزة للاستبدال"),
                    two: t("مكافأتان جاهزتان للاستبدال"),
                    few: t("مكافآت جاهزة للاستبدال"),
                    many: t("مكافأة جاهزة للاستبدال"),
                  }),
                })
              : t("كل بطاقاتك في مكان واحد")}
          </p>
        </div>

        <Link to="/notifications" className="iconbtn" aria-label={t("الإشعارات")}>
          <Icon name="bell" size={19} />
          {/* النقطة تظهر لما وصل ولم يُقرأ — لا لعدد المكافآت:
              الجرس يعد بإشعار، فإظهاره لشيء آخر يعلّم العميل
              تجاهله */}
          {unread > 0 && <span className="nd" aria-hidden="true" />}
        </Link>
      </header>

      <div className="pad section">
        {closest && <ClosestReward card={closest} />}

        {summary.data?.week && <WeekStreak week={summary.data.week} />}

        <InstallPrompt />

        {pending > 0 && (
          <Link to="/rewards" className="alert-strip">
            <Icon name="gift" size={18} />
            <span className="grow">
              <span className="num w-8">{fmt.number(pending)}</span>{" "}
              {t("كود استبدال بانتظار الصرف")}
            </span>
            <Icon name="chevronLeft" size={18} />
          </Link>
        )}

        <div className="sec-t">
          <h3>{t("بطاقاتي")}</h3>
          <Link to="/stores">{t("كل المتاجر")}</Link>
        </div>

        {cards.loading && <Loading />}

        {cards.error != null && (
          <ErrorBox error={cards.error} onRetry={cards.reload} />
        )}

        {cards.data?.length === 0 && (
          <Empty
            icon="card"
            title={t("محفظتك فاضية لسه")}
            hint={t("امسح كود المتجر عند الكاشير وابدأ تجمّع من أول زيارة.")}
          />
        )}

        <div className="stack gap">
          {cards.data?.map((card, index) => (
            <LoyaltyCard key={card.brand_id} card={card} index={index} />
          ))}
        </div>

        {activity.data && activity.data.results.length > 0 && (
          <>
            <div className="sec-t">
              <h3>{t("نشاطك الأخير")}</h3>
              <Link to="/activity">{t("الكل")}</Link>
            </div>

            <div className="card card-p">
              {activity.data.results.slice(0, RECENT).map((line) => {
                const delta = Number(line.delta);
                return (
                  <Link
                    key={line.id}
                    to={line.transaction ? `/activity/${line.transaction}` : "/activity"}
                    className="li"
                  >
                    <span
                      className={`ibox ${delta > 0 ? "g" : "o"}`}
                      aria-hidden="true"
                    >
                      <Icon name={delta > 0 ? "plus" : "gift"} size={18} />
                    </span>
                    <div className="grow">
                      <p className="li-t">{line.brand_name}</p>
                      <p className="li-s">
                        {t(line.reason_label)} · {fmt.relativeTime(line.created_at)}
                      </p>
                    </div>
                    <span
                      className={`li-v num ${delta > 0 ? "c-green" : "c-orange"}`}
                    >
                      {delta > 0 ? "+" : ""}
                      {fmt.number(line.delta)}
                    </span>
                  </Link>
                );
              })}
            </div>
          </>
        )}
      </div>
    </>
  );
}

/* ══════════════ أقرب مكافأة ══════════════ */

/**
 * الشريط البنفسجي أعلى المحفظة.
 *
 * يجيب عن «إيه أقرب حاجة أقدر آخدها؟» — وهو السؤال الذي يفتح
 * العميل التطبيق من أجله. الضغط ينقله إلى البطاقة صاحبة الهدف
 * مباشرةً لا إلى قائمة يبحث فيها عنها.
 */
function ClosestReward({ card }: { card: Card }) {
  const target = card.next_reward!;
  const remaining = Number(target.remaining);
  const done = remaining <= 0;

  return (
    <Link to={`/cards/${card.brand_id}`} className="tier">
      <span className="tb" aria-hidden="true">
        <Icon name={done ? "checkCircle" : "target"} size={20} />
      </span>

      <div className="grow">
        <b>{target.title}</b>
        {/* السطر جملة واحدة لا أجزاء في عناصر: `.tier span` يجعل
            كل span بداخله كتلةً، فكان الرقم يقفز إلى سطر وحده */}
        <span>
          {done
            ? t("جاهزة الآن — من {brand}", { brand: card.brand_name })
            : t("باقي {n} {unit} في {brand}", {
                n: fmt.number(remaining),
                unit: fmt.unit(remaining, target.unit_label),
                brand: card.brand_name,
              })}
        </span>
        <div className="tp">
          <i style={{ width: `${Math.round(target.progress * 100)}%` }} />
        </div>
      </div>

      <Icon name="chevronLeft" size={18} />
    </Link>
  );
}

/* ══════════════ بطاقة واحدة ══════════════ */

function LoyaltyCard({ card, index }: { card: Card; index: number }) {
  // الرصيد المعروض هو رصيد البرنامج صاحب الهدف الأقرب، فيتطابق
  // الرقم الكبير مع شريط التقدّم تحته. عرض أول رصيد بلا مراعاة
  // ذلك كان يُظهر «٨٢٠ نقطة» فوق شريط يقيس الأختام.
  const target = card.next_reward;
  const balance =
    card.balances.find((b) => b.next_reward?.id === target?.id) ??
    card.balances[0];

  const initial = card.brand_name.trim().charAt(0);
  const expires = balance?.expires_at;

  return (
    <Link
      to={`/cards/${card.brand_id}`}
      className={`lcard anim d${Math.min(index + 1, 6)}`}
      style={{ "--brand": card.primary_color } as React.CSSProperties}
    >
      <div className="lc-top">
        <span className="lc-logo" aria-hidden="true">
          {initial}
        </span>
        <div className="grow">
          <p className="lc-name">{card.brand_name}</p>
          <p className="lc-cat">
            {card.category ? t(card.category) : balance?.program_name}
          </p>
        </div>
        <Icon name="chevronLeft" size={18} />
      </div>

      <div className="lc-mid">
        <div>
          <p className="lc-val num">{fmt.number(balance?.amount ?? 0)}</p>
          <p className="lc-unit">
            {target
              ? t("من {n} {unit}", {
                  n: fmt.number(target.cost_amount),
                  unit: fmt.unit(target.cost_amount, balance?.unit_label ?? ""),
                })
              : fmt.unit(balance?.amount ?? 0, balance?.unit_label ?? "")}
          </p>
        </div>
        {target && <span className="lc-rew">{target.title}</span>}
      </div>

      {target && (
        <>
          <div className="lc-bar">
            <i style={{ width: `${Math.round(target.progress * 100)}%` }} />
          </div>
          <div className="lc-foot">
            <span>
              <span className="num">{fmt.share(target.progress * 100)}</span>{" "}
              {t("من الهدف")}
            </span>
            {expires && (
              <span>
                {t("تنتهي")} {fmt.date(expires)}
              </span>
            )}
          </div>
        </>
      )}
    </Link>
  );
}

/* ══════════════ سلسلة الزيارات ══════════════ */

function WeekStreak({ week }: { week: WeekDay[] }) {
  const visits = week.filter((day) => day.visited).length;

  return (
    <section className="card wl-card-p">
      <div className="row between mb-2">
        <h3 className="t-md w-8">{t("زياراتك هذا الأسبوع")}</h3>
        <span className={`badge ${visits > 0 ? "bg-g" : "bg-n"}`}>
          <span className="num">{fmt.number(visits)}</span> {t("من")}{" "}
          <span className="num">{t("٧")}</span>
        </span>
      </div>

      <div className="streak">
        {week.map((day) => (
          <i
            key={day.date}
            className={day.today ? "today" : day.visited ? "on" : ""}
            title={fmt.date(day.date)}
          >
            {t(day.letter)}
          </i>
        ))}
      </div>

      <p className="t-sm muted mt-2">
        {visits === 0
          ? t("مفيش زيارات الأسبوع ده. أقرب متجر مستنيك.")
          : t("كل زيارة بتتسجّل أول ما الكاشير يأكّد العملية.")}
      </p>
    </section>
  );
}

/* ══════════════ دعوة التثبيت ══════════════ */

interface InstallEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

/** مثبَّت بالفعل — لا دعوة ولا إرشاد. */
function isStandalone(): boolean {
  if (typeof window === "undefined") return false;
  return (
    window.matchMedia?.("(display-mode: standalone)").matches === true ||
    // Safari على iOS لا يدعم display-mode ويعلن الحالة هنا
    (window.navigator as { standalone?: boolean }).standalone === true
  );
}

/** Safari على iOS — الوحيد الذي لا يُطلق `beforeinstallprompt` أبدًا. */
function isIosSafari(): boolean {
  if (typeof navigator === "undefined") return false;
  const ua = navigator.userAgent;
  const ios = /iPad|iPhone|iPod/.test(ua) ||
    // iPadOS يعلن نفسه ماكنتوش، ويُميَّز باللمس
    (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
  // كروم وفايرفوكس على iOS يلفّان WebKit ولا يملكان زر «أضف للشاشة»
  return ios && !/CriOS|FxiOS|EdgiOS/.test(ua);
}

/**
 * دعوة التثبيت — بمسارين لأن المتصفّحات مساران.
 *
 * `beforeinstallprompt` حدث كروم وأندرويد، **ولا يُطلَق على iOS
 * إطلاقًا**. الاعتماد عليه وحده كان يعني أن شريحة iOS — وهي
 * الأعلى إنفاقًا في السوق المستهدف حسب التقرير (م-١٣) — لا ترى
 * الدعوة أبدًا. ومنتج ولاء يعيش على إعادة التفاعل، وإشعارات
 * الويب على iOS لا تعمل إلا بعد الإضافة إلى الشاشة الرئيسية
 * يدويًا. فالنتيجة: أغلى شريحة لا يصلها إشعار واحد.
 *
 * ولأن iOS لا يملك زرًّا يُضغط، يُعرض الإرشاد اليدوي بدله: خطوتان
 * بالاسم وبالأيقونة، لا جملة عامة «أضفه للشاشة».
 *
 * ولا شيء يُعرض لمن ثبّته بالفعل: دعوةٌ لفعل تمّ تجعل القارئ
 * يشكّ في أن التطبيق يعرف حالته.
 */
function InstallPrompt() {
  const [event, setEvent] = useState<InstallEvent | null>(null);
  const [dismissed, setDismissed] = useState(() => {
    // رفض الدعوة يُحترَم: إعادة عرضها كل فتحة هي الطريقة الأسرع
    // لتعليم العميل تجاهل كل ما في أعلى الشاشة
    try {
      return localStorage.getItem(DISMISS_KEY) === "1";
    } catch {
      return false;
    }
  });

  useEffect(() => {
    const onPrompt = (e: Event) => {
      // منع الشريط الافتراضي حتى نعرضه في مكاننا وبنصّنا
      e.preventDefault();
      setEvent(e as InstallEvent);
    };
    window.addEventListener("beforeinstallprompt", onPrompt);
    return () => window.removeEventListener("beforeinstallprompt", onPrompt);
  }, []);

  function dismiss() {
    setDismissed(true);
    try {
      localStorage.setItem(DISMISS_KEY, "1");
    } catch {
      /* وضع التصفّح الخاص — الرفض يعيش لهذه الجلسة وحدها */
    }
  }

  if (dismissed || isStandalone()) return null;

  if (event) {
    return (
      <div className="a2hs">
        <span className="ic" aria-hidden="true">
          <Icon name="phone" size={20} />
        </span>
        <div className="grow">
          <b>{t("ثبّت ولائي على شاشتك")}</b>
          <span>{t("يفتح زي أي تطبيق، ويوصلك إشعار أول ما تجهز مكافأة.")}</span>
        </div>
        <button
          type="button"
          className="btn btn-sm"
          style={{ background: "#fff", color: "var(--violet-700)" }}
          onClick={async () => {
            await event.prompt();
            await event.userChoice;
            setEvent(null);
          }}
        >
          {t("تثبيت")}
        </button>
      </div>
    );
  }

  if (!isIosSafari()) return null;

  return (
    <div className="a2hs a2hs-ios">
      <div className="row between">
        <div className="row">
          <span className="ic" aria-hidden="true">
            <Icon name="phone" size={20} />
          </span>
          <b>{t("ثبّت ولائي على شاشتك")}</b>
        </div>
        <button
          type="button"
          className="a2hs-x"
          onClick={dismiss}
          aria-label={t("إخفاء")}
        >
          <Icon name="close" size={16} />
        </button>
      </div>

      <span className="mt-2">
        {t("إشعارات المكافآت على آيفون لا تعمل إلا بعد إضافته للشاشة الرئيسية.")}
      </span>

      <ol className="a2hs-steps">
        <li>
          <Icon name="external" size={15} /> {t("اضغط زر المشاركة أسفل المتصفّح")}
        </li>
        <li>
          <Icon name="plus" size={15} /> {t("اختر «إضافة إلى الشاشة الرئيسية»")}
        </li>
      </ol>
    </div>
  );
}
