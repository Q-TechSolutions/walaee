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

export interface BalanceRow {
  program_id: string;
  program_name: string;
  program_type: string;
  unit_label: string;
  amount: string;
  expires_at: string | null;
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
}

export interface WalletSummary {
  cards: number;
  by_type: Record<string, string>;
  pending_redemptions: number;
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
    api.get<
      {
        id: string;
        title: string;
        description: string;
        cost_amount: string;
        cost_unit: string;
        stock: number | null;
        brand_name: string;
        program_name: string;
      }[]
    >("/me/rewards", undefined, signal),

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
