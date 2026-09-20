#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════
#  نسخة احتياطية لقاعدة البيانات.
#
#  يُشغَّل من جذر المستودع:
#      bash infra/scripts/backup.sh
#      bash infra/scripts/backup.sh /mnt/backups
#
#  يُجدوَل يوميًا بـcron على الخادم:
#      0 1 * * * cd /path/to/walaee && bash infra/scripts/backup.sh >> /var/log/walaee-backup.log 2>&1
#
#  قاعدة غير قابلة للتفاوض: النسخة غير المختبَرة ليست نسخة احتياطية.
#  جرّب `restore.sh` على خادم اختبار مرة شهريًا على الأقل.
# ══════════════════════════════════════════════════════════
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

DEST="${1:-$ROOT/backups}"
KEEP_DAYS="${BACKUP_KEEP_DAYS:-14}"
COMPOSE="docker compose --env-file .env -f infra/docker/docker-compose.prod.yml"

DB_USER="$(grep -E '^POSTGRES_USER=' .env | cut -d= -f2- || echo walaee)"
DB_NAME="$(grep -E '^POSTGRES_DB=' .env | cut -d= -f2- || echo walaee)"
DB_USER="${DB_USER:-walaee}"
DB_NAME="${DB_NAME:-walaee}"

STAMP="$(date +%Y-%m-%d_%H%M)"
FILE="$DEST/walaee-$STAMP.sql.gz"

mkdir -p "$DEST"

echo "▸ نسخ $DB_NAME …"

# الكتابة إلى ملف مؤقت ثم إعادة التسمية: انقطاع في المنتصف يترك
# ملفًا ناقصًا يبدو سليمًا، ويُكتشف يوم الاسترجاع لا قبله
TMP="$FILE.partial"
$COMPOSE exec -T postgres pg_dump -U "$DB_USER" --clean --if-exists "$DB_NAME" \
    | gzip -9 > "$TMP"

# التحقق من سلامة الضغط قبل اعتماد الملف
if ! gzip -t "$TMP" 2>/dev/null; then
    rm -f "$TMP"
    echo "✗ النسخة تالفة — لم تُعتمد" >&2
    exit 1
fi

mv "$TMP" "$FILE"
SIZE="$(du -h "$FILE" | cut -f1)"

# ملف صغير جدًّا يعني نسخة فارغة لقاعدة سليمة — فشل صامت
BYTES="$(wc -c < "$FILE")"
if [ "$BYTES" -lt 2048 ]; then
    echo "✗ النسخة أصغر من المتوقع ($BYTES بايت) — راجع الاتصال بالقاعدة" >&2
    exit 1
fi

echo "✓ $FILE ($SIZE)"

echo "▸ حذف النسخ الأقدم من $KEEP_DAYS يومًا …"
find "$DEST" -name 'walaee-*.sql.gz' -mtime "+$KEEP_DAYS" -print -delete || true

echo "✓ تمّت النسخة الاحتياطية"
