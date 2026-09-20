/**
 * تخزين التوكنات.
 *
 * `localStorage` لا `sessionStorage`: الكاشير يفتح الشاشة صباحًا
 * ويظل عليها طول اليوم، وإعادة تسجيل الدخول بعد كل إغلاق تبويب
 * تعني طابورًا عند الصندوق.
 *
 * كل عملية محاطة بـ try لأن التخزين يرمي استثناءً في وضع التصفح
 * الخاص وحين تُحجب بيانات الموقع — والتطبيق يجب أن يعمل عندها ولو
 * بجلسة لا تُحفظ بين الزيارات.
 */

import type { Tokens } from "./types";

const KEY = "walaee.tokens";

let memory: Tokens | null = null;

export function readTokens(): Tokens | null {
  if (memory) return memory;
  try {
    const raw = localStorage.getItem(KEY);
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
    localStorage.setItem(KEY, JSON.stringify(tokens));
  } catch {
    // الجلسة تعيش في الذاكرة فقط — أفضل من رفض الدخول
  }
}

export function clearTokens(): void {
  memory = null;
  try {
    localStorage.removeItem(KEY);
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
