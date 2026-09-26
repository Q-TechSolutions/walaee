/**
 * من يملك صلاحية على ماذا.
 *
 * تُفتح هذه الشاشة وقت مراجعة حادثة لا وقت الفراغ: «من كان يستطيع
 * فعل هذا؟» سؤالٌ يحتاج جوابًا في ثوانٍ. لذلك الفريق أولًا ثم
 * موظفو المتاجر مجمَّعين بأدوارهم.
 *
 * ولا تُعرض العملاء النهائيون هنا. بيانات شرائهم ملك التاجر
 * وعميله والمنصة وسيط — وهو الفصل الذي يُباع للسلاسل كميزة، ولا
 * يصحّ أن تكسره لوحةٌ داخلية.
 */

import { Badge, ErrorBox, Icon, Loading, fmt, t, useApi } from "@walaee/shared";

import { queries } from "../lib/queries";

export function Users() {
  const users = useApi((signal) => queries.users(signal), []);

  if (users.loading) return <Loading />;
  if (users.error != null) return <ErrorBox error={users.error} onRetry={users.reload} />;
  if (!users.data) return null;

  const { platform, staff, staff_total: total, by_role: roles } = users.data;

  return (
    <>
      <section className="card mb">
        <div className="card-hd">
          <h3>{t("فريق المنصة")}</h3>
          <span className="badge bg-v num">{fmt.number(platform.length)}</span>
        </div>
        <div className="table-wrap">
          <table className="tbl">
            <thead>
              <tr>
                <th>{t("المستخدم")}</th>
                <th>{t("الدور")}</th>
                <th>{t("آخر دخول")}</th>
                <th>{t("الحالة")}</th>
              </tr>
            </thead>
            <tbody>
              {platform.map((user) => (
                <tr key={user.id}>
                  <td>
                    <div className="row">
                      <span className="av av-sm" aria-hidden="true">
                        {user.name.trim().charAt(0)}
                      </span>
                      <div>
                        <b className="t-sm">{user.name}</b>
                        <p className="t-xs muted num">{fmt.phone(user.phone)}</p>
                      </div>
                    </div>
                  </td>
                  <td className="muted">{t(user.role)}</td>
                  <td className="muted t-sm">
                    {user.last_login ? fmt.relativeTime(user.last_login) : t("لم يدخل بعد")}
                  </td>
                  <td>
                    <Badge tone={user.is_active ? "green" : "muted"}>
                      {user.is_active ? t("نشط") : t("موقوف")}
                    </Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="card">
        <div className="card-hd">
          <h3>{t("موظفو المتاجر")}</h3>
          <div className="row gap-sm">
            {roles.map((row) => (
              <Badge key={row.role} tone="muted">
                {t(row.role)} <span className="num">{fmt.number(row.count)}</span>
              </Badge>
            ))}
          </div>
        </div>

        {/* القائمة مقصوصة عمدًا: هذه لوحة مراجعة لا دليل موظفين،
            ومن يحتاج موظفًا بعينه يصل إليه من ملف متجره */}
        <p className="t-sm muted card-p" style={{ paddingBottom: 0 }}>
          {t("أول {n} من {m} — مرتّبين بالعلامة ثم الدور.", {
            n: fmt.number(staff.length),
            m: fmt.number(total),
          })}
        </p>

        <div className="table-wrap">
          <table className="tbl">
            <thead>
              <tr>
                <th>{t("الموظف")}</th>
                <th>{t("الدور")}</th>
                <th>{t("العلامة")}</th>
                <th>{t("الفرع")}</th>
                <th>{t("آخر دخول")}</th>
              </tr>
            </thead>
            <tbody>
              {staff.map((member) => (
                <tr key={member.id}>
                  <td>
                    <div className="row">
                      <span className="av av-sm" aria-hidden="true">
                        {member.name.trim().charAt(0)}
                      </span>
                      <div>
                        <b className="t-sm">{member.name}</b>
                        <p className="t-xs muted num">{fmt.phone(member.phone)}</p>
                      </div>
                    </div>
                  </td>
                  <td>
                    <Badge tone={member.role_key === "owner" ? "violet" : "muted"}>
                      {t(member.role)}
                    </Badge>
                  </td>
                  <td className="muted">{member.brand}</td>
                  <td className="muted">{member.branch}</td>
                  <td className="muted t-sm">
                    {member.last_login ? fmt.relativeTime(member.last_login) : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <p className="t-sm muted mt-3">
        <Icon name="shield" size={14} /> {t("لا تعرض هذه الشاشة العملاء النهائيين — بياناتهم ملك التاجر وعميله.")}
      </p>
    </>
  );
}
