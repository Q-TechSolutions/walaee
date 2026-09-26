/**
 * روابط التطبيقات الثلاثة.
 *
 * الأربعة على أصل واحد خلف نفس الوكيل، فالمسارات نسبية: دومين
 * مكتوب هنا يعني صفحة عامة تُحوّل زوّار بيئة الاختبار إلى الإنتاج.
 *
 * تطبيق العميل على `/app/` لا على الجذر — الجذر لهذه الصفحة.
 * راجع التعليق في `landing/vite.config.ts`.
 */

export const APP = {
  customer: "/app/",
  merchant: "/merchant/",
  admin: "/admin/",
} as const;

/** أقسام الصفحة — تُستخدم في القائمة وفي روابط «تخطَّ إلى». */
export const SECTIONS = [
  { id: "coverage", label: "التغطية" },
  { id: "how", label: "كيف تعمل" },
  { id: "merchants", label: "للتجّار" },
  { id: "pricing", label: "الأسعار" },
  { id: "faq", label: "أسئلة" },
] as const;
