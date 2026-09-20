/**
 * التنقّل الصلب مع احترام المسار الأساسي.
 *
 * التطبيقات تُخدَم تحت مسارات فرعية (/merchant/ و /admin/)، و
 * `window.location.replace("/login")` يخرج من التطبيق إلى جذر
 * الدومين — أي إلى تطبيق آخر تمامًا.
 *
 * العطل لا يظهر في التطوير إطلاقًا لأن الخادم المحلي يخدم كل
 * تطبيق على جذره، فيُكتشف أول مرة بعد النشر.
 */

/** المسار الأساسي بلا شرطة زائدة: "" أو "/merchant". */
export function basePath(): string {
  const base = import.meta.env.BASE_URL ?? "/";
  return base === "/" ? "" : base.replace(/\/$/, "");
}

/** مسار مطلق داخل هذا التطبيق. */
export function appPath(path: string): string {
  return basePath() + (path.startsWith("/") ? path : `/${path}`);
}

/** هل نحن على هذا المسار داخل التطبيق؟ */
export function isAt(path: string): boolean {
  return window.location.pathname.startsWith(appPath(path));
}

/**
 * انتقال صلب يستبدل السجل.
 *
 * `replace` لا `assign`: ترك شاشة منتهية الجلسة في تاريخ التصفّح
 * يعني أن زر الرجوع يعيد المستخدم إليها فيرى بيانات لا يملكها.
 */
export function hardRedirect(path: string): void {
  window.location.replace(appPath(path));
}
