/**
 * عميل API — نقطة الاتصال الوحيدة بالخلفية.
 *
 * لا يستدعي `fetch` مباشرةً أي مكوّن في التطبيقات الثلاثة. السبب
 * ليس الترتيب: تجديد التوكن ومعالجة أخطاء المجال وتسجيل الخروج
 * عند انتهاء الجلسة كلها منطق يجب أن يكون في مكان واحد، وإلا
 * ظهر مستخدم عالق في شاشة بيضاء لأن نداءً واحدًا نسي التعامل مع 401.
 */

import { readTokens, writeTokens, clearTokens, setTokenNamespace } from "./tokens";
import type { ApiError, Tokens } from "./types";

const DEFAULT_BASE = "/api/v1";

export class WalaeeApiError extends Error {
  readonly code: string;
  readonly status: number;
  readonly details?: unknown;

  constructor(
    status: number,
    payload: ApiError | null,
    fallback: string,
    cause?: unknown,
  ) {
    super(payload?.error?.message ?? fallback);
    this.name = "WalaeeApiError";
    this.status = status;
    // ‏0 يعني «لم يصل الطلب أصلًا»: تمييزه عن أخطاء الخادم يسمح
    // للواجهة بعرض سبب مختلف تمامًا
    this.code = payload?.error?.code ?? (status === 0 ? "network_error" : "unknown_error");
    this.details = payload?.error?.details;
    if (cause !== undefined) this.cause = cause;
  }
}

type Method = "GET" | "POST" | "PATCH" | "PUT" | "DELETE";

interface RequestOptions {
  method?: Method;
  body?: unknown;
  query?: Record<string, string | number | boolean | undefined>;
  /** يتخطّى إرفاق التوكن — لمسارات الدخول */
  anonymous?: boolean;
  signal?: AbortSignal;
}

export interface ClientConfig {
  baseUrl?: string;
  /**
   * اسم التطبيق — يفصل تخزين التوكن عن التطبيقات الأخرى.
   *
   * إلزامي حين تُخدَم أكثر من واجهة من أصل واحد: `localStorage`
   * مشترك بين كل ما هو على أصل واحد، ومفتاح واحد يجعل الدخول في
   * تطبيق يبدو دخولًا في الثلاثة.
   */
  appId?: string;
  /** يُستدعى حين تنتهي الجلسة نهائيًا ولا يمكن تجديدها */
  onUnauthenticated?: () => void;
}

let config: ClientConfig = {};

export function configureApi(next: ClientConfig): void {
  config = { ...config, ...next };
  if (next.appId) setTokenNamespace(next.appId);
}

function baseUrl(): string {
  return config.baseUrl ?? import.meta.env.VITE_API_BASE_URL ?? DEFAULT_BASE;
}

function buildUrl(path: string, query?: RequestOptions["query"]): string {
  const url = new URL(
    baseUrl().replace(/\/$/, "") + "/" + path.replace(/^\//, ""),
    window.location.origin,
  );
  if (query) {
    for (const [key, value] of Object.entries(query)) {
      if (value !== undefined && value !== "") {
        url.searchParams.set(key, String(value));
      }
    }
  }
  return url.toString();
}

/**
 * طلب واحد قيد التنفيذ لتجديد التوكن.
 *
 * بدون هذا الحارس، خمسة نداءات متوازية تصطدم بـ401 معًا فترسل
 * خمسة طلبات تجديد — وأربعة منها تُبطِل توكنًا جُدّد لتوّه لأن
 * التدوير مفعّل في الخلفية.
 */
let refreshing: Promise<Tokens | null> | null = null;

async function refreshTokens(): Promise<Tokens | null> {
  const current = readTokens();
  if (!current?.refresh) return null;

  if (!refreshing) {
    refreshing = (async () => {
      try {
        const response = await fetch(buildUrl("/auth/token/refresh"), {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh: current.refresh }),
        });
        if (!response.ok) return null;

        const data = (await response.json()) as Partial<Tokens>;
        if (!data.access) return null;

        const next: Tokens = {
          access: data.access,
          refresh: data.refresh ?? current.refresh,
        };
        writeTokens(next);
        return next;
      } catch {
        return null;
      } finally {
        // التفريغ في finally لا بعد الإرجاع: استثناء هنا كان
        // سيترك الحارس مقفولًا إلى الأبد فيتعذّر أي تجديد لاحق
        refreshing = null;
      }
    })();
  }

  return refreshing;
}

async function parseBody(response: Response): Promise<unknown> {
  if (response.status === 204) return null;
  const text = await response.text();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

export async function request<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const { method = "GET", body, query, anonymous = false, signal } = options;

  const send = async (token?: string): Promise<Response> => {
    const headers: Record<string, string> = { Accept: "application/json" };
    if (body !== undefined) headers["Content-Type"] = "application/json";
    if (token) headers["Authorization"] = `Bearer ${token}`;

    return fetch(buildUrl(path, query), {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      signal,
    });
  };

  const tokens = anonymous ? null : readTokens();

  let response: Response;
  try {
    response = await send(tokens?.access);
  } catch (cause) {
    // fetch يرمي TypeError على كل فشل شبكة برسالة "Failed to fetch"
    // لا تقول شيئًا للمستخدم ولا للمطوّر. الأسباب الفعلية محدودة
    // ومعروفة، فتُذكَر بدل الرسالة الصمّاء.
    throw new WalaeeApiError(
      0,
      null,
      "تعذّر الوصول إلى الخادم. تأكد من اتصالك، ومن أن الخادم يعمل على نفس العنوان.",
      cause,
    );
  }

  // 401 مرة واحدة يعني توكنًا منتهيًا — يُجرَّب التجديد ثم يُعاد
  // الطلب مرة واحدة فقط. تكرار المحاولة يحوّل انتهاء الجلسة إلى
  // حلقة لا نهائية من الطلبات.
  if (response.status === 401 && !anonymous && tokens?.refresh) {
    const refreshed = await refreshTokens();
    if (refreshed) {
      response = await send(refreshed.access);
    } else {
      clearTokens();
      config.onUnauthenticated?.();
    }
  }

  if (!response.ok) {
    if (response.status === 401 && !anonymous) {
      clearTokens();
      config.onUnauthenticated?.();
    }
    const payload = (await parseBody(response)) as ApiError | null;
    throw new WalaeeApiError(
      response.status,
      payload,
      `فشل الطلب (${response.status})`,
    );
  }

  return (await parseBody(response)) as T;
}

export const api = {
  get: <T>(path: string, query?: RequestOptions["query"], signal?: AbortSignal) =>
    request<T>(path, { method: "GET", query, signal }),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "POST", body }),
  patch: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "PATCH", body }),
  put: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "PUT", body }),
  del: <T>(path: string) => request<T>(path, { method: "DELETE" }),
  anonymous: {
    get: <T>(path: string, query?: RequestOptions["query"]) =>
      request<T>(path, { method: "GET", query, anonymous: true }),
    post: <T>(path: string, body?: unknown) =>
      request<T>(path, { method: "POST", body, anonymous: true }),
  },
};
