/**
 * نداءات تطبيق العميل.
 *
 * كل نداء في مكان واحد لا مبعثرًا في المكوّنات: تغيير مسار في
 * الخلفية يجب أن يُصلَح هنا مرة، لا أن يُطارَد في عشر شاشات.
 */

import { api } from "@walaee/shared";
import type {
  ActivityLine,
  Customer,
  Paginated,
  Redemption,
  ScanResult,
  Transaction,
} from "@walaee/shared";

/** الهدف التالي على برنامج — أرخص مكافأة نشطة فيه. */
export interface NextReward {
  id: string;
  title: string;
  cost_amount: string;
  /** بين ٠ و١ — محسوبة في الخلفية ومحصورة هناك */
  progress: number;
  remaining: string;
  unit_label?: string;
}

export interface BalanceRow {
  program_id: string;
  program_name: string;
  program_type: string;
  unit_label: string;
  amount: string;
  expires_at: string | null;
  next_reward: NextReward | null;
}

export interface Card {
  membership_id: string;
  brand_id: string;
  brand_name: string;
  primary_color: string;
  category: string;
  joined_at: string;
  tier: string;
  last_activity: string | null;
  balances: BalanceRow[];
  /** أقرب مكافأة إلى الاكتمال عبر برامج هذه العلامة */
  next_reward: (NextReward & { unit_label: string }) | null;
}

export interface CardReward {
  id: string;
  title: string;
  description: string;
  cost_amount: string;
  unit_label: string;
  program_id: string;
  in_stock: boolean;
}

export interface CardDetail extends Card {
  rewards: CardReward[];
  activity: (ActivityLine & { unit_label: string })[];
  total_spend: string;
  /** عدد العمليات المؤكَّدة على فروع هذه العلامة — من جدول
      العمليات لا من `activity` أعلاه، فتلك مقصوصة على عشرين */
  total_visits: number;
}

/** يوم واحد في شريط سلسلة الزيارات. */
export interface WeekDay {
  date: string;
  letter: string;
  visited: boolean;
  today: boolean;
}

export interface WalletSummary {
  cards: number;
  by_type: Record<string, string>;
  pending_redemptions: number;
  week: WeekDay[];
}

export interface NearbyStore {
  branch_id: string;
  branch_name: string;
  address: string;
  brand_id: string;
  brand_name: string;
  primary_color: string;
  category: string;
  is_member: boolean;
  distance_km: number;
}

/**
 * مكافأة كما تراها الشاشة — بوقفة العميل منها.
 *
 * `ready` و`remaining` يحسبهما الخادم لا العميل: حسابهما هنا كان
 * يعني جلب كل الأرصدة ومطابقتها ببرامجها في المتصفّح، ثم عرض زر
 * «استبدال» على مكافأة يرفضها الخادم لأن الرصيد تغيّر.
 */
export interface AvailableReward {
  id: string;
  title: string;
  description: string;
  cost_amount: string;
  cost_unit: string;
  unit_label: string;
  stock: number | null;
  in_stock: boolean;
  brand_id: string;
  brand_name: string;
  primary_color: string;
  program_id: string;
  program_name: string;
  balance: string;
  remaining: string;
  ready: boolean;
  /** بين ٠ و١ */
  progress: number;
}

export interface MyRedemption {
  id: string;
  code: string;
  status: Redemption["status"];
  reward_title: string;
  brand_name: string;
  expires_at: string;
  used_at: string | null;
}

export const queries = {
  me: (signal?: AbortSignal) => api.get<Customer>("/me", undefined, signal),

  summary: (signal?: AbortSignal) =>
    api.get<WalletSummary>("/me/summary", undefined, signal),

  cards: (signal?: AbortSignal) => api.get<Card[]>("/me/cards", undefined, signal),

  card: (brandId: string, signal?: AbortSignal) =>
    api.get<CardDetail>(`/me/cards/${brandId}`, undefined, signal),

  activity: (page: number, signal?: AbortSignal) =>
    api.get<Paginated<ActivityLine & { brand_name: string }>>(
      "/me/activity",
      { page },
      signal,
    ),

  redemptions: (signal?: AbortSignal) =>
    api.get<MyRedemption[]>("/me/redemptions", undefined, signal),

  rewards: (signal?: AbortSignal) =>
    api.get<AvailableReward[]>("/me/rewards", undefined, signal),

  nearby: (lat: number, lng: number, signal?: AbortSignal) =>
    api.get<NearbyStore[]>("/stores/nearby", { lat, lng }, signal),
};

export const actions = {
  resolveCode: (code: string) => api.post<ScanResult>("/scan/resolve", { code }),

  createTransaction: (input: {
    code: string;
    invoice_no: string;
    invoice_amount: string;
  }) => api.post<Transaction>("/transactions", input),

  redeem: (rewardId: string) =>
    api.post<Redemption>("/redemptions", { reward_id: rewardId }),

  updateProfile: (input: { full_name?: string; birth_date?: string | null }) =>
    api.patch<Customer>("/me", input),

  enablePush: (subscription: PushSubscriptionJSON) =>
    api.post<{ enabled: boolean }>("/me/push-subscription", { subscription }),

  disablePush: () => api.del<{ enabled: boolean }>("/me/push-subscription"),

  requestDeletion: () => api.post<{ sent: boolean }>("/me/delete"),

  confirmDeletion: (code: string) =>
    api.del<{ deleted: boolean; message: string }>(`/me/delete?code=${code}`),
};

interface PushSubscriptionJSON {
  endpoint: string;
  keys?: Record<string, string>;
}
