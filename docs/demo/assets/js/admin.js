/* ولائي — لوحة إدارة المنصة */
(function (g) {
  var D = DATA, $ = UI.$, root;

  var NAV = [
    { g:'المنصة' },
    { id:'overview', ic:'grid',  l:'نظرة عامة' },
    { id:'kpis',     ic:'target',l:'مؤشرات الصحة' },
    { g:'الإدارة' },
    { id:'stores',   ic:'store', l:'المتاجر', badge:'١' },
    { id:'revenue',  ic:'cash',  l:'الاشتراكات والإيراد' },
    { id:'users',    ic:'users',  l:'المستخدمون' },
    { g:'النظام' },
    { id:'ops',      ic:'db',    l:'التشغيل والمراقبة' },
    { id:'config',   ic:'cog',   l:'إعدادات المنصة' }
  ];
  var TITLES = {
    overview:['نظرة عامة','أداء المنصة بالكامل'],
    kpis:['مؤشرات الصحة','الأرقام التي تقرر مصير المشروع'],
    stores:['المتاجر','إدارة المتاجر المشتركة'],
    revenue:['الاشتراكات والإيراد','الإيراد الشهري المتكرر وتوزيعه'],
    users:['المستخدمون','حسابات المنصة والصلاحيات'],
    ops:['التشغيل والمراقبة','صحة الخدمات والتكاليف'],
    config:['إعدادات المنصة','الإعدادات العامة والامتثال']
  };

  function kpi(k) {
    return '<div class="kpi" data-anim><div class="row between" style="align-items:flex-start">' +
      '<div class="grow"><div class="kt">' + k.k + '</div><div class="kv num">' + k.v + '</div></div>' +
      '<div class="ibox ' + k.tone + '">' + ICO(k.icon) + '</div></div>' +
      '<div class="mt-1"><span class="delta ' + (String(k.d).indexOf('−') === 0 ? 'dn' : 'up') + '">' + k.d + '</span></div></div>';
  }
  function hd(t, r) { return '<div class="card-hd"><h3>' + t + '</h3>' + (r || '') + '</div>'; }

  var S = {};

  S.overview = function () {
    return '<div class="grid g3 mb-3">' + D.ADMIN_KPIS.map(kpi).join('') + '</div>' +
      '<div class="grid" style="grid-template-columns:1.5fr 1fr">' +
        '<div class="card" data-anim>' + hd('نمو المتاجر المفعّلة',
          '<span class="badge bg-g">+٢٧ هذا الشهر</span>') +
          '<div class="card-p">' + UI.barChart([48,62,79,96,118,141,168,196,224,251,284,312], D.CHART_LABELS) + '</div></div>' +
        '<div class="card" data-anim>' + hd('توزيع الباقات') + '<div class="card-p">' +
          [['مجاني','١٩٤ متجر',62,''],['Starter','٧٨ متجر',25,'g'],['Growth','٣٤ متجر',11,'o'],['Chain','٦ متاجر',2,'']].map(function (p) {
            return '<div class="usage"><div style="width:70px"><b class="t-sm">' + p[0] + '</b></div>' +
              '<div class="bar ' + p[3] + '"><i style="width:' + p[2] + '%"></i></div>' +
              '<div class="t-xs muted w-7 num nowrap">' + p[1] + '</div></div>';
          }).join('') +
          '<div class="card card-p tint-o mt-3"><b class="t-sm">معدل التحويل ٩.٤٪</b>' +
          '<p class="t-xs muted w-6 mt-1">أعلى من متوسط قطاع SaaS للشركات الصغيرة (٢–٥٪) بفضل المبيعات الميدانية.</p></div>' +
        '</div></div>' +
      '</div>' +
      '<div class="card mt-3" data-anim>' + hd('أحدث المتاجر المنضمة',
        '<button class="btn btn-line btn-sm" onclick="ADM.go(\'stores\')">عرض الكل</button>') +
        '<div style="overflow-x:auto"><table class="tbl"><thead><tr><th>المتجر</th><th>النشاط</th><th>المدينة</th><th>الباقة</th><th>العملاء</th><th>الحالة</th></tr></thead><tbody>' +
        D.ADMIN_STORES.slice(0, 5).map(storeRow).join('') + '</tbody></table></div></div>';
  };

  function storeRow(s) {
    var st = { 'نشط':'bg-g', 'قيد المراجعة':'bg-a', 'موقوف':'bg-r' };
    var pl = { 'مجاني':'bg-n', 'Starter':'bg-b', 'Growth':'bg-v', 'Chain':'bg-g' };
    return '<tr><td><div class="row"><div class="av av-sm ' + s.tone + '">' + s.n[0] + '</div><b class="t-sm">' + s.n + '</b></div></td>' +
      '<td class="muted">' + s.cat + '</td><td class="muted">' + s.city + '</td>' +
      '<td><span class="badge ' + pl[s.plan] + '">' + s.plan + '</span></td>' +
      '<td class="num w-7">' + s.cust + '</td>' +
      '<td><span class="badge ' + st[s.st] + '">' + s.st + '</span></td></tr>';
  }

  S.kpis = function () {
    return '<div class="card card-p tint-v mb-3" data-anim><div class="row-t">' +
      '<div class="ibox v" style="background:#fff">' + ICO('target') + '</div><div class="grow">' +
      '<b>هذه الأرقام — لا حجم السوق ولا جمال المنتج — هي ما يقرر إن كان المشروع يستحق الاستثمار</b>' +
      '<p class="t-sm muted mt-1">تُقاس منذ اليوم الأول وتُراجع أسبوعيًا. أي مؤشر خارج هدفه يستدعي قرارًا، لا تفسيرًا.</p></div></div></div>' +
      '<div class="grid g2">' + D.PLATFORM_KPIS.map(function (k) {
        return '<div class="card card-p" data-anim><div class="row between">' +
          '<div class="grow"><div class="kt t-sm w-7 muted">' + k.k + '</div>' +
          '<div class="t-2xl w-8 num mt-1 ' + (k.ok ? 'c-green' : 'c-red') + '">' + k.v + '</div>' +
          '<div class="t-xs muted w-6">' + k.goal + '</div></div>' +
          '<div class="ibox ' + (k.ok ? 'g' : 'r') + '">' + ICO(k.ok ? 'checkc' : 'warn') + '</div></div></div>';
      }).join('') + '</div>' +
      '<div class="card card-p tint-r mt-3" data-anim><div class="row-t"><div class="ibox r" style="background:#fff">' + ICO('warn') + '</div>' +
      '<div class="grow"><b>مؤشر خارج الهدف: استرداد تكلفة الاستحواذ ٣.٨ شهر</b>' +
      '<p class="t-sm muted mt-1">الهدف أقل من ٣ شهور. العلاجات: رفع متوسط الإيراد برسوم التفعيل ورصيد الحملات، ' +
      'أو استهداف السلاسل (عقد واحد = ٢٠ متجرًا مستقلًا)، أو بناء قناة شركاء غير مباشرة.</p></div></div></div>';
  };

  S.stores = function () {
    return '<div class="card" data-anim>' +
      '<div class="card-hd"><div class="row wrap gap-sm">' +
      ['الكل','نشط','قيد المراجعة','موقوف'].map(function (s, i) {
        return '<span class="seg' + (i === 0 ? ' on' : '') + '" onclick="ADM.seg(this)">' + s + '</span>';
      }).join('') + '</div>' +
      '<div class="row gap-sm"><div style="position:relative">' +
      '<input class="input" placeholder="بحث عن متجر…" style="padding-inline-start:38px;width:220px">' +
      '<span style="position:absolute;inset-inline-start:12px;top:10px;color:var(--faint)">' + ICO('search','',17) + '</span></div>' +
      '<button class="btn btn-line btn-sm">' + ICO('down') + ' تصدير</button></div></div>' +
      '<div style="overflow-x:auto"><table class="tbl"><thead><tr>' +
      '<th>المتجر</th><th>النشاط</th><th>المدينة</th><th>الباقة</th><th>العملاء</th><th>الحالة</th><th>إجراء</th></tr></thead><tbody>' +
      D.ADMIN_STORES.map(function (s) {
        return storeRow(s).replace('</tr>',
          '<td><div class="row gap-sm">' +
          '<button class="btn btn-line btn-sm" onclick="UI.toast(\'فتح ملف ' + s.n + '\')">' + ICO('eye') + '</button>' +
          (s.st === 'قيد المراجعة'
            ? '<button class="btn btn-green btn-sm" onclick="UI.toast(\'تمت الموافقة على ' + s.n + '\')">' + ICO('check') + '</button>'
            : '<button class="btn btn-line btn-sm">' + ICO('cog') + '</button>') +
          '</div></td></tr>');
      }).join('') + '</tbody></table></div></div>';
  };

  S.revenue = function () {
    return '<div class="grid g4 mb-3">' +
      [{k:'الإيراد الشهري المتكرر',v:'١٨٤,٢٠٠ ج',d:'+١٤٪',icon:'cash',tone:'g'},
       {k:'متوسط الإيراد لكل متجر',v:'١,٥٦٠ ج',d:'+٦٪',icon:'wallet',tone:'v'},
       {k:'الإيراد السنوي المتوقع',v:'٢.٢١ م ج',d:'+١٨٪',icon:'trend',tone:'b'},
       {k:'انسحاب الإيراد',v:'١.٨٪',d:'−٠.٣٪',icon:'warn',tone:'o'}].map(kpi).join('') + '</div>' +
      '<div class="grid" style="grid-template-columns:1.5fr 1fr">' +
        '<div class="card" data-anim>' + hd('تطور الإيراد الشهري المتكرر') +
        '<div class="card-p">' + UI.barChart([42,51,63,74,89,102,118,131,146,159,172,184], D.CHART_LABELS, {green:true}) + '</div></div>' +
        '<div class="card" data-anim>' + hd('مصادر الإيراد') + '<div class="card-p">' +
          [['اشتراكات الباقات','١٤٦,٠٠٠ ج',79,'g'],['رصيد الرسائل','٢١,٤٠٠ ج',12,'o'],
           ['رسوم التفعيل','١٢,٨٠٠ ج',7,''],['تكامل POS','٤,٠٠٠ ج',2,'']].map(function (r) {
            return '<div class="usage"><div style="width:96px"><b class="t-sm">' + r[0] + '</b></div>' +
              '<div class="bar ' + r[3] + '"><i style="width:' + r[2] + '%"></i></div>' +
              '<div class="t-xs muted w-7 num nowrap">' + r[1] + '</div></div>';
          }).join('') +
          '<p class="hint mt-3">مصادر الإيراد غير الاشتراكية تمثل ٢١٪ — وهي ما يرفع متوسط الإيراد ويقصّر فترة الاسترداد.</p>' +
        '</div></div>' +
      '</div>';
  };

  S.users = function () {
    var U = [
      { n:'محمد نبيل', r:'مالك المنصة', e:'owner@walaee.app', st:'نشط', tone:'v' },
      { n:'سلمى فتحي', r:'مدير نجاح العملاء', e:'salma@walaee.app', st:'نشط', tone:'g' },
      { n:'عمر خالد', r:'مندوب مبيعات ميداني', e:'omar@walaee.app', st:'نشط', tone:'b' },
      { n:'داليا سمير', r:'دعم فني', e:'dalia@walaee.app', st:'نشط', tone:'o' },
      { n:'حساب تقني', r:'قراءة فقط (API)', e:'svc@walaee.app', st:'موقوف', tone:'v' }
    ];
    return '<div class="card" data-anim>' + hd('مستخدمو المنصة',
      '<button class="btn btn-primary btn-sm" onclick="UI.toast(\'دعوة مستخدم جديد\')">' + ICO('plus') + ' دعوة</button>') +
      '<table class="tbl"><thead><tr><th>المستخدم</th><th>الدور</th><th>البريد</th><th>الحالة</th><th></th></tr></thead><tbody>' +
      U.map(function (u) {
        return '<tr><td><div class="row"><div class="av av-sm ' + u.tone + '">' + u.n[0] + '</div><b class="t-sm">' + u.n + '</b></div></td>' +
          '<td class="muted">' + u.r + '</td><td class="muted" style="direction:ltr;text-align:right">' + u.e + '</td>' +
          '<td><span class="badge ' + (u.st === 'نشط' ? 'bg-g' : 'bg-n') + '">' + u.st + '</span></td>' +
          '<td><button class="btn btn-line btn-sm">' + ICO('cog') + '</button></td></tr>';
      }).join('') + '</tbody></table></div>';
  };

  S.ops = function () {
    var SV = [
      ['واجهة API الأساسية','٩٩.٩٨٪','١٤٢ مللي ثانية',true],
      ['قاعدة البيانات PostgreSQL','٩٩.٩٩٪','٨ مللي ثانية',true],
      ['خدمة الإشعارات','٩٩.٩٤٪','٢١٠ مللي ثانية',true],
      ['بوابة الرسائل','٩٨.٢١٪','٤٤٠ مللي ثانية',false]
    ];
    return '<div class="grid g4 mb-3">' +
      [{k:'زمن التشغيل (٣٠ يومًا)',v:'٩٩.٩٦٪',d:'مستقر',icon:'checkc',tone:'g'},
       {k:'متوسط زمن الاستجابة',v:'١٤٢ مللي',d:'−١٨ مللي',icon:'zap',tone:'v'},
       {k:'تكلفة البنية الشهرية',v:'٤٦٥ $',d:'+٤٥ $',icon:'db',tone:'b'},
       {k:'التكلفة لكل عميل نشط',v:'٠.٠٣ $',d:'−٠.٠١ $',icon:'wallet',tone:'o'}].map(kpi).join('') + '</div>' +
      '<div class="grid g2">' +
      '<div class="card" data-anim>' + hd('حالة الخدمات') + '<div class="card-p">' +
        SV.map(function (s) {
          return '<div class="li"><span class="dot" style="background:' + (s[3] ? 'var(--green-600)' : 'var(--orange-600)') + '"></span>' +
            '<div class="grow"><div class="li-t">' + s[0] + '</div><div class="li-s">زمن الاستجابة ' + s[2] + '</div></div>' +
            '<b class="t-sm num ' + (s[3] ? 'c-green' : 'c-orange') + '">' + s[1] + '</b></div>';
        }).join('') + '</div></div>' +
      '<div class="card" data-anim>' + hd('توزيع تكلفة البنية التحتية') + '<div class="card-p">' +
        [['خوادم التطبيق','١١٠ $',24,''],['قاعدة البيانات','١٣٠ $',28,'g'],['المراقبة والسجلات','٩٥ $',20,'o'],
         ['التخزين و CDN','٤٥ $',10,''],['نسخ احتياطي','٣٥ $',8,''],['أخرى','٥٠ $',10,'']].map(function (r) {
          return '<div class="usage"><div style="width:110px"><b class="t-sm">' + r[0] + '</b></div>' +
            '<div class="bar ' + r[3] + '"><i style="width:' + r[2] + '%"></i></div>' +
            '<div class="t-xs muted w-7 num nowrap">' + r[1] + '</div></div>';
        }).join('') +
        '<p class="hint mt-3">البنية التحتية تمثل أقل من ٣٪ من الإيراد — ليست بند التكلفة المقلق.</p></div></div>' +
      '</div>';
  };

  S.config = function () {
    return '<div class="grid g2">' +
      '<div class="card" data-anim>' + hd('الامتثال وحماية البيانات') + '<div class="card-p">' +
        [['قانون حماية البيانات المصري ١٥١/٢٠٢٠','مراجعة قانونية مكتملة',true],
         ['نظام حماية البيانات السعودي PDPL','قيد التجهيز للتوسع',false],
         ['عقود معالجة البيانات (DPA)','مُوقّعة مع ٣١٢ متجرًا',true],
         ['سياسة الاحتفاظ والحذف','٢٤ شهرًا من آخر نشاط',true],
         ['تشفير عند النقل والتخزين','مفعّل على كل الخدمات',true]].map(function (r) {
          return '<div class="li"><div class="ibox ' + (r[2] ? 'g' : 'a') + '">' + ICO(r[2] ? 'shield' : 'clock') + '</div>' +
            '<div class="grow"><div class="li-t">' + r[0] + '</div><div class="li-s">' + r[1] + '</div></div>' +
            '<span class="badge ' + (r[2] ? 'bg-g' : 'bg-a') + '">' + (r[2] ? 'مكتمل' : 'جارٍ') + '</span></div>';
        }).join('') + '</div></div>' +
      '<div class="card" data-anim>' + hd('نموذج النقاط عبر الشبكة') + '<div class="card-p">' +
        '<div class="card card-p tint-v mb-2"><b class="t-sm">المرحلة الحالية: رصيد منفصل لكل متجر</b>' +
        '<p class="t-xs muted w-6 mt-1">الأبسط تشغيليًا وقانونيًا. الشبكة تظهر في الهوية الموحّدة والاكتشاف والعروض المتقاطعة — دون تبادل قيمة مالية بين التجار.</p></div>' +
        [['المرحلة ١ — رصيد منفصل لكل متجر','مفعّلة الآن','g'],
         ['المرحلة ٢ — عملة شبكة تمنحها المنصة','مخططة للربع الثالث','a'],
         ['المرحلة ٣ — مقاصة حقيقية بين التجار','تحتاج مراجعة تنظيمية','n']].map(function (r) {
          return '<div class="li"><div class="grow"><div class="li-t">' + r[0] + '</div></div>' +
            '<span class="badge bg-' + r[2] + '">' + r[1] + '</span></div>';
        }).join('') + '</div></div>' +
      '</div>';
  };

  var router;
  var ADM = {
    init: function () {
      root = $('#content');
      $('#nav').innerHTML = NAV.map(function (n) {
        if (n.g) return '<div class="grp-t">' + n.g + '</div>';
        return '<div class="nav-i" data-id="' + n.id + '" onclick="ADM.go(\'' + n.id + '\')">' + ICO(n.ic) +
          '<span>' + n.l + '</span>' + (n.badge ? '<span class="pill num">' + n.badge + '</span>' : '') + '</div>';
      }).join('');
      router = UI.router(root, S, function (name) {
        UI.$$('.nav-i').forEach(function (e) { e.classList.toggle('on', e.dataset.id === name); });
        var t = TITLES[name] || ['', ''];
        $('#pt').textContent = t[0]; $('#ps').textContent = t[1];
      });
      var h=(location.hash||'').replace('#','');
      ADM.go(S[h]?h:'overview');
    },
    go: function (n) { router.go(n); if(location.hash.slice(1)!==n) location.hash=n; window.scrollTo({ top: 0, behavior: 'smooth' }); },
    seg: function (el) { UI.$$('.seg').forEach(function (e) { e.classList.remove('on'); }); el.classList.add('on'); }
  };
  g.ADM = ADM;
})(window);
