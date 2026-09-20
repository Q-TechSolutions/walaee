/** العملاء وشرائحهم وملف كل عميل داخل العلامة. */

import { useState } from "react";

import {
  Badge,
  Button,
  Empty,
  ErrorBox,
  Loading,
  Modal,
  fmt,
  useApi,
  useDebounced,
} from "@walaee/shared";

import { queries } from "../lib/queries";

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
      <header>
        <h1>العملاء</h1>
        <p className="t-sm muted">
          عملاء علامتك فقط — لا ترى المنصة ولا أي تاجر آخر هذه القائمة
        </p>
      </header>

      <div className="row gap wrap">
        <input
          className="input grow"
          placeholder="ابحث بالاسم أو رقم الهاتف"
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setPage(1);
          }}
        />

        <div className="range-switch" role="group" aria-label="الشريحة">
          {SEGMENTS.map((option) => (
            <button
              key={option.key}
              type="button"
              className={segment === option.key ? "active" : ""}
              onClick={() => {
                setSegment(option.key);
                setPage(1);
              }}
            >
              {option.label}
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
          icon="👥"
          title="لا يوجد عملاء"
          hint={
            debounced
              ? "لا نتائج مطابقة لبحثك."
              : "سيظهر العملاء هنا بعد أول عملية."
          }
        />
      )}

      {customers.data && customers.data.results.length > 0 && (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>العميل</th>
                <th>الهاتف</th>
                <th>الرصيد</th>
                <th>عضو منذ</th>
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
                          {balance.unit_label}
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
                      التفاصيل
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
            السابق
          </Button>
          <span className="t-sm muted">
            <span className="num">{page}</span> من{" "}
            <span className="num">
              {Math.ceil(customers.data.count / customers.data.results.length)}
            </span>
          </span>
          <Button
            variant="ghost"
            disabled={!customers.data.next}
            onClick={() => setPage((p) => p + 1)}
          >
            التالي
          </Button>
        </div>
      )}

      <CustomerModal id={selected} onClose={() => setSelected(null)} />
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

  if (!id) return null;

  return (
    <Modal open title="ملف العميل" onClose={onClose}>
      {detail.loading && <Loading />}
      {detail.error != null && <ErrorBox error={detail.error} />}

      {detail.data && (
        <div className="stack gap">
          <div>
            <p className="w-8 t-lg">{detail.data.full_name || "بلا اسم"}</p>
            <p className="t-sm muted num">{fmt.phone(detail.data.phone)}</p>
          </div>

          <div className="row gap wrap">
            <Badge tone="violet">
              أنفق <span className="num">{fmt.money(detail.data.total_spend)}</span>
            </Badge>
            <Badge tone="muted">عضو منذ {fmt.date(detail.data.joined_at)}</Badge>
            {detail.data.tier && <Badge tone="amber">{detail.data.tier}</Badge>}
          </div>

          <div className="stack gap">
            <h3 className="t-sm">الأرصدة</h3>
            {detail.data.balances.length === 0 ? (
              <p className="faint t-sm">لا يوجد رصيد.</p>
            ) : (
              detail.data.balances.map((balance) => (
                <div key={balance.program_id} className="row between">
                  <span className="t-sm">{balance.program_name}</span>
                  <span className="num w-7">
                    {fmt.number(balance.amount)} {balance.unit_label}
                  </span>
                </div>
              ))
            )}
          </div>

          <div className="stack gap">
            <h3 className="t-sm">آخر النشاط</h3>
            {detail.data.recent_activity.length === 0 ? (
              <p className="faint t-sm">لا يوجد نشاط.</p>
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
                    <span className="grow t-sm">{line.reason_label}</span>
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
