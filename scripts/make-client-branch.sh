#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════
#  يولّد فرع «client» من main — نسخة العميل المقصوصة
#
#  يُعاد تشغيله بعد أي تحديث على main فيُعاد بناء الفرع من جديد.
#  لا تعدّل فرع client يدويًا — أي تعديل يدوي سيُمحى عند إعادة التوليد.
#
#  الاستخدام:  bash scripts/make-client-branch.sh
# ══════════════════════════════════════════════════════════════
set -euo pipefail

BRANCH="client"
SRC="main"

cd "$(dirname "$0")/.."

if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
  echo "✗ شجرة العمل غير نظيفة — احفظ تغييراتك أولًا."
  exit 1
fi

ORIGINAL="$(git rev-parse --abbrev-ref HEAD)"
echo "▸ التوليد من $SRC …"

git checkout -q -B "$BRANCH" "$SRC"

# قصّ المحتوى غير المعروض
python scripts/trim_for_client.py

# بنية النشر الخاصة بنسخة العميل (تُخدَم على الجذر /)
cp -f deploy-client/Dockerfile        Dockerfile
cp -f deploy-client/nginx.conf        nginx.conf
cp -f deploy-client/docker-compose.yml docker-compose.yml
cp -f deploy-client/.dockerignore     .dockerignore
cp -f deploy-client/README.md         README.md
rm -rf deploy-client

# حارس: `git add -A` يكنس أي ملف غير متتبَّع إلى فرع مخصّص للنشر.
# حدث هذا فعلًا مع مستند محلي، فصار الحارس إلزاميًا.
STRAY="$(git ls-files --others --exclude-standard)"
if [ -n "$STRAY" ]; then
  echo "✗ ملفات غير متتبَّعة ستُكنس إلى فرع العميل:"
  echo "$STRAY" | sed 's/^/    /'
  echo "  أضفها إلى .gitignore أو احذفها، ثم أعد المحاولة."
  git checkout -q "$ORIGINAL"
  exit 1
fi

git add -A
git commit -q -m "Build client-facing demo (auto-generated from $SRC)

نسخة العميل: العرض التقديمي · تصفّح الواجهات · تطبيق العميل ·
لوحة صاحب المتجر · لوحة إدارة المنصة · عرض السعر.

محذوف نهائيًا من هذا الفرع: الخطة · المعمارية · الفريق · الحلول ·
التحليل الشامل · الوثيقة الأصلية · قرارات التخطيط · هيكلة المشروع.

يُخدَم على الجذر / بدل /demo/.

⚠ مولَّد آليًا — لا تعدّله يدويًا. عدّل main ثم أعد التوليد.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"

echo "▸ العودة إلى $ORIGINAL"
git checkout -q "$ORIGINAL"

echo
echo "✓ جاهز. للرفع:"
echo "    git push -f origin $BRANCH"
