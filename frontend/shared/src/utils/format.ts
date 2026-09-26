/**
 * تنسيق الأرقام والتواريخ بالعربية.
 *
 * الأرقام **عربية-هندية** (٠١٢٣…) كما في نظام التصميم المعتمد.
 * هذا قرار هوية: الواجهة عربية بالكامل، ورقم لاتيني وسط جملة
 * عربية يقطعها بصريًا ويجعل الشاشة تبدو مترجَمة لا مكتوبة.
 *
 * والاستثناء مقصود ومحصور: ما **يُطابَق حرفًا بحرف** مع شيء خارج
 * الشاشة يبقى لاتينيًا — رقم الهاتف، وكود نقطة البيع، ورقم
 * الفاتورة. الكاشير يقرأ هذه من ورقة مطبوعة أو من شاشة نظام آخر،
 * وتحويلها يجبره على الترجمة في رأسه عند كل مقارنة.
 *
 * الحدّ إذن: الكميات والمبالغ والتواريخ عربية، والمعرّفات لاتينية.
 */

import { getLocale, pick, t } from "../i18n/locale";

/**
 * الوسم واللغة يتبعان اختيار المستخدم.
 *
 * الأرقام **عربية-هندية في العربية** (٠١٢٣…) و**لاتينية في
 * الإنجليزية**. تثبيتها على العربية-الهندية في الوضعين كان يعطي
 * «1,240 customers» مكتوبة «١٬٢٤٠ customers» — سطرًا لا يقرؤه
 * قارئ أيٍّ من اللغتين.
 *
 * ويتغيّر معها أكثر من الخانات: فاصل الآلاف، وموضع رمز العملة،
 * وترتيب اليوم والشهر، وصيغة الاثني عشر ساعة. `Intl` يتكفّل بها
 * كلها ما دام الوسم صحيحًا.
 */
function tag(): string {
  return getLocale() === "ar" ? "ar-EG" : "en-EG";
}

function numerals(): "arab" | "latn" {
  return getLocale() === "ar" ? "arab" : "latn";
}

/**
 * خانات بنظام اللغة — للعناوين والنصوص السردية لا للمبالغ.
 *
 * في الإنجليزية تعود كما هي: النصّ الأصلي لاتيني أصلًا.
 */
export function toArabicDigits(value: string | number): string {
  if (getLocale() === "en") return String(value);
  return String(value).replace(/[0-9]/g, (d) => "٠١٢٣٤٥٦٧٨٩"[Number(d)]!);
}

/**
 * مبلغ بالجنيه.
 *
 * الخلفية تُرسل الأرقام المالية نصًّا لا رقمًا عشريًا، لأن
 * `number` في جافاسكريبت يفقد الدقة عند الكسور — و٠٫١ + ٠٫٢
 * لا تساوي ٠٫٣. التحويل هنا للعرض فقط ولا يُعاد إلى الخادم.
 */
export function money(value: string | number, currency = "EGP"): string {
  const amount = typeof value === "string" ? Number(value) : value;
  if (!Number.isFinite(amount)) return "—";

  return new Intl.NumberFormat(tag(), {
    style: "currency",
    currency,
    maximumFractionDigits: 2,
    numberingSystem: numerals(),
  }).format(amount);
}

/** رقم بلا عملة — للنقاط والأختام والعدّادات. */
export function number(value: string | number, digits = 0): string {
  const amount = typeof value === "string" ? Number(value) : value;
  if (!Number.isFinite(amount)) return "—";

  return new Intl.NumberFormat(tag(), {
    maximumFractionDigits: digits,
    numberingSystem: numerals(),
  }).format(amount);
}

/** رصيد بوحدته: «١٢٠ نقطة». */
export function balance(value: string | number, unit: string): string {
  return `${number(value)} ${unit}`;
}

/**
 * وحدة الرصيد مطابِقة لعددها.
 *
 * العربية تستعمل المفرد بعد ١١ فأكثر — «٦٠ نقطة» صحيحة — بينما
 * الإنجليزية تجمع: «60 point» خطأ يقرؤه كل متحدّث بالإنجليزية.
 * الوحدة تأتي من إعدادات التاجر ككلمة واحدة، فالجمع يُبنى هنا لا
 * يُطلَب منه إدخال صيغتين.
 *
 * الجمع بإضافة «s» يكفي لوحدات الولاء كلها (point/stamp/visit/
 * credit)، وما تُرجم جمعًا أصلًا يُترك كما هو.
 */
export function unit(count: string | number, label: string): string {
  const text = t(label);
  if (getLocale() === "ar") return text;

  const n = Math.abs(typeof count === "string" ? Number(count) : count);
  if (n === 1 || !text || text.endsWith("s")) return text;
  return `${text}s`;
}

export function percent(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  const sign = value > 0 ? "+" : "";
  return `${sign}${number(value, 1)}${pick("٪", "%")}`;
}

/**
 * نسبة بلا إشارة: «٧٦٪».
 *
 * `percent` يصف **تغيّرًا** فيضع «+» أمام الموجب. التقدّم نحو
 * مكافأة ليس تغيّرًا، و«+٧٦٪ من الهدف» جملة لا معنى لها. الفصل
 * هنا لأن استعمال الخطأ منهما يقرأ صحيحًا في المراجعة.
 *
 * تُبنى كنصّ واحد لا كرقم يليه علامة في عنصر آخر: فصلهما كان
 * يترك المتصفّح يضع «٪» في أول السطر لأن العلامة محايدة الاتجاه.
 */
export function share(value: number | null | undefined, digits = 0): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return "—";
  return `${number(value, digits)}${pick("٪", "%")}`;
}

/** تاريخ قصير: ٢٠ سبتمبر ٢٠٢٦. */
export function date(value: string | Date | null | undefined): string {
  if (!value) return "—";
  const d = typeof value === "string" ? new Date(value) : value;
  if (Number.isNaN(d.getTime())) return "—";

  return new Intl.DateTimeFormat(tag(), {
    day: "numeric",
    month: "long",
    year: "numeric",
    numberingSystem: numerals(),
  }).format(d);
}

/**
 * السنة وحدها: «٢٠٢٦».
 *
 * لخانة ضيّقة تحمل تسمية مثل «عضو منذ»: التاريخ الكامل ثلاث كلمات
 * تلتفّ على سطرين فيختلف ارتفاع الخانة عن جارتيها.
 */
export function year(value: string | Date | null | undefined): string {
  if (!value) return "—";
  const d = typeof value === "string" ? new Date(value) : value;
  if (Number.isNaN(d.getTime())) return "—";

  return new Intl.DateTimeFormat(tag(), {
    year: "numeric",
    numberingSystem: numerals(),
  }).format(d);
}

/**
 * يوم وشهر بلا سنة — لتسميات محور المخطط.
 *
 * السنة تتكرّر على كل عمود بلا أن تضيف شيئًا، وتأكل العرض الذي
 * يحتاجه اليوم نفسه حتى تتداخل التسميات.
 */
export function dayMonth(value: string | Date | null | undefined): string {
  if (!value) return "";
  const d = typeof value === "string" ? new Date(value) : value;
  if (Number.isNaN(d.getTime())) return "";

  return new Intl.DateTimeFormat(tag(), {
    day: "numeric",
    month: "short",
    numberingSystem: numerals(),
  }).format(d);
}

/** تاريخ ووقت — للسجلات حيث الدقيقة مهمة. */
export function dateTime(value: string | Date | null | undefined): string {
  if (!value) return "—";
  const d = typeof value === "string" ? new Date(value) : value;
  if (Number.isNaN(d.getTime())) return "—";

  return new Intl.DateTimeFormat(tag(), {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    numberingSystem: numerals(),
  }).format(d);
}

/**
 * الساعة والدقيقة وحدهما — لجدول «أحدث العمليات».
 *
 * بلا تاريخ: كل الصفوف من اليوم نفسه غالبًا، وتكرار التاريخ في
 * كل صف يزاحم أعمدة تحمل معلومة فعلية.
 */
export function clock(value: string | Date | null | undefined): string {
  if (!value) return "—";
  const d = typeof value === "string" ? new Date(value) : value;
  if (Number.isNaN(d.getTime())) return "—";

  return new Intl.DateTimeFormat(tag(), {
    hour: "2-digit",
    minute: "2-digit",
    numberingSystem: numerals(),
  }).format(d);
}

/**
 * زمن نسبي: «منذ ٥ دقائق».
 *
 * أوضح من الطابع المطلق في سجل النشاط: العميل يريد أن يعرف «متى
 * تقريبًا» لا الساعة بالثانية.
 */
export function relativeTime(value: string | Date | null | undefined): string {
  if (!value) return "—";
  const d = typeof value === "string" ? new Date(value) : value;
  if (Number.isNaN(d.getTime())) return "—";

  const seconds = Math.round((d.getTime() - Date.now()) / 1000);
  const formatter = new Intl.RelativeTimeFormat(tag(), { numeric: "auto" });

  const units: [Intl.RelativeTimeFormatUnit, number][] = [
    ["year", 31_536_000],
    ["month", 2_592_000],
    ["week", 604_800],
    ["day", 86_400],
    ["hour", 3_600],
    ["minute", 60],
  ];

  for (const [unit, size] of units) {
    if (Math.abs(seconds) >= size) {
      return formatter.format(Math.round(seconds / size), unit);
    }
  }
  return formatter.format(Math.round(seconds), "second");
}

/**
 * هاتف بصيغة مقروءة: ‎+20 10 1234 5678.
 *
 * يُعرض مفصولًا لأن القارئ يطابقه بما على شاشة هاتفه، ورقم من
 * ١٣ خانة متصلة يصعب مطابقته بنظرة.
 */
export function phone(value: string | null | undefined): string {
  if (!value) return "—";
  if (value.startsWith("deleted-")) return t("حساب محذوف");

  const match = /^\+(\d{1,3})(\d{2,3})(\d{4})(\d{4})$/.exec(value);
  if (!match) return value;

  return `+${match[1]} ${match[2]} ${match[3]} ${match[4]}`;
}

/**
 * عدّ بصيغة الجمع الصحيحة في كل لغة.
 *
 * العربية ستّ صيغ (صفر، مفرد، مثنّى، قلّة، كثرة) والإنجليزية
 * اثنتان. تمرير الصيغ العربية إلى `Intl.PluralRules` بوسم
 * إنجليزي كان يعطي «2 مكافأتان» ثم «5 مكافآت» في شاشة إنجليزية.
 *
 * في الإنجليزية تُشتقّ الصيغتان من `one` و`many` وحدهما: هما
 * الوحيدتان اللتان لهما مقابل، و«المثنّى» لا وجود له أصلًا.
 */
export function plural(
  count: number,
  forms: { zero: string; one: string; two: string; few: string; many: string },
): string {
  if (getLocale() === "en") {
    const form = count === 1 ? forms.one : forms.many;
    return `${number(count)} ${t(form)}`;
  }

  if (count === 0) return forms.zero;
  if (count === 1) return forms.one;
  if (count === 2) return forms.two;
  if (count % 100 >= 3 && count % 100 <= 10) return `${number(count)} ${forms.few}`;
  return `${number(count)} ${forms.many}`;
}

/**
 * الوقت المتبقي حتى لحظة ما، بصيغة mm:ss.
 *
 * لاتيني عمدًا: يُقرأ كساعة إيقاف تنازلية، وصيغة `mm:ss` نفسها
 * لاتينية الشكل — خلط الأرقام العربية فيها يعطي شيئًا لا يشبه
 * عدّادًا ولا رقمًا.
 */
export function countdown(target: string | Date): string {
  const d = typeof target === "string" ? new Date(target) : target;
  const remaining = Math.max(0, Math.floor((d.getTime() - Date.now()) / 1000));
  const minutes = Math.floor(remaining / 60);
  const seconds = remaining % 60;
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}
