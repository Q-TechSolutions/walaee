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

export const queries = {
  overview: (signal?: AbortSignal) =>
    api.get<Overview>("/platform/overview", undefined, signal),
  merchants: (signal?: AbortSignal) =>
    api.get<MerchantRow[]>("/platform/merchants", undefined, signal),
  invoices: (signal?: AbortSignal) =>
    api.get<UnpaidInvoice[]>("/platform/invoices", undefined, signal),
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
