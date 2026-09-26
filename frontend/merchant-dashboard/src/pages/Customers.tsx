/** العملاء وشرائحهم وملف كل عميل داخل العلامة. */

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
  useDebounced,
} from "@walaee/shared";

import type { IconName, Program } from "@walaee/shared";

import { actions, queries } from "../lib/queries";

const SEGMENTS = [
  { key: "", label: "الكل" },
  { key: "active", label: "نشطون" },
  { key: "dormant", label: "خاملون" },
  { key: "new", label: "جدد" },
];

export function Customers() {
  const [search, setSearch] = useState("");
  const [segment, setSegment] = useState("");
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<string | null>(null);

  const debounced = useDebounced(search, 350);

  const customers = useApi(
    (signal) =>
      queries.customers(
        { search: debounced || undefined, segment: segment || undefined, page },
        signal,
      ),
    [debounced, segment, page],
  );

  return (
    <div className="stack gap-lg">
      <Segments />

      <div className="row gap wrap-f">
        <input
          className="input grow"
          placeholder={t("ابحث بالاسم أو رقم الهاتف")}
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setPage(1);
          }}
        />

        <div className="tabs" role="group" aria-label={t("الشريحة")}>
          {SEGMENTS.map((option) => (
            <button
              key={option.key}
              type="button"
              className={segment === option.key ? "on" : ""}
              onClick={() => {
                setSegment(option.key);
                setPage(1);
              }}
            >
              {t(option.label)}
            </button>
          ))}
        </div>
      </div>

      {customers.loading && <Loading />}
      {customers.error != null && (
        <ErrorBox error={customers.error} onRetry={customers.reload} />
      )}

      {customers.data?.results.length === 0 && (
        <Empty
          icon="users"
          title={t("لا يوجد عملاء")}
          hint={
            debounced
              ? t("لا نتائج مطابقة لبحثك.")
              : t("سيظهر العملاء هنا بعد أول عملية.")
          }
        />
      )}

      {customers.data && customers.data.results.length > 0 && (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>{t("العميل")}</th>
                <th>{t("الهاتف")}</th>
                <th>{t("الرصيد")}</th>
                <th>{t("عضو منذ")}</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {customers.data.results.map((row) => (
                <tr key={row.id}>
                  <td>{row.full_name || "—"}</td>
                  <td className="num">{fmt.phone(row.phone)}</td>
                  <td>
                    {row.balances.length === 0 ? (
                      <span className="faint">—</span>
                    ) : (
                      row.balances.map((balance) => (
                        <span key={balance.program_id} className="balance-chip">
                          <span className="num">{fmt.number(balance.amount)}</span>{" "}
                          {t(balance.unit_label)}
                        </span>
                      ))
                    )}
                  </td>
                  <td className="t-sm muted">{fmt.date(row.joined_at)}</td>
                  <td>
                    <button
                      type="button"
                      className="link"
                      onClick={() => setSelected(row.id)}
                    >
                      {t("التفاصيل")}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {customers.data && customers.data.count > customers.data.results.length && (
        <div className="row" style={{ justifyContent: "center" }}>
          <Button
            variant="ghost"
            disabled={page === 1}
            onClick={() => setPage((p) => p - 1)}
          >
            {t("السابق")}
          </Button>
          <span className="t-sm muted">
            <span className="num">{page}</span> {t("من")}{" "}
            <span className="num">
              {Math.ceil(customers.data.count / customers.data.results.length)}
            </span>
          </span>
          <Button
            variant="ghost"
            disabled={!customers.data.next}
            onClick={() => setPage((p) => p + 1)}
          >
            {t("التالي")}
          </Button>
        </div>
      )}

      <CustomerModal id={selected} onClose={() => setSelected(null)} />
    </div>
  );
}

/* ══════════════ منح أو خصم يدوي ══════════════ */

/**
 * الطريق الوحيد الذي يكتب في رصيد عميل بلا فاتورة.
 *
 * وجوده ليس ترفًا: نموذج **الهدايا** — أحد النماذج الستة — لا
 * يمنح بالفاتورة أصلًا، فبلا هذه الشاشة يخرج التاجر الذي يختاره
 * ببرنامج لا يمنح شيئًا أبدًا. ويخدم ما هو أعمّ: تعويض عن عطل،
 * أو تصحيح خطأ كاشير، أو هدية مناسبة.
 *
 * السبب إلزامي هنا كما هو إلزامي في الخادم، ويُقال للتاجر لماذا:
 * يظهر للعميل في سجله وللمدقّق في سجل التدقيق. حقلٌ يُطلب بلا
 * تفسير يُملأ بـ«تصحيح» ولا يفسّر شيئًا بعد شهر.
 */
function GrantPanel({
  programs,
  membershipId,
  onDone,
}: {
  programs: Program[];
  membershipId: string;
  onDone: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [programId, setProgramId] = useState(programs[0]?.id ?? "");
  const [amount, setAmount] = useState("");
  const [note, setNote] = useState("");

  const grant = useAction(actions.grant);
  const unit = programs.find((p) => p.id === programId)?.unit_label ?? "";

  // برنامج الهدايا بلا رصيد قبل أول منح، فالقائمة تُبنى على
  // البرامج لا على الأرصدة — وإلا اختفى النموذج الذي وُجدت
  // هذه الشاشة من أجله
  if (programs.length === 0) return null;

  if (!open) {
    return (
      <Button variant="ghost" onClick={() => setOpen(true)}>
        <Icon name="gift" size={15} /> {t("منح أو خصم يدوي")}
      </Button>
    );
  }

  return (
    <div className="card card-p stack gap">
      <div className="row between">
        <h3 className="t-sm">{t("منح أو خصم يدوي")}</h3>
        <button type="button" className="link" onClick={() => setOpen(false)}>
          {t("إلغاء")}
        </button>
      </div>

      <Field label={t("البرنامج")}>
        <select
          className="input"
          value={programId}
          onChange={(event) => setProgramId(event.target.value)}
        >
          {programs.map((program) => (
            <option key={program.id} value={program.id}>
              {program.name}
            </option>
          ))}
        </select>
      </Field>

      <Field
        label={t("المقدار")}
        hint={t("موجب يمنح وسالب يخصم — بوحدة {unit}.", { unit: t(unit) })}
      >
        <input
          className="input num"
          inputMode="numeric"
          value={amount}
          onChange={(event) => setAmount(event.target.value.replace(/[^\d.-]/g, ""))}
          placeholder="50"
        />
      </Field>

      <Field
        label={t("السبب")}
        hint={t("يظهر للعميل في سجله وفي سجل التدقيق — اكتب ما يفهمه غيرك بعد شهر.")}
      >
        <input
          className="input"
          value={note}
          onChange={(event) => setNote(event.target.value)}
          placeholder={t("هدية عيد ميلاد العميل")}
          maxLength={200}
        />
      </Field>

      {grant.error != null && <ErrorBox error={grant.error} />}

      <Button
        block
        loading={grant.loading}
        disabled={!amount || note.trim().length < 4}
        onClick={async () => {
          const done = await grant.run({
            membership_id: membershipId,
            program_id: programId,
            amount,
            note: note.trim(),
          });
          if (done) {
            setAmount("");
            setNote("");
            setOpen(false);
            onDone();
          }
        }}
      >
        {t("تنفيذ")}
      </Button>
    </div>
  );
}

function CustomerModal({
  id,
  onClose,
}: {
  id: string | null;
  onClose: () => void;
}) {
  const detail = useApi(
    (signal) => (id ? queries.customer(id, signal) : Promise.resolve(null)),
    [id],
  );
  const programs = useApi((signal) => queries.programs(signal), []);

  if (!id) return null;

  return (
    <Modal open title={t("ملف العميل")} onClose={onClose}>
      {detail.loading && <Loading />}
      {detail.error != null && <ErrorBox error={detail.error} />}

      {detail.data && (
        <div className="stack gap">
          <div>
            <p className="w-8 t-lg">{detail.data.full_name || t("بلا اسم")}</p>
            <p className="t-sm muted num">{fmt.phone(detail.data.phone)}</p>
          </div>

          <div className="row gap wrap">
            <Badge tone="violet">
              {t("أنفق")} <span className="num">{fmt.money(detail.data.total_spend)}</span>
            </Badge>
            <Badge tone="muted"> {t("عضو منذ")} {fmt.date(detail.data.joined_at)}</Badge>
            {detail.data.tier && <Badge tone="amber">{detail.data.tier}</Badge>}
          </div>

          <div className="stack gap">
            <h3 className="t-sm">{t("الأرصدة")}</h3>
            {detail.data.balances.length === 0 ? (
              <p className="faint t-sm">{t("لا يوجد رصيد.")}</p>
            ) : (
              detail.data.balances.map((balance) => (
                <div key={balance.program_id} className="row between">
                  <span className="t-sm">{balance.program_name}</span>
                  <span className="num w-7">
                    {fmt.number(balance.amount)} {t(balance.unit_label)}
                  </span>
                </div>
              ))
            )}
          </div>

          <GrantPanel
            programs={programs.data ?? []}
            membershipId={detail.data.id}
            onDone={detail.reload}
          />

          <div className="stack gap">
            <h3 className="t-sm">{t("آخر النشاط")}</h3>
            {detail.data.recent_activity.length === 0 ? (
              <p className="faint t-sm">{t("لا يوجد نشاط.")}</p>
            ) : (
              <ul className="activity">
                {detail.data.recent_activity.map((line) => (
                  <li key={line.id}>
                    <span
                      className={`activity-delta ${
                        Number(line.delta) > 0 ? "plus" : "minus"
                      } num`}
                    >
                      {Number(line.delta) > 0 ? "+" : ""}
                      {fmt.number(line.delta)}
                    </span>
                    <span className="grow t-sm">
                      {t(line.reason_label)}
                      {line.note && (
                        <span className="t-xs muted"> — {line.note}</span>
                      )}
                    </span>
                    <span className="t-xs faint">
                      {fmt.relativeTime(line.created_at)}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}
    </Modal>
  );
}

/**
 * مؤشرات شرائح العملاء.
 *
 * الأربعة من `/merchant/segments` — تعريف الشريحة نفسه الذي
 * تستخدمه الحملات، فالرقم الذي يراه التاجر هنا هو عدد من ستصلهم
 * الرسالة هناك. تعريفان مختلفان كانا سيجعلان «٤٢ معرّضًا للفقدان»
 * تتحوّل إلى ٣٧ عند الإرسال بلا تفسير.
 */
function Segments() {
  const segments = useApi((signal) => queries.segments(signal), []);

  if (!segments.data) return null;
  const data = segments.data as Record<string, number>;

  // المفاتيح كما تُرجعها /merchant/segments حرفًا بحرف. اختراع
  // أسماء هنا كان يجعل البطاقة تختفي بصمت بدل أن تُظهر رقمًا.
  const cards: {
    key: string;
    label: string;
    sub: string;
    tone: string;
    icon: IconName;
  }[] = [
    {
      key: "total",
      label: t("إجمالي العملاء"),
      sub: t("مسجّلون في برنامجك"),
      tone: "v",
      icon: "users",
    },
    {
      key: "active_30d",
      label: t("نشطون خلال ٣٠ يومًا"),
      sub: t("سجّلوا حركة واحدة على الأقل"),
      tone: "g",
      icon: "refresh",
    },
    {
      key: "dormant_90d",
      label: t("خاملون ٩٠ يومًا"),
      sub: t("يحتاجون حملة استرجاع"),
      tone: "r",
      icon: "alert",
    },
    {
      key: "new_7d",
      label: t("جدد هذا الأسبوع"),
      sub: t("انضمّوا خلال سبعة أيام"),
      tone: "b",
      icon: "plus",
    },
  ];

  return (
    <div className="grid g4">
      {cards
        .filter((card) => data[card.key] !== undefined)
        .map((card) => (
          <article key={card.key} className="kpi">
            <div className="row between">
              <div className="grow">
                <p className="kt">{t(card.label)}</p>
                <p className="kv num">{fmt.number(data[card.key] ?? 0)}</p>
                <p className="ks">{t(card.sub)}</p>
              </div>
              <span className={`ibox ${card.tone}`} aria-hidden="true">
                <Icon name={card.icon} size={20} />
              </span>
            </div>
          </article>
        ))}
    </div>
  );
}
