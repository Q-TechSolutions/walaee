/**
 * شبكة المتاجر العامة.
 *
 * مسار واحد بلا مصادقة يغذّي الصفحة العامة وخريطة العميل ولوحة
 * إدارة المنصة. الثلاثة تعرض نفس الأرقام، وثلاثة مصادر لها تعني
 * صفحة تقول «١٥ متجرًا» وأخرى تقول «١٤» في نفس اللحظة.
 */

import { request } from "./client";

export interface PublicBranch {
  id: string;
  name: string;
  city: string;
  governorate: string;
  governorate_name: string;
  address: string;
  lat: number;
  lng: number;
  brand_slug: string;
  brand_name: string;
  color: string;
}

export interface PublicBrand {
  slug: string;
  name: string;
  category: string;
  tagline: string;
  color: string;
  logo: string | null;
  branch_count: number;
  governorates: string[];
  program_type: string | null;
  joined_on: string | null;
}

export interface PublicGovernorate {
  code: string;
  name: string;
  region: string;
  lat: number;
  lng: number;
  branch_count: number;
  brand_count: number;
}

export interface NetworkStats {
  brands: number;
  branches: number;
  governorates: number;
  cities: number;
  members: number;
  categories: number;
}

export interface PublicNetwork {
  stats: NetworkStats;
  brands: PublicBrand[];
  branches: PublicBranch[];
  governorates: PublicGovernorate[];
  categories: string[];
}

/**
 * ذاكرة داخل الصفحة.
 *
 * الصفحة العامة تعرض الشبكة في ثلاثة أقسام (الأرقام، الخريطة،
 * شبكة المتاجر). بلا هذه الذاكرة يطلبها كل قسم على حدة فتصل ثلاث
 * نسخ من نفس الحمولة — ويتغيّر الرقم بين قسم وآخر لو تجدّد
 * التخزين بينهما.
 *
 * الوعد لا النتيجة: الطلبات المتوازية الثلاثة تنتظر نفس الوعد بدل
 * أن يبدأ كل منها طلبًا قبل أن يُخزَّن رد الأول.
 */
let inflight: Promise<PublicNetwork> | null = null;

export function fetchNetwork(signal?: AbortSignal): Promise<PublicNetwork> {
  if (!inflight) {
    inflight = request<PublicNetwork>("/public/network", {
      anonymous: true,
      signal,
    }).catch((error: unknown) => {
      // الفشل لا يُخزَّن: انقطاع لحظة واحدة كان سيجعل الصفحة
      // فارغة إلى أن يُحدّثها الزائر بنفسه
      inflight = null;
      throw error;
    });
  }
  return inflight;
}

/** يُستخدم بعد تغيير يمسّ الشبكة — في لوحة الإدارة وحدها. */
export function forgetNetwork(): void {
  inflight = null;
}

/** المتاجر مرتّبة بعدد الفروع — الأكبر أولًا. */
export function byReach(brands: PublicBrand[]): PublicBrand[] {
  return [...brands].sort((a, b) => b.branch_count - a.branch_count);
}

/** يجمع الفروع تحت كل متجر — لصفحة المتجر في الدليل. */
export function branchesOf(
  network: PublicNetwork,
  slug: string,
): PublicBranch[] {
  return network.branches.filter((branch) => branch.brand_slug === slug);
}
