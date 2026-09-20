/**
 * تخزين التوكنات — مفصول لكل تطبيق.
 *
 * التطبيقات الثلاثة تُخدَم من أصل واحد (`/` و `/merchant/` و
 * `/admin/`)، و`localStorage` مشترك بين كل ما هو على أصل واحد.
 * مفتاح واحد يعني أن الدخول كعميل يجعل لوحة الإدارة تظنّك مسجّلًا:
 * فتتخطّى شاشة الدخول، ثم يرفضها الخادم ٤٠٣، فيرى المستخدم صندوق
 * خطأ أحمر ولا يجد أين يسجّل دخوله أصلًا.
 *
 * لذلك المفتاح يحمل اسم التطبيق. كل تطبيق يعلنه مرة واحدة في
 * `main.tsx` عبر `configureApi({ appId })`.
 *
 * `localStorage` لا `sessionStorage`: الكاشير يفتح الشاشة صباحًا
 * ويظل عليها طول اليوم، وإعادة الدخول بعد كل إغلاق تبويب تعني
 * طابورًا عند الصندوق.
 *
 * كل عملية محاطة بـ try لأن التخزين يرمي استثناءً في وضع التصفّح
 * الخاص وحين تُحجب بيانات الموقع — والتطبيق يجب أن يعمل عندها
 * ولو بجلسة لا تُحفظ بين الزيارات.
 */

import type { Tokens } from "./types";

const PREFIX = "walaee.tokens";

/** المفتاح القديم المشترك — يُنظَّف مرة واحدة عند أول قراءة. */
const LEGACY_KEY = PREFIX;

let appId = "app";
let memory: Tokens | null = null;
let legacyCleaned = false;

/** يُستدعى من `configureApi` — لا يُستدعى مباشرةً. */
export function setTokenNamespace(id: string): void {
  if (!id || id === appId) return;
  appId = id;
  memory = null;
}

function key(): string {
  return `${PREFIX}.${appId}`;
}

/**
 * يحذف المفتاح المشترك القديم.
 *
 * بدون هذا يبقى توكن قديم في متصفّح كل من جرّب النسخة السابقة،
 * بلا أثر ظاهر لكنه يشغل مساحة ويظهر في أدوات المطوّر فيربك من
 * يقرأه.
 */
function cleanLegacy(): void {
  if (legacyCleaned) return;
  legacyCleaned = true;
  try {
    localStorage.removeItem(LEGACY_KEY);
  } catch {
    /* لا شيء */
  }
}

export function readTokens(): Tokens | null {
  if (memory) return memory;
  cleanLegacy();
  try {
    const raw = localStorage.getItem(key());
    if (!raw) return null;
    memory = JSON.parse(raw) as Tokens;
    return memory;
  } catch {
    return null;
  }
}

export function writeTokens(tokens: Tokens): void {
  memory = tokens;
  try {
    localStorage.setItem(key(), JSON.stringify(tokens));
  } catch {
    // الجلسة تعيش في الذاكرة فقط — أفضل من رفض الدخول
  }
}

export function clearTokens(): void {
  memory = null;
  try {
    localStorage.removeItem(key());
  } catch {
    /* لا شيء يمكن فعله */
  }
}

export function isAuthenticated(): boolean {
  return readTokens() !== null;
}

/**
 * يقرأ حمولة توكن الوصول بلا تحقق من التوقيع.
 *
 * للعرض فقط — لا يُتّخذ عليها أي قرار أمني. التحقق الحقيقي في
 * الخلفية، وأي فحص هنا يستطيع المستخدم تزويره بتعديل التخزين.
 */
export function decodeAccess(): Record<string, unknown> | null {
  const tokens = readTokens();
  if (!tokens?.access) return null;
  try {
    const part = tokens.access.split(".")[1];
    if (!part) return null;
    const json = atob(part.replace(/-/g, "+").replace(/_/g, "/"));
    return JSON.parse(json) as Record<string, unknown>;
  } catch {
    return null;
  }
}

/**
 * مفتاح مساحة تخزين أخرى لهذا التطبيق.
 *
 * يستخدمه ما يحفظ حالة إضافية — مثل جلسة الموظف ودوره — ليتبع
 * نفس الفصل بلا أن يعيد اكتشافه.
 */
export function namespacedKey(name: string): string {
  return `walaee.${name}.${appId}`;
}
