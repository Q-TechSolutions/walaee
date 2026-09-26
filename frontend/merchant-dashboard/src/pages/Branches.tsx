/**
 * الفروع والكاشيرون — الهيكل التنظيمي.
 *
 * مؤسسة ← علامة ← فرع ← نقطة بيع ← كاشير، معروضة كشجرة لا
 * كجدولين. الجدولان يخفيان السؤال الوحيد المهم هنا: **مين شغّال
 * فين؟** — والشجرة تجيب عنه بنظرة.
 *
 * التسلسل مبنيّ من اليوم الأول حتى لو كان المتجر فرعًا واحدًا:
 * إضافة مستوى لاحقًا تعني ترحيل بيانات وإعادة كتابة الصلاحيات
 * والتقارير معًا.
 */

import { useState } from "react";

import {
  Badge,
  Button,
  Empty,
  ErrorBox,
  Field,
  Icon,
  Loading,
  Modal,
  fmt,
  t,
  useAction,
  useApi,
} from "@walaee/shared";

import { actions, queries } from "../lib/queries";

const ROLE_LABELS: Record<string, string> = {
  owner: "مالك",
  manager: "مدير",
  cashier: "كاشير",
};

export function Branches() {
  const brand = useApi((signal) => queries.brand(signal), []);
  const branches = useApi((signal) => queries.branches(signal), []);
  const terminals = useApi((signal) => queries.terminals(signal), []);
  const staff = useApi((signal) => queries.staff(signal), []);

  const [adding, setAdding] = useState<"branch" | "terminal" | "staff" | null>(
    null,
  );

  const reloadAll = () => {
    branches.reload();
    terminals.reload();
    staff.reload();
  };

  if (branches.loading) return <Loading />;
  if (branches.error != null)
    return <ErrorBox error={branches.error} onRetry={branches.reload} />;

  const rows = branches.data ?? [];

  // التجميع بالاسم لا بالمعرّف: قوائم نقاط البيع والموظفين تُرجع
  // اسم الفرع لا معرّفه. الأسماء فريدة داخل العلامة عمليًا، ولو
  // تكرّرت ظهر الموظف تحت الفرعين — وهو أوضح من اختفائه.
  const byBranch = (name: string) => ({
    terminals: (terminals.data ?? []).filter((t) => t.branch_name === name),
    staff: (staff.data ?? []).filter((m) => m.branch_name === name),
  });

  return (
    <div className="stack gap-lg">
      <section className="card card-p tint-v">
        <div className="row-t">
          <span className="ibox v" style={{ background: "#fff" }}>
            <Icon name="building" size={20} />
          </span>
          <div className="grow">
            <b>{t("تسلسل هرمي من اليوم الأول")}</b>
            <p className="t-sm muted mt-1">
              {t("مؤسسة ← علامة تجارية ← فرع ← نقطة بيع ← مستخدم. بناء هذا التسلسل لاحقًا يعني ترحيل بيانات مؤلمًا وإعادة كتابة الصلاحيات والتقارير معًا.")}
            </p>
          </div>
        </div>
      </section>

      <section className="card">
        <div className="card-hd">
          <h3>{t("الهيكل التنظيمي")}</h3>
          <div className="row gap-sm">
            <Button variant="ghost" size="md" onClick={() => setAdding("staff")}>
              <Icon name="plus" size={14} />
              {t("موظف")}
            </Button>
            <Button
              variant="ghost"
              size="md"
              onClick={() => setAdding("terminal")}
            >
              <Icon name="plus" size={14} />
              {t("نقطة بيع")}
            </Button>
            <Button size="md" onClick={() => setAdding("branch")}>
              <Icon name="plus" size={14} />
              {t("فرع جديد")}
            </Button>
          </div>
        </div>

        <div className="card-p">
          {rows.length === 0 ? (
            <Empty
              icon="building"
              title={t("لا توجد فروع")}
              hint={t("أضف فرعك الأول لتبدأ تسجيل العمليات.")}
            />
          ) : (
            <div className="tree">
              <div className="node">
                <div className="row">
                  <span className="ibox v" aria-hidden="true">
                    <Icon name="layers" size={20} />
                  </span>
                  <div className="grow">
                    <b className="t-md">
                      {brand.data?.organization_name ?? t("مؤسستك")}
                    </b>
                    <p className="t-xs muted">
                      {brand.data?.name} ·{" "}
                      <span className="num">{fmt.number(rows.length)}</span> {t("فرعًا ·")} <span className="num">
                        {fmt.number((staff.data ?? []).length)}
                      </span>{" "}
                      {t("موظفًا")}
                    </p>
                  </div>
                  <Badge tone="violet">{t("مؤسسة")}</Badge>
                </div>

                <div className="kids">
                  {rows.map((branch) => {
                    const { terminals: pos, staff: team } = byBranch(branch.name);

                    return (
                      <div key={branch.id} className="node">
                        <div className="row">
                          <span
                            className={`ibox ${branch.is_active ? "g" : "r"}`}
                            aria-hidden="true"
                          >
                            <Icon name="store" size={18} />
                          </span>
                          <div className="grow">
                            <b className="t-sm">{branch.name}</b>
                            <p className="t-xs muted">
                              {branch.address || t("بلا عنوان")} ·{" "}
                              <span className="num">
                                {fmt.number(pos.length)}
                              </span>{" "}
                              {t("نقطة بيع")}
                            </p>
                          </div>
                          <Badge tone={branch.is_active ? "green" : "muted"}>
                            {branch.is_active ? t("نشط") : t("غير مفعّل")}
                          </Badge>
                        </div>

                        {(team.length > 0 || pos.length > 0) && (
                          <div className="kids">
                            {team.map((member) => (
                              <div
                                key={member.id}
                                className="node"
                                style={{ padding: "9px 13px" }}
                              >
                                <div className="row">
                                  <span className="av av-sm b" aria-hidden="true">
                                    {(member.full_name || t("؟")).trim().charAt(0)}
                                  </span>
                                  <div className="grow">
                                    <b className="t-sm">{member.full_name}</b>
                                    <p className="t-xs muted num">
                                      {fmt.phone(member.phone)}
                                    </p>
                                  </div>
                                  <Badge
                                    tone={member.is_active ? "violet" : "muted"}
                                  >
                                    {t(ROLE_LABELS[member.role] ?? member.role)}
                                  </Badge>
                                </div>
                              </div>
                            ))}

                            {pos.map((terminal) => (
                              <div
                                key={terminal.id}
                                className="node"
                                style={{ padding: "9px 13px" }}
                              >
                                <div className="row">
                                  <span className="ibox" aria-hidden="true">
                                    <Icon name="qr" size={16} />
                                  </span>
                                  <div className="grow">
                                    <b className="t-sm">{terminal.label}</b>
                                    <p className="t-xs muted">{t("نقطة بيع")}</p>
                                  </div>
                                  <Badge
                                    tone={terminal.is_active ? "green" : "muted"}
                                  >
                                    {terminal.is_active ? t("نشطة") : t("موقوفة")}
                                  </Badge>
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          )}
        </div>
      </section>

      <p className="t-sm muted">
        {t("حساب مستقل لكل كاشير شرطٌ لكشف الاحتيال: الحساب المشترك بين اثنين يجعل نسبة أي نمط مشبوه إلى شخص بعينه مستحيلة.")}
      </p>

      <AddBranchModal
        open={adding === "branch"}
        onClose={() => setAdding(null)}
        onDone={() => {
          setAdding(null);
          reloadAll();
        }}
      />
      <AddTerminalModal
        open={adding === "terminal"}
        branches={rows}
        onClose={() => setAdding(null)}
        onDone={() => {
          setAdding(null);
          reloadAll();
        }}
      />
      <AddStaffModal
        open={adding === "staff"}
        branches={rows}
        onClose={() => setAdding(null)}
        onDone={() => {
          setAdding(null);
          reloadAll();
        }}
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
      title={t("فرع جديد")}
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
          {t("إضافة")}
        </Button>
      }
    >
      <div className="stack gap">
        <Field label={t("اسم الفرع")}>
          <input
            className="input"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </Field>
        <Field label={t("العنوان")} hint={t("اختياري")}>
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
      title={t("نقطة بيع جديدة")}
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
          {t("إضافة")}
        </Button>
      }
    >
      <div className="stack gap">
        <Field label={t("الفرع")}>
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
        <Field label={t("التسمية")} hint={t("مثال: كاشير ١")}>
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
      title={t("موظف جديد")}
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
          {t("إضافة")}
        </Button>
      }
    >
      <div className="stack gap">
        <Field label={t("رقم الهاتف")} hint={t("يُستخدم للدخول")}>
          <input
            className="input num"
            type="tel"
            value={form.phone}
            onChange={(e) => setForm({ ...form, phone: e.target.value })}
          />
        </Field>
        <Field label={t("الاسم")}>
          <input
            className="input"
            value={form.full_name}
            onChange={(e) => setForm({ ...form, full_name: e.target.value })}
          />
        </Field>
        <Field label={t("الفرع")}>
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
        <Field label={t("الدور")}>
          <select
            className="input"
            value={form.role}
            onChange={(e) => setForm({ ...form, role: e.target.value })}
          >
            <option value="cashier">{t("كاشير — يؤكّد العمليات فقط")}</option>
            <option value="manager">{t("مدير — يرى التقارير والحملات")}</option>
            <option value="owner">{t("مالك — صلاحيات كاملة")}</option>
          </select>
        </Field>
        <Field label={t("كلمة المرور المبدئية")}>
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
