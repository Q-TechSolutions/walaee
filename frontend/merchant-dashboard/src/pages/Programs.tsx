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
import type { Program } from "@walaee/shared";

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

  const [editing, setEditing] = useState<Program | null>(null);
  const [creatingProgram, setCreatingProgram] = useState(false);

  return (
    <div className="stack gap-lg">
      <section className="card card-p tint-o">
        <div className="row-t">
          <span className="ibox o" style={{ background: "#fff" }}>
            <Icon name="layers" size={20} />
          </span>
          <div className="grow">
            <b>{t("ستة نماذج ولاء داخل نظام واحد")}</b>
            <p className="t-sm muted mt-1">
              {t("اختر النموذج المناسب لنشاطك — المقهى يفضّل الأختام، والصيدلية النقاط، وغسيل السيارات الاسترداد النقدي. ويمكنك تشغيل أكثر من نموذج في نفس الوقت.")}
            </p>
          </div>
        </div>
      </section>

      <div className="row between wrap-f">
        <h3 className="t-lg">{t("برامجك")}</h3>
        {atLeast("owner") && (
          <Button size="md" onClick={() => setCreatingProgram(true)}>
            <Icon name="plus" size={15} />
            {t("برنامج جديد")}
          </Button>
        )}
      </div>

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
                    {program.is_active ? t("نشط") : t("متوقف")}
                  </Badge>
                  <Badge tone="violet">
                    {TYPES.find((t) => t.value === program.type)?.label ??
                      program.type}
                  </Badge>
                </div>
                {program.rule && (
                  <p className="t-sm muted">
                    <span className="num">{fmt.number(program.rule.earn_rate, 2)}</span>{" "}
                    {t(program.unit_label)} {t("لكل جنيه")}
                    {Number(program.rule.min_invoice) > 0 && (
                      <>
                        {t(" · أقل فاتورة ")}
                        <span className="num">
                          {fmt.money(program.rule.min_invoice)}
                        </span>
                      </>
                    )}
                    {program.rule.expiry_months && (
                      <>
                        {t(" · صلاحية ")}
                        <span className="num">{fmt.number(program.rule.expiry_months)}</span>{" "}
                        {t("شهرًا")}
                      </>
                    )}
                    {program.rule.welcome_bonus > 0 && (
                      <>
                        {t(" · ترحيب ")}
                        <span className="num">{fmt.number(program.rule.welcome_bonus)}</span>
                      </>
                    )}
                  </p>
                )}
              </div>

              {atLeast("owner") && (
                <Button variant="ghost" onClick={() => setEditing(program)}>
                  {t("تعديل القواعد")}
                </Button>
              )}
            </div>
          </div>
        ))}
      </div>

      <div className="dash-split">
        {atLeast("owner") && <LiabilityCard />}
        <CardPreview />
      </div>

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

    </div>
  );
}

/**
 * الالتزام القائم بجوار قواعد البرنامج.
 *
 * مكانه هنا لا في لوحة المعلومات: هذا الرقم **نتيجة** للقواعد
 * أعلاه — معدل المنح وصلاحية الرصيد وثمن المكافآت. وضعه بجوارها
 * يجعل أثر أي تعديل مرئيًا في نفس الشاشة بدل أن يُكتشَف بعد شهر.
 */
function LiabilityCard() {
  const liability = useApi((signal) => queries.liability(signal), []);

  if (liability.loading) return <Loading />;
  if (liability.error != null || !liability.data) return null;

  const data = liability.data;

  return (
    <section className="card card-p tint-a">
      <div className="row-t">
        <span className="ibox a" style={{ background: "#fff" }}>
          <Icon name="wallet" size={20} />
        </span>
        <div className="grow">
          <b className="t-sm">{t("الالتزام القائم الآن")}</b>
          <p className="t-2xl w-8 num mt-1">
            {fmt.money(data.estimated_value)}
          </p>
          <p className="t-xs muted mt-1">
            {t("القيمة النقدية لما مُنح ولم يُستبدَل بعد —")}{" "}
            <span className="num">{fmt.number(data.total_units)}</span> {t("وحدة. تقصير مدة الصلاحية يخفضه.")}
          </p>

          {data.by_program.length > 1 && (
            <div className="stack gap mt-3">
              {data.by_program.map((line) => (
                <div key={line.program_id} className="row between t-sm">
                  <span>{line.program_name}</span>
                  <span className="num w-7">
                    {fmt.money(line.estimated_value)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

/**
 * معاينة البطاقة كما يراها العميل.
 *
 * نفس مكوّن البطاقة في تطبيق العميل ونفس أنماطه من المكتبة
 * المشتركة — لا رسم توضيحي. التاجر يضبط قاعدة هنا ويرى أثرها على
 * ما سيصل عميله، وهو الشيء الوحيد الذي يهمّه من كل هذه الحقول.
 */
function CardPreview() {
  const brand = useApi((signal) => queries.brand(signal), []);
  const programs = useApi((signal) => queries.programs(signal), []);
  const rewards = useApi((signal) => queries.rewards(signal), []);

  if (!brand.data) return null;

  const program = programs.data?.find((p) => p.is_active) ?? programs.data?.[0];
  const reward = [...(rewards.data ?? [])]
    .filter((r) => r.is_active !== false)
    .sort((a, b) => Number(a.cost_amount) - Number(b.cost_amount))[0];

  const goal = reward ? Number(reward.cost_amount) : 0;
  // قيمة معروضة لا رصيد عميل: سبعون بالمئة من الهدف تُظهر الشريط
  // في حالته الوسطى، وهي الحالة التي يراها التاجر أكثر من غيرها.
  const shown = goal ? Math.round(goal * 0.7) : 0;

  return (
    <section className="card">
      <div className="card-hd">
        <h3>{t("معاينة البطاقة عند العميل")}</h3>
      </div>
      <div className="card-p">
        <div style={{ maxWidth: 300, marginInline: "auto" }}>
          <div
            className="lcard"
            style={{ "--brand": brand.data.primary_color } as React.CSSProperties}
          >
            <div className="lc-top">
              <span className="lc-logo">
                {brand.data.name.trim().charAt(0)}
              </span>
              <div className="grow">
                <p className="lc-name">{brand.data.name}</p>
                <p className="lc-cat">{brand.data.category || t("متجر")}</p>
              </div>
            </div>

            <div className="lc-mid">
              <div>
                <p className="lc-val num">{fmt.number(shown)}</p>
                <p className="lc-unit">
                  {goal
                    ? t("من {n} {unit}", {
                        n: fmt.number(goal),
                        unit: t(program?.unit_label ?? ""),
                      })
                    : (program?.unit_label ?? t("نقطة"))}
                </p>
              </div>
              {reward && <span className="lc-rew">{reward.title}</span>}
            </div>

            {goal > 0 && (
              <div className="lc-bar">
                <i style={{ width: "70%" }} />
              </div>
            )}
          </div>
        </div>

        <p className="t-sm muted center mt-2">
          {reward
            ? t("هكذا يراها عميلك داخل التطبيق مباشرةً.")
            : t("أضف مكافأة ليظهر للعميل هدف يسعى إليه.")}
        </p>
      </div>
    </section>
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
      title={t("قواعد {name}", { name: program.name })}
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
            {t("حفظ")}
          </Button>
          <Button variant="ghost" onClick={onClose}>
            {t("تراجع")}
          </Button>
        </>
      }
    >
      <div className="stack gap">
        <div className="notice">
          {t("التعديل يسري على")} <strong>{t("المنح الجديدة فقط")}</strong>{t(". أرصدة العملاء الحالية لا تتغيّر — وهذا مقصود: تغيير رصيد عميل بأثر رجعي بلا أن يفعل شيئًا يفقده الثقة.")}
        </div>

        <Field label={t("معدل المنح")} hint={`كم ${t(program.unit_label)} {t("لكل جنيه")}`}>
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
          label={t("أقل فاتورة مؤهّلة")}
          hint={t("يمنع تفتيت الفواتير للحصول على منح متكررة")}
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
          label={t("السقف اليومي للعميل")}
          hint={t("اتركه فارغًا لبلا سقف — السقف يغلق باب الاحتيال الداخلي")}
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
          label={t("صلاحية الرصيد بالأشهر")}
          hint={t("تُجدَّد مع كل عملية — العميل المنتظم لا يفقد رصيده")}
        >
          <input
            className="input num"
            type="number"
            min="0"
            value={value("expiry_months")}
            onChange={(e) => setForm({ ...form, expiry_months: e.target.value })}
          />
        </Field>

        <Field label={t("مكافأة الانضمام")} hint={t("تُمنح مرة واحدة عند أول عملية")}>
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
      title={t("برنامج جديد")}
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
          {t("إنشاء")}
        </Button>
      }
    >
      <div className="stack gap">
        <Field label={t("الاسم")} hint={t("يظهر للعميل في بطاقته")}>
          <input
            className="input"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder={t("مثال: نقاط الذهب")}
          />
        </Field>

        <Field label={t("النموذج")}>
          <select
            className="input"
            value={type}
            onChange={(e) => setType(e.target.value)}
          >
            {TYPES.map((option) => (
              <option key={option.value} value={option.value}>
                {t(option.label)}
              </option>
            ))}
          </select>
        </Field>

        {create.error != null && <ErrorBox error={create.error} />}
      </div>
    </Modal>
  );
}
