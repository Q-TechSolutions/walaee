/**
 * متاجر قريبة.
 *
 * يطلب الموقع عند الضغط لا عند فتح الشاشة: طلب إذن يظهر بلا سبب
 * واضح يُرفض في الغالب، ورفضه مرة يجعل استعادته لاحقًا أصعب بكثير.
 */

import { useState } from "react";
import { Link } from "react-router-dom";

import { Badge, Button, Empty, ErrorBox, Loading, fmt } from "@walaee/shared";

import { queries } from "../lib/queries";
import type { NearbyStore } from "../lib/queries";

type State =
  | { kind: "idle" }
  | { kind: "locating" }
  | { kind: "loading" }
  | { kind: "ready"; stores: NearbyStore[] }
  | { kind: "error"; error: unknown };

export function Stores() {
  const [state, setState] = useState<State>({ kind: "idle" });

  function locate() {
    if (!("geolocation" in navigator)) {
      setState({
        kind: "error",
        error: new Error("متصفحك لا يدعم تحديد الموقع."),
      });
      return;
    }

    setState({ kind: "locating" });

    navigator.geolocation.getCurrentPosition(
      async (position) => {
        setState({ kind: "loading" });
        try {
          const stores = await queries.nearby(
            position.coords.latitude,
            position.coords.longitude,
          );
          setState({ kind: "ready", stores });
        } catch (error) {
          setState({ kind: "error", error });
        }
      },
      () => {
        setState({
          kind: "error",
          error: new Error(
            "تعذّر تحديد موقعك. فعّل إذن الموقع من إعدادات المتصفح ثم حاول مجددًا.",
          ),
        });
      },
      { enableHighAccuracy: false, timeout: 10_000, maximumAge: 60_000 },
    );
  }

  return (
    <div className="page">
      <h1 className="mb">متاجر قريبة منك</h1>

      {state.kind === "idle" && (
        <Empty
          icon="📍"
          title="اعرف المتاجر حولك"
          hint="سنستخدم موقعك لعرض الفروع القريبة فقط — ولا نحتفظ به."
          action={
            <Button size="lg" onClick={locate}>
              تحديد موقعي
            </Button>
          }
        />
      )}

      {(state.kind === "locating" || state.kind === "loading") && (
        <Loading
          label={
            state.kind === "locating" ? "جارٍ تحديد موقعك…" : "جارٍ البحث…"
          }
        />
      )}

      {state.kind === "error" && (
        <ErrorBox error={state.error} onRetry={locate} />
      )}

      {state.kind === "ready" && state.stores.length === 0 && (
        <Empty
          icon="🗺"
          title="لا توجد متاجر قريبة"
          hint="جرّب مجددًا من موقع آخر."
          action={
            <Button variant="ghost" onClick={locate}>
              إعادة البحث
            </Button>
          }
        />
      )}

      <div className="stack gap">
        {state.kind === "ready" &&
          state.stores.map((store) => (
            <Link
              key={store.branch_id}
              to={store.is_member ? `/cards/${store.brand_id}` : "/scan"}
              className="store-row"
              style={{ "--brand": store.primary_color } as React.CSSProperties}
            >
              <span className="store-dot" aria-hidden="true" />
              <div className="grow">
                <p className="w-7">{store.brand_name}</p>
                <p className="t-sm muted">
                  {store.branch_name}
                  {store.address && ` · ${store.address}`}
                </p>
              </div>
              <div className="stack" style={{ alignItems: "flex-end", gap: 4 }}>
                <span className="t-sm num">
                  {fmt.number(store.distance_km, 1)} كم
                </span>
                {store.is_member ? (
                  <Badge tone="green">عضو</Badge>
                ) : (
                  <Badge tone="violet">جديد</Badge>
                )}
              </div>
            </Link>
          ))}
      </div>
    </div>
  );
}
