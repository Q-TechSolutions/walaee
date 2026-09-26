/**
 * حالة التشغيل — من مصادر حقيقية فقط.
 *
 * هذه الشاشة تُفتح وقت الشك، ورقمٌ لا مصدر له فيها يُقرأ كطمأنة
 * فيوقف التحقيق في لحظة بدايته. لذلك لا نسبة زمن تشغيل هنا ولا
 * متوسط استجابة: لا يوجد APM في هذا النشر، وغياب الرقم أصدق من
 * رقم مخترَع.
 *
 * وما يُعرض هو ما يمكن إثباته الآن: هل استجابت القاعدة والكاش
 * ومتى، ومتى عملت كل مهمة دورية آخر مرة، وهل الأرصدة مطابقة
 * لقيودها في عيّنة تُقرأ لحظيًا.
 */

import { Badge, ErrorBox, Icon, Loading, fmt, t, useApi } from "@walaee/shared";

import { queries } from "../lib/queries";

/** فوق هذا العدد من الساعات تُعدّ المهمة صامتة. أطول فجوة في
 *  الجدول يوم واحد، فضعفه يعني تفويت تشغيلة كاملة. */
const SILENT_AFTER_HOURS = 48;

const VOLUME_LABELS: Record<string, string> = {
  customers: "عميل",
  memberships: "عضوية",
  transactions: "عملية",
  ledger_entries: "قيد",
  branches: "فرع",
};

export function Ops() {
  const ops = useApi((signal) => queries.ops(signal), []);

  if (ops.loading) return <Loading />;
  if (ops.error != null) return <ErrorBox error={ops.error} onRetry={ops.reload} />;
  if (!ops.data) return null;

  const { services, tasks, integrity, volume, checked_at: checkedAt } = ops.data;
  const down = services.filter((service) => !service.ok);
  const silent = tasks.filter(
    (task) =>
      task.enabled && (task.silent_hours === null || task.silent_hours > SILENT_AFTER_HOURS),
  );

  return (
    <>
      {(down.length > 0 || !integrity.ok || silent.length > 0) && (
        <section className="card card-p tint-r mb">
          <div className="row-t">
            <span className="ibox r" aria-hidden="true">
              <Icon name="alert" size={20} />
            </span>
            <div className="grow">
              <b>{t("ما يحتاج نظرة الآن")}</b>
              <ul className="t-sm muted mt-1">
                {down.map((service) => (
                  <li key={service.name}>
                    {t("{name} لا تستجيب", { name: t(service.name) })}
                  </li>
                ))}
                {!integrity.ok && (
                  <li>
                    {t("انحراف في {n} محفظة من العيّنة — أوقف النشر وراجع", {
                      n: fmt.number(integrity.drifted),
                    })}
                  </li>
                )}
                {silent.map((task) => (
                  <li key={task.name}>{t("{name} لم تعمل منذ فترة", { name: task.name })}</li>
                ))}
              </ul>
            </div>
          </div>
        </section>
      )}

      <div className="grid g2 mb">
        <section className="card">
          <div className="card-hd">
            <h3>{t("حالة الخدمات")}</h3>
            <span className="t-xs muted">{fmt.relativeTime(checkedAt)}</span>
          </div>
          <div className="card-p">
            {services.map((service) => (
              <div key={service.name} className="li">
                <span
                  className={`ibox ${service.ok ? "g" : "r"}`}
                  aria-hidden="true"
                >
                  <Icon name={service.ok ? "checkCircle" : "alert"} size={18} />
                </span>
                <div className="grow">
                  <p className="li-t">{t(service.name)}</p>
                  <p className="li-s">
                    {service.detail || t("استجابت")}
                  </p>
                </div>
                <span className={`li-v num ${service.ok ? "c-green" : "c-red"}`}>
                  {fmt.number(service.latency_ms, 1)} {t("مللي")}
                </span>
              </div>
            ))}
          </div>
        </section>

        <section className="card">
          <div className="card-hd">
            <h3>{t("مطابقة الأرصدة لقيودها")}</h3>
            <Badge tone={integrity.ok ? "green" : "red"}>
              {integrity.ok ? t("سليم") : t("انحراف")}
            </Badge>
          </div>
          <div className="card-p">
            <p className="t-2xl w-8 num">{fmt.number(integrity.checked)}</p>
            <p className="t-sm muted">{t("محفظة في العيّنة اللحظية")}</p>
            <p className="t-sm muted mt-2">
              {integrity.ok
                ? t("الفحص الكامل يمرّ على كل محفظة ليلًا — راجع سجل المهام بالأسفل.")
                : t("القيود مصدر الحقيقة. لا تصحّح اللقطة قبل أن تعرف أي مسار كتب خارج المحرك.")}
            </p>
          </div>
        </section>
      </div>

      <section className="card mb">
        <div className="card-hd">
          <h3>{t("المهام الدورية")}</h3>
          <span className="t-xs muted">
            {t("المهمة الصامتة عطل لا يصدر عنه صوت")}
          </span>
        </div>
        <div className="table-wrap">
          <table className="tbl">
            <thead>
              <tr>
                <th>{t("المهمة")}</th>
                <th>{t("الجدول")}</th>
                <th>{t("آخر تشغيل")}</th>
                <th>{t("مرات التشغيل")}</th>
                <th>{t("الحالة")}</th>
              </tr>
            </thead>
            <tbody>
              {tasks.map((task) => {
                const quiet =
                  task.enabled &&
                  (task.silent_hours === null || task.silent_hours > SILENT_AFTER_HOURS);
                return (
                  <tr key={task.name}>
                    <td className="w-7">{task.name}</td>
                    <td className="muted t-sm num" style={{ direction: "ltr", textAlign: "start" }}>
                      {task.schedule}
                    </td>
                    <td className="muted t-sm">
                      {task.last_run_at ? fmt.relativeTime(task.last_run_at) : t("لم تعمل بعد")}
                    </td>
                    <td className="num">{fmt.number(task.total_runs)}</td>
                    <td>
                      {!task.enabled ? (
                        <Badge tone="muted">{t("معطّلة")}</Badge>
                      ) : quiet ? (
                        <Badge tone="orange">{t("صامتة")}</Badge>
                      ) : (
                        <Badge tone="green">{t("تعمل")}</Badge>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      <section className="card">
        <div className="card-hd">
          <h3>{t("حجم البيانات")}</h3>
        </div>
        <div className="card-p grid g3">
          {Object.entries(volume).map(([key, count]) => (
            <div key={key} className="center">
              <p className="t-xl w-8 num">{fmt.number(count)}</p>
              <p className="t-sm muted">{t(VOLUME_LABELS[key] ?? key)}</p>
            </div>
          ))}
        </div>
      </section>
    </>
  );
}
