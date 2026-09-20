/**
 * جلسة الموظف ودوره.
 *
 * الدور يُقرأ من الجلسة المحفوظة لا من التوكن: التوكن يحمل الهوية
 * والخلفية تفرض الصلاحية، أما الدور هنا فلإخفاء ما لا يستطيع
 * المستخدم فعله — إظهار زر يُرفض دائمًا تجربة سيئة لا ثغرة.
 */

import { clearTokens, writeTokens } from "@walaee/shared";
import type { StaffRole, StaffSession } from "@walaee/shared";

const KEY = "walaee.session";

export type Role = StaffRole["role"];

export interface Session {
  user: StaffSession["user"];
  roles: StaffRole[];
  activeRoleId: string | null;
}

let cached: Session | null = null;

export function saveSession(payload: StaffSession): Session {
  writeTokens({ access: payload.access, refresh: payload.refresh });

  const session: Session = {
    user: payload.user,
    roles: payload.roles,
    activeRoleId: payload.roles[0]?.id ?? null,
  };

  cached = session;
  try {
    localStorage.setItem(KEY, JSON.stringify(session));
  } catch {
    /* الجلسة تعيش في الذاكرة */
  }
  return session;
}

export function readSession(): Session | null {
  if (cached) return cached;
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return null;
    cached = JSON.parse(raw) as Session;
    return cached;
  } catch {
    return null;
  }
}

export function endSession(): void {
  cached = null;
  clearTokens();
  try {
    localStorage.removeItem(KEY);
  } catch {
    /* لا شيء */
  }
}

export function activeRole(): StaffRole | null {
  const session = readSession();
  if (!session) return null;
  return (
    session.roles.find((role) => role.id === session.activeRoleId) ??
    session.roles[0] ??
    null
  );
}

const RANK: Record<Role, number> = { cashier: 1, manager: 2, owner: 3 };

/** هل يملك الدور الحالي هذه الرتبة أو أعلى؟ */
export function atLeast(role: Role): boolean {
  const current = activeRole();
  if (!current) return false;
  return RANK[current.role] >= RANK[role];
}

export function isPlatformAdmin(): boolean {
  return readSession()?.user.is_platform_admin ?? false;
}
