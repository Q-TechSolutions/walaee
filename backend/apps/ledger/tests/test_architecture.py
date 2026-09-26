"""
حراسة القواعد المعمارية المعلَنة في العرض.

المخطط المعماري يَعِد بقواعد لا يفرضها المترجم: «كل تعديل على
الرصيد يمر عبر خدمة واحدة»، و«منطق الأعمال في services.py».
قواعد كهذه تتآكل بصمت — سطر واحد في عجلة إصلاح عطل يكسرها، ولا
يلاحظ أحد حتى يختلّ رصيد عميل بعد شهور.

الاختبارات هنا تقرأ الشجرة المصدرية نفسها. ليست اختبارات سلوك بل
اختبارات **عقد**: ما دامت خضراء، فما في العرض صحيح.
"""

import ast
from pathlib import Path

import pytest

APPS = Path(__file__).resolve().parents[3] / "apps"

#: المواضع المسموح لها بالكتابة في `Balance` مباشرةً.
#:
#: الأول هو `apply_entry` نفسه — المحرّك.
#: والثاني أمر المصالحة: يُعيد حساب اللقطة من دفتر القيود حين
#: تنحرف، فهو لا «يعدّل رصيدًا» بل يصلح نسخة مشتقّة من المصدر.
#: أي موضع ثالث خرقٌ للقاعدة مهما بدا مبرّرًا.
BALANCE_WRITERS = {
    "ledger/services.py",
    "ledger/management/commands/verify_ledger.py",
}

#: أوامر الإدارة التي تنشئ بيانات تجريبية تُستثنى من قاعدة الحذف.
SEED_COMMANDS = {"tenancy/management/commands/seed_demo.py"}


def python_files():
    for path in APPS.rglob("*.py"):
        rel = path.relative_to(APPS).as_posix()
        if "/tests/" in rel or rel.startswith("tests/"):
            continue
        yield rel, path


def writes_to_balance(tree: ast.AST) -> bool:
    """هل يستدعي هذا الملف `update()` أو `save()` على استعلام Balance؟"""
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Attribute) or func.attr not in {
            "update",
            "delete",
            "create",
            "bulk_create",
        }:
            continue
        # يكفي أن يظهر اسم Balance في سلسلة الاستدعاء
        chain = ast.dump(func)
        if "'Balance'" in chain:
            return True
    return False


class TestLedgerIsTheOnlyWriter:
    """
    **القاعدة المعمارية غير القابلة للكسر.**

    الرصيد لقطة مشتقّة من دفتر القيود. الكتابة فيه من مكان آخر
    تنتج رصيدًا لا يقابله قيد — أي رقمًا لا يمكن تفسيره لعميل ولا
    تدقيقه لمحاسب، ولا يكشفه شيء إلا مصادفةً.
    """

    def test_only_sanctioned_modules_write_balance(self):
        offenders = []

        for rel, path in python_files():
            if rel in BALANCE_WRITERS or rel in SEED_COMMANDS:
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            if writes_to_balance(tree):
                offenders.append(rel)

        assert offenders == [], (
            "كتابة مباشرة في Balance خارج المحرّك: "
            + ", ".join(offenders)
            + " — استخدم ledger.services.apply_entry"
        )

    def test_the_engine_still_writes_it(self):
        """
        الحارس يجب أن يكشف الكتابة فعلًا.

        بدون هذا الفحص كان يكفي أن يتغيّر شكل الاستدعاء ليصير
        الاختبار أعلاه أخضر دائمًا بلا أن يفحص شيئًا.
        """
        engine = APPS / "ledger" / "services.py"
        tree = ast.parse(engine.read_text(encoding="utf-8"), filename=str(engine))

        assert writes_to_balance(tree)


class TestDomainLayout:
    """بنية المشروع كما يعلنها المخطط: تقسيم بالمجال لا بالنوع."""

    EXPECTED = {
        "accounts",
        "tenancy",
        "loyalty",
        "ledger",
        "pos",
        "fraud",
        "campaigns",
        "billing",
        "insights",
        "publicapi",
        "audit",
    }

    def test_every_declared_app_exists(self):
        present = {p.name for p in APPS.iterdir() if p.is_dir() and not p.name.startswith("_")}

        assert self.EXPECTED <= present, f"تطبيقات ناقصة: {self.EXPECTED - present}"

    #: التطبيقات التي تحمل منطق أعمال، والوحدة التي يعيش فيها.
    #:
    #: `loyalty` يسمّي وحدته `rules.py`: محتواه قواعد حساب («كم
    #: نقطة لهذه الفاتورة؟») لا خدمات تُنفّذ أثرًا، والاسم يصف
    #: المحتوى. المبدأ واحد — المنطق خارج `views` و`models`.
    #:
    #: ما ليس في هذه الخريطة لا منطق له أصلًا: `tenancy` إنشاء
    #: وتعديل صِرف يفوّض فحص الحدود إلى `billing.services`،
    #: و`audit` وسيط، و`insights` و`publicapi` خلف مفاتيح ميزات.
    LOGIC_MODULE = {
        "accounts": "services.py",
        "loyalty": "rules.py",
        "ledger": "services.py",
        "pos": "services.py",
        "fraud": "services.py",
        "campaigns": "services.py",
        "billing": "services.py",
    }

    def test_domain_apps_keep_their_logic_in_a_dedicated_module(self):
        """
        منطق الأعمال في وحدته لا في `views.py` ولا في `models.py`.

        الخريطة صريحة لا مشتقّة: الاستثناء الضمني يبتلع تطبيقًا
        نُسي فيه الملف، فيبدو أنه بلا منطق وهو يحمله في مكان خاطئ.
        """
        for app, module in sorted(self.LOGIC_MODULE.items()):
            assert (APPS / app / module).exists(), f"{app} بلا {module}"

    @pytest.mark.parametrize("app", ["ledger", "pos", "loyalty", "campaigns", "billing"])
    def test_views_do_not_touch_the_orm_for_writes(self, app):
        """
        الـView يستقبل ويتحقق ويستدعي الخدمة.

        كتابة مباشرة في `views.py` تعني منطقًا لا يستطيع Celery ولا
        أمر إدارة استدعاءه، فيُنسخ ثانيةً وينحرف عن الأصل.
        """
        views = APPS / app / "views.py"
        if not views.exists():
            pytest.skip(f"{app} بلا views.py")

        source = views.read_text(encoding="utf-8")

        # الإنشاء عبر السيريالايزر مسموح — هو طبقة تحقق لا منطق
        for banned in (".objects.bulk_create(", "transaction.atomic()"):
            assert banned not in source, f"{app}/views.py يحمل منطقًا: {banned}"
