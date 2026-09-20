#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════
#  استرجاع قاعدة البيانات من نسخة احتياطية.
#
#      bash infra/scripts/restore.sh backups/walaee-2026-09-20_0100.sql.gz
#
#  ⚠ يستبدل محتوى القاعدة الحالية بالكامل.
#
#  شغّله على خادم اختبار مرة شهريًا. نسخة احتياطية لم يُجرَّب
#  استرجاعها هي افتراض لا ضمان — ويوم الحاجة إليها ليس وقت
#  اكتشاف أنها لا تعمل.
# ══════════════════════════════════════════════════════════
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

FILE="${1:-}"
if [ -z "$FILE" ] || [ ! -f "$FILE" ]; then
    echo "الاستخدام: bash infra/scripts/restore.sh <ملف.sql.gz>" >&2
    exit 1
fi

if ! gzip -t "$FILE" 2>/dev/null; then
    echo "✗ الملف تالف أو ليس gzip: $FILE" >&2
    exit 1
fi

COMPOSE="docker compose --env-file .env -f infra/docker/docker-compose.prod.yml"

DB_USER="$(grep -E '^POSTGRES_USER=' .env | cut -d= -f2- || echo walaee)"
DB_NAME="$(grep -E '^POSTGRES_DB=' .env | cut -d= -f2- || echo walaee)"
DB_USER="${DB_USER:-walaee}"
DB_NAME="${DB_NAME:-walaee}"

echo "⚠ سيُستبدل محتوى قاعدة «$DB_NAME» بالكامل من:"
echo "   $FILE"
printf "اكتب اسم القاعدة للتأكيد: "
read -r CONFIRM

# التأكيد باسم القاعدة لا بـ"نعم": من يكتب اسم قاعدة الإنتاج
# يكون قد قرأ السطر الذي فوقه
if [ "$CONFIRM" != "$DB_NAME" ]; then
    echo "أُلغي." >&2
    exit 1
fi

# إيقاف كل ما يكتب في القاعدة أولًا: استرجاع بينما عامل يكتب
# يعطي قاعدة نصفها قديم ونصفها جديد
echo "▸ إيقاف التطبيق والعمّال …"
$COMPOSE stop api worker-realtime worker-default beat

echo "▸ الاسترجاع …"
gunzip -c "$FILE" | $COMPOSE exec -T postgres psql -U "$DB_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1

echo "▸ إعادة التشغيل …"
$COMPOSE start api worker-realtime worker-default beat

echo "▸ تدقيق سلامة الأرصدة بعد الاسترجاع …"
sleep 15
# التمييز بين «فشل التنفيذ» و«اكتُشف انحراف» مقصود: خلطهما يجعل
# صورة قديمة بلا الأمر تبدو كقاعدة بيانات فاسدة، فيُهدر وقت في
# مطاردة عطل لا وجود له.
set +e
OUT="$($COMPOSE exec -T api python manage.py verify_ledger 2>&1)"
CODE=$?
set -e

echo "$OUT"

if echo "$OUT" | grep -q "Unknown command"; then
    echo "⚠ أمر التدقيق غير موجود في هذه الصورة — أعد البناء ثم شغّل: make verify-ledger" >&2
elif [ "$CODE" -ne 0 ]; then
    echo "⚠ التدقيق اكتشف انحرافًا في الأرصدة — راجعه قبل فتح النظام للتجّار" >&2
fi

echo "✓ تمّ الاسترجاع"
