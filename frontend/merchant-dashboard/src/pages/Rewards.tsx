/**
 * المكافآت — ما الذي يحصل عليه عميلك.
 *
 * شاشة مستقلة عن «إعداد البرنامج» كما في العرض المعتمد، والفصل
 * ليس ترتيبًا: القواعد تُضبط مرة عند الإطلاق ثم لا تُلمس، أما
 * المكافآت فتُضاف وتُوقَف موسميًا. دفنهما في صفحة واحدة يجعل
 * التاجر يمرّ على إعدادات حسّاسة كلما أراد تعديل عرضًا.
 *
 * العمود الحاسم هنا **مرات الاستبدال**: مكافأة لم تُصرف مرة واحدة
 * ليست مكافأة بل شرط تعجيزي، ولا يكتشف التاجر ذلك من قائمة تعرض
 * الأسماء والأثمان وحدها.
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
import type { Program, Reward } from "@walaee/shared";

import { actions, queries } from "../lib/queries";

/** النطاق الصحي لمعدل الاستبدال — راجع البطاقة التحليلية أسفل الشاشة. */
const HEALTHY = { min: 25, max: 45 };

export function Rewards() {
  const rewards = useApi((signal) => queries.rewards(signal), []);
  const programs = useApi((signal) => queries.programs(signal), []);
  const board = useApi((signal) => queries.dashboard(30, signal), []);
  const [creating, setCreating] = useState(false);

  const rows = rewards.data ?? [];
  const redeemed = rows.reduce((sum, r) => sum + (r.redeemed_count ?? 0), 0);

  return (
    <div className="stack gap-lg">
      <section className="card">
        <div className="card-hd">
          <h3>{t("مكافآت متجرك")}</h3>
          <Button size="md" onClick={() => setCreating(true)}>
            <Icon name="plus" size={15} />
            {t("مكافأة جديدة")}
          </Button>
        </div>

        {rewards.loading && <Loading />}
        {rewards.error != null && (
          <ErrorBox error={rewards.error} onRetry={rewards.reload} />
        )}

        {rows.length === 0 && !rewards.loading ? (
          <Empty
            icon="gift"
            title={t("لا توجد مكافآت")}
            hint={t("بلا مكافأة قريبة المنال لا يجد العميل سببًا ليعود.")}
          />
        ) : (
          <div className="table-wrap">
            <table className="tbl">
              <thead>
                <tr>
                  <th>{t("المكافأة")}</th>
                  <th>{t("التكلفة على العميل")}</th>
                  <th>{t("مرات الاستبدال")}</th>
                  <th>{t("تكلفتها عليك")}</th>
                  <th>{t("المخزون")}</th>
                  <th>{t("الحالة")}</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {rows.map((reward) => (
                  <RewardRow
                    key={reward.id}
                    reward={reward}
                    onChange={rewards.reload}
                  />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <div className="grid g2">
        <RedemptionHealth
          granted={board.data?.redemptions ?? 0}
          redeemed={redeemed}
        />
        <RewardValue
          average={board.data?.revenue.average_invoice ?? "0"}
          rewards={rows}
        />
      </div>

      <NewRewardModal
        open={creating}
        programs={programs.data ?? []}
        onClose={() => setCreating(false)}
        onDone={() => {
          setCreating(false);
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
    <tr>
      <td>
        <div className="row">
          <span className="ibox o" aria-hidden="true">
            <Icon name="gift" size={18} />
          </span>
          <b className="t-sm">{reward.title}</b>
        </div>
      </td>
      <td className="num w-7">
        {fmt.number(reward.cost_amount)} {t(reward.unit_label ?? "نقطة")}
      </td>
      <td className="num">
        {reward.redeemed_count ? (
          t("{n} مرة", { n: fmt.number(reward.redeemed_count) })
        ) : (
          <span className="faint">{t("لم تُصرف بعد")}</span>
        )}
      </td>
      <td className="num w-7">{fmt.money(reward.merchant_cost ?? "0")}</td>
      <td className="num">
        {reward.stock === null ? (
          <span className="faint">{t("بلا حد")}</span>
        ) : (
          fmt.number(reward.stock)
        )}
      </td>
      <td>
        <Badge tone={reward.is_active ? "green" : "muted"}>
          {reward.is_active ? t("مفعّلة") : t("موقوفة")}
        </Badge>
      </td>
      <td>
        <Button
          variant="ghost"
          size="md"
          loading={toggle.loading}
          onClick={async () => {
            const done = await toggle.run(reward.id, {
              is_active: !reward.is_active,
            });
            if (done) onChange();
          }}
        >
          {reward.is_active ? t("إيقاف") : t("تفعيل")}
        </Button>
      </td>
    </tr>
  );
}

/**
 * معدل الاستبدال وحكمه.
 *
 * الرقم وحده لا يقول شيئًا — لا التاجر يعرف أن ٦٪ سيّئ ولا أن
 * ٧٠٪ أسوأ. النطاق الصحي مذكور صراحةً مع سبب كل طرف منه.
 */
function RedemptionHealth({
  granted,
  redeemed,
}: {
  granted: number;
  redeemed: number;
}) {
  if (granted === 0 && redeemed === 0) {
    return (
      <div className="card card-p tint-v">
        <div className="row-t">
          <span className="ibox v" style={{ background: "#fff" }}>
            <Icon name="target" size={20} />
          </span>
          <div className="grow">
            <b>{t("لا استبدالات بعد")}</b>
            <p className="t-sm muted mt-1">
              {t("معدل الاستبدال يظهر هنا بعد أول مكافأة يصرفها عميل.")}
            </p>
          </div>
        </div>
      </div>
    );
  }

  const rate = granted > 0 ? (redeemed / granted) * 100 : 0;
  const healthy = rate >= HEALTHY.min && rate <= HEALTHY.max;

  return (
    <div className={`card card-p ${healthy ? "tint-g" : "tint-o"}`}>
      <div className="row-t">
        <span
          className={`ibox ${healthy ? "g" : "o"}`}
          style={{ background: "#fff" }}
        >
          <Icon name="target" size={20} />
        </span>
        <div className="grow">
          <b>
            {t("معدل الاستبدال")} <span className="num">{fmt.percent(rate)}</span>
          </b>
          <p className="t-sm muted mt-1">
            {healthy
              ? t("داخل النطاق الصحي ({min}–{max}٪).", {
                  min: HEALTHY.min,
                  max: HEALTHY.max,
                })
              : rate < HEALTHY.min
                ? t("أقل من النطاق الصحي — المكافآت بعيدة المنال فلا تحفّز أحدًا.")
                : t("أعلى من النطاق الصحي — أنت تمنح أكثر مما يلزم لإعادة العميل.")}
          </p>
        </div>
      </div>
    </div>
  );
}

/**
 * قيمة المكافأة مقابل متوسط الفاتورة.
 *
 * القاعدة المستخدمة: المكافأة المعقولة بين ٢٠٪ و٢٨٪ من متوسط
 * الفاتورة. الهامش الحقيقي يعرفه التاجر وحده، فالحساب يُعرض
 * كإشارة لا كحكم — ومكتوب صراحةً أنه تقدير.
 */
function RewardValue({
  average,
  rewards,
}: {
  average: string;
  rewards: Reward[];
}) {
  const avg = Number(average);

  if (!avg || rewards.length === 0) {
    return (
      <div className="card card-p tint-v">
        <div className="row-t">
          <span className="ibox v" style={{ background: "#fff" }}>
            <Icon name="coins" size={20} />
          </span>
          <div className="grow">
            <b>{t("قيمة المكافأة")}</b>
            <p className="t-sm muted mt-1">
              {t("تظهر المقارنة بعد أول فواتير مسجّلة على البرنامج.")}
            </p>
          </div>
        </div>
      </div>
    );
  }

  const low = avg * 0.2;
  const high = avg * 0.28;
  const over = rewards.filter((r) => Number(r.merchant_cost ?? 0) > high);

  return (
    <div className="card card-p tint-v">
      <div className="row-t">
        <span className="ibox v" style={{ background: "#fff" }}>
          <Icon name="coins" size={20} />
        </span>
        <div className="grow">
          <b>{t("قيمة المكافأة المقترحة")}</b>
          <p className="t-sm muted mt-1">
            {t("متوسط فاتورتك")} <span className="num">{fmt.money(avg)}</span> {t("، فالقيمة المعقولة للمكافأة بين")}{" "}
            <span className="num">{fmt.money(low)}</span> {t("و")}{" "}
            <span className="num">{fmt.money(high)}</span> {t("— تقدير يعتمد على هامش نموذجي، والهامش الحقيقي تعرفه أنت.")}
          </p>
          {over.length > 0 && (
            <p className="t-sm mt-1 c-orange w-7">
              {over.length === 1
                ? t("«{title}» أعلى من الحد الموصى به.", { title: over[0]!.title })
                : t("{n} مكافآت أعلى من الحد الموصى به.", {
                    n: fmt.number(over.length),
                  })}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

function NewRewardModal({
  open,
  programs,
  onClose,
  onDone,
}: {
  open: boolean;
  programs: Program[];
  onClose: () => void;
  onDone: () => void;
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
      title={t("مكافأة جديدة")}
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
              onDone();
            }
          }}
        >
          {t("إضافة")}
        </Button>
      }
    >
      <div className="stack gap">
        <Field label={t("البرنامج")}>
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

        <Field label={t("عنوان المكافأة")}>
          <input
            className="input"
            value={form.title}
            onChange={(e) => setForm({ ...form, title: e.target.value })}
            placeholder={t("مثال: قهوة مجانية")}
          />
        </Field>

        <Field label={t("التكلفة بالوحدات")} hint={t("كم يدفع العميل من رصيده")}>
          <input
            className="input num"
            type="number"
            min="1"
            value={form.cost_amount}
            onChange={(e) => setForm({ ...form, cost_amount: e.target.value })}
          />
        </Field>

        <Field
          label={t("تكلفتها عليك بالجنيه")}
          hint={t("يُحسب بها الالتزام القائم — رقم خاطئ هنا يعطيك التزامًا خاطئًا")}
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
