# -*- coding: utf-8 -*-
"""
يحوّل نسخة العمل الحالية إلى «نسخة العميل» — تُشغَّل من فرع client فقط.

ما يبقى:  العرض التقديمي · تصفّح الواجهات · تطبيق العميل ·
          لوحة صاحب المتجر · لوحة إدارة المنصة · عرض السعر (صفحة + PDF)

ما يُحذَف نهائيًا من الفرع (فلا يصل إليه أحد):
          الخطة · المعمارية · الفريق · الحلول · التحليل الشامل ·
          الوثيقة الأصلية · قرارات التخطيط · هيكلة المشروع

يُشغَّل عبر:  scripts/make-client-branch.sh
"""
import io, os, re, shutil, sys

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

DEMO = 'docs/demo'
REPORTS = 'docs/reports'

# ═══════════════════ ١) حذف كل ما لا يُعرض ═══════════════════
REMOVE = [
    f'{DEMO}/plan', f'{DEMO}/architecture', f'{DEMO}/team', f'{DEMO}/solutions',
    f'{REPORTS}/Walaee_Analysis_Report_AR.pdf',
    f'{REPORTS}/Walaee_Analysis_Report_AR.html',
    f'{REPORTS}/Walaee_Executive_Brief_Book_Mobile.pdf',
    'docs/planning', 'docs/DEPLOY-DEMO.md', 'docs/README.md',
    'project', 'PROJECT_STRUCTURE.md', '.github',
    'scripts',
]
removed = []
for p in REMOVE:
    if os.path.isdir(p):
        shutil.rmtree(p); removed.append(p + '/')
    elif os.path.isfile(p):
        os.remove(p); removed.append(p)

# ═══════════════════ ٢) تشذيب روابط الفهرس ═══════════════════
def cut_block(s, start_marker, end_marker, label):
    """يحذف كتلة من start_marker حتى end_marker (شاملًا)."""
    i = s.find(start_marker)
    if i < 0:
        print('  ⚠ لم يُعثر على: ' + label); return s
    j = s.find(end_marker, i)
    if j < 0:
        print('  ⚠ نهاية غير موجودة: ' + label); return s
    return s[:i] + s[j + len(end_marker):]

p = f'{DEMO}/index.html'
s = io.open(p, encoding='utf-8', newline='').read()

# بطاقات المستندات المحذوفة
for href, label in [('plan/index.html', 'خطة التطوير'),
                    ('architecture/index.html', 'المخطط المعماري'),
                    ('../reports/Walaee_Analysis_Report_AR.pdf', 'التحليل الشامل'),
                    ('solutions/index.html', 'تتبّع الحلول — بطاقة')]:
    s = cut_block(s, '<a class="card3 doc', '</a>', label) if False else s
# إزالة دقيقة بالـregex: كل <a class="card3 doc ..." href="X" ...> ... </a>
for href in ['plan/index.html', 'architecture/index.html',
             '../reports/Walaee_Analysis_Report_AR.pdf', 'solutions/index.html']:
    pat = re.compile(
        r'\s*<a class="card3 doc[^"]*" href="' + re.escape(href) + r'".*?</a>',
        re.S)
    s, n = pat.subn('', s)
    print(f'  بطاقة {href}: حُذفت' if n else f'  ⚠ بطاقة {href}: غير موجودة')

# قسم «تتبّع الحلول» بالكامل
s = cut_block(s, '<!-- ══ 3 · الحلول ══ -->', '</section>', 'قسم الحلول')
# قسم «مستند داخلي» بالكامل
s = cut_block(s, '<!-- ══ 4 · داخلي ══ -->', '</section>', 'قسم داخلي')

# رابط التنقّل للحلول
s = re.sub(r'\s*<a href="#s3">[^<]*</a>', '', s)

# مسار PDF عرض السعر — يُخدَم على /reports/ والفهرس على الجذر
s = s.replace('href="../reports/Walaee_Pricing_Proposal_AR.pdf"',
              'href="reports/Walaee_Pricing_Proposal_AR.pdf"')

# تصحيح عدّاد المستندات في شريط الأرقام
s = s.replace('<div><b>٨</b><span>مستندات</span></div>',
              '<div><b>٥</b><span>واجهات ومستندات</span></div>')
s = s.replace('<div><b>١٦</b><span>مشكلة مُعالَجة</span></div>',
              '<div><b>٦</b><span>نماذج ولاء</span></div>')
io.open(p, 'w', encoding='utf-8', newline='').write(s)
print('✓ docs/demo/index.html')

# ═══════════════════ ٣) الشريحة الأخيرة في العرض ═══════════════════
p = f'{DEMO}/present/index.html'
s = io.open(p, encoding='utf-8', newline='').read()
for href in ['../plan/index.html', '../architecture/index.html',
             '../../reports/Walaee_Analysis_Report_AR.pdf']:
    s = re.sub(r'\s*<a class="pill2[^"]*" href="' + re.escape(href) + r'">[^<]*</a>', '', s)
s = s.replace('<a class="pill2" href="../pricing/index.html">',
              '<a class="pill2 o" href="../pricing/index.html">')
if 'pricing/index.html' not in s:
    s = s.replace('<a class="pill2 o" href="../admin/index.html">لوحة الإدارة</a>',
                  '<a class="pill2 o" href="../admin/index.html">لوحة الإدارة</a>\n'
                  '    <a class="pill2" href="../pricing/index.html">عرض السعر</a>')
io.open(p, 'w', encoding='utf-8', newline='').write(s)
print('✓ docs/demo/present/index.html')

# ═══════════════════ ٤) شريط تصفّح الواجهات ═══════════════════
p = f'{DEMO}/preview/index.html'
s = io.open(p, encoding='utf-8', newline='').read()
s = re.sub(r'\s*<a href="\.\./solutions/index\.html">[^<]*</a>', '', s)
s = s.replace('<a href="../index.html">ملف المشروع</a>', '<a href="../index.html">الرئيسية</a>')
io.open(p, 'w', encoding='utf-8', newline='').write(s)
print('✓ docs/demo/preview/index.html')

# ═══════════════════ ٥) المبدّل العائم ═══════════════════
p = f'{DEMO}/assets/js/switcher.js'
s = io.open(p, encoding='utf-8', newline='').read()
for k in ['solutions', 'plan', 'architecture', 'team']:
    s = re.sub(r"\s*\{ k:'" + k + r"',.*?\},?\r?\n", '\n', s)
s = s.replace("{ k:'pricing',      l:'عرض السعر', href: base + 'pricing/index.html',      ic:'cash'  },",
              "{ k:'pricing',      l:'عرض السعر', href: base + 'pricing/index.html',      ic:'cash'  }")
s = s.replace("|| at('team') || at('pricing') || at('solutions') || at('preview') ? '../' : './';",
              "|| at('pricing') || at('preview') ? '../' : './';")
s = s.replace("!at('architecture') && !at('present') && !at('team') && !at('pricing') && !at('solutions') && !at('preview'))",
              "!at('present') && !at('pricing') && !at('preview'))")
io.open(p, 'w', encoding='utf-8', newline='').write(s)
print('✓ docs/demo/assets/js/switcher.js')

# ═══════════════════ ٦) فحص نهائي — لا أثر للمحذوف ═══════════════════
BANNED = ['plan/index.html', 'architecture/index.html', 'team/index.html',
          'solutions/index.html', 'Walaee_Analysis_Report_AR',
          'Walaee_Executive_Brief_Book']
leaks = []
for root, _, files in os.walk('docs'):
    for fn in files:
        if not fn.endswith(('.html', '.js', '.css', '.md')):
            continue
        fp = os.path.join(root, fn)
        txt = io.open(fp, encoding='utf-8', errors='ignore').read()
        for b in BANNED:
            if b in txt:
                leaks.append(f'{fp} → {b}')

print('\n── حُذف ──')
for r in removed:
    print('  ✗ ' + r)
if leaks:
    print('\n⚠ مراجع متبقية للمحذوف:')
    for l in leaks:
        print('  ! ' + l)
    sys.exit(1)
print('\n✓ لا توجد أي مراجع للمحتوى المحذوف')
