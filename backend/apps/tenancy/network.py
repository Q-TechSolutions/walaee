"""
شبكة التجّار المتعاقدين — كتالوج الإطلاق.

هذا ليس «بيانات تجريبية». هذه هي الشبكة التي تُبنى عليها الخريطة
العامة وصفحة الدليل، ويُنشئها `seed_network` في أي بيئة بما فيها
الإنتاج. البيانات التجريبية الوحيدة في المنصة هي الحسابات، وتظل
معزولة في `demo_accounts`.

لماذا الكتالوج في الكود لا في ملف JSON: الإحداثيات والفئات
والبرامج يقرؤها مطوّر ويراجعها مسؤول تجاري، وملف بيانات بلا تعليق
يجعل «لماذا هذا الفرع هنا؟» سؤالًا بلا جواب. التعليق يعيش مع الصف.

قاعدة الإحداثيات: نقطة العمران الفعلية للحيّ لا مركز المدينة
الإداري. علامة على مركز المدينة الإداري في ٦ أكتوبر تضع الفرع في
صحراء، ومن يفتح الخريطة ليقيس تغطيتنا يرى تغطية لا وجود لها.
"""

from __future__ import annotations

from decimal import Decimal
from typing import NamedTuple

from apps.loyalty.models import LoyaltyProgram as P


class BranchSpec(NamedTuple):
    name: str
    city: str
    governorate: str
    lat: float
    lng: float
    address: str
    terminals: int = 1


class RewardSpec(NamedTuple):
    title: str
    cost: Decimal
    merchant_cost: Decimal
    description: str = ""


class ProgramSpec(NamedTuple):
    type: str
    name: str
    earn_rate: Decimal
    rewards: tuple[RewardSpec, ...]
    min_invoice: Decimal = Decimal("0")
    expiry_months: int | None = 12
    welcome_bonus: int = 0
    max_per_day: Decimal | None = None


class BrandSpec(NamedTuple):
    slug: str
    name: str
    category: str
    tagline: str
    color: str
    organization: str
    joined_on: str
    program: ProgramSpec
    branches: tuple[BranchSpec, ...]


# ══════════════ الفئات ══════════════
# تظهر كما هي في مرشّح الدليل العام، فتُكتب مرة واحدة هنا لا في
# كل علامة على حدة حتى لا تصير «مقاهي» و«مقاهٍ» فئتين منفصلتين.
CAFE = "مقاهٍ ومشروبات"
BAKERY = "مخبوزات وحلويات"
RESTAURANT = "مطاعم"
GRILL = "مشويات"
SEAFOOD = "مأكولات بحرية"
PHARMACY = "صيدليات"
GROCERY = "بقالة وسوبر ماركت"
BEAUTY = "تجميل وعناية"
SPORTS = "رياضة ولياقة"
FASHION = "ملابس وأحذية"
ELECTRONICS = "إلكترونيات"
BOOKS = "مكتبات وقرطاسية"
GIFTS = "هدايا وزهور"

CATEGORY_ORDER = (
    CAFE,
    RESTAURANT,
    GRILL,
    SEAFOOD,
    BAKERY,
    GROCERY,
    PHARMACY,
    BEAUTY,
    SPORTS,
    FASHION,
    ELECTRONICS,
    BOOKS,
    GIFTS,
)


# ══════════════ الشبكة ══════════════

NETWORK: tuple[BrandSpec, ...] = (
    BrandSpec(
        slug="ahwa-el-medan",
        name="قهوة الميدان",
        category=CAFE,
        tagline="قهوة مختصة في قلب كل حي",
        color="#6F4E37",
        organization="مجموعة الميدان للضيافة",
        joined_on="2025-11-03",
        # الأختام لا النقاط: المقهى يبيع صنفًا واحدًا متكرّرًا بسعر
        # متقارب، والنقاط على قيمة الفاتورة تعطي فروقًا لا يفهمها
        # العميل بين كوب وكوب.
        program=ProgramSpec(
            type=P.TYPE_STAMPS,
            name="ختم على كل مشروب",
            earn_rate=Decimal("1"),
            min_invoice=Decimal("25"),
            expiry_months=6,
            welcome_bonus=1,
            max_per_day=Decimal("3"),
            rewards=(
                RewardSpec(
                    "مشروب مجاني", Decimal("8"), Decimal("22"), "أي مشروب من القائمة الأساسية"
                ),
                RewardSpec("قطعة حلو مع مشروبك", Decimal("5"), Decimal("14")),
            ),
        ),
        branches=(
            BranchSpec("وسط البلد", "القاهرة", "CAI", 30.0459, 31.2400, "شارع شريف، وسط البلد", 2),
            BranchSpec("الزمالك", "القاهرة", "CAI", 30.0614, 31.2197, "شارع ٢٦ يوليو، الزمالك"),
            BranchSpec("مصر الجديدة", "القاهرة", "CAI", 30.0876, 31.3255, "ميدان روكسي"),
            BranchSpec(
                "المهندسين", "الجيزة", "GIZ", 30.0578, 31.2001, "شارع جامعة الدول العربية", 2
            ),
            BranchSpec("سموحة", "الإسكندرية", "ALX", 31.2140, 29.9440, "شارع فوزي معاذ"),
            BranchSpec("المنصورة", "المنصورة", "DKH", 31.0409, 31.3785, "شارع الجمهورية"),
            BranchSpec("الغردقة", "الغردقة", "RSS", 27.2579, 33.8116, "شارع الشيراتون"),
        ),
    ),
    BrandSpec(
        slug="beit-el-forn",
        name="بيت الفرن",
        category=BAKERY,
        tagline="مخبوزات طازجة من فجر كل يوم",
        color="#C9762B",
        organization="مجموعة الميدان للضيافة",
        joined_on="2025-11-03",
        program=ProgramSpec(
            type=P.TYPE_POINTS,
            name="نقاط الفرن",
            earn_rate=Decimal("2"),
            min_invoice=Decimal("30"),
            expiry_months=12,
            welcome_bonus=50,
            rewards=(
                RewardSpec("خصم ٢٠ جنيهًا", Decimal("200"), Decimal("20")),
                RewardSpec("صينية معجنات صغيرة", Decimal("450"), Decimal("45")),
                RewardSpec("تورتة عيد ميلاد", Decimal("1200"), Decimal("140"), "حتى كيلو واحد"),
            ),
        ),
        branches=(
            BranchSpec("شبرا", "القاهرة", "CAI", 30.0800, 31.2450, "شارع شبرا الرئيسي"),
            BranchSpec("المعادي", "القاهرة", "CAI", 29.9603, 31.2578, "شارع ٩، المعادي"),
            BranchSpec("الدقي", "الجيزة", "GIZ", 30.0388, 31.2122, "شارع التحرير، الدقي"),
            BranchSpec("بنها", "بنها", "QLY", 30.4600, 31.1838, "شارع فريد ندا"),
            BranchSpec("طنطا", "طنطا", "GHR", 30.7865, 31.0004, "شارع البحر"),
            BranchSpec("الزقازيق", "الزقازيق", "SHR", 30.5877, 31.5020, "شارع سعد زغلول"),
        ),
    ),
    BrandSpec(
        slug="mazaq-masr",
        name="مذاق مصر",
        category=RESTAURANT,
        tagline="أكل بيتي مصري على أصوله",
        color="#B3392F",
        organization="شركة مذاق مصر للمطاعم",
        joined_on="2025-12-15",
        # الزيارات لا النقاط: الفاتورة هنا تختلف كثيرًا بين وجبة فرد
        # ووليمة عائلة، ومكافأة الزيارة تساوي بينهما — وهي بالضبط
        # الرسالة التي يريدها المطعم: «تعالى كتير».
        program=ProgramSpec(
            type=P.TYPE_VISITS,
            name="زيارات مذاق",
            earn_rate=Decimal("1"),
            min_invoice=Decimal("60"),
            expiry_months=9,
            max_per_day=Decimal("1"),
            rewards=(
                RewardSpec("طبق جانبي مجاني", Decimal("4"), Decimal("18")),
                RewardSpec("وجبة كاملة", Decimal("10"), Decimal("95")),
            ),
        ),
        branches=(
            BranchSpec("مدينة نصر", "القاهرة", "CAI", 30.0626, 31.3439, "شارع عباس العقاد", 2),
            BranchSpec("التجمع الخامس", "القاهرة", "CAI", 30.0131, 31.4914, "التسعين الشمالي"),
            BranchSpec("الهرم", "الجيزة", "GIZ", 29.9870, 31.1313, "شارع الهرم"),
            BranchSpec("محطة الرمل", "الإسكندرية", "ALX", 31.2001, 29.9010, "شارع صفية زغلول"),
            BranchSpec("أسيوط", "أسيوط", "AST", 27.1809, 31.1837, "شارع الجمهورية"),
            BranchSpec("الأقصر", "الأقصر", "LUX", 25.6872, 32.6396, "شارع التلفزيون"),
            BranchSpec("الإسماعيلية", "الإسماعيلية", "ISM", 30.5965, 32.2715, "شارع سعد زغلول"),
        ),
    ),
    BrandSpec(
        slug="grill-el-basha",
        name="جريل الباشا",
        category=GRILL,
        tagline="مشويات على الفحم من ١٩٩٨",
        color="#7A2E1E",
        organization="شركة مذاق مصر للمطاعم",
        joined_on="2025-12-15",
        program=ProgramSpec(
            type=P.TYPE_STAMPS,
            name="ختم الباشا",
            earn_rate=Decimal("1"),
            min_invoice=Decimal("150"),
            expiry_months=12,
            rewards=(
                RewardSpec("ساندوتش شاورما", Decimal("6"), Decimal("55")),
                RewardSpec("وجبة مشويات لفردين", Decimal("12"), Decimal("210")),
            ),
        ),
        branches=(
            BranchSpec("العباسية", "القاهرة", "CAI", 30.0700, 31.2800, "شارع العباسية"),
            BranchSpec("فيصل", "الجيزة", "GIZ", 30.0100, 31.1700, "شارع فيصل الرئيسي"),
            BranchSpec("شبين الكوم", "شبين الكوم", "MNF", 30.5519, 30.9876, "شارع جمال عبد الناصر"),
            BranchSpec("بورسعيد", "بورسعيد", "PTS", 31.2653, 32.3019, "شارع الجمهورية"),
            BranchSpec("سوهاج", "سوهاج", "SHG", 26.5591, 31.6957, "كورنيش النيل"),
        ),
    ),
    BrandSpec(
        slug="bahr-el-samak",
        name="بحر السمك",
        category=SEAFOOD,
        tagline="صيد اليوم على طاولتك",
        color="#0E6C86",
        organization="شركة سواحل للمأكولات البحرية",
        joined_on="2026-01-20",
        program=ProgramSpec(
            type=P.TYPE_POINTS,
            name="نقاط الصيد",
            earn_rate=Decimal("1.5"),
            min_invoice=Decimal("100"),
            expiry_months=12,
            welcome_bonus=100,
            rewards=(
                RewardSpec("طبق جمبري", Decimal("800"), Decimal("110")),
                RewardSpec("خصم ٥٠ جنيهًا", Decimal("500"), Decimal("50")),
            ),
        ),
        branches=(
            BranchSpec(
                "المنتزه", "الإسكندرية", "ALX", 31.2830, 30.0140, "طريق الكورنيش، المنتزه", 2
            ),
            BranchSpec("العجمي", "الإسكندرية", "ALX", 31.1000, 29.7600, "طريق البيطاش"),
            BranchSpec("دمياط", "دمياط", "DMT", 31.4165, 31.8133, "كورنيش النيل"),
            BranchSpec("بورسعيد", "بورسعيد", "PTS", 31.2700, 32.3100, "شارع الميناء"),
            BranchSpec("الغردقة", "الغردقة", "RSS", 27.2400, 33.8300, "شارع سقالة"),
            BranchSpec("مرسى مطروح", "مرسى مطروح", "MAT", 31.3543, 27.2373, "كورنيش مطروح"),
        ),
    ),
    BrandSpec(
        slug="saydaliyat-el-nil",
        name="صيدليات النيل",
        category=PHARMACY,
        tagline="دواؤك ونصيحتك في مكان واحد",
        color="#127A53",
        organization="مجموعة النيل الطبية",
        joined_on="2025-10-12",
        # استرداد نقدي لا نقاط: العميل في الصيدلية يشتري ما يحتاجه لا
        # ما يجمع عليه، ووعد «٣٪ ترجع لك» أوضح بكثير من جدول تحويل.
        program=ProgramSpec(
            type=P.TYPE_CASHBACK,
            name="استرداد النيل",
            earn_rate=Decimal("0.03"),
            min_invoice=Decimal("50"),
            expiry_months=6,
            max_per_day=Decimal("30"),
            rewards=(
                RewardSpec(
                    "خصم من الرصيد", Decimal("25"), Decimal("25"), "يُخصم مباشرة من الفاتورة"
                ),
            ),
        ),
        branches=(
            BranchSpec("المعادي", "القاهرة", "CAI", 29.9590, 31.2600, "شارع ٩، المعادي"),
            BranchSpec("حلوان", "القاهرة", "CAI", 29.8419, 31.3342, "شارع منصور"),
            BranchSpec("مدينة نصر", "القاهرة", "CAI", 30.0580, 31.3400, "شارع مصطفى النحاس"),
            BranchSpec("٦ أكتوبر", "٦ أكتوبر", "GIZ", 29.9285, 30.9188, "المحور المركزي"),
            BranchSpec("شبرا الخيمة", "شبرا الخيمة", "QLY", 30.1286, 31.2422, "شارع ترعة الجبل"),
            BranchSpec("دمنهور", "دمنهور", "BHR", 31.0341, 30.4682, "شارع الجمهورية"),
            BranchSpec("كفر الشيخ", "كفر الشيخ", "KFS", 31.1117, 30.9398, "شارع الجيش"),
            BranchSpec("المنيا", "المنيا", "MNY", 28.1099, 30.7503, "شارع الحرية"),
            BranchSpec("قنا", "قنا", "QNA", 26.1551, 32.7160, "شارع الجمهورية"),
        ),
    ),
    BrandSpec(
        slug="super-el-hayy",
        name="سوبر ماركت الحي",
        category=GROCERY,
        tagline="احتياج البيت كله تحت سقف واحد",
        color="#1F6F5C",
        organization="مجموعة الحي التجارية",
        joined_on="2025-09-28",
        program=ProgramSpec(
            type=P.TYPE_POINTS,
            name="نقاط الحي",
            earn_rate=Decimal("1"),
            min_invoice=Decimal("0"),
            expiry_months=18,
            welcome_bonus=100,
            rewards=(
                RewardSpec("خصم ٢٥ جنيهًا", Decimal("250"), Decimal("25")),
                RewardSpec("خصم ٧٥ جنيهًا", Decimal("700"), Decimal("75")),
                RewardSpec("كرتونة زيت", Decimal("1500"), Decimal("180")),
            ),
        ),
        branches=(
            BranchSpec("شبرا", "القاهرة", "CAI", 30.0830, 31.2470, "شارع شبرا", 3),
            BranchSpec("التجمع الخامس", "القاهرة", "CAI", 30.0180, 31.4800, "الحي الأول", 2),
            BranchSpec("الهرم", "الجيزة", "GIZ", 29.9900, 31.1400, "شارع الهرم", 2),
            BranchSpec("٦ أكتوبر", "٦ أكتوبر", "GIZ", 29.9350, 30.9250, "الحي السابع"),
            BranchSpec("بنها", "بنها", "QLY", 30.4650, 31.1800, "شارع الجمهورية"),
            BranchSpec("المحلة الكبرى", "المحلة الكبرى", "GHR", 30.9700, 31.1669, "شارع البحر"),
            BranchSpec("ميت غمر", "ميت غمر", "DKH", 30.7180, 31.2600, "شارع الجيش"),
            BranchSpec(
                "العاشر من رمضان", "العاشر من رمضان", "SHR", 30.2960, 31.7420, "الحي الثاني"
            ),
            BranchSpec("بني سويف", "بني سويف", "BNS", 29.0661, 31.0994, "شارع سعد زغلول"),
            BranchSpec("الفيوم", "الفيوم", "FYM", 29.3084, 30.8428, "شارع الحرية"),
            BranchSpec("أسوان", "أسوان", "ASN", 24.0889, 32.8998, "شارع السوق"),
            BranchSpec("السويس", "السويس", "SUZ", 29.9668, 32.5498, "شارع الجيش"),
        ),
    ),
    BrandSpec(
        slug="lammset-gamal",
        name="لمسة جمال",
        category=BEAUTY,
        tagline="عناية تبدأ من أول زيارة",
        color="#B0367A",
        organization="مجموعة الحي التجارية",
        joined_on="2026-02-08",
        program=ProgramSpec(
            type=P.TYPE_POINTS,
            name="نقاط اللمسة",
            earn_rate=Decimal("2"),
            min_invoice=Decimal("80"),
            expiry_months=12,
            welcome_bonus=150,
            rewards=(
                RewardSpec("جلسة عناية بالشعر", Decimal("900"), Decimal("120")),
                RewardSpec("خصم ٤٠ جنيهًا", Decimal("400"), Decimal("40")),
            ),
        ),
        branches=(
            BranchSpec("مصر الجديدة", "القاهرة", "CAI", 30.0890, 31.3300, "شارع الحجاز"),
            BranchSpec("المهندسين", "الجيزة", "GIZ", 30.0600, 31.2050, "شارع شهاب"),
            BranchSpec("سموحة", "الإسكندرية", "ALX", 31.2160, 29.9480, "شارع مصطفى كامل"),
            BranchSpec("طنطا", "طنطا", "GHR", 30.7900, 31.0050, "شارع سعيد"),
            BranchSpec("المنصورة", "المنصورة", "DKH", 31.0450, 31.3820, "شارع المشاية"),
        ),
    ),
    BrandSpec(
        slug="nadi-el-liaqa",
        name="نادي اللياقة",
        category=SPORTS,
        tagline="اشتراك واحد وكل الفروع مفتوحة لك",
        color="#2D6CDF",
        organization="شركة اللياقة الرياضية",
        joined_on="2026-01-05",
        program=ProgramSpec(
            type=P.TYPE_VISITS,
            name="سجل الحضور",
            earn_rate=Decimal("1"),
            min_invoice=Decimal("0"),
            expiry_months=3,
            max_per_day=Decimal("1"),
            rewards=(
                RewardSpec("جلسة مدرب خاص", Decimal("12"), Decimal("150")),
                RewardSpec("أسبوع مجاني", Decimal("24"), Decimal("200")),
            ),
        ),
        branches=(
            BranchSpec("التجمع الخامس", "القاهرة", "CAI", 30.0200, 31.4700, "شارع التسعين"),
            BranchSpec("مدينة نصر", "القاهرة", "CAI", 30.0560, 31.3380, "شارع الطيران"),
            BranchSpec("٦ أكتوبر", "٦ أكتوبر", "GIZ", 29.9400, 30.9300, "الحي المتميز"),
            BranchSpec("سيدي جابر", "الإسكندرية", "ALX", 31.2231, 29.9469, "شارع أبو قير"),
            BranchSpec("الإسماعيلية", "الإسماعيلية", "ISM", 30.6000, 32.2750, "حي الشيخ زايد"),
        ),
    ),
    BrandSpec(
        slug="khotwa-sport",
        name="خطوة سبورت",
        category=FASHION,
        tagline="أحذية ولبس رياضي لكل خطوة",
        color="#E0602A",
        organization="شركة اللياقة الرياضية",
        joined_on="2026-01-05",
        program=ProgramSpec(
            type=P.TYPE_POINTS,
            name="نقاط الخطوة",
            earn_rate=Decimal("1"),
            min_invoice=Decimal("200"),
            expiry_months=12,
            rewards=(
                RewardSpec("خصم ١٠٠ جنيه", Decimal("1000"), Decimal("100")),
                RewardSpec("جوارب رياضية", Decimal("300"), Decimal("35")),
            ),
        ),
        branches=(
            BranchSpec("وسط البلد", "القاهرة", "CAI", 30.0480, 31.2440, "شارع طلعت حرب"),
            BranchSpec("مدينة نصر", "القاهرة", "CAI", 30.0650, 31.3460, "سيتي سنتر"),
            BranchSpec("المهندسين", "الجيزة", "GIZ", 30.0560, 31.2030, "شارع جامعة الدول"),
            BranchSpec("محطة الرمل", "الإسكندرية", "ALX", 31.2010, 29.9030, "شارع سعد زغلول"),
            BranchSpec("الزقازيق", "الزقازيق", "SHR", 30.5900, 31.5050, "شارع القومية"),
            BranchSpec("أسيوط", "أسيوط", "AST", 27.1850, 31.1880, "شارع الجيش"),
        ),
    ),
    BrandSpec(
        slug="el-mohandes-tech",
        name="المهندس تك",
        category=ELECTRONICS,
        tagline="أجهزة أصلية وضمان معتمد",
        color="#3B3F8C",
        organization="مجموعة المهندس للتجارة",
        joined_on="2025-11-22",
        program=ProgramSpec(
            type=P.TYPE_CASHBACK,
            name="استرداد المهندس",
            earn_rate=Decimal("0.02"),
            min_invoice=Decimal("500"),
            expiry_months=12,
            max_per_day=Decimal("500"),
            rewards=(
                RewardSpec(
                    "خصم من الرصيد", Decimal("100"), Decimal("100"), "يُخصم من فاتورتك القادمة"
                ),
            ),
        ),
        branches=(
            BranchSpec("وسط البلد", "القاهرة", "CAI", 30.0470, 31.2420, "شارع عبد العزيز", 2),
            BranchSpec("مصر الجديدة", "القاهرة", "CAI", 30.0860, 31.3280, "شارع الميرغني"),
            BranchSpec("الدقي", "الجيزة", "GIZ", 30.0400, 31.2100, "شارع التحرير"),
            BranchSpec("سموحة", "الإسكندرية", "ALX", 31.2120, 29.9420, "شارع فوزي معاذ"),
            BranchSpec("المنصورة", "المنصورة", "DKH", 31.0430, 31.3800, "شارع الترعة"),
            BranchSpec("طنطا", "طنطا", "GHR", 30.7880, 31.0020, "شارع الجيش"),
        ),
    ),
    BrandSpec(
        slug="roknet-el-ketab",
        name="ركن الكتاب",
        category=BOOKS,
        tagline="كتب وقرطاسية ومساحة للقراءة",
        color="#5C4B9B",
        organization="مجموعة المهندس للتجارة",
        joined_on="2026-03-01",
        program=ProgramSpec(
            type=P.TYPE_POINTS,
            name="نقاط القارئ",
            earn_rate=Decimal("3"),
            min_invoice=Decimal("50"),
            expiry_months=24,
            welcome_bonus=100,
            rewards=(
                RewardSpec("كتاب من ركن العروض", Decimal("900"), Decimal("85")),
                RewardSpec("خصم ٣٠ جنيهًا", Decimal("300"), Decimal("30")),
            ),
        ),
        branches=(
            BranchSpec("الزمالك", "القاهرة", "CAI", 30.0600, 31.2210, "شارع البرازيل"),
            BranchSpec("المعادي", "القاهرة", "CAI", 29.9620, 31.2560, "شارع ٢٣٣"),
            BranchSpec("المهندسين", "الجيزة", "GIZ", 30.0590, 31.2010, "شارع لبنان"),
            BranchSpec("سيدي جابر", "الإسكندرية", "ALX", 31.2220, 29.9450, "شارع الإسكندر الأكبر"),
            BranchSpec("الأقصر", "الأقصر", "LUX", 25.6900, 32.6420, "شارع المحطة"),
        ),
    ),
    BrandSpec(
        slug="zahrat-el-ward",
        name="زهرة الورد",
        category=GIFTS,
        tagline="هدية جاهزة في أقل من ربع ساعة",
        color="#C2185B",
        organization="شركة زهرة للهدايا",
        joined_on="2026-02-18",
        # هدايا لا نقاط: المشتري هنا يشتري لغيره في مناسبة، والعلاقة
        # بالمتجر موسمية. جدول هدايا صريح يُقرأ في ثانية أنسب من
        # رصيد يتراكم بين مناسبتين متباعدتين.
        program=ProgramSpec(
            type=P.TYPE_GIFTS,
            name="هدايا الورد",
            earn_rate=Decimal("1"),
            min_invoice=Decimal("120"),
            expiry_months=12,
            rewards=(
                RewardSpec("باقة ورد صغيرة", Decimal("5"), Decimal("90")),
                RewardSpec("كارت معايدة مطبوع", Decimal("2"), Decimal("15")),
            ),
        ),
        branches=(
            BranchSpec("مصر الجديدة", "القاهرة", "CAI", 30.0880, 31.3240, "شارع بغداد"),
            BranchSpec("التجمع الخامس", "القاهرة", "CAI", 30.0150, 31.4850, "الحي الثاني"),
            BranchSpec("الدقي", "الجيزة", "GIZ", 30.0370, 31.2110, "شارع مصدق"),
            BranchSpec("سموحة", "الإسكندرية", "ALX", 31.2150, 29.9460, "شارع كمال الدين صلاح"),
        ),
    ),
    BrandSpec(
        slug="malabes-el-osra",
        name="ملابس الأسرة",
        category=FASHION,
        tagline="لبس البيت كله بسعر واحد",
        color="#8A6D3B",
        organization="شركة زهرة للهدايا",
        joined_on="2026-03-14",
        program=ProgramSpec(
            type=P.TYPE_POINTS,
            name="نقاط الأسرة",
            earn_rate=Decimal("1"),
            min_invoice=Decimal("150"),
            expiry_months=12,
            welcome_bonus=200,
            rewards=(
                RewardSpec("خصم ٥٠ جنيهًا", Decimal("500"), Decimal("50")),
                RewardSpec("قطعة أطفال", Decimal("1100"), Decimal("110")),
            ),
        ),
        branches=(
            BranchSpec("شبرا الخيمة", "شبرا الخيمة", "QLY", 30.1300, 31.2450, "شارع الترعة"),
            BranchSpec("فيصل", "الجيزة", "GIZ", 30.0080, 31.1680, "شارع فيصل"),
            BranchSpec("المحلة الكبرى", "المحلة الكبرى", "GHR", 30.9680, 31.1650, "شارع ٢٣ يوليو"),
            BranchSpec("دمنهور", "دمنهور", "BHR", 31.0360, 30.4700, "شارع عبد السلام الشاذلي"),
            BranchSpec("سوهاج", "سوهاج", "SHG", 26.5620, 31.6980, "شارع النيل"),
            BranchSpec("المنيا", "المنيا", "MNY", 28.1120, 30.7530, "شارع الجمهورية"),
            BranchSpec("العريش", "العريش", "NSI", 31.1249, 33.7984, "شارع ٢٣ يوليو"),
        ),
    ),
    BrandSpec(
        slug="shatt-resorts",
        name="شط الريّان",
        category=CAFE,
        tagline="كافيه ومطعم على البحر",
        color="#0F8F9E",
        organization="شركة سواحل للمأكولات البحرية",
        joined_on="2026-04-02",
        program=ProgramSpec(
            type=P.TYPE_STAMPS,
            name="ختم الشط",
            earn_rate=Decimal("1"),
            min_invoice=Decimal("80"),
            expiry_months=12,
            rewards=(
                RewardSpec("مشروب مجاني", Decimal("6"), Decimal("45")),
                RewardSpec("وجبة إفطار", Decimal("10"), Decimal("120")),
            ),
        ),
        branches=(
            BranchSpec("الجونة", "الجونة", "RSS", 27.3950, 33.6780, "الميدان الرئيسي"),
            BranchSpec("شرم الشيخ", "شرم الشيخ", "SSI", 27.9158, 34.3300, "خليج نعمة"),
            BranchSpec("دهب", "دهب", "SSI", 28.5091, 34.5136, "الممشى"),
            BranchSpec("مرسى علم", "مرسى علم", "RSS", 25.0760, 34.8880, "طريق الكورنيش"),
            BranchSpec("مرسى مطروح", "مرسى مطروح", "MAT", 31.3520, 27.2400, "شاطئ الغرام"),
            BranchSpec("الخارجة", "الخارجة", "WAD", 25.4514, 30.5467, "شارع الجمهورية"),
        ),
    ),
)


def branch_count() -> int:
    return sum(len(brand.branches) for brand in NETWORK)


def governorate_codes() -> set[str]:
    return {branch.governorate for brand in NETWORK for branch in brand.branches}
