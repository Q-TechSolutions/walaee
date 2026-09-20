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
  Modal,
  clearTokens,
  fmt,
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
    const full = await fetch("/api/v1/me/export", {
      headers: {
        Authorization: `Bearer ${JSON.parse(localStorage.getItem("walaee.tokens") ?? "{}").access}`,
      },
    }).then((r) => r.json());

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
    window.location.replace("/login");
  }

  return (
    <div className="page">
      <h1 className="mb">حسابي</h1>

      <section className="section">
        <div className="profile-head">
          <div className="profile-avatar" aria-hidden="true">
            {(me.data.full_name || "؟").trim().charAt(0)}
          </div>
          <div>
            <p className="w-7">{me.data.full_name || "بلا اسم"}</p>
            <p className="t-sm muted num">{fmt.phone(me.data.phone)}</p>
            <p className="t-xs faint">عضو منذ {fmt.date(me.data.created_at)}</p>
          </div>
        </div>
      </section>

      <section className="section">
        <h2>بياناتي</h2>

        <Field label="الاسم" hint="يظهر للمتاجر التي تنضم إليها">
          <input
            className="input"
            value={current}
            onChange={(e) => setName(e.target.value)}
            placeholder="اكتب اسمك"
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
          حفظ
        </Button>
      </section>

      <section className="section">
        <h2>الخصوصية</h2>

        <div className="stack gap">
          <div className="privacy-row">
            <div className="grow">
              <p className="w-7">تحميل نسخة من بياناتي</p>
              <p className="t-sm muted">
                كل ما تحتفظ به المنصة عنك في ملف واحد.
              </p>
            </div>
            <Button
              variant="ghost"
              loading={exportData.loading}
              onClick={() => exportData.run()}
            >
              تحميل
            </Button>
          </div>

          <div className="privacy-row">
            <div className="grow">
              <p className="w-7">حذف حسابي</p>
              <p className="t-sm muted">
                تُمحى بياناتك الشخصية نهائيًا. سجلات المعاملات تبقى بمعرّف
                مجهول لأن أرصدة المتاجر محسوبة عليها.
              </p>
            </div>
            <Button variant="danger" onClick={() => setDeleting(true)}>
              حذف
            </Button>
          </div>
        </div>
      </section>

      <section className="section">
        <Button variant="ghost" block onClick={signOut}>
          تسجيل الخروج
        </Button>
      </section>

      <DeleteAccountModal open={deleting} onClose={() => setDeleting(false)} />
    </div>
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
    <Modal open={open} title="حذف الحساب" onClose={onClose}>
      {stage === "confirm" ? (
        <div className="stack gap">
          <p>
            سنرسل كود تأكيد إلى رقمك. بعد التأكيد تُمحى بياناتك الشخصية ولا
            يمكن استرجاعها.
          </p>
          <p className="t-sm muted">
            نقاطك في كل المتاجر ستُفقد، وسجلات المعاملات تبقى بمعرّف مجهول.
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
              أرسل كود التأكيد
            </Button>
            <Button variant="ghost" onClick={onClose}>
              تراجع
            </Button>
          </div>
        </div>
      ) : (
        <div className="stack gap">
          <Field label="كود التأكيد">
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
                window.location.replace("/login");
              }
            }}
          >
            تأكيد الحذف نهائيًا
          </Button>
        </div>
      )}
    </Modal>
  );
}
