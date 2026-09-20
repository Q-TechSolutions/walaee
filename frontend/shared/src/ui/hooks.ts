/**
 * Hooks مشتركة.
 *
 * `useApi` بديل مقصود عن مكتبة جلب بيانات كاملة: النطاق هنا محدود
 * والمكتبة تضيف ١٥ ك.ب مضغوطة وطبقة كاش لا يحتاجها تطبيق يقرأ
 * أرقامًا لحظية أصلًا.
 */

import { useCallback, useEffect, useRef, useState } from "react";

interface ApiState<T> {
  data: T | null;
  loading: boolean;
  error: unknown;
}

/**
 * يجلب بيانات عند التركيب ويعيد الجلب عند تغيّر المفاتيح.
 *
 * `AbortController` إلزامي لا تحسين: المستخدم يتنقّل بين الشاشات
 * أسرع من الشبكة، وبدون الإلغاء تصل استجابة شاشة قديمة فتكتب فوق
 * حالة الشاشة الحالية.
 */
export function useApi<T>(
  fetcher: (signal: AbortSignal) => Promise<T>,
  deps: unknown[] = [],
): ApiState<T> & { reload: () => void } {
  const [state, setState] = useState<ApiState<T>>({
    data: null,
    loading: true,
    error: null,
  });
  const [nonce, setNonce] = useState(0);

  // المرجع يمنع إعادة الجلب لمجرد أن الدالة أُعيد إنشاؤها في
  // كل تصيير — وهو السبب الأشهر لحلقة طلبات لا تنتهي
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  useEffect(() => {
    const controller = new AbortController();
    let active = true;

    setState((prev) => ({ ...prev, loading: true, error: null }));

    fetcherRef
      .current(controller.signal)
      .then((data) => {
        if (active) setState({ data, loading: false, error: null });
      })
      .catch((error: unknown) => {
        if (!active) return;
        if (error instanceof DOMException && error.name === "AbortError") return;
        setState({ data: null, loading: false, error });
      });

    return () => {
      active = false;
      controller.abort();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, nonce]);

  const reload = useCallback(() => setNonce((n) => n + 1), []);

  return { ...state, reload };
}

/** يدير إجراءً يكتب (POST/PATCH) مع حالة التحميل والخطأ. */
export function useAction<Args extends unknown[], T>(
  action: (...args: Args) => Promise<T>,
): {
  run: (...args: Args) => Promise<T | null>;
  loading: boolean;
  error: unknown;
  reset: () => void;
} {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<unknown>(null);

  const run = useCallback(
    async (...args: Args): Promise<T | null> => {
      setLoading(true);
      setError(null);
      try {
        return await action(...args);
      } catch (err) {
        setError(err);
        return null;
      } finally {
        setLoading(false);
      }
    },
    [action],
  );

  return { run, loading, error, reset: () => setError(null) };
}

/** يعيد التنفيذ كل فترة، ويتوقّف حين تكون الصفحة مخفية. */
export function useInterval(callback: () => void, ms: number | null): void {
  const saved = useRef(callback);
  saved.current = callback;

  useEffect(() => {
    if (ms === null) return;

    const tick = () => {
      // التبويب المخفي لا يحتاج تحديثًا — الاستمرار يستهلك بطارية
      // جهاز الكاشير ويولّد طلبات بلا مشاهد
      if (document.visibilityState === "visible") saved.current();
    };

    const id = window.setInterval(tick, ms);
    return () => window.clearInterval(id);
  }, [ms]);
}

/** قيمة مؤجَّلة — للبحث أثناء الكتابة. */
export function useDebounced<T>(value: T, ms = 350): T {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const id = window.setTimeout(() => setDebounced(value), ms);
    return () => window.clearTimeout(id);
  }, [value, ms]);

  return debounced;
}

/** عدّاد تنازلي بالثواني. */
export function useCountdown(seconds: number): [number, () => void] {
  const [remaining, setRemaining] = useState(seconds);

  useEffect(() => {
    if (remaining <= 0) return;
    const id = window.setTimeout(() => setRemaining((r) => r - 1), 1000);
    return () => window.clearTimeout(id);
  }, [remaining]);

  const restart = useCallback(() => setRemaining(seconds), [seconds]);

  return [remaining, restart];
}
