"""
جغرافيا مصر — المرجع الوحيد للمحافظات.

لماذا جدول ثابت في الكود لا جدولًا في قاعدة البيانات: محافظات مصر
سبع وعشرون تتغيّر مرة كل عقد تقريبًا، وجعلها بيانات يعني هجرة
وواجهة إدارة وحالة «محافظة غير موجودة» في كل بيئة تُنشأ من جديد.
الثابت هنا يُفحص عند التحقّق من النموذج فيستحيل حفظ فرع في محافظة
لا وجود لها.

`anchor` ليس مركزًا هندسيًا بل نقطة تمثيل بصرية: المركز الهندسي
للوادي الجديد يقع في صحراء خالية، ووضع علامة المحافظة هناك يجعل
الخريطة تكذب على من يقرأها. النقطة المختارة هي مركز العمران فيها.
"""

from __future__ import annotations

from typing import NamedTuple


class Governorate(NamedTuple):
    code: str
    name: str
    anchor_lat: float
    anchor_lng: float
    region: str
    #: أقصى بُعد معقول لفرع عن المرساة، بالدرجات.
    #:
    #: المحافظات ليست متساوية الحجم ولا قريبًا من ذلك: دمياط تُقطَع
    #: في نصف ساعة، والبحر الأحمر يمتد من السويس إلى حلايب. حارس
    #: واحد لكل المحافظات إما يقبل فرعًا في البحر أو يرفض مرسى علم.
    #: يستخدمه فحص سلامة الكتالوج، ويستخدمه الرسم ليقرّر حجم التجميع.
    span: float = 1.2


# الأقاليم كما تستخدمها خطة التوسّع التجاري — docs/planning
REGION_CAIRO = "greater_cairo"
REGION_DELTA = "delta"
REGION_CANAL = "canal"
REGION_ALEX = "alexandria"
REGION_UPPER = "upper"
REGION_RED_SEA = "red_sea"
REGION_SINAI = "sinai"
REGION_WEST = "west"

REGION_NAMES = {
    REGION_CAIRO: "القاهرة الكبرى",
    REGION_DELTA: "الدلتا",
    REGION_CANAL: "القناة",
    REGION_ALEX: "الإسكندرية والساحل",
    REGION_UPPER: "الصعيد",
    REGION_RED_SEA: "البحر الأحمر",
    REGION_SINAI: "سيناء",
    REGION_WEST: "الوادي والصحراء",
}

GOVERNORATES: tuple[Governorate, ...] = (
    Governorate("CAI", "القاهرة", 30.0444, 31.2357, REGION_CAIRO),
    # المرساة غرب مدينة الجيزة لا فيها: المحافظة تمتد غربًا حتى
    # ٦ أكتوبر، ووضعها على المدينة يجعل فقاعتها فوق فقاعة القاهرة
    # تمامًا فتبتلع إحداهما الأخرى على الخريطة.
    Governorate("GIZ", "الجيزة", 29.9300, 30.9000, REGION_CAIRO, 2.5),
    Governorate("QLY", "القليوبية", 30.3292, 31.2168, REGION_CAIRO),
    Governorate("ALX", "الإسكندرية", 31.2001, 29.9187, REGION_ALEX),
    Governorate("BHR", "البحيرة", 31.0341, 30.4682, REGION_DELTA, 1.6),
    Governorate("KFS", "كفر الشيخ", 31.1117, 30.9398, REGION_DELTA),
    Governorate("GHR", "الغربية", 30.7865, 31.0004, REGION_DELTA),
    Governorate("MNF", "المنوفية", 30.5519, 30.9876, REGION_DELTA),
    Governorate("DKH", "الدقهلية", 31.0409, 31.3785, REGION_DELTA),
    Governorate("DMT", "دمياط", 31.4165, 31.8133, REGION_DELTA),
    Governorate("SHR", "الشرقية", 30.5877, 31.5020, REGION_DELTA, 1.6),
    Governorate("PTS", "بورسعيد", 31.2653, 32.3019, REGION_CANAL),
    Governorate("ISM", "الإسماعيلية", 30.5965, 32.2715, REGION_CANAL),
    Governorate("SUZ", "السويس", 29.9668, 32.5498, REGION_CANAL),
    Governorate("FYM", "الفيوم", 29.3084, 30.8428, REGION_UPPER),
    Governorate("BNS", "بني سويف", 29.0661, 31.0994, REGION_UPPER),
    Governorate("MNY", "المنيا", 28.1099, 30.7503, REGION_UPPER, 1.6),
    Governorate("AST", "أسيوط", 27.1809, 31.1837, REGION_UPPER, 1.6),
    Governorate("SHG", "سوهاج", 26.5591, 31.6957, REGION_UPPER),
    Governorate("QNA", "قنا", 26.1551, 32.7160, REGION_UPPER),
    Governorate("LUX", "الأقصر", 25.6872, 32.6396, REGION_UPPER),
    Governorate("ASN", "أسوان", 24.0889, 32.8998, REGION_UPPER, 2.0),
    Governorate("RSS", "البحر الأحمر", 27.2579, 33.8116, REGION_RED_SEA, 4.0),
    Governorate("WAD", "الوادي الجديد", 25.4514, 30.5467, REGION_WEST, 4.0),
    Governorate("MAT", "مطروح", 31.3543, 27.2373, REGION_WEST, 4.0),
    Governorate("NSI", "شمال سيناء", 31.1249, 33.7984, REGION_SINAI, 2.0),
    Governorate("SSI", "جنوب سيناء", 28.2416, 33.6222, REGION_SINAI, 2.0),
)

BY_CODE: dict[str, Governorate] = {g.code: g for g in GOVERNORATES}

# صيغة Django لحقل `choices` — تُبنى مرة واحدة لا عند كل هجرة
GOVERNORATE_CHOICES = [(g.code, g.name) for g in GOVERNORATES]


def name_of(code: str) -> str:
    """اسم المحافظة، أو الرمز نفسه إن كان غير معروف.

    لا يرمي: هذه الدالة تُستدعى في مسارات عرض، وسقوط صفحة الدليل
    كلها بسبب رمز واحد خاطئ في صف قديم مقايضة خاسرة.
    """
    found = BY_CODE.get(code)
    return found.name if found else code


def region_of(code: str) -> str:
    found = BY_CODE.get(code)
    return found.region if found else ""
