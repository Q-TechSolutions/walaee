"""
لون العلامة الافتراضي.

الوعد الوحيد الذي يقدّمه هذا الملف هو **الثبات**: العلامة نفسها
تأخذ اللون نفسه في كل بيئة وبعد كل إعادة إنشاء. كُسر هذا الوعد
مرة في هذا المشروع حين استُعمل `hash` المدمج — وهو معشّى عبر
التشغيلات — فتبدّلت الأرقام بين نشرة وأخرى. الاختبار هنا يمنع
تكرارها.

وما يليه: أن يكون المُخرَج لونًا صالحًا تقبله `Brand.primary_color`
(سبعة محارف)، وأن تتوزّع الأسماء على اللوحة بدل أن تتكدّس على
لون واحد — فالغرض كله أن تتمايز البطاقات في محفظة العميل.
"""

import os
import subprocess
import sys

from apps.tenancy.palette import PALETTE, brand_color

NAMES = [
    "نخبة كافيه",
    "سوبر ماركت الحي",
    "مخبز الحصاد",
    "صالون رُقي",
    "وش النضافة",
    "مطعم الركن الشامي",
    "صيدلية الشفاء",
    "ملابس أوريجن",
    "جيم بلس",
    "قهوة الميدان",
]


class TestStability:
    def test_the_same_name_gives_the_same_colour(self):
        assert brand_color("نخبة كافيه") == brand_color("نخبة كافيه")

    def test_it_survives_a_fresh_interpreter(self):
        """
        الثبات عبر التشغيلات لا داخل التشغيل الواحد.

        `hash` المدمج معشّى بـPYTHONHASHSEED، فيعطي نفس الجواب طوال
        العملية الواحدة ويتبدّل بعد إعادة التشغيل — وهو ما يجعل
        اختبارًا داخل عملية واحدة يمرّ على دالة مكسورة. هذا
        الاختبار يشغّل مفسّرًا جديدًا ببذرة مختلفة صراحةً.
        """
        code = (
            "import hashlib;"
            "from apps.tenancy.palette import brand_color;"
            "print(brand_color('نخبة كافيه'))"
        )
        runs = {
            subprocess.run(  # noqa: S603
                [sys.executable, "-c", code],
                capture_output=True,
                text=True,
                encoding="utf-8",
                # بيئة موروثة مع تبديل البذرة وحدها: استبدالها
                # كاملةً يحرم المفسّر من PATH وSYSTEMROOT فيفشل
                # الاختبار لسبب لا علاقة له بما يقيسه
                env={**os.environ, "PYTHONHASHSEED": seed},
                check=True,
            ).stdout.strip()
            for seed in ("0", "1", "12345")
        }

        assert len(runs) == 1
        assert runs == {brand_color("نخبة كافيه")}

    def test_surrounding_whitespace_does_not_change_it(self):
        """اسم مأخوذ من نموذج قد يحمل مسافة زائدة — ولونه لا يتغيّر بها."""
        assert brand_color("  نخبة كافيه ") == brand_color("نخبة كافيه")


class TestOutput:
    def test_every_colour_is_a_valid_hex(self):
        """`Brand.primary_color` طوله سبعة — لون أطول يُقصّ بلا خطأ."""
        for name in NAMES:
            colour = brand_color(name)
            assert len(colour) == 7
            assert colour.startswith("#")
            int(colour[1:], 16)

    def test_it_only_returns_colours_from_the_palette(self):
        assert {brand_color(name) for name in NAMES} <= set(PALETTE)

    def test_the_palette_has_no_duplicates(self):
        """لونان متطابقان في اللوحة يضيّعان خانة بلا سبب."""
        assert len(set(PALETTE)) == len(PALETTE)


class TestSpread:
    def test_it_does_not_collapse_onto_one_colour(self):
        """
        الغرض كله أن تتمايز البطاقات.

        دالة تعيد نفس اللون للجميع تمرّ كل الاختبارات أعلاه وتفشل
        في الشيء الوحيد المطلوب منها.
        """
        assert len({brand_color(name) for name in NAMES}) >= 5
