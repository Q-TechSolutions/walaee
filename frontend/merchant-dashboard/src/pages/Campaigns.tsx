/**
 * الحملات.
 *
 * القاعدة الحاكمة في هذه الشاشة: **الرقم قبل الإرسال.**
 *
 * التاجر يعدّل الشريحة فيرى عدد المستهدفين والتكلفة تتغيّر لحظيًا،
 * ولا يظهر زر «إرسال» إلا بعد أن يرى الرقم ويؤكّده. تاجر يكتشف
 * فاتورة الحملة بعد إرسالها هو تاجر يلغي اشتراكه — مهما كانت
 * الحملة ناجحة.
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
  t,
  useAction,
  useApi,
  useDebounced,
} from "@walaee/shared";
import type { Campaign, CampaignEstimate } from "@walaee/shared";

import { SendTimeCard } from "../components/Suggestions";
import { actions, queries } from "../lib/queries";

const STATUS_TONE: Record<string, "muted" | "violet" | "green" | "red" | "amber"> = {
  draft: "muted",
  scheduled: "violet",
  sending: "amber",
  sent: "green",
  cancelled: "muted",
  failed: "red",
};

const STATUS_LABEL: Record<string, string> = {
  draft: "مسودة",
  scheduled: "مجدولة",
  sending: "قيد الإرسال",
  sent: "أُرسلت",
  cancelled: "ملغاة",
  failed: "فشلت",
};

export function Campaigns() {
  const campaigns = useApi((signal) => queries.campaigns(signal), []);
  const insights = useApi((signal) => queries.insights(signal), []);
  const [composing, setComposing] = useState(false);

  return (
    <div className="stack gap-lg">
      <div className="row between wrap-f">
        <p className="t-sm muted">{t("راسل عملاءك على أرخص قناة تصل إليهم — الإشعار أولًا، ثم ما يخرج إلى شبكة الاتصالات.")}</p>
        <Button onClick={() => setComposing(true)}>{t("حملة جديدة")}</Button>
      </div>

      {/* التوقيت قبل القائمة: الرسالة تكلّف رصيدًا، وإرسالها
          في الساعة الخطأ يدفع ثمنها بلا أن تُقرأ */}
      <SendTimeCard data={insights.data?.send_time} loading={insights.loading} />

      {campaigns.loading && <Loading />}
      {campaigns.error != null && (
        <ErrorBox error={campaigns.error} onRetry={campaigns.reload} />
      )}

      {campaigns.data?.length === 0 && (
        <Empty
          icon="message"
          title={t("لا توجد حملات بعد")}
          hint={t("ابدأ بحملة لعملائك الخاملين — غالبًا أعلى عائد لأول حملة.")}
          action={<Button onClick={() => setComposing(true)}>{t("حملة جديدة")}</Button>}
        />
      )}

      <div className="stack gap">
        {campaigns.data?.map((campaign) => (
          <CampaignRow
            key={campaign.id}
            campaign={campaign}
            onChange={campaigns.reload}
          />
        ))}
      </div>

      <Composer
        open={composing}
        onClose={() => setComposing(false)}
        onCreated={campaigns.reload}
      />
    </div>
  );
}

function CampaignRow({
  campaign,
  onChange,
}: {
  campaign: Campaign;
  onChange: () => void;
}) {
  const send = useAction(actions.sendCampaign);
  const cancel = useAction(actions.cancelCampaign);

  const editable = campaign.status === "draft" || campaign.status === "scheduled";

  return (
    <div className="campaign-row">
      <div className="grow">
        <div className="row" style={{ gap: 8 }}>
          <span className="w-7">{campaign.name}</span>
          <Badge tone={STATUS_TONE[campaign.status] ?? "muted"}>
            {t(STATUS_LABEL[campaign.status] ?? campaign.status)}
          </Badge>
        </div>
        <p className="t-sm muted campaign-preview">{campaign.message_template}</p>
        <p className="t-xs faint">
          <span className="num">{fmt.number(campaign.estimated_recipients)}</span>{" "}
          {t("مستهدف · تكلفة مقدَّرة")}{" "}
          <span className="num">{fmt.money(campaign.estimated_cost)}</span>
          {campaign.status === "sent" && (
            <>
              {t(" · أُرسلت ")}
              <span className="num">{fmt.number(campaign.sent_count)}</span>
              {campaign.failed_count > 0 && (
                <>
                  {t(" · فشلت ")}
                  <span className="num">{fmt.number(campaign.failed_count)}</span>
                </>
              )}
              {t(" · التكلفة الفعلية ")}
              <span className="num">{fmt.money(campaign.actual_cost)}</span>
            </>
          )}
        </p>
        {(send.error != null || cancel.error != null) && (
          <ErrorBox error={send.error ?? cancel.error} />
        )}
      </div>

      {editable && (
        <div className="row" style={{ gap: 8 }}>
          <Button
            loading={send.loading}
            onClick={async () => {
              const done = await send.run(campaign.id);
              if (done) onChange();
            }}
          >
            {t("إرسال الآن")}
          </Button>
          <Button
            variant="ghost"
            loading={cancel.loading}
            onClick={async () => {
              const done = await cancel.run(campaign.id);
              if (done) onChange();
            }}
          >
            {t("إلغاء")}
          </Button>
        </div>
      )}
    </div>
  );
}

/**
 * منشئ الحملة.
 *
 * التقدير يُعاد حسابه مع كل تعديل على الشريحة بتأخير قصير: النداء
 * رخيص (لا يكتب شيئًا) والفائدة كبيرة — التاجر يرى أثر كل شرط
 * على الرقم فورًا فيضبط الشريحة بدل أن يرسل ويندم.
 */
function Composer({
  open,
  onClose,
  onCreated,
}: {
  open: boolean;
  onClose: () => void;
  onCreated: () => void;
}) {
  const [name, setName] = useState("");
  const [template, setTemplate] = useState(
    t("اشتقنا لك يا {name}! رصيدك في {brand} بانتظارك."),
  );
  const [inactiveDays, setInactiveDays] = useState("30");
  const [minBalance, setMinBalance] = useState("");

  const segment = buildSegment(inactiveDays, minBalance);
  const debouncedSegment = useDebounced(JSON.stringify(segment), 400);

  const estimate = useApi(
    () => actions.previewCampaign({ segment_query: JSON.parse(debouncedSegment) }),
    [debouncedSegment, open],
  );

  const create = useAction(actions.createCampaign);

  return (
    <Modal
      open={open}
      title={t("حملة جديدة")}
      onClose={onClose}
      footer={
        <>
          <Button
            loading={create.loading}
            disabled={!name.trim() || !estimate.data?.reachable}
            onClick={async () => {
              const created = await create.run({
                name: name.trim(),
                message_template: template,
                segment_query: segment,
              });
              if (created) {
                onCreated();
                onClose();
              }
            }}
          >
            {t("إنشاء الحملة")}
          </Button>
          <Button variant="ghost" onClick={onClose}>
            {t("تراجع")}
          </Button>
        </>
      }
    >
      <div className="stack gap">
        <Field label={t("اسم الحملة")} hint={t("للتمييز في قائمتك فقط — لا يراه العميل")}>
          <input
            className="input"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder={t("مثال: عودة الخاملين — أكتوبر")}
          />
        </Field>

        <Field
          label={t("نص الرسالة")}
          hint={t("يمكنك استخدام {name} لاسم العميل و {brand} لاسم متجرك")}
        >
          <textarea
            className="input"
            rows={3}
            value={template}
            onChange={(e) => setTemplate(e.target.value)}
          />
        </Field>

        <div className="row gap wrap">
          <Field label={t("لم يشترِ منذ (أيام)")} hint={t("اتركه فارغًا لكل العملاء")}>
            <input
              className="input num"
              type="number"
              min="0"
              value={inactiveDays}
              onChange={(e) => setInactiveDays(e.target.value)}
            />
          </Field>

          <Field label={t("رصيده لا يقل عن")} hint={t("اختياري")}>
            <input
              className="input num"
              type="number"
              min="0"
              value={minBalance}
              onChange={(e) => setMinBalance(e.target.value)}
            />
          </Field>
        </div>

        {estimate.error != null && <ErrorBox error={estimate.error} />}
        {estimate.loading && <Loading label={t("جارٍ حساب التكلفة…")} />}
        {estimate.data && <EstimatePanel estimate={estimate.data} />}

        {create.error != null && <ErrorBox error={create.error} />}
      </div>
    </Modal>
  );
}

function buildSegment(inactiveDays: string, minBalance: string) {
  const segment: Record<string, number> = {};
  const days = Number(inactiveDays);
  const balance = Number(minBalance);

  if (inactiveDays.trim() !== "" && Number.isFinite(days) && days >= 0) {
    segment["inactive_days"] = days;
  }
  if (minBalance.trim() !== "" && Number.isFinite(balance) && balance >= 0) {
    segment["min_balance"] = balance;
  }
  return segment;
}

function EstimatePanel({ estimate }: { estimate: CampaignEstimate }) {
  const affordable = estimate.billable_messages <= estimate.wallet_balance;

  return (
    <div className={`estimate ${affordable ? "" : "estimate-short"}`}>
      <p className="t-sm">{estimate.segment_description}</p>

      <div className="row between">
        <span className="w-7">{t("سيصل إلى")}</span>
        <span className="num w-8">{fmt.number(estimate.reachable)}</span>
      </div>

      {estimate.unreachable > 0 && (
        <p className="t-xs faint">
          <span className="num">{fmt.number(estimate.unreachable)}</span> {t("عميل لا يمكن الوصول إليه — لن تُحتسب عليك تكلفتهم.")}
        </p>
      )}

      <div className="estimate-channels">
        {Object.entries(estimate.per_channel).map(([channel, info]) => (
          <div key={channel} className="row between t-sm">
            <span>{t(info.label)}</span>
            <span>
              <span className="num">{fmt.number(info.count)}</span>
              {Number(info.unit_cost) === 0 ? (
                <Badge tone="green">{t("مجاني")}</Badge>
              ) : (
                <span className="faint num">
                  {" × "}
                  {fmt.money(info.unit_cost)}
                </span>
              )}
            </span>
          </div>
        ))}
      </div>

      <div className="row between estimate-total">
        <span className="w-8">{t("التكلفة")}</span>
        <span className="num w-8">{fmt.money(estimate.cost)}</span>
      </div>

      <p className="t-xs">
        {t("رصيد رسائلك")}{" "}
        <span className="num w-7">{fmt.number(estimate.wallet_balance)}</span> {t("· تحتاج")}{" "}
        <span className="num w-7">
          {fmt.number(estimate.billable_messages)}
        </span>
        {!affordable && t(" — الرصيد غير كافٍ، اشحن قبل الإرسال.")}
      </p>
    </div>
  );
}
