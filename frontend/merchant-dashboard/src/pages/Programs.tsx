/**
 * البرامج والقواعد والمكافآت.
 *
 * تعديل القاعدة يعرض تحذيرًا صريحًا: **يسري على المنح الجديدة فقط.**
 * تاجر يظن أنه رفع معدل المنح بأثر رجعي سيفاجأ بشكاوى عملاء لم
 * تتغيّر أرصدتهم — والسبب ليس عطلًا بل سوء فهم كان يمكن منعه بسطر.
 */

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
import type { Program, Reward } from "@walaee/shared";

import { actions, queries } from "../lib/queries";
import { atLeast } from "../lib/session";

const TYPES = [
  { value: "points", label: "نقاط" },
  { value: "stamps", label: "أختام" },
  { value: "visits", label: "زيارات" },
  { value: "cashback", label: "استرداد نقدي" },
  { value: "rewards", label: "مكافآت" },
  { value: "gifts", label: "هدايا" },
];

export function Programs() {
  const programs = useApi((signal) => queries.programs(signal), []);
  const rewards = useApi((signal) => queries.rewards(signal), []);

  const [editing, setEditing] = useState<Program | null>(null);
  const [creatingProgram, setCreatingProgram] = useState(false);
  const [creatingReward, setCreatingReward] = useState(false);

  return (
    <div className="stack gap-lg">
      <header className="row between wrap">
        <div>
          <h1>البرامج والمكافآت</h1>
          <p className="t-sm muted">قواعد المنح وما يمكن للعميل استبداله</p>
        </div>
        {atLeast("owner") && (
          <Button onClick={() => setCreatingProgram(true)}>برنامج جديد</Button>
        )}
      </header>

      {programs.loading && <Loading />}
      {programs.error != null && (
        <ErrorBox error={programs.error} onRetry={programs.reload} />
      )}

      <div className="stack gap">
        {programs.data?.map((program) => (
          <div key={program.id} className="card wl-card-p">
            <div className="row between wrap">
              <div>
                <div className="row" style={{ gap: 8 }}>
                  <span className="w-7">{program.name}</span>
                  <Badge tone={program.is_active ? "green" : "muted"}>
                    {program.is_active ? "نشط" : "متوقف"}
                  </Badge>
                  <Badge tone="violet">
                    {TYPES.find((t) => t.value === program.type)?.label ??
                      program.type}
                  </Badge>
                </div>
                {program.rule && (
                  <p className="t-sm muted">
                    <span className="num">{program.rule.earn_rate}</span>{" "}
                    {program.unit_label} لكل جنيه
                    {Number(program.rule.min_invoice) > 0 && (
                      <>
                        {" · أقل فاتورة "}
                        <span className="num">
                          {fmt.money(program.rule.min_invoice)}
                        </span>
                      </>
                    )}
                    {program.rule.expiry_months && (
                      <>
                        {" · صلاحية "}
                        <span className="num">{program.rule.expiry_months}</span>{" "}
                        شهرًا
                      </>
                    )}
                    {program.rule.welcome_bonus > 0 && (
                      <>
                        {" · ترحيب "}
                        <span className="num">{program.rule.welcome_bonus}</span>
                      </>
                    )}
                  </p>
                )}
              </div>

              {atLeast("owner") && (
                <Button variant="ghost" onClick={() => setEditing(program)}>
                  تعديل القواعد
                </Button>
              )}
            </div>
          </div>
        ))}
      </div>

      <section className="stack gap">
        <div className="row between wrap">
          <h2>المكافآت</h2>
          <Button variant="ghost" onClick={() => setCreatingReward(true)}>
            مكافأة جديدة
          </Button>
        </div>

        {rewards.data?.length === 0 && (
          <Empty
            icon="🎁"
            title="لا توجد مكافآت"
            hint="بلا مكافأة قريبة المنال لا يجد العميل سببًا ليعود."
          />
        )}

        <div className="stack gap">
          {rewards.data?.map((reward) => (
            <RewardRow key={reward.id} reward={reward} onChange={rewards.reload} />
          ))}
        </div>
      </section>

      <RuleModal
        program={editing}
        onClose={() => setEditing(null)}
        onSaved={() => {
          setEditing(null);
          programs.reload();
        }}
      />

      <NewProgramModal
        open={creatingProgram}
        onClose={() => setCreatingProgram(false)}
        onCreated={() => {
          setCreatingProgram(false);
          programs.reload();
        }}
      />

      <NewRewardModal
        open={creatingReward}
        programs={programs.data ?? []}
        onClose={() => setCreatingReward(false)}
        onCreated={() => {
          setCreatingReward(false);
          rewards.reload();
        }}
      />
    </div>
  );
}

function RewardRow({
  reward,
  onChange,
}: {
  reward: Reward;
  onChange: () => void;
}) {
  const toggle = useAction(actions.updateReward);

  return (
    <div className="reward-row">
      <div className="grow">
        <p className="w-7">{reward.title}</p>
        <p className="t-sm muted">
          <span className="num">{fmt.number(reward.cost_amount)}</span>{" "}
          {reward.unit_label ?? "نقطة"} · تكلفتها عليك{" "}
          <span className="num">{fmt.money(reward.merchant_cost ?? "0")}</span>
          {reward.stock !== null && (
            <>
              {" · المخزون "}
              <span className="num">{fmt.number(reward.stock)}</span>
            </>
          )}
        </p>
      </div>

      <Button
        variant="ghost"
        loading={toggle.loading}
        onClick={async () => {
          const done = await toggle.run(reward.id, {
            is_active: !reward.is_active,
          });
          if (done) onChange();
        }}
      >
        {reward.is_active ? "إيقاف" : "تفعيل"}
      </Button>
    </div>
  );
}

function RuleModal({
  program,
  onClose,
  onSaved,
}: {
  program: Program | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [form, setForm] = useState<Record<string, string>>({});
  const save = useAction(actions.updateRule);

  if (!program?.rule) return null;

  const value = (key: keyof NonNullable<Program["rule"]>) =>
    form[key] ?? String(program.rule?.[key] ?? "");

  return (
    <Modal
      open
      title={`قواعد ${program.name}`}
      onClose={onClose}
      footer={
        <>
          <Button
            loading={save.loading}
            onClick={async () => {
              const done = await save.run(program.id, form);
              if (done) {
                setForm({});
                onSaved();
              }
            }}
          >
            حفظ
          </Button>
          <Button variant="ghost" onClick={onClose}>
            تراجع
          </Button>
        </>
      }
    >
      <div className="stack gap">
        <div className="notice">
          التعديل يسري على <strong>المنح الجديدة فقط</strong>. أرصدة العملاء
          الحالية لا تتغيّر — وهذا مقصود: تغيير رصيد عميل بأثر رجعي بلا أن
          يفعل شيئًا يفقده الثقة.
        </div>

        <Field label="معدل المنح" hint={`كم ${program.unit_label} لكل جنيه`}>
          <input
            className="input num"
            type="number"
            step="0.0001"
            min="0"
            value={value("earn_rate")}
            onChange={(e) => setForm({ ...form, earn_rate: e.target.value })}
          />
        </Field>

        <Field
          label="أقل فاتورة مؤهّلة"
          hint="يمنع تفتيت الفواتير للحصول على منح متكررة"
        >
          <input
            className="input num"
            type="number"
            step="0.01"
            min="0"
            value={value("min_invoice")}
            onChange={(e) => setForm({ ...form, min_invoice: e.target.value })}
          />
        </Field>

        <Field
          label="السقف اليومي للعميل"
          hint="اتركه فارغًا لبلا سقف — السقف يغلق باب الاحتيال الداخلي"
        >
          <input
            className="input num"
            type="number"
            step="1"
            min="0"
            value={value("max_per_day")}
            onChange={(e) => setForm({ ...form, max_per_day: e.target.value })}
          />
        </Field>

        <Field
          label="صلاحية الرصيد بالأشهر"
          hint="تُجدَّد مع كل عملية — العميل المنتظم لا يفقد رصيده"
        >
          <input
            className="input num"
            type="number"
            min="0"
            value={value("expiry_months")}
            onChange={(e) => setForm({ ...form, expiry_months: e.target.value })}
          />
        </Field>

        <Field label="مكافأة الانضمام" hint="تُمنح مرة واحدة عند أول عملية">
          <input
            className="input num"
            type="number"
            min="0"
            value={value("welcome_bonus")}
            onChange={(e) => setForm({ ...form, welcome_bonus: e.target.value })}
          />
        </Field>

        {save.error != null && <ErrorBox error={save.error} />}
      </div>
    </Modal>
  );
}

function NewProgramModal({
  open,
  onClose,
  onCreated,
}: {
  open: boolean;
  onClose: () => void;
  onCreated: () => void;
}) {
  const [name, setName] = useState("");
  const [type, setType] = useState("points");
  const create = useAction(actions.createProgram);

  return (
    <Modal
      open={open}
      title="برنامج جديد"
      onClose={onClose}
      footer={
        <Button
          loading={create.loading}
          disabled={!name.trim()}
          onClick={async () => {
            const done = await create.run({ name: name.trim(), type });
            if (done) {
              setName("");
              onCreated();
            }
          }}
        >
          إنشاء
        </Button>
      }
    >
      <div className="stack gap">
        <Field label="الاسم" hint="يظهر للعميل في بطاقته">
          <input
            className="input"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="مثال: نقاط الذهب"
          />
        </Field>

        <Field label="النموذج">
          <select
            className="input"
            value={type}
            onChange={(e) => setType(e.target.value)}
          >
            {TYPES.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </Field>

        {create.error != null && <ErrorBox error={create.error} />}
      </div>
    </Modal>
  );
}

function NewRewardModal({
  open,
  programs,
  onClose,
  onCreated,
}: {
  open: boolean;
  programs: Program[];
  onClose: () => void;
  onCreated: () => void;
}) {
  const [form, setForm] = useState({
    title: "",
    cost_amount: "",
    merchant_cost: "",
    program_id: "",
  });
  const create = useAction(actions.createReward);

  const programId = form.program_id || programs[0]?.id || "";

  return (
    <Modal
      open={open}
      title="مكافأة جديدة"
      onClose={onClose}
      footer={
        <Button
          loading={create.loading}
          disabled={!form.title.trim() || !form.cost_amount || !programId}
          onClick={async () => {
            const done = await create.run({
              title: form.title.trim(),
              cost_amount: form.cost_amount,
              merchant_cost: form.merchant_cost || "0",
              program_id: programId,
            });
            if (done) {
              setForm({
                title: "",
                cost_amount: "",
                merchant_cost: "",
                program_id: "",
              });
              onCreated();
            }
          }}
        >
          إضافة
        </Button>
      }
    >
      <div className="stack gap">
        <Field label="البرنامج">
          <select
            className="input"
            value={programId}
            onChange={(e) => setForm({ ...form, program_id: e.target.value })}
          >
            {programs.map((program) => (
              <option key={program.id} value={program.id}>
                {program.name}
              </option>
            ))}
          </select>
        </Field>

        <Field label="عنوان المكافأة">
          <input
            className="input"
            value={form.title}
            onChange={(e) => setForm({ ...form, title: e.target.value })}
            placeholder="مثال: قهوة مجانية"
          />
        </Field>

        <Field label="التكلفة بالوحدات" hint="كم يدفع العميل من رصيده">
          <input
            className="input num"
            type="number"
            min="1"
            value={form.cost_amount}
            onChange={(e) => setForm({ ...form, cost_amount: e.target.value })}
          />
        </Field>

        <Field
          label="تكلفتها عليك بالجنيه"
          hint="يُحسب بها الالتزام القائم — رقم خاطئ هنا يعطيك التزامًا خاطئًا"
        >
          <input
            className="input num"
            type="number"
            step="0.01"
            min="0"
            value={form.merchant_cost}
            onChange={(e) => setForm({ ...form, merchant_cost: e.target.value })}
          />
        </Field>

        {create.error != null && <ErrorBox error={create.error} />}
      </div>
    </Modal>
  );
}
