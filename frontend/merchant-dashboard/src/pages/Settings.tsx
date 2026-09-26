/**
 * الإعدادات — بيانات المتجر والخصوصية.
 *
 * الفروع والفريق والاشتراك انتقلت إلى شاشاتها المستقلة كما في
 * العرض المعتمد. ما بقي هنا شيئان: ما يراه العميل عن متجرك، وما
 * تلتزم به تجاه بياناته.
 *
 * قسم الخصوصية ليس نصًّا قانونيًا مركونًا في التذييل: التاجر هو
 * «المتحكّم» في بيانات عملائه وولائي «المعالِج»، وهذا التوزيع
 * يحدّد من يردّ على طلب حذف ومن يوقّع عقد المعالجة. إخفاؤه يجعل
 * التاجر يكتشف مسؤوليته أول مرة من محامٍ لا من لوحته.
 */

import { useState } from "react";

import {
  Button,
  ErrorBox,
  Field,
  Icon,
  Loading,
  fmt,
  t,
  useAction,
  useApi,
} from "@walaee/shared";

import { actions, queries } from "../lib/queries";

/**
 * التزامات المنصة تجاه بيانات العملاء.
 *
 * مكتوبة هنا لا مجلوبة من الخادم: هذه سياسات المنصة نفسها، لا
 * إعدادات لهذا المتجر. جلبها من واجهة كان سيوحي بأنها قابلة
 * للتعديل من هنا — وهي ليست كذلك.
 */
const PRIVACY: [string, string][] = [
  ["موافقة صريحة عند التسجيل", "مسجّلة بالتاريخ والوقت ورقم النسخة"],
  ["عزل بيانات كل علامة", "لا يرى متجر آخر عميلًا واحدًا من عملائك"],
  ["تشفير عند النقل والتخزين", "مفعّل دائمًا"],
  ["حق العميل في التصدير والحذف", "ذاتي من التطبيق بلا وسيط"],
  ["سجل تدقيق غير قابل للحذف", "كل قيد يبقى، والعكس يُسجَّل قيدًا جديدًا"],
];

export function Settings() {
  const brand = useApi((signal) => queries.brand(signal), []);
  const save = useAction(actions.updateBrand);

  const [form, setForm] = useState<{ name?: string; category?: string }>({});

  if (brand.loading) return <Loading />;
  if (brand.error != null)
    return <ErrorBox error={brand.error} onRetry={brand.reload} />;
  if (!brand.data) return null;

  const data = brand.data;
  const name = form.name ?? data.name;
  const category = form.category ?? data.category ?? "";
  const dirty = name !== data.name || category !== (data.category ?? "");

  return (
    <div className="grid g2">
      <section className="card">
        <div className="card-hd">
          <h3>{t("بيانات المتجر")}</h3>
        </div>

        <div className="card-p">
          <Field label={t("اسم المتجر")} hint={t("يظهر للعميل على بطاقته وفي الدليل العام")}>
            <input
              className="input"
              value={name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
            />
          </Field>

          <Field label={t("النشاط")} hint={t("يحدّد أيقونة متجرك في الدليل")}>
            <input
              className="input"
              value={category}
              onChange={(e) => setForm({ ...form, category: e.target.value })}
              placeholder={t("مثال: مقاهٍ ومشروبات")}
            />
          </Field>

          <div className="field">
            <label>{t("لون العلامة")}</label>
            <div className="row">
              <span
                className="brand-swatch"
                style={{ background: data.primary_color }}
                aria-hidden="true"
              />
              <span className="t-sm muted num">{data.primary_color}</span>
            </div>
            <p className="t-xs faint">
              {t("يُستخدم في بطاقة العميل. تغييره يحتاج مراجعة الفريق حتى لا تفقد البطاقة تباينها مع النص الأبيض.")}
            </p>
          </div>

          {save.error != null && <ErrorBox error={save.error} />}

          <Button
            loading={save.loading}
            disabled={!dirty}
            onClick={async () => {
              const done = await save.run({ name, category });
              if (done) {
                setForm({});
                brand.reload();
              }
            }}
          >
            {t("حفظ")}
          </Button>
        </div>
      </section>

      <div className="stack gap-lg">
        <section className="card card-p tint-g">
          <div className="row-t">
            <span className="ibox g" style={{ background: "#fff" }}>
              <Icon name="shield" size={20} />
            </span>
            <div className="grow">
              <b className="t-md">{t("أنت «المتحكّم» وولائي «المعالِج»")}</b>
              <p className="t-sm muted mt-1">
                {t("بيانات عملائك ملكك. ولائي يعالجها نيابةً عنك، ولا تُشارك مع أي متجر آخر على المنصة.")}
              </p>
            </div>
          </div>
        </section>

        <section className="card">
          <div className="card-hd">
            <h3>{t("الخصوصية وحماية البيانات")}</h3>
          </div>
          <div className="card-p">
            {PRIVACY.map(([title, note]) => (
              <div key={title} className="li">
                <span className="ibox v" aria-hidden="true">
                  <Icon name="lock" size={18} />
                </span>
                <div className="grow">
                  <p className="li-t">{t(title)}</p>
                  <p className="li-s">{t(note)}</p>
                </div>
                <Icon name="checkCircle" size={18} className="c-green" />
              </div>
            ))}
          </div>
        </section>

        <section className="card card-p">
          <p className="t-sm muted">
            {t("العلامة أُنشئت")}{" "}
            <span className="num">{fmt.date(data.created_at)}</span>{t(". لحذف برنامج الولاء نهائيًا أو تصدير كل بياناتك، تواصل مع فريق ولائي — الإجراء يدوي عمدًا لأنه غير قابل للتراجع.")}
          </p>
        </section>
      </div>
    </div>
  );
}
