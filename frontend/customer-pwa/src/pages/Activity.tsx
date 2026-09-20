/** سجل النشاط الكامل عبر كل البطاقات. */

import { useState } from "react";

import { Button, Empty, ErrorBox, Loading, fmt, useApi } from "@walaee/shared";

import { queries } from "../lib/queries";

export function Activity() {
  const [page, setPage] = useState(1);
  const activity = useApi((signal) => queries.activity(page, signal), [page]);

  return (
    <div className="page">
      <h1 className="mb">سجل النشاط</h1>

      {activity.loading && <Loading />}
      {activity.error != null && (
        <ErrorBox error={activity.error} onRetry={activity.reload} />
      )}

      {activity.data?.results.length === 0 && (
        <Empty icon="🕗" title="لا يوجد نشاط بعد" />
      )}

      <ul className="activity">
        {activity.data?.results.map((line) => (
          <li key={line.id}>
            <span
              className={`activity-delta ${
                Number(line.delta) > 0 ? "plus" : "minus"
              } num`}
            >
              {Number(line.delta) > 0 ? "+" : ""}
              {fmt.number(line.delta)}
            </span>
            <span className="grow">
              <span className="w-7">{line.brand_name}</span>
              <span className="t-xs faint"> · {line.reason_label}</span>
            </span>
            <span className="t-xs faint">
              {fmt.relativeTime(line.created_at)}
            </span>
          </li>
        ))}
      </ul>

      {activity.data && activity.data.count > activity.data.results.length && (
        <div className="row" style={{ justifyContent: "center", marginTop: 16 }}>
          <Button
            variant="ghost"
            disabled={page === 1}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
          >
            السابق
          </Button>
          <span className="t-sm muted num">{page}</span>
          <Button
            variant="ghost"
            disabled={!activity.data.next}
            onClick={() => setPage((p) => p + 1)}
          >
            التالي
          </Button>
        </div>
      )}
    </div>
  );
}
