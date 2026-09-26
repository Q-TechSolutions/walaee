/** نداءات لوحة التاجر. */

import { api } from "@walaee/shared";
import type {
  Branch,
  Brand,
  Campaign,
  CampaignEstimate,
  CreditLine,
  Dashboard,
  FraudSignal,
  Invoice,
  Membership,
  MembershipDetail,
  Paginated,
  Program,
  Redemption,
  Reward,
  SeriesPoint,
  StaffMember,
  StaffSession,
  Subscription,
  Terminal,
  TerminalCode,
  Transaction,
} from "@walaee/shared";

/** صف في تدفّق «أحدث العمليات». */
export interface ActivityRow {
  id: string;
  kind: string;
  at: string;
  customer: string;
  branch: string;
  cashier: string;
  amount: string;
  delta: string;
  status: string;
}

/** ملخّص وردية الكاشير الحالي. */
export interface Shift {
  transactions: number;
  revenue: string;
  customers: number;
  staff_name: string;
  role_label: string;
  branch_name: string;
}

/* ══════════════ التوصيات الإحصائية ══════════════ */

/**
 * توصية بلا بيانات كافية تعود بـ`enough_data: false` ولا تحمل
 * رقمًا. الشاشة تعرض العتبة بدل أن تخترع اقتراحًا.
 */
export interface RewardValueSuggestion {
  enough_data: boolean;
  sample: number;
  needed: number;
  window_days: number;
  average_invoice: string;
  target_visits?: number;
  confidence?: "low" | "medium" | "high";
  programs: {
    program_id: string;
    program_name: string;
    program_type: string;
    unit_label: string;
    cost_amount: string;
    cost_low: string;
    cost_high: string;
    reward_worth: string;
  }[];
}

export interface SendTimeSuggestion {
  enough_data: boolean;
  sample: number;
  needed: number;
  window_days: number;
  confidence?: "low" | "medium" | "high";
  best_day?: number;
  best_day_name?: string;
  best_hour?: number;
  peak_hour?: number;
  days: { weekday: number; name: string; visits: number }[];
  hours: { hour: number; visits: number }[];
}

export interface Insights {
  reward_value: RewardValueSuggestion;
  send_time: SendTimeSuggestion;
}

export const queries = {
  // ── الكاشير ──
  terminalCode: (signal?: AbortSignal) =>
    api.get<TerminalCode>("/pos/code", undefined, signal),
  pendingTransactions: (signal?: AbortSignal) =>
    api.get<Transaction[]>("/pos/pending", undefined, signal),

  // ── اللوحة ──
  dashboard: (days: number, signal?: AbortSignal) =>
    api.get<Dashboard>("/merchant/dashboard", { days }, signal),
  activity: (signal?: AbortSignal) =>
    api.get<{ activity: ActivityRow[] }>("/merchant/activity", undefined, signal),
  shift: (signal?: AbortSignal) =>
    api.get<Shift>("/merchant/shift", undefined, signal),
  series: (days: number, signal?: AbortSignal) =>
    api.get<{ series: SeriesPoint[] }>("/merchant/series", { days }, signal),
  liability: (signal?: AbortSignal) =>
    api.get<Dashboard["liability"]>("/merchant/liability", undefined, signal),
  segments: (signal?: AbortSignal) =>
    api.get<Record<string, number>>("/merchant/segments", undefined, signal),
  insights: (signal?: AbortSignal) =>
    api.get<Insights>("/merchant/insights", undefined, signal),
  report: (kind: string, signal?: AbortSignal) =>
    api.get<{ kind: string; rows: Record<string, string | number>[] }>(
      `/merchant/reports/${kind}`,
      undefined,
      signal,
    ),

  // ── العملاء ──
  customers: (
    params: { search?: string; segment?: string; page?: number },
    signal?: AbortSignal,
  ) => api.get<Paginated<Membership>>("/merchant/customers", params, signal),
  customer: (id: string, signal?: AbortSignal) =>
    api.get<MembershipDetail>(`/merchant/customers/${id}`, undefined, signal),

  // ── البرامج والمكافآت ──
  programs: (signal?: AbortSignal) =>
    api.get<Program[]>("/merchant/programs", undefined, signal),
  rewards: (signal?: AbortSignal) =>
    api.get<Reward[]>("/merchant/rewards", undefined, signal),

  // ── الحوكمة ──
  brand: (signal?: AbortSignal) =>
    api.get<Brand>("/merchant/brand", undefined, signal),
  branches: (signal?: AbortSignal) =>
    api.get<Branch[]>("/merchant/branches", undefined, signal),
  terminals: (signal?: AbortSignal) =>
    api.get<Terminal[]>("/merchant/terminals", undefined, signal),
  staff: (signal?: AbortSignal) =>
    api.get<StaffMember[]>("/merchant/staff", undefined, signal),

  // ── الاحتيال ──
  fraudSignals: (status: string, signal?: AbortSignal) =>
    api.get<FraudSignal[]>("/merchant/fraud-signals", { status }, signal),

  // ── الحملات ──
  campaigns: (signal?: AbortSignal) =>
    api.get<Campaign[]>("/merchant/campaigns", undefined, signal),
  campaign: (id: string, signal?: AbortSignal) =>
    api.get<Campaign>(`/merchant/campaigns/${id}`, undefined, signal),

  // ── الاشتراك ──
  subscription: (signal?: AbortSignal) =>
    api.get<Subscription>("/merchant/subscription", undefined, signal),
  invoices: (signal?: AbortSignal) =>
    api.get<Invoice[]>("/merchant/invoices", undefined, signal),
  wallet: (signal?: AbortSignal) =>
    api.get<{ balance: number; history: CreditLine[] }>(
      "/merchant/message-wallet",
      undefined,
      signal,
    ),
};

export const actions = {
  /** منح أو خصم يدوي — المسار الوحيد الذي يكتب في رصيد بلا فاتورة */
  grant: (input: {
    membership_id: string;
    program_id: string;
    amount: string;
    note: string;
  }) =>
    api.post<{
      entry_id: string;
      delta: string;
      balance_after: string;
      unit_label: string;
      note: string;
    }>("/merchant/grant", input),

  updateBrand: (input: { name?: string; category?: string }) =>
    api.patch<Brand>("/merchant/brand", input),

  login: (phone: string, password: string) =>
    api.anonymous.post<StaffSession>("/auth/staff/login", { phone, password }),

  rotateCode: () => api.post<TerminalCode>("/pos/code/rotate"),

  confirmTransaction: (id: string) =>
    api.post<Transaction>(`/pos/transactions/${id}/confirm`),

  manualTransaction: (input: {
    phone: string;
    invoice_amount: string;
    invoice_no: string;
  }) => api.post<Transaction>("/pos/manual", input),

  useRedemption: (code: string) =>
    api.post<Redemption>(`/pos/redemptions/${code}/use`),

  updateRule: (programId: string, rule: Record<string, unknown>) =>
    api.put<Record<string, unknown>>(
      `/merchant/programs/${programId}/rule`,
      rule,
    ),

  createProgram: (input: { name: string; type: string }) =>
    api.post<Program>("/merchant/programs", input),

  createReward: (input: {
    title: string;
    description?: string;
    cost_amount: string;
    merchant_cost: string;
    stock?: number | null;
    program_id: string;
  }) => api.post<Reward>("/merchant/rewards", input),

  updateReward: (id: string, input: Record<string, unknown>) =>
    api.patch<Reward>(`/merchant/rewards/${id}`, input),

  createBranch: (input: { name: string; address?: string }) =>
    api.post<Branch>("/merchant/branches", input),

  createTerminal: (input: { label: string; branch_id: string }) =>
    api.post<Terminal>("/merchant/terminals", input),

  createStaff: (input: {
    phone: string;
    full_name?: string;
    role: string;
    branch_id: string;
    password?: string;
  }) => api.post<StaffMember>("/merchant/staff", input),

  disableStaff: (id: string) =>
    api.del<{ id: string; is_active: boolean }>(`/merchant/staff/${id}`),

  resolveSignal: (id: string, action: "accept" | "reject") =>
    api.post<{ id: string; status: string; reversed_entries: string[] }>(
      `/merchant/fraud-signals/${id}/resolve`,
      { action },
    ),

  previewCampaign: (input: {
    segment_query: Record<string, unknown>;
    channel_priority?: string[];
  }) => api.post<CampaignEstimate>("/merchant/campaigns/preview", input),

  createCampaign: (input: {
    name: string;
    message_template: string;
    segment_query: Record<string, unknown>;
    channel_priority?: string[];
    scheduled_at?: string | null;
  }) =>
    api.post<Campaign & { estimate: CampaignEstimate; wallet_balance: number }>(
      "/merchant/campaigns",
      input,
    ),

  sendCampaign: (id: string) =>
    api.post<{ id: string; queued: boolean; message: string }>(
      `/merchant/campaigns/${id}/send`,
    ),

  cancelCampaign: (id: string) =>
    api.post<Campaign>(`/merchant/campaigns/${id}/cancel`),

  invoicePayment: (id: string) =>
    api.get<{
      reference: string;
      amount: string;
      instructions: string;
      checkout_url: string;
    }>(`/merchant/invoices/${id}/payment`),
};
