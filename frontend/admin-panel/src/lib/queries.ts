/** نداءات لوحة إدارة المنصة. */

import { api } from "@walaee/shared";
import type { StaffSession } from "@walaee/shared";

export interface Overview {
  mrr: string;
  organizations: {
    total: number;
    paying: number;
    free: number;
    past_due: number;
  };
  brands: number;
  branches: number;
  customers: { total: number; new_30d: number };
  memberships: number;
  transactions_30d: number;
  gmv_30d: string;
  entries_30d: number;
  unpaid_invoices: number;
  by_plan: Record<string, number>;
}

export interface MerchantRow {
  id: string;
  name: string;
  status: string;
  brands: number;
  brand_names: string[];
  plan: string;
  plan_label: string;
  subscription_status: string;
  mrr: string;
  transactions_30d: number;
  last_activity: string | null;
}

export interface UnpaidInvoice {
  id: string;
  number: string;
  organization: string;
  amount: string;
  status: string;
  issued_at: string | null;
  period_end: string;
}

/* ══════════════ مؤشرات الصحة ══════════════ */

export interface HealthMetric {
  key: string;
  label: string;
  value: number;
  unit: string;
  target: number;
  /** "up" يعني الأعلى أفضل */
  direction: "up" | "down";
  on_target: boolean;
  hint: string;
  /** خانات القالب — تُنسَّق في الواجهة بنظام أرقام اللغة */
  hint_vars: Record<string, string>;
}

export interface Health {
  metrics: HealthMetric[];
  off_target: HealthMetric[];
  generated_at: string;
}

/* ══════════════ المستخدمون ══════════════ */

export interface PlatformUser {
  id: string;
  name: string;
  phone: string;
  role: string;
  is_active: boolean;
  last_login: string | null;
  joined_at: string;
}

export interface StaffRow {
  id: string;
  name: string;
  phone: string;
  role: string;
  role_key: string;
  brand: string;
  branch: string;
  is_active: boolean;
  last_login: string | null;
}

export interface Users {
  platform: PlatformUser[];
  staff: StaffRow[];
  staff_total: number;
  by_role: { role: string; count: number }[];
}

/* ══════════════ التشغيل ══════════════ */

export interface Service {
  name: string;
  ok: boolean;
  latency_ms: number;
  detail: string;
}

export interface ScheduledTask {
  name: string;
  task: string;
  enabled: boolean;
  schedule: string;
  last_run_at: string | null;
  total_runs: number;
  silent_hours: number | null;
}

export interface Ops {
  services: Service[];
  tasks: ScheduledTask[];
  integrity: { checked: number; drifted: number; ok: boolean };
  volume: Record<string, number>;
  checked_at: string;
}

/* ══════════════ الإعدادات ══════════════ */

export interface PrivacyRow {
  key: string;
  label: string;
  enabled: boolean;
  detail: string;
}

export interface PlanRow {
  code: string;
  name: string;
  monthly_price: string;
  limits: Record<string, number | null>;
  subscribers: number;
}

export interface Config {
  retention: Record<string, number | null>;
  privacy: PrivacyRow[];
  network_model: {
    phase: number;
    label: string;
    detail: string;
    stages: { stage: number; label: string; status: string }[];
  };
  features: { key: string; enabled: boolean }[];
  plans: PlanRow[];
}

export const queries = {
  overview: (signal?: AbortSignal) =>
    api.get<Overview>("/platform/overview", undefined, signal),
  merchants: (signal?: AbortSignal) =>
    api.get<MerchantRow[]>("/platform/merchants", undefined, signal),
  invoices: (signal?: AbortSignal) =>
    api.get<UnpaidInvoice[]>("/platform/invoices", undefined, signal),
  health: (signal?: AbortSignal) => api.get<Health>("/platform/health", undefined, signal),
  users: (signal?: AbortSignal) => api.get<Users>("/platform/users", undefined, signal),
  ops: (signal?: AbortSignal) => api.get<Ops>("/platform/ops", undefined, signal),
  config: (signal?: AbortSignal) => api.get<Config>("/platform/config", undefined, signal),
};

export const actions = {
  login: (phone: string, password: string) =>
    api.anonymous.post<StaffSession>("/auth/staff/login", { phone, password }),

  markPaid: (id: string, reference: string) =>
    api.post<{ id: string; number: string; status: string }>(
      `/platform/invoices/${id}/mark-paid`,
      { reference },
    ),
};
