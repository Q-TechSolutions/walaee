/* ولائي — تطبيق العميل (PWA) — منطق الشاشات */
(function (g) {
  var D = DATA, $ = UI.$, root, tabbar, tab = 'home';

  /* ================= مكونات مشتركة ================= */
  function statusbar(dark) {
    return '<div class="statusbar' + (dark ? ' on-dark' : '') + '">' +
      '<span class="num">٩:٤١</span><div class="sb-r">' +
      '<svg viewBox="0 0 20 14" width="17" height="12" fill="currentColor"><rect x="0" y="9" width="3" height="5" rx="1"/><rect x="5" y="6" width="3" height="8" rx="1"/><rect x="10" y="3" width="3" height="11" rx="1"/><rect x="15" y="0" width="3" height="14" rx="1" opacity=".35"/></svg>' +
      '<i></i></div></div>';
  }
  function head(title, sub, actions) {
    return '<div class="mhead"><div><h1>' + title + '</h1>' +
      (sub ? '<div class="sub">' + sub + '</div>' : '') + '</div>' + (actions || '') + '</div>';
  }
  function topbar(title, back) {
    return '<div class="topbar"><button class="iconbtn" onclick="CUS.go(\'' + (back || 'home') + '\')">' +
      ICO('fwd') + '</button><h2>' + title + '</h2></div>';
  }
  function card(c) {
    var pct = Math.round(c.progress / c.target * 100);
    return '<div class="lcard" style="background:' + c.color + '" onclick="CUS.go(\'card\',' + c.id + ')" data-anim>' +
      '<div class="lc-top"><div class="lc-logo">' + c.logo + '</div>' +
      '<div class="grow"><div class="lc-name">' + c.store + '</div><div class="lc-cat">' + c.cat + ' · ' + c.dist + '</div></div>' +
      ICO('fwd', '', 18) + '</div>' +
      '<div class="lc-mid"><div><div class="lc-val num">' + UI.ar(c.progress) + '</div>' +
      '<div class="lc-unit">من ' + UI.ar(c.target) + ' ' + c.unit + '</div></div>' +
      '<div class="lc-rew">' + c.reward + '</div></div>' +
      '<div class="lc-bar"><i style="width:' + pct + '%"></i></div>' +
      '<div class="lc-foot"><span>' + UI.ar(pct) + '٪ من الهدف</span><span>تنتهي ' + c.expires + '</span></div></div>';
  }

  /* ================= الشاشات ================= */
  var S = {};

  /* ---------- الرئيسية ---------- */
  S.home = function () {
    var ready = D.REWARDS.filter(function (r) { return r.ready; }).length;
    return statusbar() + '<div class="view pad-b" data-scroll>' +
      head('أهلاً محمد 👋', 'عندك ' + UI.ar(ready) + ' مكافآت جاهزة للاستبدال',
        '<button class="iconbtn" onclick="UI.toast(\'لا توجد إشعارات جديدة\')">' + ICO('bell') + '<span class="nd"></span></button>') +
      '<div class="pad">' +
        '<div class="a2hs" data-anim><div class="ic">' + ICO('phone') + '</div>' +
        '<div class="grow"><b>ثبّت ولائي على شاشتك</b><span>عشان توصلك إشعارات المكافآت — واكسب ٥٠ نقطة ترحيبية.</span></div>' +
        '<button class="btn btn-sm" style="background:#fff;color:var(--violet-700)" onclick="UI.toast(\'تم تثبيت التطبيق · +٥٠ نقطة\')">تثبيت</button></div>' +

        '<div class="sec-t"><h3>بطاقاتي</h3><a onclick="CUS.setTab(\'stores\')">كل المتاجر</a></div>' +
        '<div class="col" style="gap:13px">' + D.CARDS.map(card).join('') + '</div>' +

        '<div class="sec-t"><h3>نشاطك الأخير</h3><a onclick="CUS.go(\'activity\')">الكل</a></div>' +
        '<div class="card card-p" data-anim>' + D.ACTIVITY.slice(0, 4).map(function (a) {
          return '<div class="li"><div class="ibox ' + a.tone + '">' + ICO(a.icon) + '</div>' +
            '<div class="grow"><div class="li-t">' + a.title + '</div><div class="li-s">' + a.sub + '</div></div>' +
            '<div class="li-v c-' + (a.tone === 'g' ? 'green' : a.tone === 'o' ? 'orange' : 'violet') + '">' + a.val + '</div></div>';
        }).join('') + '</div>' +
      '</div></div>';
  };

  /* ---------- تفاصيل البطاقة ---------- */
  S.card = function (id) {
    var c = D.CARDS.filter(function (x) { return x.id === id; })[0] || D.CARDS[0];
    var pct = Math.round(c.progress / c.target * 100);
    var isStamp = c.model === 'stamps' || c.model === 'visits';
    var body = '';

    if (isStamp) {
      var cells = '';
      for (var i = 0; i < c.target; i++) {
        var cls = i < c.progress ? 'fill' : (i === c.progress ? 'next' : '');
        cells += '<div class="stamp ' + cls + '">' + ICO(i < c.progress ? 'check' : 'star') + '</div>';
      }
      body = '<div class="card card-p" data-anim><div class="row between mb-2"><h3 class="t-md">تقدّمك</h3>' +
        '<span class="badge bg-g">' + UI.ar(c.target - c.progress) + ' متبقية</span></div>' +
        '<div class="stamps">' + cells + '</div>' +
        '<p class="hint mt-2">كل زيارة = ختم. عند اكتمال البطاقة تحصل على <b>' + c.reward + '</b>.</p></div>';
    } else {
      body = '<div class="card card-p center" data-anim>' +
        '<div style="position:relative;display:inline-grid;place-items:center">' +
        UI.ring(pct, 148, 12, '#4B1E9E') +
        '<div style="position:absolute;text-align:center"><div class="t-2xl w-8 num">' + UI.ar(c.progress) + '</div>' +
        '<div class="t-xs muted w-7">من ' + UI.ar(c.target) + ' ' + c.unit + '</div></div></div>' +
        '<p class="hint">باقي <b>' + UI.ar(c.target - c.progress) + ' ' + c.unit + '</b> للحصول على ' + c.reward + '</p></div>';
    }

    return statusbar() + '<div class="view pad-b" data-scroll>' + topbar(c.store) +
      '<div class="pad">' +
        '<div class="lcard mb-3" style="background:' + c.color + '" data-anim>' +
          '<div class="lc-top"><div class="lc-logo">' + c.logo + '</div>' +
          '<div class="grow"><div class="lc-name">' + c.store + '</div><div class="lc-cat">' + c.cat + ' · انضممت ' + c.joined + '</div></div></div>' +
          '<div class="lc-mid"><div><div class="lc-val num">' + UI.ar(c.progress) + '</div><div class="lc-unit">' + c.unit + '</div></div>' +
          '<div class="lc-rew">' + c.reward + '</div></div>' +
          '<div class="lc-bar"><i style="width:' + pct + '%"></i></div></div>' +

        body +

        '<div class="grid g3 mt-3" data-anim>' +
          ['<div class="card card-p center"><div class="t-lg w-8 num">' + UI.ar(c.visits) + '</div><div class="t-xs muted w-7">زيارة</div></div>',
           '<div class="card card-p center"><div class="t-lg w-8 num">' + UI.ar(c.saved) + '</div><div class="t-xs muted w-7">جنيه وفّرتها</div></div>',
           '<div class="card card-p center"><div class="t-lg w-8">' + c.dist + '</div><div class="t-xs muted w-7">المسافة</div></div>'].join('') +
        '</div>' +

        '<div class="card card-p tint-a mt-3" style="background:var(--amber-100);border-color:#F0DFA8" data-anim>' +
          '<div class="row-t"><div class="ibox a" style="background:#fff">' + ICO('clock') + '</div>' +
          '<div class="grow"><b class="t-sm">رصيدك صالح حتى ' + c.expires + '</b>' +
          '<div class="t-xs muted w-6 mt-1">هننبهك قبلها بشهر. الرصيد ده خاص بـ<b>' + c.store + '</b> فقط.</div></div></div></div>' +

        '<div class="sec-t"><h3>مكافآت هذا المتجر</h3></div>' +
        '<div class="col gap-sm">' + D.REWARDS.filter(function (r) { return c.store.indexOf(r.store.split(' ')[0]) > -1 || r.store.indexOf(c.store.split(' ')[0]) > -1; })
          .map(rwRow).join('') + '</div>' +

        '<button class="btn btn-primary btn-lg btn-block mt-3" onclick="CUS.scan()">' + ICO('scan') + ' امسح واكسب الآن</button>' +
      '</div></div>';
  };

  function rwRow(r) {
    return '<div class="rw ' + (r.ready ? 'ready' : '') + '" data-anim>' +
      '<div class="ibox ' + r.tone + '">' + ICO(r.icon) + '</div>' +
      '<div class="grow"><div class="rw-t">' + r.title + '</div>' +
      '<div class="rw-s">' + r.store + ' · ' + r.cost + (r.need ? ' · ' + r.need : '') + '</div></div>' +
      (r.ready
        ? '<button class="btn btn-green btn-sm" onclick="CUS.redeem(\'' + r.title + '\')">استبدال</button>'
        : '<span class="badge bg-n">قريبًا</span>') + '</div>';
  }

  /* ---------- المكافآت ---------- */
  S.rewards = function () {
    var ready = D.REWARDS.filter(function (r) { return r.ready; });
    var soon  = D.REWARDS.filter(function (r) { return !r.ready; });
    return statusbar() + '<div class="view pad-b" data-scroll>' +
      head('المكافآت', UI.ar(ready.length) + ' جاهزة الآن · ' + UI.ar(soon.length) + ' قريبة') +
      '<div class="pad">' +
        '<div class="sec-t"><h3>جاهزة للاستبدال</h3><span class="badge bg-g">' + UI.ar(ready.length) + '</span></div>' +
        '<div class="col gap-sm">' + ready.map(rwRow).join('') + '</div>' +
        '<div class="sec-t"><h3>قريبة منك</h3></div>' +
        '<div class="col gap-sm">' + soon.map(rwRow).join('') + '</div>' +
      '</div></div>';
  };

  /* ---------- المتاجر ---------- */
  S.stores = function () {
    return statusbar() + '<div class="view pad-b" data-scroll>' +
      head('المتاجر', 'متاجر تقبل ولائي قريبة منك') +
      '<div class="pad">' +
        '<div class="row mb-3"><div class="grow" style="position:relative">' +
        '<input class="input" placeholder="ابحث عن متجر أو فئة…" style="padding-inline-start:40px">' +
        '<span style="position:absolute;inset-inline-start:13px;top:11px;color:var(--faint)">' + ICO('search', '', 18) + '</span></div>' +
        '<button class="iconbtn">' + ICO('filter') + '</button></div>' +

        '<div class="card" style="height:132px;background:linear-gradient(135deg,#EDE6FB,#E4F6EC);display:grid;place-items:center;overflow:hidden;position:relative" data-anim>' +
          '<div class="center"><div class="ibox v" style="margin:0 auto 6px;background:#fff">' + ICO('map') + '</div>' +
          '<b class="t-sm">٨ متاجر في نطاق ٣ كم</b><div class="t-xs muted w-6">اضغط لفتح الخريطة</div></div></div>' +

        '<div class="sec-t"><h3>بطاقاتك النشطة</h3></div>' +
        '<div class="card card-p" data-anim>' + D.CARDS.map(function (c) {
          return '<div class="li"><div class="av ' + c.tone + '">' + c.logo + '</div>' +
            '<div class="grow"><div class="li-t">' + c.store + '</div>' +
            '<div class="li-s">' + UI.ar(c.progress) + '/' + UI.ar(c.target) + ' ' + c.unit + ' · ' + c.dist + '</div></div>' +
            '<button class="btn btn-line btn-sm" onclick="CUS.go(\'card\',' + c.id + ')">فتح</button></div>';
        }).join('') + '</div>' +

        '<div class="sec-t"><h3>اكتشف متاجر جديدة</h3><span class="badge bg-o">عروض ترحيب</span></div>' +
        '<div class="card card-p" data-anim>' + D.DISCOVER.map(function (s) {
          return '<div class="li"><div class="av ' + s.tone + '">' + s.logo + '</div>' +
            '<div class="grow"><div class="li-t">' + s.name + '</div>' +
            '<div class="li-s">' + s.cat + ' · ' + s.dist + ' · <span class="c-orange w-7">' + s.offer + '</span></div></div>' +
            '<button class="btn btn-ghost btn-sm" onclick="UI.toast(\'تم الانضمام إلى ' + s.name + '\')">انضم</button></div>';
        }).join('') + '</div>' +
      '</div></div>';
  };

  /* ---------- النشاط ---------- */
  S.activity = function () {
    return statusbar() + '<div class="view pad-b" data-scroll>' + topbar('سجل النشاط') +
      '<div class="pad"><div class="card card-p" data-anim>' +
      D.ACTIVITY.concat(D.ACTIVITY).map(function (a) {
        return '<div class="li"><div class="ibox ' + a.tone + '">' + ICO(a.icon) + '</div>' +
          '<div class="grow"><div class="li-t">' + a.title + '</div><div class="li-s">' + a.sub + '</div></div>' +
          '<div class="li-v">' + a.val + '</div></div>';
      }).join('') + '</div></div></div>';
  };

  /* ---------- حسابي ---------- */
  S.me = function () {
    function toggle(label, sub, on, note) {
      return '<div class="li"><div class="grow"><div class="li-t">' + label + '</div>' +
        '<div class="li-s">' + sub + '</div></div>' +
        '<div class="switch' + (on ? ' on' : '') + '" onclick="this.classList.toggle(\'on\');UI.toast(\'' + (note || 'تم الحفظ') + '\')"></div></div>';
    }
    return statusbar() + '<div class="view pad-b" data-scroll>' + head('حسابي') +
      '<div class="pad">' +
        '<div class="card card-p row" data-anim><div class="av av-lg">م</div>' +
        '<div class="grow"><b>محمد نبيل</b><div class="t-sm muted w-6 num">٠١٠٠١٢٣٤٥٦٧</div></div>' +
        '<button class="btn btn-line btn-sm">' + ICO('edit') + '</button></div>' +

        '<div class="grid g3 mt-3" data-anim>' +
          '<div class="card card-p center"><div class="t-lg w-8 num">٤</div><div class="t-xs muted w-7">بطاقة</div></div>' +
          '<div class="card card-p center"><div class="t-lg w-8 num">٣٨</div><div class="t-xs muted w-7">زيارة</div></div>' +
          '<div class="card card-p center"><div class="t-lg w-8 num">٥٩٤</div><div class="t-xs muted w-7">ج وفّرتها</div></div>' +
        '</div>' +

        '<div class="sec-t"><h3>الإشعارات</h3></div>' +
        '<div class="card card-p" data-anim>' +
          toggle('إشعارات التطبيق', 'مجانية — القناة الأساسية', true) +
          toggle('واتساب', 'للتنبيهات المهمة فقط', true) +
          toggle('رسائل SMS', 'عند تعذّر القنوات الأخرى', false) +
        '</div>' +

        '<div class="sec-t"><h3>الخصوصية وبياناتي</h3></div>' +
        '<div class="card card-p" data-anim>' +
          '<div class="row-t mb-2"><div class="ibox g">' + ICO('shield') + '</div>' +
          '<div class="grow"><b class="t-sm">بياناتك مِلكك</b>' +
          '<div class="t-xs muted w-6 mt-1">المتاجر تشوف سلوك شرائك عندها فقط. تقدر تسحب موافقتك أو تحذف حسابك في أي وقت.</div></div></div>' +
          '<div class="li"><div class="grow"><div class="li-t">تحميل نسخة من بياناتي</div>' +
          '<div class="li-s">ملف مفصّل بكل عملياتك</div></div>' +
          '<button class="btn btn-line btn-sm" onclick="UI.toast(\'هيوصلك الملف خلال دقائق\')">' + ICO('down') + '</button></div>' +
          '<div class="li"><div class="grow"><div class="li-t c-red">حذف الحساب نهائيًا</div>' +
          '<div class="li-s">يشمل حذف كل سجل الشراء</div></div>' +
          '<button class="btn btn-line btn-sm c-red" onclick="UI.toast(\'تحتاج تأكيد بالـ OTP\',\'warn\')">' + ICO('trash') + '</button></div>' +
        '</div>' +

        '<div class="sec-t"><h3>عام</h3></div>' +
        '<div class="card card-p" data-anim>' +
          '<div class="li"><div class="ibox v">' + ICO('doc') + '</div><div class="grow"><div class="li-t">الشروط والأحكام</div></div>' + ICO('fwd', 'faint', 18) + '</div>' +
          '<div class="li"><div class="ibox b">' + ICO('whatsapp') + '</div><div class="grow"><div class="li-t">مساعدة ودعم</div></div>' + ICO('fwd', 'faint', 18) + '</div>' +
          '<div class="li"><div class="ibox r">' + ICO('logout') + '</div><div class="grow"><div class="li-t c-red">تسجيل الخروج</div></div></div>' +
        '</div>' +
        '<p class="hint center mt-3">ولائي — النسخة ١.٠.٠ · كلنا كسبانين</p>' +
      '</div></div>';
  };

  /* ================= التسجيل (Onboarding) ================= */
  var onbStep = 0;
  var ONB = [
    { icon:'wallet', t:'كل بطاقات ولائك في مكان واحد', p:'مش محتاج تفتكر أي متجر عنده نقاط وأي متجر عنده أختام. كل حاجة قدامك في تطبيق واحد.' },
    { icon:'scan',   t:'امسح واكسب في ثانية', p:'بعد ما تدفع، امسح رمز المتجر واكتب قيمة الفاتورة — ونقاطك تتسجّل فورًا. من غير كروت ولا أجهزة.' },
    { icon:'gift',   t:'مكافآت حقيقية تستحق', p:'تابع تقدمك لحظة بلحظة، وهنبّهك أول ما تقرب من مكافأة أو قبل ما رصيدك ينتهي.' }
  ];
  function onbView() {
    var s = ONB[onbStep];
    return '<div class="onb" data-anim>' + statusbar(true) +
      '<div class="art"><div style="width:158px;height:158px;border-radius:44px;background:rgba(255,255,255,.12);display:grid;place-items:center" class="anim-pop">' +
      ICO(s.icon, '', 74) + '</div></div>' +
      '<div class="dots">' + ONB.map(function (_, i) { return '<i class="' + (i === onbStep ? 'on' : '') + '"></i>'; }).join('') + '</div>' +
      '<h2>' + s.t + '</h2><p>' + s.p + '</p>' +
      '<div class="foot"><button class="btn btn-lg btn-block" style="background:#fff;color:var(--violet-800)" onclick="CUS.onbNext()">' +
      (onbStep < ONB.length - 1 ? 'التالي' : 'يلا نبدأ') + '</button>' +
      '<button class="btn btn-block mt-2" style="color:rgba(255,255,255,.7)" onclick="CUS.closeOnb()">تخطي</button></div></div>';
  }
  function regView() {
    return '<div class="onb" data-anim>' + statusbar(true) +
      '<div style="padding-top:26px"><button class="iconbtn" style="background:rgba(255,255,255,.13);border:none;color:#fff" onclick="CUS.closeOnb()">' + ICO('fwd') + '</button></div>' +
      '<div class="art" style="flex:none;padding:26px 0 6px"><div style="text-align:center">' +
      '<div style="width:74px;height:74px;border-radius:24px;background:rgba(255,255,255,.14);display:grid;place-items:center;margin:0 auto 16px">' + ICO('phone', '', 34) + '</div>' +
      '<h2>تسجيل في ١٥ ثانية</h2><p style="margin-top:8px">اسمك ورقم تليفونك بس. مفيش باسورد ولا خطوات طويلة.</p></div></div>' +
      '<div class="grow">' +
      '<label class="field"><span style="color:rgba(255,255,255,.8)">الاسم</span>' +
      '<input class="input" value="محمد نبيل" style="background:rgba(255,255,255,.1);border-color:rgba(255,255,255,.22);color:#fff"></label>' +
      '<label class="field"><span style="color:rgba(255,255,255,.8)">رقم الموبايل</span>' +
      '<input class="input num" value="٠١٠٠١٢٣٤٥٦٧" style="background:rgba(255,255,255,.1);border-color:rgba(255,255,255,.22);color:#fff"></label>' +
      '<div class="t-xs" style="color:rgba(255,255,255,.6);line-height:1.7">بالمتابعة أنت توافق على الشروط وسياسة الخصوصية، وتقدر تسحب موافقتك في أي وقت من إعدادات الحساب.</div>' +
      '<div class="otp mt-3"><input value="٤" readonly><input value="٨" readonly><input value="٢" readonly><input value="١" readonly></div>' +
      '<p class="center t-xs" style="color:rgba(255,255,255,.6)">أدخلنا كود التجربة تلقائيًا</p></div>' +
      '<div class="foot"><button class="btn btn-lg btn-block" style="background:#fff;color:var(--violet-800)" onclick="CUS.finishReg()">تأكيد وإنشاء الحساب</button></div></div>';
  }

  /* ================= المسح والنجاح ================= */
  function scanView() {
    return '<div class="scanview" data-anim>' + statusbar(true) +
      '<button class="scan-close" onclick="CUS.closeOverlay()">' + ICO('x') + '</button>' +
      '<div class="scan-cam"><div class="scan-frame"><div class="laser"></div>' +
      '<div class="cn c1"></div><div class="cn c2"></div><div class="cn c3"></div><div class="cn c4"></div></div></div>' +
      '<div class="scan-hint"><h3>وجّه الكاميرا لرمز المتجر</h3>' +
      '<p>الرمز معروض على شاشة الكاشير ويتغيّر كل ٣٠ ثانية لحماية حسابك.</p></div>' +
      '<div class="scan-actions">' +
      '<button class="btn btn-green btn-lg btn-block" onclick="CUS.amount()">' + ICO('checkc') + ' محاكاة: تم قراءة الرمز</button>' +
      '<button class="btn btn-block" style="color:rgba(255,255,255,.65)" onclick="CUS.manual()">أو أدخل كود المتجر يدويًا</button>' +
      '</div></div>';
  }
  function amountView() {
    return '<div class="scanview" data-anim style="background:#0B0918">' + statusbar(true) +
      '<button class="scan-close" onclick="CUS.closeOverlay()">' + ICO('x') + '</button>' +
      '<div class="scan-cam" style="background:radial-gradient(circle at 50% 35%,#123A25,#0B0918 70%)">' +
      '<div class="center" style="padding:0 34px;width:100%">' +
      '<div style="width:62px;height:62px;border-radius:20px;background:rgba(74,222,128,.18);display:grid;place-items:center;margin:0 auto 16px;color:#4ADE80" class="anim-pop">' + ICO('checkc', '', 32) + '</div>' +
      '<h3 style="font-size:19px">كافيه بن وسط</h3>' +
      '<p style="opacity:.6;font-size:12.5px;margin-top:4px">الفرع الرئيسي · الكاشير محمود</p>' +
      '<div style="margin-top:26px"><div style="font-size:12px;opacity:.6;font-weight:700;margin-bottom:8px">قيمة الفاتورة</div>' +
      '<div style="font-size:44px;font-weight:800;line-height:1" class="num">٦٥ <span style="font-size:19px;opacity:.6">ج</span></div></div>' +
      '<p style="opacity:.5;font-size:11.5px;margin-top:18px;line-height:1.7">صاحب المتجر هيأكد العملية من لوحته.<br>الرمز صالح لمرة واحدة فقط.</p>' +
      '</div></div>' +
      '<div class="scan-actions"><button class="btn btn-green btn-lg btn-block" onclick="CUS.success()">تأكيد وكسب النقاط</button></div></div>';
  }
  function successView() {
    return '<div class="success" data-anim>' + statusbar(true) +
      '<div class="tick anim-pop">' + ICO('check', '', 48) + '</div>' +
      '<h2>تمام! 🎉</h2><p>اتسجّلت زيارتك في كافيه بن وسط</p>' +
      '<div class="gain">+١ ختم</div>' +
      '<p>باقي لك <b>ختمين</b> على القهوة المجانية</p>' +
      '<div class="recap">' +
      '<div class="r"><span>قيمة الفاتورة</span><b class="num">٦٥ ج</b></div>' +
      '<div class="r"><span>رصيدك الآن</span><b class="num">٨ من ١٠ أختام</b></div>' +
      '<div class="r"><span>رقم العملية</span><b class="num">#WL-8842</b></div></div>' +
      '<button class="btn btn-lg btn-block mt-4" style="background:#fff;color:var(--green-700)" onclick="CUS.closeOverlay(1)">تمام</button></div>';
  }

  /* ================= الواجهة العامة ================= */
  var router;
  var CUS = {
    init: function () {
      root = $('#screen');
      router = UI.router(root, S, function (name) {
        var map = { home:'home', stores:'stores', rewards:'rewards', me:'me' };
        if (map[name]) tab = name;
        CUS.paintTabs();
      });
      var h=(location.hash||'').replace('#','');
      router.go(S[h]?h:'home');
      CUS.paintTabs();
    },
    go: function (n, a) { CUS.closeOverlay(); router.go(n, a); if(location.hash.slice(1)!==n) location.hash=n; },
    setTab: function (n) { CUS.go(n); },
    paintTabs: function () {
      var items = [
        { id:'home',    ic:'home',   l:'الرئيسية' },
        { id:'stores',  ic:'store',  l:'المتاجر' },
        { id:'scan',    ic:'scan',   l:'' },
        { id:'rewards', ic:'gift',   l:'المكافآت' },
        { id:'me',      ic:'user',   l:'حسابي' }
      ];
      $('#tabbar').innerHTML = items.map(function (t) {
        if (t.id === 'scan') return '<div class="tab scan" onclick="CUS.scan()"><div class="fab">' + ICO('scan') + '</div></div>';
        return '<div class="tab ' + (tab === t.id ? 'on' : '') + '" onclick="CUS.setTab(\'' + t.id + '\')">' + ICO(t.ic) + '<span>' + t.l + '</span></div>';
      }).join('');
    },
    overlay: function (h) {
      var o = $('#overlay'); o.innerHTML = h; o.style.display = 'block';
    },
    closeOverlay: function (toast) {
      var o = $('#overlay'); if (o) { o.innerHTML = ''; o.style.display = 'none'; }
      if (toast) { router.go('home'); UI.toast('رصيدك اتحدّث · +١ ختم'); }
    },
    scan:    function () { CUS.overlay(scanView()); },
    amount:  function () { CUS.overlay(amountView()); },
    success: function () { CUS.overlay(successView()); },
    manual:  function () { UI.toast('أدخل كود المتجر: WL-2291', 'warn'); },
    redeem:  function (t) {
      CUS.overlay('<div class="success" data-anim style="background:linear-gradient(160deg,#3A1078,#6D3BD6)">' + statusbar(true) +
        '<div class="tick anim-pop">' + ICO('gift', '', 48) + '</div>' +
        '<h2>مبروك!</h2><p style="margin-top:6px">' + t + '</p>' +
        '<div style="background:#fff;border-radius:20px;padding:20px;margin-top:24px">' + UI.qr(7, 172) + '</div>' +
        '<p style="margin-top:16px;font-size:12.5px">اعرض الكود ده على الكاشير</p>' +
        '<div style="font-size:26px;font-weight:800;letter-spacing:3px;margin-top:6px" class="num">WL-4471</div>' +
        '<p style="opacity:.7;font-size:11.5px;margin-top:10px">صالح لمدة ١٥ دقيقة</p>' +
        '<button class="btn btn-lg btn-block mt-4" style="background:#fff;color:var(--violet-800)" onclick="CUS.closeOverlay()">تم</button></div>');
    },
    /* أونبوردنج */
    onb: function () { onbStep = 0; CUS.overlay(onbView()); },
    onbNext: function () {
      if (onbStep < ONB.length - 1) { onbStep++; CUS.overlay(onbView()); }
      else CUS.overlay(regView());
    },
    closeOnb: function () { CUS.closeOverlay(); },
    finishReg: function () { CUS.closeOverlay(); router.go('home'); UI.toast('أهلاً بيك في ولائي · +٥٠ نقطة ترحيبية'); }
  };
  g.CUS = CUS;
})(window);
