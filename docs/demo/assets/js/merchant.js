/* ولائي — لوحة تحكم صاحب المتجر */
(function (g) {
  var D = DATA, $ = UI.$, root, cur = 'dash';

  var NAV = [
    { g:'التشغيل اليومي' },
    { id:'dash',    ic:'chart',  l:'لوحة المعلومات' },
    { id:'pos',     ic:'qr',     l:'وضع الكاشير' },
    { id:'customers', ic:'users', l:'العملاء' },
    { g:'برنامج الولاء' },
    { id:'program', ic:'star',   l:'إعداد البرنامج' },
    { id:'rewards', ic:'gift',   l:'المكافآت' },
    { id:'campaigns', ic:'send', l:'الحملات' },
    { g:'التحليل والحوكمة' },
    { id:'reports', ic:'trend',  l:'التقارير' },
    { id:'fraud',   ic:'shield', l:'المراجعة والاحتيال', badge:'٣' },
    { id:'branches',ic:'branch', l:'الفروع والكاشيرين' },
    { g:'الحساب' },
    { id:'billing', ic:'wallet', l:'الاشتراك والفواتير' },
    { id:'settings',ic:'cog',    l:'الإعدادات' }
  ];
  var TITLES = {
    dash:['لوحة المعلومات','نظرة سريعة على أداء برنامج الولاء'],
    pos:['وضع الكاشير','الشاشة اللي بتشتغل عند نقطة البيع'],
    customers:['العملاء','قاعدة عملائك وشرائحهم'],
    program:['إعداد برنامج الولاء','اختر النموذج واضبط قواعده'],
    rewards:['المكافآت','ما الذي يحصل عليه عميلك'],
    campaigns:['الحملات','تواصل مع شرائح محددة بتكلفة واضحة'],
    reports:['التقارير','أثر برنامج الولاء على نشاطك'],
    fraud:['المراجعة والاحتيال','ضوابط تحمي بياناتك وثقتك'],
    branches:['الفروع والكاشيرين','مؤسسة ← علامة ← فرع ← كاشير'],
    billing:['الاشتراك والفواتير','باقتك واستهلاكك'],
    settings:['الإعدادات','بيانات المتجر والخصوصية']
  };

  /* ================ مكونات ================ */
  var SPK = { 'عملاء جدد هذا الشهر':['newCust','#4B1E9E'], 'العملاء العائدون':['returning','#16A34A'],
              'معدل تكرار الشراء':['repeat','#2563EB'], 'مكافآت مُستبدلة':['redeem','#F97316'],
              'الالتزام القائم':['liability','#CA8A04'], 'عمليات تحتاج مراجعة':['flags','#DC2626'] };

  function kpi(k) {
    var sp = SPK[k.k];
    return '<div class="kpi" data-anim><div class="row between" style="align-items:flex-start">' +
      '<div class="grow"><div class="kt">' + k.k + '</div><div class="kv num">' + k.v + '</div>' +
      '<div class="ks">' + (k.sub || '') + '</div></div>' +
      '<div class="ibox ' + k.tone + '">' + ICO(k.icon) + '</div></div>' +
      (sp && D.SPARK[sp[0]] ? '<div class="spk">' + UI.spark(D.SPARK[sp[0]], { color: sp[1], h: 28 }) + '</div>' : '') +
      (k.d ? '<div class="row between mt-1"><span class="delta ' + (k.up ? 'up' : 'dn') + '">' +
             (k.up ? '▲' : '▼') + ' ' + k.d + '</span>' +
             '<span class="t-xs faint w-7">آخر ٧ أيام</span></div>' : '') +
      '</div>';
  }
  function sectionHd(t, right) {
    return '<div class="card-hd"><h3>' + t + '</h3>' + (right || '') + '</div>';
  }
  function segBadge(s) {
    var m = { 'VIP':'bg-g', 'عائد':'bg-v', 'معرّض للفقدان':'bg-r', 'جديد':'bg-b' };
    return '<span class="badge ' + (m[s] || 'bg-n') + '">' + s + '</span>';
  }

  /* ================ الشاشات ================ */
  var S = {};

  /* ---------- لوحة المعلومات ---------- */
  S.dash = function () {
    return '<div class="grid g3 mb-3">' + D.KPIS.map(kpi).join('') + '</div>' +

      '<div class="grid" style="grid-template-columns:1.6fr 1fr">' +
        '<div class="card" data-anim>' + sectionHd('الزيارات خلال ١٢ شهرًا',
          '<div class="tabs"><button class="on">الزيارات</button><button onclick="UI.toast(\'عرض تجريبي\')">عملاء جدد</button></div>') +
          '<div class="card-p">' + UI.barChart(D.CHART_VISITS, D.CHART_LABELS) +
          '<div class="row between mt-3" style="border-top:1px solid var(--line-2);padding-top:14px">' +
          '<div><div class="t-xs muted w-7">إجمالي الزيارات</div><div class="t-lg w-8 num">٩١٤</div></div>' +
          '<div><div class="t-xs muted w-7">متوسط الفاتورة</div><div class="t-lg w-8 num">٨٧ ج</div></div>' +
          '<div><div class="t-xs muted w-7">أعلى شهر</div><div class="t-lg w-8">ديسمبر</div></div></div></div></div>' +

        '<div class="card" data-anim>' + sectionHd('عملاء معرّضون للفقدان',
          '<span class="badge bg-r">٢ عميل</span>') +
          '<div class="card-p">' +
          '<p class="hint mb-2">لم يعودوا خلال ضعف متوسط فترة زيارتهم المعتادة.</p>' +
          D.CUSTOMERS.filter(function (c) { return c.seg === 'معرّض للفقدان'; }).map(function (c) {
            return '<div class="li"><div class="av r" style="background:var(--red-100);color:var(--red-600)">' + c.n[0] + '</div>' +
              '<div class="grow"><div class="li-t">' + c.n + '</div><div class="li-s">آخر زيارة ' + c.last + ' · ' + c.spend + '</div></div></div>';
          }).join('') +
          '<button class="btn btn-orange btn-block mt-3" onclick="MER.go(\'campaigns\')">' + ICO('send') + ' أطلق حملة استرجاع</button>' +
          '</div></div>' +
      '</div>' +

      '<div class="card mt-3" data-anim>' + sectionHd(
        'أحدث العمليات <span class="live" style="margin-inline-start:9px"><i></i> مباشر</span>',
        '<button class="btn btn-line btn-sm" onclick="MER.go(\'pos\')">' + ICO('qr') + ' فتح وضع الكاشير</button>') +
        '<div style="overflow-x:auto"><table class="tbl"><thead><tr>' +
        '<th>الوقت</th><th>العميل</th><th>الفرع</th><th>الكاشير</th><th>الفاتورة</th><th>الأثر</th><th>الحالة</th></tr></thead><tbody id="livetbl">' +
        D.TXNS.map(function (t) {
          var st = { ok:'<span class="badge bg-g">مؤكدة</span>', new:'<span class="badge bg-b">عميل جديد</span>',
                     redeem:'<span class="badge bg-v">استبدال</span>', flag:'<span class="badge bg-r">تحتاج مراجعة</span>' };
          return '<tr><td class="num">' + t.t + '</td><td class="w-7">' + t.c + '</td><td class="muted">' + t.b + '</td>' +
            '<td class="muted">' + t.cash + '</td><td class="num w-7">' + t.amt + '</td>' +
            '<td class="num w-8 c-green">' + t.pts + '</td><td>' + st[t.st] + '</td></tr>';
        }).join('') + '</tbody></table></div></div>';
  };

  /* ---------- وضع الكاشير ---------- */
  S.pos = function () {
    return '<div class="card tint-v card-p mb-3" data-anim><div class="row-t">' +
      '<div class="ibox v" style="background:#fff">' + ICO('zap') + '</div><div class="grow">' +
      '<b>هذه هي الإجابة على سؤال «كيف تُثبَت عملية الشراء؟»</b>' +
      '<p class="t-sm muted mt-1">رمز متغيّر كل ٣٠ ثانية على شاشة الكاشير — العميل يمسحه ويُدخل قيمة الفاتورة، وأنت تؤكد. ' +
      'لا أجهزة إضافية، ولا يمكن إعادة استخدام الرمز.</p></div></div></div>' +

      '<div class="pos">' +
        '<div class="pos-qr" data-anim>' +
          '<div class="t-sm w-7" style="opacity:.75">اعرض هذا الرمز للعميل</div>' +
          '<div class="qrbox">' + UI.qr(3, 208) + '</div>' +
          '<div class="code" id="poscode">WL-2291</div>' +
          '<div class="timer"><span class="ring"></span> يتجدد خلال <b class="num" id="postimer">٢٤</b> ثانية</div>' +
          '<div class="row gap-sm mt-3" style="justify-content:center;position:relative;z-index:2">' +
          '<button class="btn btn-sm" style="background:rgba(255,255,255,.18);color:#fff" onclick="MER.newCode()">' + ICO('refresh') + ' تجديد فوري</button>' +
          '<button class="btn btn-sm" style="background:rgba(255,255,255,.18);color:#fff" onclick="MER.manual()">' + ICO('phone') + ' إدخال يدوي</button>' +
          '</div>' +
        '</div>' +

        '<div class="col" style="gap:16px">' +
          '<div class="card card-p" data-anim>' +
            '<div class="row between mb-2"><b class="t-md">مناوبة اليوم</b><span class="badge bg-g"><span class="dot" style="background:currentColor"></span> نشطة</span></div>' +
            '<div class="row"><div class="av g">م</div><div class="grow"><b class="t-sm">محمود سعيد</b>' +
            '<div class="t-xs muted w-6">كاشير أول · الفرع الرئيسي</div></div></div>' +
            '<div class="grid g2 mt-3">' +
            '<div class="card card-p center" style="box-shadow:none"><div class="t-xl w-8 num">٤١</div><div class="t-xs muted w-7">عملية اليوم</div></div>' +
            '<div class="card card-p center" style="box-shadow:none"><div class="t-xl w-8 num">٩</div><div class="t-xs muted w-7">عميل جديد</div></div></div>' +
          '</div>' +

          '<div class="card grow" data-anim>' + sectionHd('العمليات لحظيًا') +
            '<div class="card-p ticker" id="ticker">' + D.TXNS.map(txRow).join('') + '</div></div>' +
        '</div>' +
      '</div>';
  };
  function txRow(t) {
    var tone = t.st === 'flag' ? 'r' : t.st === 'redeem' ? 'v' : t.st === 'new' ? 'b' : 'g';
    return '<div class="t-row"><div class="ibox ' + tone + '">' + ICO(t.st === 'redeem' ? 'gift' : t.st === 'flag' ? 'warn' : 'check') + '</div>' +
      '<div class="grow"><b class="t-sm">' + t.c + '</b><div class="t-xs muted w-6">' + t.t + ' · ' + t.cash + ' · ' + t.b + '</div></div>' +
      '<div class="col" style="align-items:flex-end;gap:2px"><b class="t-sm num">' + t.amt + '</b>' +
      '<span class="t-xs w-8 num c-' + (tone === 'g' ? 'green' : tone === 'r' ? 'red' : 'violet') + '">' + t.pts + '</span></div></div>';
  }

  /* ---------- العملاء ---------- */
  S.customers = function () {
    var segs = ['الكل', 'VIP', 'عائد', 'جديد', 'معرّض للفقدان'];
    return '<div class="grid g4 mb-3">' +
      [{k:'إجمالي العملاء',v:'١,٢٤٠',sub:'+١٤٢ هذا الشهر',icon:'users',tone:'v',d:'+١٨٪',up:true},
       {k:'عملاء VIP',v:'٨٦',sub:'أعلى ١٠٪ إنفاقًا',icon:'star',tone:'g',d:'+٩',up:true},
       {k:'معرّضون للفقدان',v:'٤٢',sub:'يحتاجون حملة استرجاع',icon:'warn',tone:'r',d:'−٥',up:true},
       {k:'متوسط قيمة العميل',v:'١,٨٤٠ ج',sub:'خلال ١٢ شهرًا',icon:'wallet',tone:'b',d:'+٢٢٪',up:true}].map(kpi).join('') + '</div>' +

      '<div class="card" data-anim>' +
        '<div class="card-hd"><div class="row wrap gap-sm">' +
          segs.map(function (sg, i) { return '<span class="seg' + (i === 0 ? ' on' : '') +
            '" data-seg="' + sg + '" onclick="MER.seg(this)">' + sg + '</span>'; }).join('') +
        '</div>' +
        '<div class="row gap-sm"><div style="position:relative">' +
        '<input class="input" id="csearch" oninput="MER.search(this.value)" placeholder="بحث بالاسم أو الرقم…" style="padding-inline-start:38px;width:230px">' +
        '<span style="position:absolute;inset-inline-start:12px;top:10px;color:var(--faint)">' + ICO('search','',17) + '</span></div>' +
        '<button class="btn btn-line btn-sm">' + ICO('down') + ' تصدير</button></div></div>' +
        '<div style="overflow-x:auto"><table class="tbl"><thead><tr>' +
        '<th>العميل</th><th>الشريحة</th><th class="srt" onclick="MER.sort(2)">الزيارات</th><th>آخر زيارة</th>' +
        '<th>الرصيد</th><th class="srt" onclick="MER.sort(5)">إجمالي الإنفاق</th><th></th></tr></thead><tbody id="custtbl">' +
        D.CUSTOMERS.map(function (c) {
          return '<tr data-seg="' + c.seg + '" data-v="' + c.visits + '" data-s="' + c.spendN + '">' +
            '<td><div class="row"><div class="av av-sm ' + c.tone + '">' + c.n[0] + '</div>' +
            '<div><b class="t-sm">' + c.n + '</b><div class="t-xs muted num">' + c.p + '</div></div></div></td>' +
            '<td>' + segBadge(c.seg) + '</td><td class="num w-7">' + UI.ar(c.visits) + '</td>' +
            '<td class="muted">' + c.last + '</td><td class="num w-7">' + c.bal + '</td>' +
            '<td class="num w-8">' + c.spend + '</td>' +
            '<td><button class="btn btn-line btn-sm" onclick="MER.cust(\'' + c.n + '\')">' + ICO('eye') + '</button></td></tr>';
        }).join('') + '</tbody></table></div></div>';
  };

  /* ---------- إعداد البرنامج ---------- */
  S.program = function () {
    return '<div class="card card-p tint-o mb-3" data-anim><div class="row-t">' +
      '<div class="ibox o" style="background:#fff">' + ICO('layers') + '</div><div class="grow">' +
      '<b>ستة نماذج ولاء داخل نظام واحد</b>' +
      '<p class="t-sm muted mt-1">اختر النموذج المناسب لنشاطك — الكافيه يفضّل الأختام، والصيدلية النقاط، وغسيل السيارات الكاش باك. ' +
      'يمكنك تشغيل أكثر من نموذج في نفس الوقت.</p></div></div></div>' +

      '<div class="card mb-3" data-anim>' + sectionHd('ابدأ من قالب قطاعك',
        '<span class="badge bg-g">يضبط كل شيء تلقائيًا</span>') + '<div class="card-p">' +
        '<p class="hint mb-2">اختر نشاطك ويضبط النظام نموذج الولاء والقواعد والمكافآت المقترحة — ' +
        'ثم عدّل ما تشاء. لا تبدأ من صفحة بيضاء.</p>' +
        '<div class="grid g3">' + D.SECTORS.map(function (t, i) {
          return '<div class="sect' + (i === 0 ? ' on' : '') + '" onclick="MER.pickSector(this,\'' + t.id + '\')">' +
            '<div class="row"><div class="ibox ' + t.tone + '">' + ICO(t.icon) + '</div>' +
            '<div class="grow"><b class="t-sm">' + t.n + '</b>' +
            '<div class="t-xs muted w-7">' + t.model + '</div></div></div>' +
            '<div class="sr">' + t.rule + '</div>' +
            '<div class="sw">' + ICO('brain', '', 12) + ' ' + t.why + '</div></div>';
        }).join('') + '</div></div></div>' +

      '<div class="grid g3 mb-3">' + D.MODELS.map(function (m, i) {
        return '<div class="model' + (i === 1 ? ' on' : '') + '" onclick="MER.pickModel(this)" data-anim>' +
          '<div class="ibox ' + m.color + '">' + ICO(m.icon) + '</div>' +
          '<b>' + m.name + '</b><span>' + m.desc + '</span></div>';
      }).join('') + '</div>' +

      '<div class="grid" style="grid-template-columns:1.2fr 1fr">' +
        '<div class="card" data-anim>' + sectionHd('قواعد نموذج «الأختام»') + '<div class="card-p">' +
          '<div class="grid g2">' +
          '<label class="field"><span>ختم مقابل كل فاتورة أدنى من</span><input class="input num" value="٥٠ ج"></label>' +
          '<label class="field"><span>عدد الأختام للمكافأة</span><input class="input num" value="١٠"></label>' +
          '<label class="field"><span>الحد الأقصى للأختام يوميًا</span><input class="input num" value="١"><div class="hint">يمنع منح أختام متعددة لنفس العميل في نفس اليوم.</div></label>' +
          '<label class="field"><span>صلاحية الرصيد</span><select class="select"><option>٦ أشهر</option><option selected>١٢ شهرًا</option><option>بدون انتهاء</option></select>' +
          '<div class="hint">تُقلّل الالتزام المالي القائم.</div></label>' +
          '</div>' +
          '<div class="li"><div class="grow"><div class="li-t">تنبيه العميل قبل انتهاء رصيده</div>' +
          '<div class="li-s">إشعار مجاني قبل الانتهاء بشهر</div></div><div class="switch on" onclick="this.classList.toggle(\'on\')"></div></div>' +
          '<div class="li"><div class="grow"><div class="li-t">عكس الأختام تلقائيًا عند إرجاع الفاتورة</div>' +
          '<div class="li-s">يحمي حساباتك من الاختلال</div></div><div class="switch on" onclick="this.classList.toggle(\'on\')"></div></div>' +
          '<div class="li"><div class="grow"><div class="li-t">نقاط ترحيبية للعميل الجديد</div>' +
          '<div class="li-s">٥٠ نقطة عند أول تسجيل</div></div><div class="switch on" onclick="this.classList.toggle(\'on\')"></div></div>' +
          '<button class="btn btn-primary mt-3" onclick="UI.toast(\'تم حفظ إعدادات البرنامج\')">' + ICO('check') + ' حفظ التغييرات</button>' +
        '</div></div>' +

        '<div class="col" style="gap:16px">' +
          '<div class="card card-p tint-a" style="background:var(--amber-100);border-color:#F0DFA8" data-anim>' +
            '<div class="row-t"><div class="ibox a" style="background:#fff">' + ICO('wallet') + '</div><div class="grow">' +
            '<b class="t-sm">الالتزام القائم الآن</b><div class="t-2xl w-8 num mt-1">٤,٣٢٠ ج</div>' +
            '<p class="t-xs muted w-6 mt-1">القيمة النقدية للأختام والنقاط الممنوحة وغير المستبدلة. ' +
            'انخفضت ٨٪ بعد تفعيل سياسة الصلاحية.</p></div></div></div>' +

          '<div class="card" data-anim>' + sectionHd('معاينة البطاقة عند العميل') + '<div class="card-p center">' +
          '<div style="max-width:280px;margin:0 auto">' +
          '<div class="lcard" style="background:linear-gradient(135deg,#0F7A3D,#16A34A);cursor:default">' +
          '<div class="lc-top"><div class="lc-logo">ب</div><div class="grow">' +
          '<div class="lc-name">كافيه بن وسط</div><div class="lc-cat">كافيه · ٤٠٠ م</div></div></div>' +
          '<div class="lc-mid"><div><div class="lc-val num">٧</div><div class="lc-unit">من ١٠ أختام</div></div>' +
          '<div class="lc-rew">قهوة مجانية</div></div>' +
          '<div class="lc-bar"><i style="width:70%"></i></div></div></div>' +
          '<p class="hint mt-2">هكذا سيراها عميلك داخل التطبيق مباشرة.</p></div></div>' +
        '</div>' +
      '</div>';
  };

  /* ---------- المكافآت ---------- */
  S.rewards = function () {
    var rws = [
      { t:'قهوة مجانية', c:'١٠ أختام', used:'٣٤ مرة', cost:'٢٢ ج', on:true },
      { t:'خصم ٢٥٪ على الحلويات', c:'٥ أختام', used:'٥١ مرة', cost:'١٤ ج', on:true },
      { t:'كرواسون مجاني', c:'٧ أختام', used:'١٨ مرة', cost:'١٦ ج', on:true },
      { t:'خصم ٥٠ ج', c:'١٠٠٠ نقطة', used:'٩ مرات', cost:'٥٠ ج', on:false }
    ];
    return '<div class="card" data-anim>' + sectionHd('مكافآت متجرك',
      '<button class="btn btn-primary btn-sm" onclick="MER.addReward()">' + ICO('plus') + ' مكافأة جديدة</button>') +
      '<div style="overflow-x:auto"><table class="tbl"><thead><tr>' +
      '<th>المكافأة</th><th>التكلفة على العميل</th><th>مرات الاستبدال</th><th>تكلفتها عليك</th><th>الحالة</th><th></th></tr></thead><tbody>' +
      rws.map(function (r) {
        return '<tr><td><div class="row"><div class="ibox o">' + ICO('gift') + '</div><b class="t-sm">' + r.t + '</b></div></td>' +
          '<td class="num w-7">' + r.c + '</td><td class="num">' + r.used + '</td><td class="num w-7">' + r.cost + '</td>' +
          '<td>' + (r.on ? '<span class="badge bg-g">مفعّلة</span>' : '<span class="badge bg-n">موقوفة</span>') + '</td>' +
          '<td><button class="btn btn-line btn-sm">' + ICO('edit') + '</button></td></tr>';
      }).join('') + '</tbody></table></div></div>' +

      '<div class="grid g2 mt-3">' +
        '<div class="card card-p tint-g" data-anim><div class="row-t"><div class="ibox g" style="background:#fff">' + ICO('target') + '</div>' +
        '<div class="grow"><b>معدل الاستبدال ٣٤٪</b><p class="t-sm muted mt-1">داخل النطاق الصحي (٢٥–٤٥٪). ' +
        'المعدل المنخفض يعني مكافآت بعيدة المنال، والمرتفع جدًا يعني أنك تمنح أكثر من اللازم.</p></div></div></div>' +
        '<div class="card card-p tint-v" data-anim><div class="row-t"><div class="ibox v" style="background:#fff">' + ICO('brain') + '</div>' +
        '<div class="grow"><b>اقتراح تحليلي</b><p class="t-sm muted mt-1">متوسط فاتورتك ٨٧ ج وهامشك التقديري ٤٠٪. ' +
        'قيمة المكافأة المثلى بين ١٨ و ٢٤ ج — مكافأة «خصم ٥٠ ج» أعلى من الحد الموصى به.</p></div></div></div>' +
      '</div>';
  };

  /* ---------- الحملات ---------- */
  S.campaigns = function () {
    return '<div class="grid" style="grid-template-columns:1fr 380px">' +
      '<div class="card" data-anim>' + sectionHd('الحملات السابقة',
        '<button class="btn btn-primary btn-sm" onclick="MER.newCampaign()">' + ICO('plus') + ' حملة جديدة</button>') +
        '<div style="overflow-x:auto"><table class="tbl"><thead><tr>' +
        '<th>الحملة</th><th>الشريحة</th><th>القناة</th><th>أُرسلت</th><th>فتح</th><th>تحويل</th><th>التكلفة</th><th>الحالة</th></tr></thead><tbody>' +
        D.CAMPAIGNS.map(function (c) {
          return '<tr><td class="w-7">' + c.n + '</td><td>' + segBadge(c.seg) + '</td>' +
            '<td><span class="badge ' + (c.ch === 'إشعار' ? 'bg-g' : 'bg-b') + '">' + c.ch + '</span></td>' +
            '<td class="num">' + c.sent + '</td><td class="num">' + c.open + '</td>' +
            '<td class="num w-8 c-green">' + c.conv + '</td><td class="num w-7">' + c.cost + '</td>' +
            '<td>' + (c.st === 'جارية' ? '<span class="badge bg-o">جارية</span>' : '<span class="badge bg-n">مكتملة</span>') + '</td></tr>';
        }).join('') + '</tbody></table></div></div>' +

      '<div class="col" style="gap:16px">' +
        '<div class="card" data-anim>' + sectionHd('اختر القناة') + '<div class="card-p col gap-sm">' +
          '<div class="chan on" onclick="MER.pickChan(this)"><div class="row">' +
            '<div class="ibox g">' + ICO('bell') + '</div><div class="grow"><b class="t-sm">إشعار التطبيق</b>' +
            '<div class="t-xs muted w-6">أعلى وصول لمن فعّل الإشعارات</div></div>' +
            '<div class="cost c-green">مجاني</div></div></div>' +
          '<div class="chan" onclick="MER.pickChan(this)"><div class="row">' +
            '<div class="ibox b">' + ICO('whatsapp') + '</div><div class="grow"><b class="t-sm">واتساب</b>' +
            '<div class="t-xs muted w-6">أعلى معدل قراءة</div></div>' +
            '<div class="cost c-orange num">٠.٤٥ ج/رسالة</div></div></div>' +
          '<div class="chan" onclick="MER.pickChan(this)"><div class="row">' +
            '<div class="ibox o">' + ICO('phone') + '</div><div class="grow"><b class="t-sm">رسالة SMS</b>' +
            '<div class="t-xs muted w-6">ملاذ أخير — الأغلى</div></div>' +
            '<div class="cost c-red num">٠.١٥ ج/رسالة</div></div></div>' +
          '<p class="hint">نرتّب القنوات بالتكلفة تلقائيًا: الإشعار أولًا، ثم واتساب، ثم SMS لمن لم تصله الرسالة.</p>' +
        '</div></div>' +

        '<div class="card card-p" data-anim>' +
          '<div class="row between mb-2"><b class="t-md">رصيد الرسائل</b>' +
          '<button class="btn btn-ghost btn-sm" onclick="UI.toast(\'فتح صفحة الشحن\')">شحن</button></div>' +
          '<div class="row between t-sm w-7"><span>المتبقي</span><span class="num">٣٤٢ رسالة</span></div>' +
          '<div class="bar o mt-2"><i style="width:34%"></i></div>' +
          '<p class="hint mt-2">استهلكت ٦٥٨ من ١,٠٠٠ رسالة هذا الشهر. الإشعارات لا تُخصم من الرصيد.</p></div>' +
      '</div></div>';
  };

  /* ---------- التقارير ---------- */
  S.reports = function () {
    return '<div class="grid g4 mb-3">' +
      [{k:'ارتفاع تكرار الشراء',v:'+١٧٪',sub:'مقارنة بما قبل البرنامج',icon:'trend',tone:'g',d:'الهدف > ١٥٪',up:true},
       {k:'معدل تفعيل العميل',v:'٧١٪',sub:'سجّلوا وأتموا عملية',icon:'zap',tone:'v',d:'+٤٪',up:true},
       {k:'عائد البرنامج التقديري',v:'٦.٢×',sub:'مقابل تكلفة المكافآت',icon:'cash',tone:'b',d:'+٠.٨',up:true},
       {k:'متوسط الفاتورة',v:'٨٧ ج',sub:'عضو الولاء مقابل ٦٤ ج لغيره',icon:'wallet',tone:'o',d:'+٣٦٪',up:true}].map(kpi).join('') + '</div>' +

      '<div class="grid g2">' +
        '<div class="card" data-anim>' + sectionHd('العملاء الجدد شهريًا') +
        '<div class="card-p">' + UI.barChart(D.CHART_NEW, D.CHART_LABELS, { green:true }) + '</div></div>' +
        '<div class="card" data-anim>' + sectionHd('نمو قاعدة العملاء') +
        '<div class="card-p">' + UI.lineChart(D.CHART_VISITS) +
        '<div class="row between mt-3"><div><div class="t-xs muted w-7">إجمالي</div><div class="t-lg w-8 num">١,٢٤٠</div></div>' +
        '<div><div class="t-xs muted w-7">نشطون</div><div class="t-lg w-8 num">٨٤٦</div></div>' +
        '<div><div class="t-xs muted w-7">خاملون</div><div class="t-lg w-8 num">٣٩٤</div></div></div></div></div>' +
      '</div>' +

      '<div class="card mt-3" data-anim>' + sectionHd('تفصيل حسب الفرع',
        '<button class="btn btn-line btn-sm">' + ICO('down') + ' تصدير PDF</button>') +
        '<table class="tbl"><thead><tr><th>الفرع</th><th>الزيارات</th><th>عملاء جدد</th><th>الاستبدال</th><th>متوسط الفاتورة</th><th>الأداء</th></tr></thead><tbody>' +
        [['الفرع الرئيسي','٥٦٢','٨٤','٥١','٩٢ ج',78],['فرع المعادي','٣٥٢','٥٨','٣٥','٧٩ ج',61]].map(function (r) {
          return '<tr><td class="w-7">' + r[0] + '</td><td class="num">' + r[1] + '</td><td class="num">' + r[2] + '</td>' +
            '<td class="num">' + r[3] + '</td><td class="num w-7">' + r[4] + '</td>' +
            '<td style="width:170px"><div class="bar"><i style="width:' + r[5] + '%"></i></div></td></tr>';
        }).join('') + '</tbody></table></div>';
  };

  /* ---------- المراجعة والاحتيال ---------- */
  S.fraud = function () {
    return '<div class="card card-p tint-r mb-3" data-anim><div class="row-t">' +
      '<div class="ibox r" style="background:#fff">' + ICO('shield') + '</div><div class="grow">' +
      '<b>لماذا هذه الشاشة موجودة؟</b>' +
      '<p class="t-sm muted mt-1">أي نظام ولاء بلا ضوابط يُستغَل خلال أسابيع: كاشير يمنح نقاطًا لرقمه أو لأصدقائه. ' +
      'النظام يربط كل منح برقم الفاتورة وقيمتها، ويكشف الشذوذ آليًا، ويحتفظ بسجل تدقيق غير قابل للحذف.</p></div></div></div>' +

      '<div class="grid g3 mb-3">' +
      [{k:'عمليات تحتاج مراجعة',v:'٣',sub:'خلال آخر ٧ أيام',icon:'warn',tone:'r'},
       {k:'عمليات مُدقّقة',v:'٩١٤',sub:'١٠٠٪ من العمليات',icon:'checkc',tone:'g'},
       {k:'حسابات كاشير نشطة',v:'٤',sub:'لكل كاشير حساب مستقل',icon:'users',tone:'v'}].map(kpi).join('') + '</div>' +

      '<div class="card" data-anim>' + sectionHd('عمليات مرفوعة للمراجعة') +
        '<div style="overflow-x:auto"><table class="tbl"><thead><tr>' +
        '<th>سبب الرفع</th><th>الفرع</th><th>الكاشير</th><th>الوقت</th><th>الخطورة</th><th>الإجراء</th></tr></thead><tbody>' +
        D.FLAGS.map(function (f, i) {
          var m = { 'عالية':'bg-r', 'متوسطة':'bg-a', 'منخفضة':'bg-n' };
          return '<tr><td class="w-7">' + f.r + '</td><td class="muted">' + f.b + '</td><td class="muted">' + f.cash + '</td>' +
            '<td class="muted num">' + f.time + '</td><td><span class="badge ' + m[f.sev] + '">' + f.sev + '</span></td>' +
            '<td><div class="row gap-sm"><button class="btn btn-line btn-sm" onclick="MER.resolve(this,1)">' + ICO('check') + ' مقبولة</button>' +
            '<button class="btn btn-line btn-sm c-red" onclick="MER.resolve(this,0)">' + ICO('x') + ' إلغاء</button></div></td></tr>';
        }).join('') + '</tbody></table></div></div>' +

      '<div class="card mt-3" data-anim>' + sectionHd('الضوابط المفعّلة') + '<div class="card-p">' +
        [['سقف يومي للأختام لكل عميل','ختم واحد يوميًا',true],
         ['ربط المنح برقم الفاتورة وقيمتها','إلزامي',true],
         ['رفض إعادة استخدام نفس الرمز','الرمز صالح لمرة واحدة',true],
         ['تنبيه عند المنح خارج ساعات العمل','من ١٢ ص إلى ٦ ص',true],
         ['سجل تدقيق غير قابل للحذف','يُحفظ ٢٤ شهرًا',true]].map(function (r) {
          return '<div class="li"><div class="ibox g">' + ICO('lock') + '</div><div class="grow">' +
            '<div class="li-t">' + r[0] + '</div><div class="li-s">' + r[1] + '</div></div>' +
            '<div class="switch on" onclick="this.classList.toggle(\'on\')"></div></div>';
        }).join('') + '</div></div>';
  };

  /* ---------- الفروع ---------- */
  S.branches = function () {
    return '<div class="card card-p tint-v mb-3" data-anim><div class="row-t">' +
      '<div class="ibox v" style="background:#fff">' + ICO('branch') + '</div><div class="grow">' +
      '<b>تسلسل هرمي من اليوم الأول</b>' +
      '<p class="t-sm muted mt-1">مؤسسة ← علامة تجارية ← فرع ← نقطة بيع ← مستخدم. ' +
      'بناء هذا التسلسل لاحقًا يعني ترحيل بيانات مؤلمًا وإعادة كتابة الصلاحيات والتقارير.</p></div></div></div>' +

      '<div class="card" data-anim>' + sectionHd('الهيكل التنظيمي',
        '<button class="btn btn-primary btn-sm" onclick="UI.toast(\'إضافة فرع جديد\')">' + ICO('plus') + ' فرع جديد</button>') +
        '<div class="card-p"><div class="tree">' +
        '<div class="node"><div class="row"><div class="ibox v">' + ICO('layers') + '</div>' +
        '<div class="grow"><b class="t-md">شركة بن وسط للمشروبات</b>' +
        '<div class="t-xs muted w-6">مؤسسة · علامة واحدة · ٣ فروع · ٤ كاشيرين</div></div>' +
        '<span class="badge bg-v">مؤسسة</span></div>' +
        '<div class="kids">' + D.BRANCHES.map(function (b) {
          return '<div class="node"><div class="row"><div class="ibox ' + (b.act ? 'g' : 'r') + '">' + ICO('store') + '</div>' +
            '<div class="grow"><b class="t-sm">' + b.n + '</b>' +
            '<div class="t-xs muted w-6">' + UI.ar(b.staff) + ' كاشير · ' + b.txn + ' عملية</div></div>' +
            (b.act ? '<span class="badge bg-g">نشط</span>' : '<span class="badge bg-n">غير مفعّل</span>') + '</div>' +
            (b.cashiers.length ? '<div class="kids">' + b.cashiers.map(function (c) {
              return '<div class="node" style="padding:9px 13px"><div class="row"><div class="av av-sm b">' + c.n[0] + '</div>' +
                '<div class="grow"><b class="t-sm">' + c.n + '</b><div class="t-xs muted w-6">' + c.r + ' · ' + c.t + ' عملية</div></div>' +
                '<button class="btn btn-line btn-sm">' + ICO('cog') + '</button></div></div>';
            }).join('') + '</div>' : '') + '</div>';
        }).join('') + '</div></div></div></div>';
  };

  /* ---------- الاشتراك ---------- */
  S.billing = function () {
    return '<div class="grid" style="grid-template-columns:1fr 340px" >' +
      '<div class="card" data-anim>' + sectionHd('الباقات') + '<div class="card-p">' +
        '<div class="grid g4">' + D.PLANS.map(function (p) {
          return '<div class="plan' + (p.active ? ' cur' : '') + (p.pop ? ' pop' : '') + '">' +
            (p.pop ? '<div class="tag">الأكثر اختيارًا</div>' : '') +
            '<b class="t-md">' + p.n + '</b><div class="pr num">' + p.price + '</div>' +
            '<div class="t-xs muted w-7">' + (p.cur || 'للأبد') + '</div>' +
            '<ul class="mt-2">' + p.limits.map(function (l) { return '<li>' + ICO('check') + '<span>' + l + '</span></li>'; }).join('') + '</ul>' +
            '<button class="btn btn-block btn-sm mt-3 ' + (p.active ? 'btn-line' : p.pop ? 'btn-primary' : 'btn-ghost') + '" ' +
            (p.active ? 'disabled' : 'onclick="UI.toast(\'تحويل إلى صفحة الدفع\')"') + '>' +
            (p.active ? 'باقتك الحالية' : p.cta) + '</button></div>';
        }).join('') + '</div>' +
        '<div class="card card-p tint-v mt-3"><div class="row-t"><div class="ibox v" style="background:#fff">' + ICO('zap') + '</div>' +
        '<div class="grow"><b class="t-sm">إضافات اختيارية</b>' +
        '<p class="t-xs muted w-6 mt-1">تكامل نقاط البيع (+٩٠٠ ج/شهر) · رصيد رسائل إضافي · رسوم تفعيل لمرة واحدة عند الانضمام.</p></div></div></div>' +
      '</div></div>' +

      '<div class="col" style="gap:16px">' +
        '<div class="card" data-anim>' + sectionHd('استهلاكك الحالي') + '<div class="card-p">' +
          [['العملاء النشطون','٨٤٦ من ١,٥٠٠',56,''],
           ['الفروع','٢ من ٢',100,'o'],
           ['رصيد الرسائل','٣٤٢ من ١,٠٠٠',34,'o'],
           ['نماذج الولاء','٢ من ∞',20,'g']].map(function (u) {
            return '<div class="usage"><div style="width:96px"><b class="t-sm">' + u[0] + '</b></div>' +
              '<div class="bar ' + u[3] + '"><i style="width:' + u[2] + '%"></i></div>' +
              '<div class="t-xs muted w-7 num nowrap">' + u[1] + '</div></div>';
          }).join('') +
          '<div class="card card-p tint-o mt-3"><b class="t-sm">وصلت لحد الفروع</b>' +
          '<p class="t-xs muted w-6 mt-1">الترقية إلى Growth تتيح ٥ فروع وحملات وتقارير متقدمة.</p>' +
          '<button class="btn btn-orange btn-sm btn-block mt-2" onclick="UI.toast(\'ترقية الباقة\')">ترقية الآن</button></div>' +
        '</div></div>' +

        '<div class="card" data-anim>' + sectionHd('آخر الفواتير') + '<div class="card-p">' +
          [['أغسطس ٢٠٢٦','١,٢٥٠ ج','مدفوعة'],['يوليو ٢٠٢٦','١,٢٥٠ ج','مدفوعة'],['يونيو ٢٠٢٦','١,٢٥٠ ج','مدفوعة']].map(function (f) {
            return '<div class="li"><div class="ibox v">' + ICO('doc') + '</div><div class="grow">' +
              '<div class="li-t">' + f[0] + '</div><div class="li-s">' + f[1] + '</div></div>' +
              '<span class="badge bg-g">' + f[2] + '</span></div>';
          }).join('') + '</div></div>' +
      '</div></div>';
  };

  /* ---------- الإعدادات ---------- */
  S.settings = function () {
    return '<div class="grid" style="grid-template-columns:1fr 1fr">' +
      '<div class="card" data-anim>' + sectionHd('بيانات المتجر') + '<div class="card-p">' +
        '<label class="field"><span>اسم المتجر</span><input class="input" value="كافيه بن وسط"></label>' +
        '<label class="field"><span>النشاط</span><select class="select"><option selected>كافيه ومشروبات</option><option>مخبوزات</option><option>تجميل</option><option>خدمات</option></select></label>' +
        '<label class="field"><span>رقم التواصل</span><input class="input num" value="٠١٠٠٩٨٧٦٥٤٣"></label>' +
        '<label class="field"><span>العنوان</span><input class="input" value="٢٧ شارع شريف — وسط البلد، القاهرة"></label>' +
        '<button class="btn btn-primary" onclick="UI.toast(\'تم حفظ بيانات المتجر\')">حفظ</button></div></div>' +

      '<div class="col" style="gap:16px">' +
        '<div class="card" data-anim>' + sectionHd('الخصوصية وحماية البيانات') + '<div class="card-p">' +
          '<div class="card card-p tint-g mb-2"><div class="row-t"><div class="ibox g" style="background:#fff">' + ICO('shield') + '</div>' +
          '<div class="grow"><b class="t-sm">أنت «المتحكّم» وولائي «المعالِج»</b>' +
          '<p class="t-xs muted w-6 mt-1">بيانات عملائك ملكك. ولائي يعالجها نيابةً عنك بموجب عقد معالجة بيانات، ' +
          'ولا تُشارك مع أي متجر آخر.</p></div></div></div>' +
          [['موافقة صريحة عند التسجيل','مسجّلة بالتاريخ والوقت'],
           ['سياسة الاحتفاظ بالبيانات','٢٤ شهرًا من آخر نشاط'],
           ['تشفير عند النقل والتخزين','مفعّل دائمًا'],
           ['حق العميل في الحذف','ذاتي من التطبيق']].map(function (r) {
            return '<div class="li"><div class="ibox v">' + ICO('lock') + '</div><div class="grow">' +
              '<div class="li-t">' + r[0] + '</div><div class="li-s">' + r[1] + '</div></div>' + ICO('checkc','c-green',18) + '</div>';
          }).join('') +
          '<button class="btn btn-line btn-block mt-3" onclick="UI.toast(\'تحميل عقد معالجة البيانات\')">' + ICO('down') + ' تحميل عقد معالجة البيانات (DPA)</button>' +
        '</div></div>' +

        '<div class="card" data-anim>' + sectionHd('التكاملات') + '<div class="card-p">' +
          [['تكامل نقاط البيع (POS)','متاح في باقة Chain','o','قريبًا'],
           ['واجهات API','لربط أنظمتك الخاصة','b','قريبًا'],
           ['تصدير إلى Excel','متاح الآن','g','مفعّل']].map(function (r) {
            return '<div class="li"><div class="ibox ' + r[2] + '">' + ICO('code') + '</div><div class="grow">' +
              '<div class="li-t">' + r[0] + '</div><div class="li-s">' + r[1] + '</div></div>' +
              '<span class="badge ' + (r[3] === 'مفعّل' ? 'bg-g' : 'bg-n') + '">' + r[3] + '</span></div>';
          }).join('') + '</div></div>' +
      '</div></div>';
  };

  /* ================ التشغيل ================ */
  var router;
  var MER = {
    init: function () {
      root = $('#content');
      $('#nav').innerHTML = NAV.map(function (n) {
        if (n.g) return '<div class="grp-t">' + n.g + '</div>';
        return '<div class="nav-i" data-id="' + n.id + '" onclick="MER.go(\'' + n.id + '\')">' + ICO(n.ic) +
          '<span>' + n.l + '</span>' + (n.badge ? '<span class="pill num">' + n.badge + '</span>' : '') + '</div>';
      }).join('');
      router = UI.router(root, S, function (name) {
        cur = name;
        UI.$$('.nav-i').forEach(function (e) { e.classList.toggle('on', e.dataset.id === name); });
        var t = TITLES[name] || ['', ''];
        $('#pt').textContent = t[0]; $('#ps').textContent = t[1];
      });
      var h=(location.hash||'').replace('#','');
      MER.go(S[h]?h:'dash');
      MER.tick();
    },
    go: function (n) { router.go(n); if(location.hash.slice(1)!==n) location.hash=n; window.scrollTo({ top: 0, behavior: 'smooth' }); },
    tick: function () {
      var t = 24;
      setInterval(function () {
        var el = $('#postimer'); if (!el) return;
        t--; if (t < 0) { t = 30; MER.newCode(true); }
        el.textContent = UI.ar(t);
      }, 1000);
    },
    newCode: function (silent) {
      var el = $('#poscode'); if (!el) return;
      var s = 'WL-' + Math.floor(1000 + Math.random() * 8999);
      el.textContent = s;
      if (!silent) UI.toast('تم تجديد الرمز · ' + s);
    },
    manual: function () {
      UI.modal('إدخال يدوي — بديل المسح',
        '<p class="t-sm muted mb-3">لو كاميرا العميل مش شغالة، أدخل رقم موبايله وقيمة الفاتورة. ' +
        'للمبالغ فوق ٢٠٠ ج يُطلب كود تأكيد لحماية الطرفين.</p>' +
        '<label class="field"><span>رقم موبايل العميل</span><input class="input num" placeholder="٠١٠٠٠٠٠٠٠٠٠"></label>' +
        '<label class="field"><span>قيمة الفاتورة</span><input class="input num" placeholder="٠٫٠٠ ج"></label>' +
        '<label class="field"><span>رقم الفاتورة</span><input class="input num" placeholder="INV-0000"><div class="hint">إلزامي — يربط النقاط بعملية بيع حقيقية.</div></label>',
        '<button class="btn btn-line" onclick="UI.closeModal()">إلغاء</button>' +
        '<button class="btn btn-primary" onclick="UI.closeModal();UI.toast(\'تم تسجيل العملية\')">تسجيل</button>');
    },
    seg: function (el) {
      UI.$$('.seg').forEach(function (e) { e.classList.remove('on'); });
      el.classList.add('on');
      var want = el.dataset.seg;
      var n = 0;
      UI.$$('#custtbl tr').forEach(function (tr) {
        var ok = (want === 'الكل' || tr.dataset.seg === want);
        tr.style.display = ok ? '' : 'none';
        if (ok) { n++; tr.classList.add('rowin'); setTimeout(function(){tr.classList.remove('rowin');}, 620); }
      });
      UI.toast('عرض ' + UI.ar(n) + ' عميل');
    },

    search: function (q) {
      q = (q || '').trim();
      UI.$$('#custtbl tr').forEach(function (tr) {
        tr.style.display = (!q || tr.textContent.indexOf(q) > -1) ? '' : 'none';
      });
    },

    sort: function (col) {
      var th = UI.$$('#custtbl').length ? UI.$$('th.srt') : [];
      var tb = UI.$('#custtbl'); if (!tb) return;
      var key = col === 2 ? 'v' : 's';
      var asc = tb.dataset.dir !== 'asc' || tb.dataset.col !== String(col);
      tb.dataset.dir = asc ? 'asc' : 'desc'; tb.dataset.col = String(col);
      th.forEach(function (h) { h.classList.remove('asc', 'desc'); });
      var active = th[col === 2 ? 0 : 1]; if (active) active.classList.add(asc ? 'asc' : 'desc');
      var rows = UI.$$('#custtbl tr');
      rows.sort(function (a, b) {
        var x = +a.dataset[key], y = +b.dataset[key];
        return asc ? x - y : y - x;
      });
      rows.forEach(function (r, i) { tb.appendChild(r); r.classList.add('rowin'); r.style.animationDelay = (i * .03) + 's'; });
      setTimeout(function () { rows.forEach(function (r) { r.classList.remove('rowin'); r.style.animationDelay = ''; }); }, 900);
    },

    /* بث عمليات جديدة لحظيًا في لوحة المعلومات ووضع الكاشير */
    liveFeed: function () {
      var i = 0;
      setInterval(function () {
        var tb = UI.$('#livetbl'), tk = UI.$('#ticker');
        if (!tb && !tk) return;
        var x = D.LIVE_POOL[i % D.LIVE_POOL.length]; i++;
        var now = new Date();
        var t = UI.ar(('0' + ((now.getHours() % 12) || 12)).slice(-2) + ':' + ('0' + now.getMinutes()).slice(-2)) +
                (now.getHours() < 12 ? ' ص' : ' م');
        var rec = { t: t, c: x.c, b: x.b, cash: x.cash, amt: x.amt, pts: x.pts, st: x.st };

        if (tb) {
          var st = { ok:'<span class="badge bg-g">مؤكدة</span>', new:'<span class="badge bg-b">عميل جديد</span>',
                     redeem:'<span class="badge bg-v">استبدال</span>', flag:'<span class="badge bg-r">تحتاج مراجعة</span>' };
          var tr = document.createElement('tr');
          tr.className = 'rowin';
          tr.innerHTML = '<td class="num">' + rec.t + '</td><td class="w-7">' + rec.c + '</td>' +
            '<td class="muted">' + rec.b + '</td><td class="muted">' + rec.cash + '</td>' +
            '<td class="num w-7">' + rec.amt + '</td><td class="num w-8 c-green">' + rec.pts + '</td>' +
            '<td>' + st[rec.st] + '</td>';
          tb.insertBefore(tr, tb.firstChild);
          while (tb.children.length > 7) tb.removeChild(tb.lastChild);
        }
        if (tk) {
          var d = document.createElement('div');
          d.innerHTML = txRow(rec);
          var el = d.firstChild; el.classList.add('rowin');
          tk.insertBefore(el, tk.firstChild);
          while (tk.children.length > 8) tk.removeChild(tk.lastChild);
        }
      }, 6500);
    },
    pickSector: function (el, id) {
      UI.$$('.sect').forEach(function (e) { e.classList.remove('on'); });
      el.classList.add('on');
      var t = D.SECTORS.filter(function (x) { return x.id === id; })[0];
      UI.toast('تم تطبيق قالب «' + t.n + '» — نموذج ' + t.model);
    },

    pickModel: function (el) { UI.$$('.model').forEach(function (e) { e.classList.remove('on'); }); el.classList.add('on'); UI.toast('تم اختيار النموذج'); },
    pickChan: function (el) { UI.$$('.chan').forEach(function (e) { e.classList.remove('on'); }); el.classList.add('on'); },
    resolve: function (btn, ok) {
      var tr = btn.closest('tr'); tr.style.transition = '.3s'; tr.style.opacity = '.35';
      UI.toast(ok ? 'تم اعتماد العملية' : 'تم إلغاء العملية وسحب النقاط', ok ? '' : 'warn');
    },
    cust: function (n) {
      var c = D.CUSTOMERS.filter(function (x) { return x.n === n; })[0];
      UI.drawer('ملف العميل',
        '<div class="row mb-3"><div class="av av-lg ' + c.tone + '">' + c.n[0] + '</div>' +
        '<div class="grow"><b class="t-lg">' + c.n + '</b>' +
        '<div class="t-sm muted num">' + c.p + '</div></div>' + segBadge(c.seg) + '</div>' +

        '<div class="grid g3 mb-3">' +
        '<div class="card card-p center"><div class="t-lg w-8 num" data-n="' + c.visits + '">٠</div>' +
        '<div class="t-xs muted w-7">زيارة</div></div>' +
        '<div class="card card-p center"><div class="t-lg w-8 num">' + c.bal + '</div>' +
        '<div class="t-xs muted w-7">الرصيد</div></div>' +
        '<div class="card card-p center"><div class="t-lg w-8 num" data-n="' + c.spendN + '" data-suf=" ج">٠</div>' +
        '<div class="t-xs muted w-7">الإنفاق</div></div></div>' +

        '<div class="card card-p mb-3"><div class="row between mb-2">' +
        '<b class="t-sm">نشاطه خلال ٧ أسابيع</b><span class="t-xs faint w-7">زيارات</span></div>' +
        UI.spark([2,3,1,4,3,5,4], { color:'#4B1E9E', h:44 }) + '</div>' +

        '<b class="t-sm" style="display:block;margin-bottom:10px">الخط الزمني</b>' +
        '<div class="tml">' + D.CUST_TL.map(function (t) {
          return '<div class="ti ' + t.c + '"><b>' + t.t + '</b><span>' + t.s + '</span></div>';
        }).join('') + '</div>' +

        '<div class="card card-p tint-v mt-2"><b class="t-sm">ملاحظة تحليلية</b>' +
        '<p class="t-xs muted w-6 mt-1">متوسط الفترة بين زياراته ١٢ يومًا. آخر زيارة ' + c.last + '. ' +
        (c.seg === 'معرّض للفقدان'
          ? 'تجاوز ضعف فترته المعتادة — مرشّح لحملة استرجاع.'
          : 'ضمن نمطه الطبيعي.') + '</p></div>',

        '<button class="btn btn-line" onclick="UI.closeDrawer()">إغلاق</button>' +
        '<button class="btn btn-primary" onclick="UI.closeDrawer();UI.toast(\'تمت إضافته للحملة\')">' +
        ICO('send') + ' أرسل عرضًا</button>');
    },

    addReward: function () {
      UI.modal('مكافأة جديدة',
        '<label class="field"><span>اسم المكافأة</span><input class="input" placeholder="مثال: قهوة مجانية"></label>' +
        '<div class="grid g2"><label class="field"><span>التكلفة على العميل</span><input class="input num" placeholder="١٠"></label>' +
        '<label class="field"><span>الوحدة</span><select class="select"><option>أختام</option><option>نقاط</option><option>زيارات</option></select></label></div>' +
        '<label class="field"><span>تكلفتها التقديرية عليك</span><input class="input num" placeholder="٢٢ ج">' +
        '<div class="hint">تُستخدم لحساب الالتزام القائم وعائد البرنامج.</div></label>',
        '<button class="btn btn-line" onclick="UI.closeModal()">إلغاء</button>' +
        '<button class="btn btn-primary" onclick="UI.closeModal();UI.toast(\'تمت إضافة المكافأة\')">إضافة</button>');
    },
    newCampaign: function () {
      UI.modal('حملة جديدة',
        '<label class="field"><span>اسم الحملة</span><input class="input" value="استرجاع العملاء المعرّضين للفقدان"></label>' +
        '<label class="field"><span>الشريحة المستهدفة</span><select class="select"><option selected>معرّض للفقدان (٤٢ عميلًا)</option><option>VIP (٨٦)</option><option>جديد (١٩٤)</option><option>الكل (١,٢٤٠)</option></select></label>' +
        '<label class="field"><span>الرسالة</span><textarea class="input" rows="3">وحشتنا! رجعلنا واستلم مشروبك المفضل بنص التمن 💚</textarea></label>' +
        '<div class="card card-p tint-o"><div class="row between"><b class="t-sm">التكلفة المتوقعة</b>' +
        '<b class="t-lg num c-orange">١٩ ج</b></div>' +
        '<p class="t-xs muted w-6 mt-1">٢٦ عميلًا لديهم إشعارات مفعّلة (مجاني) + ١٦ عبر واتساب (٠.٤٥ ج للرسالة).</p></div>',
        '<button class="btn btn-line" onclick="UI.closeModal()">إلغاء</button>' +
        '<button class="btn btn-primary" onclick="UI.closeModal();UI.toast(\'تم جدولة الحملة · ٤٢ مستلمًا\')">' + ICO('send') + ' إرسال</button>');
    }
  };
  g.MER = MER;
})(window);
