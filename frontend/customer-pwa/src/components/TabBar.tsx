/**
 * شريط التنقّل السفلي.
 *
 * خمسة عناصر بحد أقصى، والمسح في المنتصف مرفوعًا: هو الإجراء
 * الوحيد الذي يقوم به العميل وهو واقف عند الصندوق، ويجب أن يُصاب
 * بالإبهام بلا نظر.
 */

import { NavLink } from "react-router-dom";

const TABS = [
  { to: "/", label: "بطاقاتي", icon: "▤" },
  { to: "/rewards", label: "المكافآت", icon: "◈" },
  { to: "/scan", label: "امسح", icon: "⬚", primary: true },
  { to: "/stores", label: "متاجر", icon: "◉" },
  { to: "/profile", label: "حسابي", icon: "☰" },
] as const;

export function TabBar() {
  return (
    <nav className="tabbar" aria-label="التنقّل الرئيسي">
      {TABS.map((tab) => (
        <NavLink
          key={tab.to}
          to={tab.to}
          end={tab.to === "/"}
          className={({ isActive }) =>
            [
              "tab",
              isActive ? "tab-active" : "",
              "primary" in tab && tab.primary ? "tab-primary" : "",
            ]
              .filter(Boolean)
              .join(" ")
          }
        >
          <span className="tab-icon" aria-hidden="true">
            {tab.icon}
          </span>
          <span className="tab-label">{tab.label}</span>
        </NavLink>
      ))}
    </nav>
  );
}
