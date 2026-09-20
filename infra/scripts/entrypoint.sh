#!/usr/bin/env sh
# نقطة دخول الحاوية.
#
# الهجرات تُطبَّق هنا لا في أمر البناء: البناء قد يحدث على جهاز لا
# يرى قاعدة الإنتاج أصلًا.
set -e

echo "▸ انتظار قاعدة البيانات …"
python - <<'PY'
import os, sys, time
import psycopg

dsn = os.environ.get("DATABASE_URL")
if not dsn:
    dsn = "postgresql://{u}:{p}@{h}:{P}/{d}".format(
        u=os.environ.get("POSTGRES_USER", "walaee"),
        p=os.environ.get("POSTGRES_PASSWORD", ""),
        h=os.environ.get("POSTGRES_HOST", "postgres"),
        P=os.environ.get("POSTGRES_PORT", "5432"),
        d=os.environ.get("POSTGRES_DB", "walaee"),
    )

for attempt in range(60):
    try:
        psycopg.connect(dsn, connect_timeout=3).close()
        sys.exit(0)
    except Exception:
        time.sleep(1)

print("✗ تعذّر الاتصال بقاعدة البيانات بعد ٦٠ محاولة", file=sys.stderr)
sys.exit(1)
PY

# العامل والمجدول لا يطبّقان الهجرات — نسخة واحدة تكفي وتفاديًا للتسابق
case "$1" in
  gunicorn)
    echo "▸ تطبيق الهجرات …"
    python manage.py migrate --noinput
    echo "▸ تجميع الملفات الثابتة …"
    python manage.py collectstatic --noinput --clear

    # المجدول يقرأ جدوله من قاعدة البيانات، وقاعدة جديدة تبدأ
    # فارغة — فيعمل beat بلا أن ينفّذ شيئًا ولا يظهر ذلك في أي
    # سجل. أول ما يُكتشف رصيد لم ينتهِ بعد سنة من موعده.
    echo "▸ تثبيت جدول المهام الدورية …"
    python manage.py install_schedule

    # حسابات التجربة تُنشأ تلقائيًا حين يكون النشر تجريبيًا.
    # مطالبة من يجرّب المنتج بتشغيل أمر يدوي قبل أن يستطيع الدخول
    # هي عقبة بلا سبب — ولن يفعلها أحد.
    if [ -n "${DEMO_STAFF_PASSWORD:-}" ] || [ -n "${DEMO_LOGIN_PHONES:-}" ]; then
        echo "▸ تهيئة حسابات التجربة …"
        python manage.py demo_accounts --with-data             --password "${DEMO_STAFF_PASSWORD:-Walaee@2026}" ||             echo "  (تُخطّيت — راجع السجل)"
    fi
    ;;
esac

echo "▸ تشغيل: $*"
exec "$@"
