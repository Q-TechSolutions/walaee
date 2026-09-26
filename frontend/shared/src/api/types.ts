/** أنواع مشتركة بين التطبيقات الثلاثة — مشتقّة من عقد OpenAPI. */

export interface Tokens {
  access: string;
  refresh: string;
}

export interface ApiError {
  error: {
    code: string;
    message: string;
    details?: unknown;
  };
}

export interface Customer {
  id: string;
  phone: string;
  full_name: string;
  birth_date: string | null;
  has_consent: boolean;
  created_at: string;
}

export interface StaffRole {
  id: string;
  role: "owner" | "manager" | "cashier";
  role_label: string;
  branch_id: string;
  branch_name: string;
  brand_id: string;
  brand_name: string;
}

export interface StaffSession {
  access: string;
  refresh: string;
  user: {
    id: string;
    phone: string;
    full_name: string;
    is_platform_admin: boolean;
  };
  roles: StaffRole[];
}

export interface BalanceLine {
  program: string;
  program_name: string;
  amount: string;
  unit: string;
}

export interface ScanResult {
  terminal: { id: string; label: string };
  branch: { id: string; name: string };
  brand: { id: string; name: string; primary_color: string };
  is_member: boolean;
  balances: BalanceLine[];
}

export interface Transaction {
  id: string;
  invoice_no: string;
  invoice_amount: string;
  status: "pending" | "confirmed" | "rejected" | "reversed";
  customer_phone?: string;
  customer_name?: string;
  created_at: string;
  confirmed_at: string | null;
}

export interface Brand {
  id: string;
  name: string;
  slug: string;
  category: string;
  tagline: string;
  primary_color: string;
  logo: string | null;
  is_active: boolean;
  organization_name: string;
  created_at: string;
}

export interface Reward {
  id: string;
  title: string;
  description: string;
  cost_amount: string;
  cost_unit: string;
  stock: number | null;
  brand_name?: string;
  program_name?: string;
  unit_label?: string;
  merchant_cost?: string;
  is_active?: boolean;
  /** مرات الصرف الفعلي — تُرسَل في قائمة مكافآت التاجر وحدها */
  redeemed_count?: number;
}

export interface Redemption {
  id: string;
  code: string;
  status: "pending" | "used" | "expired";
  expires_at: string;
  used_at: string | null;
  reward_title: string;
}

export interface TerminalCode {
  terminal_id: string;
  label: string;
  code: string;
}

export interface LiabilityLine {
  program_id: string;
  program_name: string;
  type: string;
  unit_label: string;
  outstanding_units: string;
  unit_value: string;
  estimated_value: string;
}

export interface Liability {
  total_units: string;
  estimated_value: string;
  currency: string;
  by_program: LiabilityLine[];
  note: string;
}

export interface Dashboard {
  period_days: number;
  transactions: { count: number; change_pct: number | null };
  revenue: { total: string; average_invoice: string; change_pct: number | null };
  customers: {
    total: number;
    new: number;
    active: number;
    repeat: number;
    repeat_rate_pct: number;
  };
  redemptions: number;
  liability: Liability;
  open_fraud_signals: number;
}

export interface SeriesPoint {
  date: string;
  transactions: number;
  revenue: string;
}

export interface BalanceRow {
  program_id: string;
  program_name: string;
  program_type: string;
  unit_label: string;
  amount: string;
  expires_at: string | null;
}

export interface Membership {
  id: string;
  phone: string;
  full_name: string;
  status: string;
  tier: string;
  joined_at: string;
  balances: BalanceRow[];
}

export interface ActivityLine {
  id: string;
  delta: string;
  reason: string;
  reason_label: string;
  program: string;
  balance_after: string;
  created_at: string;
  /** العملية التي أنتجت القيد — null للترحيب والتسوية وانتهاء الصلاحية */
  transaction?: string | null;
  /** السبب المكتوب — يظهر على المنح اليدوي وحده */
  note?: string;
}

export interface MembershipDetail extends Membership {
  recent_activity: ActivityLine[];
  total_spend: string;
}

export interface ProgramRule {
  earn_rate: string;
  min_invoice: string;
  max_per_day: string | null;
  expiry_months: number | null;
  reversal_policy: string;
  welcome_bonus: number;
}

export interface Program {
  id: string;
  name: string;
  type: string;
  is_active: boolean;
  starts_at: string | null;
  ends_at: string | null;
  unit_label: string;
  rule: ProgramRule | null;
  rewards_count: number;
}

export interface FraudSignal {
  id: string;
  rule_code: string;
  rule_label: string;
  severity: "low" | "medium" | "high";
  status: "open" | "accepted" | "rejected";
  details: Record<string, unknown>;
  created_at: string;
  reviewed_at: string | null;
  invoice_no: string;
  invoice_amount: string;
  customer_phone: string | null;
  staff_name: string | null;
  branch_name: string;
}

export interface Campaign {
  id: string;
  name: string;
  message_template: string;
  segment_query: Record<string, unknown>;
  channel_priority: string[];
  status: string;
  scheduled_at: string | null;
  started_at: string | null;
  finished_at: string | null;
  estimated_recipients: number;
  estimated_cost: string;
  actual_cost: string;
  created_by_name: string | null;
  sent_count: number;
  failed_count: number;
  created_at: string;
}

export interface CampaignEstimate {
  recipients: number;
  reachable: number;
  unreachable: number;
  cost: string;
  billable_messages: number;
  per_channel: Record<
    string,
    { count: number; unit_cost: string; label: string }
  >;
  segment_description: string;
  wallet_balance: number;
}

export interface Branch {
  id: string;
  name: string;
  address: string;
  lat: string | null;
  lng: string | null;
  is_active: boolean;
  terminals_count: number;
  staff_count: number;
}

export interface Terminal {
  id: string;
  label: string;
  is_active: boolean;
  branch_name: string;
  code_expires_at: string | null;
}

export interface StaffMember {
  id: string;
  phone: string;
  full_name: string;
  role: string;
  branch_name: string;
  is_active: boolean;
}

export interface Subscription {
  id: string;
  plan: string;
  plan_label: string;
  status: string;
  status_label: string;
  mrr: string;
  current_period_start: string;
  current_period_end: string;
  limits: Record<string, string | null>;
  usage: Record<string, number>;
  message_balance: number;
}

export interface Invoice {
  id: string;
  number: string;
  amount: string;
  tax_amount: string;
  total: string;
  status: string;
  status_label: string;
  period_start: string;
  period_end: string;
  issued_at: string | null;
  paid_at: string | null;
}

export interface CreditLine {
  id: string;
  delta: number;
  reason: string;
  reason_label: string;
  balance_after: number;
  note: string;
  created_at: string;
}

export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}
