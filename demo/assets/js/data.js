/* ولائي — بيانات تجريبية (Mock Data) لعرض الديمو */
(function (g) {

  /* ---------- نماذج الولاء الستة ---------- */
  var MODELS = [
    { id:'points',  name:'النقاط',    icon:'star',  color:'v', desc:'نقطة مقابل كل مبلغ يُنفق، تُستبدل بمكافآت.' },
    { id:'stamps',  name:'الأختام',   icon:'stamp', color:'g', desc:'ختم لكل زيارة، وعند اكتمال البطاقة مكافأة.' },
    { id:'visits',  name:'الزيارات',  icon:'calendar', color:'b', desc:'مكافأة عند بلوغ عدد زيارات محدد.' },
    { id:'cashback',name:'الكاش باك', icon:'cash',  color:'o', desc:'نسبة من قيمة الفاتورة تعود كرصيد.' },
    { id:'rewards', name:'المكافآت',  icon:'gift',  color:'v', desc:'مكافآت مباشرة على سلوك محدد.' },
    { id:'gifts',   name:'الهدايا',   icon:'heart', color:'r', desc:'هدايا المناسبات وأعياد الميلاد.' }
  ];

  /* ---------- بطاقات العميل ---------- */
  var CARDS = [
    { id:1, store:'كافيه بن وسط', cat:'كافيه', logo:'ب', tone:'g', model:'stamps',
      progress:7, target:10, unit:'ختم', reward:'قهوة مجانية', dist:'٤٠٠ م',
      expires:'٢٠٢٧/٠٢/١٤', joined:'منذ ٤ أشهر', visits:19, saved:340,
      color:'linear-gradient(135deg,#0F7A3D,#16A34A)' },
    { id:2, store:'مخبز الحصاد', cat:'مخبوزات', logo:'ح', tone:'o', model:'points',
      progress:820, target:1000, unit:'نقطة', reward:'خصم ٥٠ ج', dist:'١.٢ كم',
      expires:'٢٠٢٧/٠٥/٠١', joined:'منذ شهرين', visits:11, saved:190,
      color:'linear-gradient(135deg,#C2410C,#F97316)' },
    { id:3, store:'صالون رُقي', cat:'تجميل', logo:'ر', tone:'v', model:'visits',
      progress:3, target:6, unit:'زيارة', reward:'جلسة مجانية', dist:'٢.٤ كم',
      expires:'٢٠٢٧/٠١/٣٠', joined:'منذ ٦ أسابيع', visits:3, saved:0,
      color:'linear-gradient(135deg,#3A1078,#6D3BD6)' },
    { id:4, store:'وش النضافة — غسيل سيارات', cat:'خدمات', logo:'و', tone:'b', model:'cashback',
      progress:64, target:100, unit:'ج رصيد', reward:'غسلة مجانية', dist:'٣.١ كم',
      expires:'٢٠٢٧/٠٣/٢٢', joined:'منذ شهر', visits:5, saved:64,
      color:'linear-gradient(135deg,#1E40AF,#3B82F6)' }
  ];

  /* ---------- سجل نشاط العميل ---------- */
  var ACTIVITY = [
    { icon:'plus',   tone:'g', title:'ختم جديد — كافيه بن وسط',   sub:'فاتورة ٦٥ ج · اليوم ١٠:٤٢ ص', val:'+١ ختم' },
    { icon:'plus',   tone:'v', title:'نقاط — مخبز الحصاد',        sub:'فاتورة ١٢٠ ج · أمس ٦:١٥ م',  val:'+١٢٠' },
    { icon:'gift',   tone:'o', title:'استبدال — قهوة مجانية',      sub:'كافيه بن وسط · منذ ٤ أيام',   val:'−١٠ أختام' },
    { icon:'plus',   tone:'b', title:'كاش باك — وش النضافة',      sub:'فاتورة ٨٠ ج · منذ ٥ أيام',    val:'+٨ ج' },
    { icon:'star',   tone:'v', title:'انضممت إلى صالون رُقي',      sub:'منذ ٦ أسابيع',                val:'ترحيب +٥٠' }
  ];

  /* ---------- المكافآت المتاحة ---------- */
  var REWARDS = [
    { id:1, store:'كافيه بن وسط', title:'قهوة مجانية',        cost:'١٠ أختام', ready:false, need:'باقي ٣ أختام', tone:'g', icon:'gift' },
    { id:2, store:'كافيه بن وسط', title:'خصم ٢٥٪ على الحلويات', cost:'٥ أختام',  ready:true,  need:'',           tone:'g', icon:'ticket' },
    { id:3, store:'مخبز الحصاد',  title:'خصم ٥٠ جنيه',        cost:'١٠٠٠ نقطة', ready:false, need:'باقي ١٨٠ نقطة', tone:'o', icon:'ticket' },
    { id:4, store:'مخبز الحصاد',  title:'عبوة كرواسون',        cost:'٦٠٠ نقطة',  ready:true,  need:'',           tone:'o', icon:'gift' },
    { id:5, store:'وش النضافة',   title:'تلميع مجاني',         cost:'٥٠ ج رصيد', ready:true,  need:'',           tone:'b', icon:'zap' },
    { id:6, store:'صالون رُقي',   title:'جلسة عناية مجانية',   cost:'٦ زيارات',  ready:false, need:'باقي ٣ زيارات', tone:'v', icon:'heart' }
  ];

  /* ---------- متاجر للاكتشاف ---------- */
  var DISCOVER = [
    { name:'مطعم الركن الشامي', cat:'مأكولات', dist:'٦٥٠ م', logo:'ش', tone:'o', offer:'٢٠٠ نقطة ترحيبية' },
    { name:'صيدلية الشفاء',     cat:'صيدلية', dist:'٩٠٠ م', logo:'ص', tone:'g', offer:'كاش باك ٣٪' },
    { name:'ملابس أوريجن',      cat:'أزياء',  dist:'١.٥ كم', logo:'أ', tone:'v', offer:'خصم ١٠٪ لأول عملية' },
    { name:'جيم بلس',           cat:'رياضة',  dist:'٢.٠ كم', logo:'ج', tone:'b', offer:'أسبوع مجاني' }
  ];

  /* ---------- مؤشرات لوحة التاجر ---------- */
  var KPIS = [
    { k:'عملاء جدد هذا الشهر',  v:'١٤٢', d:'+١٨٪', up:true,  icon:'users',  tone:'v', sub:'مقابل ١٢٠ الشهر الماضي' },
    { k:'العملاء العائدون',      v:'٦٨٪', d:'+٦٪',  up:true,  icon:'refresh',tone:'g', sub:'من إجمالي الزيارات' },
    { k:'معدل تكرار الشراء',     v:'٢.٤', d:'+١٥٪', up:true,  icon:'trend',  tone:'b', sub:'زيارة/عميل شهريًا' },
    { k:'مكافآت مُستبدلة',       v:'٨٦',  d:'٣٤٪',  up:true,  icon:'gift',   tone:'o', sub:'معدل استبدال صحي' },
    { k:'الالتزام القائم',       v:'٤,٣٢٠ ج', d:'−٨٪', up:false, icon:'wallet', tone:'a', sub:'قيمة النقاط غير المستبدلة' },
    { k:'عمليات تحتاج مراجعة',   v:'٣',   d:'',     up:false, icon:'shield', tone:'r', sub:'كشف شذوذ آلي' }
  ];

  /* ---------- عملاء التاجر ---------- */
  var CUSTOMERS = [
    { n:'أحمد سيد',    p:'٠١٠٠٢٢٣٣٤٤١', seg:'VIP',        visits:24, last:'اليوم',       bal:'٨٤٠ نقطة', spend:'٣,٢٥٠ ج', tone:'g' },
    { n:'منى عبد الله', p:'٠١١٢٣٤٥٦٧٨٩', seg:'عائد',       visits:11, last:'أمس',         bal:'٣٢٠ نقطة', spend:'١,٤٠٠ ج', tone:'v' },
    { n:'كريم فؤاد',   p:'٠١٢٩٨٧٦٥٤٣٢', seg:'معرّض للفقدان', visits:8,  last:'منذ ٣٨ يومًا', bal:'٦١٠ نقطة', spend:'٢,١٠٠ ج', tone:'r' },
    { n:'سارة محمود',  p:'٠١٠٥٥٦٦٧٧٨٨', seg:'جديد',        visits:2,  last:'منذ ٤ أيام',  bal:'١٤٠ نقطة', spend:'٣٢٠ ج',   tone:'b' },
    { n:'يوسف حسن',    p:'٠١٢٤٤٣٣٢٢١١', seg:'عائد',        visits:15, last:'منذ يومين',   bal:'٩٥٠ نقطة', spend:'٢,٨٠٠ ج', tone:'v' },
    { n:'نورهان علي',  p:'٠١١٧٧٨٨٩٩٠٠', seg:'VIP',         visits:31, last:'اليوم',       bal:'١,٤٢٠ نقطة', spend:'٥,١٠٠ ج', tone:'g' },
    { n:'محمد رضا',    p:'٠١٠٣٣٤٤٥٥٦٦', seg:'معرّض للفقدان', visits:6,  last:'منذ ٤٥ يومًا', bal:'٢٨٠ نقطة', spend:'٩٤٠ ج',   tone:'r' },
    { n:'هبة إبراهيم', p:'٠١٢٢٢٣٣٤٤٥٥', seg:'جديد',        visits:1,  last:'منذ يوم',     bal:'٥٠ نقطة',  spend:'١١٠ ج',   tone:'b' }
  ];

  /* ---------- أحدث العمليات ---------- */
  var TXNS = [
    { t:'١٠:٤٢ ص', c:'أحمد سيد',   b:'الفرع الرئيسي', cash:'محمود',  amt:'٦٥ ج',  pts:'+٦٥',  st:'ok' },
    { t:'١٠:٣٦ ص', c:'نورهان علي', b:'الفرع الرئيسي', cash:'محمود',  amt:'١٤٠ ج', pts:'+١٤٠', st:'ok' },
    { t:'١٠:٢٠ ص', c:'زائر جديد',  b:'فرع المعادي',  cash:'سمر',    amt:'٤٥ ج',  pts:'+٤٥',  st:'new' },
    { t:'٠٩:٥٨ ص', c:'كريم فؤاد',  b:'الفرع الرئيسي', cash:'محمود',  amt:'٢٢٠ ج', pts:'استبدال', st:'redeem' },
    { t:'٠٩:٤١ ص', c:'—',          b:'فرع المعادي',  cash:'سمر',    amt:'٩٥ ج',  pts:'+٩٥',  st:'flag' }
  ];

  /* ---------- عمليات تحتاج مراجعة (كشف الاحتيال) ---------- */
  var FLAGS = [
    { r:'نفس رقم الهاتف تكرر ٧ مرات في ٤٠ دقيقة', b:'فرع المعادي', cash:'سمر',   time:'اليوم ٠٩:٤١', sev:'عالية' },
    { r:'منح نقاط خارج ساعات العمل الرسمية',       b:'الفرع الرئيسي', cash:'محمود', time:'أمس ٢:١٤ ص', sev:'متوسطة' },
    { r:'قيمة فاتورة أعلى من المتوسط بـ ٨ أضعاف',  b:'فرع المعادي', cash:'سمر',   time:'منذ يومين',  sev:'منخفضة' }
  ];

  /* ---------- الفروع والكاشيرين ---------- */
  var BRANCHES = [
    { n:'الفرع الرئيسي — وسط البلد', staff:4, txn:'٨٤٢', act:true,
      cashiers:[{n:'محمود سعيد',r:'كاشير أول',t:'٣١٢'},{n:'إيمان طارق',r:'كاشير',t:'٢٠٤'}] },
    { n:'فرع المعادي', staff:3, txn:'٥١٦', act:true,
      cashiers:[{n:'سمر عادل',r:'كاشير',t:'٢٦١'},{n:'خالد نبيل',r:'كاشير',t:'١٤٨'}] },
    { n:'فرع مدينة نصر — قيد التجهيز', staff:0, txn:'٠', act:false, cashiers:[] }
  ];

  /* ---------- الحملات ---------- */
  var CAMPAIGNS = [
    { n:'استرجاع العملاء المعرّضين للفقدان', seg:'معرّض للفقدان', ch:'واتساب', sent:'٤٨', open:'٧٩٪', conv:'٢٢٪', st:'مكتملة', cost:'٢١ ج' },
    { n:'عرض نهاية الأسبوع',                seg:'الكل',        ch:'إشعار',  sent:'٦١٢', open:'٤١٪', conv:'١٤٪', st:'مكتملة', cost:'٠ ج' },
    { n:'تذكير: نقاطك تنتهي قريبًا',         seg:'رصيد > ٥٠٠',  ch:'واتساب', sent:'٩٤',  open:'٨٣٪', conv:'٣١٪', st:'جارية',  cost:'٤١ ج' }
  ];

  /* ---------- بيانات الرسوم البيانية ---------- */
  var CHART_VISITS = [42,55,48,66,72,61,88,79,95,86,104,118];
  var CHART_LABELS = ['يناير','فبراير','مارس','أبريل','مايو','يونيو','يوليو','أغسطس','سبتمبر','أكتوبر','نوفمبر','ديسمبر'];
  var CHART_NEW    = [30,34,28,40,44,36,52,46,58,50,62,71];

  /* ---------- الباقات ---------- */
  var PLANS = [
    { id:'free', n:'مجاني', price:'٠', cur:'', limits:['٢٠٠ عميل نشط','فرع واحد','نموذج ولاء واحد','تقارير ٣٠ يومًا','بدون حملات'], cta:'الحالية', active:false },
    { id:'starter', n:'Starter', price:'١,٢٥٠', cur:'ج/شهر', limits:['١,٥٠٠ عميل','فرعان','كل نماذج الولاء','تقارير كاملة','دعم بالبريد'], cta:'ترقية', active:true },
    { id:'growth', n:'Growth', price:'٣,٠٠٠', cur:'ج/شهر', limits:['١٠,٠٠٠ عميل','٥ فروع','حملات + تصدير','تحليلات متقدمة','دعم أولوية'], cta:'ترقية', active:false, pop:true },
    { id:'chain', n:'Chain', price:'٧,٥٠٠', cur:'ج/شهر+', limits:['فروع غير محدودة','تكامل POS','واجهات API','مدير حساب مخصص','اتفاقية مستوى خدمة'], cta:'تواصل معنا', active:false }
  ];

  /* ---------- لوحة الإدارة ---------- */
  var ADMIN_KPIS = [
    { k:'الإيراد الشهري المتكرر', v:'١٨٤,٢٠٠ ج', d:'+١٤٪', icon:'cash',  tone:'g' },
    { k:'متاجر مفعّلة',           v:'٣١٢',        d:'+٢٧',  icon:'store', tone:'v' },
    { k:'عملاء نهائيون',          v:'٨٤,٦٣٠',     d:'+٥,١٢٠', icon:'users', tone:'b' },
    { k:'عمليات هذا الشهر',       v:'٢١٤,٨٨٠',    d:'+٩٪',  icon:'zap',   tone:'o' },
    { k:'تحويل مجاني ← مدفوع',   v:'٩.٤٪',       d:'+١.٢٪', icon:'trend', tone:'v' },
    { k:'انسحاب التجار (شهري)',   v:'٢.١٪',       d:'−٠.٤٪', icon:'warn',  tone:'r' }
  ];

  var ADMIN_STORES = [
    { n:'كافيه بن وسط',  cat:'كافيه',   plan:'Growth',  cust:'١,٢٤٠', st:'نشط',        city:'القاهرة', tone:'g' },
    { n:'مخبز الحصاد',   cat:'مخبوزات', plan:'Starter', cust:'٨٦٠',   st:'نشط',        city:'الجيزة',  tone:'o' },
    { n:'صالون رُقي',    cat:'تجميل',   plan:'مجاني',   cust:'١٩٠',   st:'نشط',        city:'القاهرة', tone:'v' },
    { n:'وش النضافة',    cat:'خدمات',   plan:'Starter', cust:'٤١٠',   st:'نشط',        city:'القاهرة', tone:'b' },
    { n:'مطعم الركن',    cat:'مأكولات', plan:'Growth',  cust:'٢,٠٥٠', st:'نشط',        city:'الإسكندرية', tone:'o' },
    { n:'ملابس أوريجن',  cat:'أزياء',   plan:'مجاني',   cust:'٧٠',    st:'قيد المراجعة', city:'القاهرة', tone:'v' },
    { n:'جيم بلس',       cat:'رياضة',   plan:'Chain',   cust:'٣,٦٢٠', st:'نشط',        city:'القاهرة', tone:'b' },
    { n:'صيدلية الشفاء', cat:'صيدلية',  plan:'Starter', cust:'٩٤٠',   st:'موقوف',      city:'الجيزة',  tone:'g' }
  ];

  var PLATFORM_KPIS = [
    { k:'معدل تفعيل التاجر',     v:'٦٤٪',  goal:'الهدف > ٦٠٪',  ok:true },
    { k:'احتفاظ التاجر بعد ٣ شهور', v:'٨٣٪',  goal:'الهدف > ٨٠٪',  ok:true },
    { k:'عملاء جدد لكل متجر/شهر', v:'١١٨',  goal:'الهدف > ١٠٠',  ok:true },
    { k:'ارتفاع تكرار الشراء',    v:'+١٧٪', goal:'الهدف > ١٥٪',  ok:true },
    { k:'معدل استبدال المكافآت',  v:'٣٤٪',  goal:'النطاق ٢٥–٤٥٪', ok:true },
    { k:'استرداد تكلفة الاستحواذ', v:'٣.٨ شهر', goal:'الهدف < ٣ شهور', ok:false },
    { k:'نمو الإيراد الشهري',     v:'+١٤٪', goal:'الهدف > ١٢٪',  ok:true },
    { k:'تكلفة متغيرة/عميل نشط',  v:'٠.٠٣ $', goal:'الهدف < ٠.٠٥ $', ok:true }
  ];

  g.DATA = {
    MODELS:MODELS, CARDS:CARDS, ACTIVITY:ACTIVITY, REWARDS:REWARDS, DISCOVER:DISCOVER,
    KPIS:KPIS, CUSTOMERS:CUSTOMERS, TXNS:TXNS, FLAGS:FLAGS, BRANCHES:BRANCHES,
    CAMPAIGNS:CAMPAIGNS, CHART_VISITS:CHART_VISITS, CHART_LABELS:CHART_LABELS, CHART_NEW:CHART_NEW,
    PLANS:PLANS, ADMIN_KPIS:ADMIN_KPIS, ADMIN_STORES:ADMIN_STORES, PLATFORM_KPIS:PLATFORM_KPIS
  };
})(window);
