/**
 * الحساب والخصوصية.
 *
 * التصدير والحذف في الشاشة نفسها لا مدفونين في إعدادات فرعية:
 * حقّان للعميل يجب أن يكونا ظاهرين بقدر أي ميزة أخرى.
 */

import { useState } from "react";

import {
  Button,
  ErrorBox,
  Field,
  Loading,
  LocaleToggle,
  Modal,
  ThemeToggle,
  clearTokens,
  fmt,
  hardRedirect,
  request,
  t,
  useAction,
  useApi,
} from "@walaee/shared";

import { actions, queries } from "../lib/queries";

export function Profile() {
  const me = useApi((signal) => queries.me(signal), []);
  const [name, setName] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);

  const save = useAction(actions.updateProfile);
  const exportData = useAction(async () => {
    const data = await queries.me();
    // التوكن من المكتبة لا من `localStorage` مباشرةً: المفتاح صار
    // يحمل اسم التطبيق بعد فصل التخزين بين الواجهات الثلاث، وقراءة
    // الاسم القديم هنا كانت ترسل الطلب بلا ترويسة مصادقة أصلًا —
    // فيفشل التصدير بصمت ويُنزَّل ملف يحمل رسالة خطأ.
    const full = await request<unknown>("/me/export");

    // التنزيل من الذاكرة لا من رابط خادم: الملف يحتوي بيانات
    // شخصية ولا يجب أن يعيش على أي خادم ولو مؤقتًا
    const blob = new Blob([JSON.stringify(full, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `walaee-${data.phone}.json`;
    link.click();
    URL.revokeObjectURL(url);
    return true;
  });

  if (me.loading) return <Loading />;
  if (me.error != null)
    return (
      <div className="page">
        <ErrorBox error={me.error} onRetry={me.reload} />
      </div>
    );
  if (!me.data) return null;

  const current = name ?? me.data.full_name;

  function signOut() {
    clearTokens();
    hardRedirect("/login");
  }

  return (
    <>
      <header className="mhead">
        <div className="grow">
          <h1>{t("حسابي")}</h1>
          <p className="sub">{t("بياناتك وخصوصيتك")}</p>
        </div>
      </header>

      <div className="pad section">
      <section className="card card-p">
        <div className="profile-head">
          <div className="av av-lg" aria-hidden="true">
            {(me.data.full_name || t("؟")).trim().charAt(0)}
          </div>
          <div className="grow">
            <p className="w-8 t-md">{me.data.full_name || t("بلا اسم")}</p>
            <p className="t-sm muted num">{fmt.phone(me.data.phone)}</p>
            <p className="t-xs faint"> {t("عضو منذ")} {fmt.date(me.data.created_at)}</p>
          </div>
        </div>
      </section>

      <section className="section">
        <div className="sec-t"><h3>{t("المظهر واللغة")}</h3></div>
        <div className="card card-p stack gap">
          <div className="row between">
            <span className="t-sm">{t("اللغة")}</span>
            <LocaleToggle />
          </div>
          <div className="row between">
            <span className="t-sm">{t("السمة")}</span>
            <ThemeToggle compact />
          </div>
        </div>
      </section>

      <section className="section">
        <div className="sec-t"><h3>{t("بياناتي")}</h3></div>

        <Field label={t("الاسم")} hint={t("يظهر للمتاجر التي تنضم إليها")}>
          <input
            className="input"
            value={current}
            onChange={(e) => setName(e.target.value)}
            placeholder={t("اكتب اسمك")}
          />
        </Field>

        {save.error != null && <ErrorBox error={save.error} />}

        <Button
          loading={save.loading}
          disabled={current === me.data.full_name}
          onClick={async () => {
            const updated = await save.run({ full_name: current });
            if (updated) {
              setName(null);
              me.reload();
            }
          }}
        >
          {t("حفظ")}
        </Button>
      </section>

      <section className="section">
        <div className="sec-t"><h3>{t("الخصوصية")}</h3></div>

        <div className="stack gap">
          <div className="privacy-row">
            <div className="grow">
              <p className="w-7">{t("تحميل نسخة من بياناتي")}</p>
              <p className="t-sm muted">
                {t("كل ما تحتفظ به المنصة عنك في ملف واحد.")}
              </p>
            </div>
            <Button
              variant="ghost"
              loading={exportData.loading}
              onClick={() => exportData.run()}
            >
              {t("تحميل")}
            </Button>
          </div>

          <div className="privacy-row">
            <div className="grow">
              <p className="w-7">{t("حذف حسابي")}</p>
              <p className="t-sm muted">
                {t("تُمحى بياناتك الشخصية نهائيًا. سجلات المعاملات تبقى بمعرّف مجهول لأن أرصدة المتاجر محسوبة عليها.")}
              </p>
            </div>
            <Button variant="danger" onClick={() => setDeleting(true)}>
              {t("حذف")}
            </Button>
          </div>
        </div>
      </section>

      <section className="section">
        <Button variant="ghost" block onClick={signOut}>
          {t("تسجيل الخروج")}
        </Button>
      </section>

      <DeleteAccountModal open={deleting} onClose={() => setDeleting(false)} />
      </div>
    </>
  );
}

/**
 * حذف الحساب بخطوتين مع كود جديد.
 *
 * الجلسة المفتوحة لا تكفي: هاتف في يد شخص آخر لا يجب أن يمحو حساب
 * صاحبه بضغطتين.
 */
function DeleteAccountModal({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const [stage, setStage] = useState<"confirm" | "code">("confirm");
  const [code, setCode] = useState("");

  const requestCode = useAction(actions.requestDeletion);
  const confirmDelete = useAction(actions.confirmDeletion);

  return (
    <Modal open={open} title={t("حذف الحساب")} onClose={onClose}>
      {stage === "confirm" ? (
        <div className="stack gap">
          <p>
            {t("سنرسل كود تأكيد إلى رقمك. بعد التأكيد تُمحى بياناتك الشخصية ولا يمكن استرجاعها.")}
          </p>
          <p className="t-sm muted">
            {t("نقاطك في كل المتاجر ستُفقد، وسجلات المعاملات تبقى بمعرّف مجهول.")}
          </p>

          {requestCode.error != null && <ErrorBox error={requestCode.error} />}

          <div className="row">
            <Button
              variant="danger"
              loading={requestCode.loading}
              onClick={async () => {
                const sent = await requestCode.run();
                if (sent) setStage("code");
              }}
            >
              {t("أرسل كود التأكيد")}
            </Button>
            <Button variant="ghost" onClick={onClose}>
              {t("تراجع")}
            </Button>
          </div>
        </div>
      ) : (
        <div className="stack gap">
          <Field label={t("كود التأكيد")}>
            <input
              className="input num code-input"
              inputMode="numeric"
              maxLength={6}
              value={code}
              onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
            />
          </Field>

          {confirmDelete.error != null && (
            <ErrorBox error={confirmDelete.error} />
          )}

          <Button
            variant="danger"
            block
            loading={confirmDelete.loading}
            onClick={async () => {
              const result = await confirmDelete.run(code);
              if (result) {
                clearTokens();
                hardRedirect("/login");
              }
            }}
          >
            {t("تأكيد الحذف نهائيًا")}
          </Button>
        </div>
      )}
    </Modal>
  );
}
