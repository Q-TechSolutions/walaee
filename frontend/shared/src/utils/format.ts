/**
 * تنسيق الأرقام والتواريخ بالعربية.
 *
 * قاعدة حاكمة: **الأرقام تبقى لاتينية في الشاشات التشغيلية.**
 * الأرقام العربية-الهندية أجمل في نص مقروء، لكنها تُبطئ قراءة
 * مبلغ عند الصندوق وتربك من يقارن رقمًا بفاتورة ورقية مطبوعة
 * بالأرقام اللاتينية. تُستخدم في العناوين والعدّادات التسويقية فقط.
 */

const AR = "ar-EG";

/** أرقام عربية-هندية — للعناوين والنصوص السردية لا للمبالغ. */
export function toArabicDigits(value: string | number): string {
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

  return new Intl.NumberFormat(AR, {
    style: "currency",
    currency,
    maximumFractionDigits: 2,
    numberingSystem: "latn",
  }).format(amount);
}

/** رقم بلا عملة — للنقاط والأختام والعدّادات. */
export function number(value: string | number, digits = 0): string {
  const amount = typeof value === "string" ? Number(value) : value;
  if (!Number.isFinite(amount)) return "—";

  return new Intl.NumberFormat(AR, {
    maximumFractionDigits: digits,
    numberingSystem: "latn",
  }).format(amount);
}

/** رصيد بوحدته: «١٢٠ نقطة». */
export function balance(value: string | number, unit: string): string {
  return `${number(value)} ${unit}`;
}

export function percent(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  const sign = value > 0 ? "+" : "";
  return `${sign}${number(value, 1)}٪`;
}

/** تاريخ قصير: ٢٠ سبتمبر ٢٠٢٦. */
export function date(value: string | Date | null | undefined): string {
  if (!value) return "—";
  const d = typeof value === "string" ? new Date(value) : value;
  if (Number.isNaN(d.getTime())) return "—";

  return new Intl.DateTimeFormat(AR, {
    day: "numeric",
    month: "long",
    year: "numeric",
    numberingSystem: "latn",
  }).format(d);
}

/** تاريخ ووقت — للسجلات حيث الدقيقة مهمة. */
export function dateTime(value: string | Date | null | undefined): string {
  if (!value) return "—";
  const d = typeof value === "string" ? new Date(value) : value;
  if (Number.isNaN(d.getTime())) return "—";

  return new Intl.DateTimeFormat(AR, {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    numberingSystem: "latn",
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
  const formatter = new Intl.RelativeTimeFormat(AR, { numeric: "auto" });

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
  if (value.startsWith("deleted-")) return "حساب محذوف";

  const match = /^\+(\d{1,3})(\d{2,3})(\d{4})(\d{4})$/.exec(value);
  if (!match) return value;

  return `+${match[1]} ${match[2]} ${match[3]} ${match[4]}`;
}

/** عدّ بصيغة الجمع العربية الصحيحة. */
export function plural(
  count: number,
  forms: { zero: string; one: string; two: string; few: string; many: string },
): string {
  if (count === 0) return forms.zero;
  if (count === 1) return forms.one;
  if (count === 2) return forms.two;
  if (count % 100 >= 3 && count % 100 <= 10) return `${number(count)} ${forms.few}`;
  return `${number(count)} ${forms.many}`;
}

/** الوقت المتبقي حتى لحظة ما، بصيغة mm:ss. */
export function countdown(target: string | Date): string {
  const d = typeof target === "string" ? new Date(target) : target;
  const remaining = Math.max(0, Math.floor((d.getTime() - Date.now()) / 1000));
  const minutes = Math.floor(remaining / 60);
  const seconds = remaining % 60;
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}
