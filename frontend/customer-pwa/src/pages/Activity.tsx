/** سجل النشاط الكامل عبر كل البطاقات. */

import { useState } from "react";
import { Link } from "react-router-dom";

import { Button, Empty, ErrorBox, Icon, Loading, fmt, t, useApi } from "@walaee/shared";

import { queries } from "../lib/queries";

export function Activity() {
  const [page, setPage] = useState(1);
  const activity = useApi((signal) => queries.activity(page, signal), [page]);

  return (
    <>
      <header className="topbar">
        <Link to="/" className="iconbtn" aria-label={t("رجوع إلى بطاقاتي")}>
          <Icon name="chevronRight" size={19} />
        </Link>
        <h2>{t("سجل النشاط")}</h2>
      </header>

      <div className="pad section">
        {activity.loading && <Loading />}
        {activity.error != null && (
          <ErrorBox error={activity.error} onRetry={activity.reload} />
        )}

        {activity.data?.results.length === 0 && (
          <Empty
            icon="clock"
            title={t("لا يوجد نشاط بعد")}
            hint={t("أول عملية تتسجّل هنا فور تأكيد الكاشير لها.")}
          />
        )}

        {activity.data && activity.data.results.length > 0 && (
          <div className="card card-p">
            {activity.data.results.map((line) => {
              const delta = Number(line.delta);
              return (
                <div key={line.id} className="li">
                  <span
                    className={`ibox ${delta > 0 ? "g" : "o"}`}
                    aria-hidden="true"
                  >
                    <Icon name={delta > 0 ? "plus" : "gift"} size={18} />
                  </span>

                  <div className="grow">
                    <p className="li-t">{line.brand_name}</p>
                    <p className="li-s">
                      {t(line.reason_label)} · {fmt.relativeTime(line.created_at)}
                    </p>
                  </div>

                  <span
                    className={`li-v num ${delta > 0 ? "c-green" : "c-orange"}`}
                  >
                    {delta > 0 ? "+" : ""}
                    {fmt.number(line.delta)}
                  </span>
                </div>
              );
            })}
          </div>
        )}

        {activity.data && activity.data.count > activity.data.results.length && (
          <div className="row center" style={{ justifyContent: "center" }}>
            <Button
              variant="ghost"
              disabled={page === 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
            >
              {t("السابق")}
            </Button>
            <span className="t-sm muted num">{fmt.number(page)}</span>
            <Button
              variant="ghost"
              disabled={!activity.data.next}
              onClick={() => setPage((p) => p + 1)}
            >
              {t("التالي")}
            </Button>
          </div>
        )}
      </div>
    </>
  );
}
