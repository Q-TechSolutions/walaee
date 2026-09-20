/** الفروع ونقاط البيع والفريق والاشتراك — كلها للمالك. */

import { useState } from "react";

import {
  Badge,
  Button,
  Empty,
  ErrorBox,
  Field,
  Loading,
  Modal,
  fmt,
  useAction,
  useApi,
} from "@walaee/shared";

import { actions, queries } from "../lib/queries";

type Tab = "branches" | "staff" | "subscription";

const TABS: { key: Tab; label: string }[] = [
  { key: "branches", label: "الفروع ونقاط البيع" },
  { key: "staff", label: "الفريق" },
  { key: "subscription", label: "الاشتراك" },
];

export function Settings() {
  const [tab, setTab] = useState<Tab>("branches");

  return (
    <div className="stack gap-lg">
      <header>
        <h1>الإعدادات</h1>
        <p className="t-sm muted">هيكل متجرك وفريقك واشتراكك</p>
      </header>

      <div className="range-switch" role="tablist">
        {TABS.map((option) => (
          <button
            key={option.key}
            type="button"
            role="tab"
            aria-selected={tab === option.key}
            className={tab === option.key ? "active" : ""}
            onClick={() => setTab(option.key)}
          >
            {option.label}
          </button>
        ))}
      </div>

      {tab === "branches" && <Branches />}
      {tab === "staff" && <Staff />}
      {tab === "subscription" && <SubscriptionPanel />}
    </div>
  );
}

/* ══════════════ الفروع ونقاط البيع ══════════════ */

function Branches() {
  const branches = useApi((signal) => queries.branches(signal), []);
  const terminals = useApi((signal) => queries.terminals(signal), []);
  const [adding, setAdding] = useState<"branch" | "terminal" | null>(null);

  return (
    <div className="stack gap-lg">
      <section className="stack gap">
        <div className="row between">
          <h2>الفروع</h2>
          <Button variant="ghost" onClick={() => setAdding("branch")}>
            إضافة فرع
          </Button>
        </div>

        {branches.loading && <Loading />}
        {branches.error != null && (
          <ErrorBox error={branches.error} onRetry={branches.reload} />
        )}

        {branches.data?.map((branch) => (
          <div key={branch.id} className="row between card wl-card-p">
            <div>
              <p className="w-7">{branch.name}</p>
              <p className="t-sm muted">{branch.address || "بلا عنوان"}</p>
            </div>
            <div className="row gap wrap">
              <Badge tone="muted">
                <span className="num">{branch.terminals_count}</span> نقطة بيع
              </Badge>
              <Badge tone="muted">
                <span className="num">{branch.staff_count}</span> موظف
              </Badge>
              <Badge tone={branch.is_active ? "green" : "red"}>
                {branch.is_active ? "نشط" : "متوقف"}
              </Badge>
            </div>
          </div>
        ))}
      </section>

      <section className="stack gap">
        <div className="row between">
          <h2>نقاط البيع</h2>
          <Button variant="ghost" onClick={() => setAdding("terminal")}>
            إضافة نقطة بيع
          </Button>
        </div>

        {terminals.data?.length === 0 && (
          <Empty icon="▭" title="لا توجد نقاط بيع" />
        )}

        {terminals.data?.map((terminal) => (
          <div key={terminal.id} className="row between card wl-card-p">
            <div>
              <p className="w-7">{terminal.label}</p>
              <p className="t-sm muted">{terminal.branch_name}</p>
            </div>
            <Badge tone={terminal.is_active ? "green" : "muted"}>
              {terminal.is_active ? "نشطة" : "متوقفة"}
            </Badge>
          </div>
        ))}
      </section>

      <AddBranchModal
        open={adding === "branch"}
        onClose={() => setAdding(null)}
        onDone={branches.reload}
      />
      <AddTerminalModal
        open={adding === "terminal"}
        branches={branches.data ?? []}
        onClose={() => setAdding(null)}
        onDone={terminals.reload}
      />
    </div>
  );
}

function AddBranchModal({
  open,
  onClose,
  onDone,
}: {
  open: boolean;
  onClose: () => void;
  onDone: () => void;
}) {
  const [name, setName] = useState("");
  const [address, setAddress] = useState("");
  const create = useAction(actions.createBranch);

  return (
    <Modal
      open={open}
      title="فرع جديد"
      onClose={onClose}
      footer={
        <Button
          loading={create.loading}
          disabled={!name.trim()}
          onClick={async () => {
            const done = await create.run({
              name: name.trim(),
              address: address.trim(),
            });
            if (done) {
              setName("");
              setAddress("");
              onDone();
              onClose();
            }
          }}
        >
          إضافة
        </Button>
      }
    >
      <div className="stack gap">
        <Field label="اسم الفرع">
          <input
            className="input"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </Field>
        <Field label="العنوان" hint="اختياري">
          <input
            className="input"
            value={address}
            onChange={(e) => setAddress(e.target.value)}
          />
        </Field>
        {create.error != null && <ErrorBox error={create.error} />}
      </div>
    </Modal>
  );
}

function AddTerminalModal({
  open,
  branches,
  onClose,
  onDone,
}: {
  open: boolean;
  branches: { id: string; name: string }[];
  onClose: () => void;
  onDone: () => void;
}) {
  const [label, setLabel] = useState("");
  const [branchId, setBranchId] = useState("");
  const create = useAction(actions.createTerminal);

  const selected = branchId || branches[0]?.id || "";

  return (
    <Modal
      open={open}
      title="نقطة بيع جديدة"
      onClose={onClose}
      footer={
        <Button
          loading={create.loading}
          disabled={!label.trim() || !selected}
          onClick={async () => {
            const done = await create.run({
              label: label.trim(),
              branch_id: selected,
            });
            if (done) {
              setLabel("");
              onDone();
              onClose();
            }
          }}
        >
          إضافة
        </Button>
      }
    >
      <div className="stack gap">
        <Field label="الفرع">
          <select
            className="input"
            value={selected}
            onChange={(e) => setBranchId(e.target.value)}
          >
            {branches.map((branch) => (
              <option key={branch.id} value={branch.id}>
                {branch.name}
              </option>
            ))}
          </select>
        </Field>
        <Field label="التسمية" hint="مثال: كاشير ١">
          <input
            className="input"
            value={label}
            onChange={(e) => setLabel(e.target.value)}
          />
        </Field>
        {create.error != null && <ErrorBox error={create.error} />}
      </div>
    </Modal>
  );
}

/* ══════════════ الفريق ══════════════ */

const ROLE_LABEL: Record<string, string> = {
  owner: "مالك",
  manager: "مدير",
  cashier: "كاشير",
};

const ROLE_TONE: Record<string, "violet" | "blue" | "muted"> = {
  owner: "violet",
  manager: "blue",
  cashier: "muted",
};

function Staff() {
  const staff = useApi((signal) => queries.staff(signal), []);
  const branches = useApi((signal) => queries.branches(signal), []);
  const [adding, setAdding] = useState(false);
  const disable = useAction(actions.disableStaff);

  return (
    <div className="stack gap">
      <div className="row between">
        <h2>الفريق</h2>
        <Button variant="ghost" onClick={() => setAdding(true)}>
          إضافة موظف
        </Button>
      </div>

      <div className="notice">
        حساب مستقل لكل كاشير شرط لكشف الاحتيال: الحساب المشترك يجعل نسبة أي
        نمط مشبوه إلى شخص بعينه مستحيلة.
      </div>

      {staff.loading && <Loading />}
      {staff.error != null && (
        <ErrorBox error={staff.error} onRetry={staff.reload} />
      )}
      {disable.error != null && <ErrorBox error={disable.error} />}

      {staff.data?.map((person) => (
        <div key={person.id} className="row between card wl-card-p">
          <div>
            <p className="w-7">{person.full_name || "بلا اسم"}</p>
            <p className="t-sm muted num">{fmt.phone(person.phone)}</p>
            <p className="t-xs faint">{person.branch_name}</p>
          </div>
          <div className="row gap">
            <Badge tone={ROLE_TONE[person.role] ?? "muted"}>
              {ROLE_LABEL[person.role] ?? person.role}
            </Badge>
            {person.is_active ? (
              <Button
                variant="ghost"
                loading={disable.loading}
                onClick={async () => {
                  const done = await disable.run(person.id);
                  if (done) staff.reload();
                }}
              >
                تعطيل
              </Button>
            ) : (
              <Badge tone="red">معطّل</Badge>
            )}
          </div>
        </div>
      ))}

      <AddStaffModal
        open={adding}
        branches={branches.data ?? []}
        onClose={() => setAdding(false)}
        onDone={staff.reload}
      />
    </div>
  );
}

function AddStaffModal({
  open,
  branches,
  onClose,
  onDone,
}: {
  open: boolean;
  branches: { id: string; name: string }[];
  onClose: () => void;
  onDone: () => void;
}) {
  const [form, setForm] = useState({
    phone: "",
    full_name: "",
    role: "cashier",
    password: "",
  });
  const [branchId, setBranchId] = useState("");
  const create = useAction(actions.createStaff);

  const selected = branchId || branches[0]?.id || "";

  return (
    <Modal
      open={open}
      title="موظف جديد"
      onClose={onClose}
      footer={
        <Button
          loading={create.loading}
          disabled={!form.phone.trim() || !selected}
          onClick={async () => {
            const done = await create.run({ ...form, branch_id: selected });
            if (done) {
              setForm({
                phone: "",
                full_name: "",
                role: "cashier",
                password: "",
              });
              onDone();
              onClose();
            }
          }}
        >
          إضافة
        </Button>
      }
    >
      <div className="stack gap">
        <Field label="رقم الهاتف" hint="يُستخدم للدخول">
          <input
            className="input num"
            type="tel"
            value={form.phone}
            onChange={(e) => setForm({ ...form, phone: e.target.value })}
          />
        </Field>
        <Field label="الاسم">
          <input
            className="input"
            value={form.full_name}
            onChange={(e) => setForm({ ...form, full_name: e.target.value })}
          />
        </Field>
        <Field label="الفرع">
          <select
            className="input"
            value={selected}
            onChange={(e) => setBranchId(e.target.value)}
          >
            {branches.map((branch) => (
              <option key={branch.id} value={branch.id}>
                {branch.name}
              </option>
            ))}
          </select>
        </Field>
        <Field label="الدور">
          <select
            className="input"
            value={form.role}
            onChange={(e) => setForm({ ...form, role: e.target.value })}
          >
            <option value="cashier">كاشير — يؤكّد العمليات فقط</option>
            <option value="manager">مدير — يرى التقارير والحملات</option>
            <option value="owner">مالك — صلاحيات كاملة</option>
          </select>
        </Field>
        <Field label="كلمة المرور المبدئية">
          <input
            className="input"
            type="text"
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
          />
        </Field>
        {create.error != null && <ErrorBox error={create.error} />}
      </div>
    </Modal>
  );
}

/* ══════════════ الاشتراك ══════════════ */

const LIMIT_LABELS: Record<string, string> = {
  max_branches: "الفروع",
  max_terminals: "نقاط البيع",
  max_staff: "الموظفون",
  max_programs: "البرامج",
  max_customers: "العملاء",
};

const USAGE_KEYS: Record<string, string> = {
  max_branches: "branches",
  max_terminals: "terminals",
  max_staff: "staff",
  max_programs: "programs",
  max_customers: "customers",
};

function SubscriptionPanel() {
  const subscription = useApi((signal) => queries.subscription(signal), []);
  const invoices = useApi((signal) => queries.invoices(signal), []);
  const wallet = useApi((signal) => queries.wallet(signal), []);

  if (subscription.loading) return <Loading />;
  if (subscription.error != null)
    return <ErrorBox error={subscription.error} onRetry={subscription.reload} />;
  if (!subscription.data) return null;

  const data = subscription.data;

  return (
    <div className="stack gap-lg">
      <div className="card wl-card-p row between wrap">
        <div>
          <p className="t-sm muted">باقتك الحالية</p>
          <p className="t-lg w-8">{data.plan_label}</p>
          <p className="t-sm muted">
            {data.status_label} · تتجدّد {fmt.date(data.current_period_end)}
          </p>
        </div>
        <div>
          <p className="t-sm muted">رصيد الرسائل</p>
          <p className="t-lg w-8 num">{fmt.number(data.message_balance)}</p>
        </div>
      </div>

      <section className="stack gap">
        <h2>الاستخدام مقابل حدود الباقة</h2>
        {Object.entries(LIMIT_LABELS).map(([key, label]) => {
          const raw = data.limits[key];
          const used = data.usage[USAGE_KEYS[key] ?? ""] ?? 0;
          const cap = raw === null || raw === undefined ? null : Number(raw);
          const ratio = cap ? Math.min(100, (used / cap) * 100) : 0;

          return (
            <div key={key} className="stack" style={{ gap: 5 }}>
              <div className="row between t-sm">
                <span>{label}</span>
                <span className="num">
                  {fmt.number(used)}
                  {cap === null ? " / بلا حد" : ` / ${fmt.number(cap)}`}
                </span>
              </div>
              {cap !== null && (
                <div className="usage-bar">
                  <span
                    style={{ width: `${ratio}%` }}
                    className={
                      ratio >= 90 ? "danger" : ratio >= 70 ? "warn" : ""
                    }
                  />
                </div>
              )}
            </div>
          );
        })}
      </section>

      <section className="stack gap">
        <h2>الفواتير</h2>
        {invoices.data?.length === 0 && (
          <Empty icon="▤" title="لا توجد فواتير بعد" />
        )}
        {invoices.data?.map((invoice) => (
          <div key={invoice.id} className="row between card wl-card-p">
            <div>
              <p className="w-7 num">{invoice.number}</p>
              <p className="t-sm muted">
                {fmt.date(invoice.period_start)} — {fmt.date(invoice.period_end)}
              </p>
            </div>
            <div className="row gap">
              <span className="num w-7">{fmt.money(invoice.total)}</span>
              <Badge tone={invoice.status === "paid" ? "green" : "amber"}>
                {invoice.status_label}
              </Badge>
            </div>
          </div>
        ))}
      </section>

      <section className="stack gap">
        <h2>حركة رصيد الرسائل</h2>
        {wallet.data?.history.slice(0, 10).map((line) => (
          <div key={line.id} className="row between t-sm">
            <span>{line.reason_label}</span>
            <span className="num" style={{ color: line.delta > 0 ? "var(--green-600)" : "var(--red-600)" }}>
              {line.delta > 0 ? "+" : ""}
              {fmt.number(line.delta)}
            </span>
          </div>
        ))}
      </section>
    </div>
  );
}
