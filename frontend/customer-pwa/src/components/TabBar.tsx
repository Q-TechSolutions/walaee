/**
 * شريط التنقّل السفلي.
 *
 * خمسة عناصر بحد أقصى، والمسح في المنتصف مرفوعًا: هو الإجراء
 * الوحيد الذي يقوم به العميل وهو واقف عند الصندوق، ويجب أن يُصاب
 * بالإبهام بلا نظر.
 */

import { NavLink } from "react-router-dom";

import { Icon, t } from "@walaee/shared";
import type { IconName } from "@walaee/shared";

const TABS = [
  { to: "/", label: "الرئيسية", icon: "home" },
  { to: "/stores", label: "المتاجر", icon: "store" },
  { to: "/scan", label: "امسح", icon: "scan", primary: true },
  { to: "/rewards", label: "المكافآت", icon: "gift" },
  { to: "/profile", label: "حسابي", icon: "user" },
] as const satisfies readonly {
  to: string;
  label: string;
  icon: IconName;
  primary?: boolean;
}[];

export function TabBar() {
  return (
    <nav className="tabbar" aria-label={t("التنقّل الرئيسي")}>
      {TABS.map((tab) => {
        const primary = "primary" in tab && tab.primary;

        return (
          <NavLink
            key={tab.to}
            to={tab.to}
            end={tab.to === "/"}
            className={({ isActive }) =>
              [
                "tab",
                isActive && !primary ? "tab-active" : "",
                primary ? "tab-primary" : "",
              ]
                .filter(Boolean)
                .join(" ")
            }
          >
            {primary ? (
              <span className="tab-fab">
                <Icon name={tab.icon} size={26} label={t(tab.label)} />
              </span>
            ) : (
              <>
                <Icon name={tab.icon} size={22} />
                <span>{t(tab.label)}</span>
              </>
            )}
          </NavLink>
        );
      })}
    </nav>
  );
}
