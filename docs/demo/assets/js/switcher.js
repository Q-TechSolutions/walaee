/* ولائي — مبدّل الواجهات العائم + زر العودة لأعلى
   يُحقن تلقائيًا في أي صفحة تستدعيه. لا يحتاج أي إعداد. */
(function () {
  /* لا يظهر داخل iframe — وضع التضمين في صفحة تصفّح الواجهات */
  if (window.self !== window.top) return;
  var here = location.pathname.replace(/\\/g, '/');
  function at(seg) { return here.indexOf('/' + seg + '/') > -1; }

  var base = at('customer') || at('merchant') || at('admin') || at('plan') ||
             at('architecture') || at('present') || at('team') || at('pricing') || at('solutions') || at('preview') ? '../' : './';

  var ITEMS = [
    { k:'index',        l:'المعرض',    href: base + 'index.html',              ic:'grid'  },
    { k:'present',      l:'العرض',     href: base + 'present/index.html',      ic:'play'  },
    { k:'preview',      l:'تصفّح الواجهات', href: base + 'preview/index.html',  ic:'grid'  },
    { k:'customer',     l:'العميل',    href: base + 'customer/index.html',     ic:'phone' },
    { k:'merchant',     l:'التاجر',    href: base + 'merchant/index.html',     ic:'store' },
    { k:'admin',        l:'الإدارة',   href: base + 'admin/index.html',        ic:'cog'   },
    { k:'pricing',      l:'عرض السعر', href: base + 'pricing/index.html',      ic:'cash'  },
    { k:'solutions',    l:'الحلول',    href: base + 'solutions/index.html',    ic:'check' },
    { k:'plan',         l:'الخطة',     href: base + 'plan/index.html',         ic:'doc'   },
    { k:'architecture', l:'المعمارية', href: base + 'architecture/index.html', ic:'code'  },
    { k:'team',         l:'الفريق ⚠',  href: base + 'team/index.html',         ic:'users', int:true }
  ];

  var I = {
    grid:'<rect x="3.5" y="3.5" width="7" height="7" rx="1.5"/><rect x="13.5" y="3.5" width="7" height="7" rx="1.5"/><rect x="3.5" y="13.5" width="7" height="7" rx="1.5"/><rect x="13.5" y="13.5" width="7" height="7" rx="1.5"/>',
    play:'<path d="M7 4.5v15l13-7.5z" fill="currentColor" stroke="none"/>',
    phone:'<rect x="6" y="2.5" width="12" height="19" rx="2.6"/><path d="M10.5 5.6h3"/>',
    store:'<path d="M3 9V6.5A1.5 1.5 0 0 1 4.5 5h15A1.5 1.5 0 0 1 21 6.5V9"/><path d="M3 9a3 3 0 0 0 6 0 3 3 0 0 0 6 0 3 3 0 0 0 6 0"/><path d="M5 12v7a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-7"/>',
    cog:'<circle cx="12" cy="12" r="3"/><path d="M12 3v2M12 19v2M21 12h-2M5 12H3M18.4 5.6l-1.4 1.4M7 17l-1.4 1.4M18.4 18.4 17 17M7 7 5.6 5.6"/>',
    doc:'<path d="M6 3h8l4 4v14a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1z"/><path d="M14 3v4h4M8.5 13h7M8.5 17h5"/>',
    code:'<path d="m9 8-5 4 5 4M15 8l5 4-5 4"/>',
    cash:'<circle cx="12" cy="12" r="9"/><path d="M15 9.5c-.6-1-1.8-1.5-3-1.5-1.7 0-3 .9-3 2s1 1.7 3 2 3 .9 3 2-1.3 2-3 2c-1.2 0-2.4-.5-3-1.5M12 6v12"/>',
    up:'<path d="M12 19V6M6.5 11.5 12 6l5.5 5.5"/>',
    check:'<path d="m4 12.5 5 5L20 6.5"/>',
    menu:'<path d="M4 7h16M4 12h16M4 17h16"/>'
  };
  function svg(n) {
    return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" ' +
           'stroke-linecap="round" stroke-linejoin="round">' + (I[n] || I.grid) + '</svg>';
  }

  var css = document.createElement('style');
  css.textContent = [
    '.wsw{position:fixed;bottom:20px;inset-inline-start:20px;z-index:500;display:flex;',
    '  flex-direction:column-reverse;align-items:flex-start;gap:9px;font-family:var(--font,sans-serif);}',
    '.wsw-t{width:46px;height:46px;border-radius:15px;display:grid;place-items:center;cursor:pointer;',
    '  background:linear-gradient(140deg,#6D3BD6,#3A1078);color:#fff;border:none;',
    '  box-shadow:0 10px 26px rgba(75,30,158,.45);transition:transform .2s,box-shadow .2s;}',
    '.wsw-t:hover{transform:translateY(-2px) scale(1.05);box-shadow:0 14px 32px rgba(75,30,158,.6);}',
    '.wsw-t:focus-visible{outline:3px solid #C4B4F5;outline-offset:2px;}',
    '.wsw-t svg{width:21px;height:21px;transition:transform .3s;}',
    '.wsw.open .wsw-t svg{transform:rotate(90deg);}',
    '.wsw-p{background:rgba(20,20,43,.94);backdrop-filter:blur(18px);border:1px solid rgba(255,255,255,.14);',
    '  border-radius:17px;padding:8px;display:flex;flex-direction:column;gap:3px;min-width:186px;',
    '  box-shadow:0 20px 50px rgba(0,0,0,.5);opacity:0;transform:translateY(10px) scale(.95);',
    '  pointer-events:none;transition:opacity .22s,transform .22s cubic-bezier(.34,1.4,.64,1);transform-origin:bottom right;}',
    '.wsw.open .wsw-p{opacity:1;transform:none;pointer-events:auto;}',
    '.wsw-p .hd{font-size:9.5px;letter-spacing:1.6px;color:#7E6FA8;font-weight:800;padding:5px 11px 7px;}',
    '.wsw-a{display:flex;align-items:center;gap:10px;padding:8px 11px;border-radius:11px;',
    '  color:#CFC3EC;font-size:13px;font-weight:700;text-decoration:none;transition:background .16s,color .16s;}',
    '.wsw-a:hover{background:rgba(255,255,255,.1);color:#fff;}',
    '.wsw-a:focus-visible{outline:2px solid #C4B4F5;outline-offset:-2px;}',
    '.wsw-a svg{width:16px;height:16px;opacity:.8;flex:none;}',
    '.wsw-a.on{background:rgba(109,59,214,.42);color:#fff;}',
    '.wsw-a.on::after{content:"";width:6px;height:6px;border-radius:50%;background:#4ADE80;margin-inline-start:auto;}',
    '.wsw-a.intl{color:#FDBA74;border-top:1px solid rgba(255,255,255,.1);margin-top:4px;padding-top:10px;}',
    '.wtop{position:fixed;bottom:20px;inset-inline-end:20px;z-index:500;width:42px;height:42px;',
    '  border-radius:13px;display:grid;place-items:center;cursor:pointer;border:1px solid var(--line,#E9E4F5);',
    '  background:var(--surface,#fff);color:var(--violet-700,#4B1E9E);box-shadow:0 6px 18px rgba(20,20,43,.14);',
    '  opacity:0;pointer-events:none;transition:opacity .25s,transform .25s;}',
    '.wtop.show{opacity:1;pointer-events:auto;}',
    '.wtop:hover{transform:translateY(-3px);}',
    '.wtop svg{width:19px;height:19px;}',
    '@media print{.wsw,.wtop{display:none !important;}}',
    '@media(max-width:600px){.wsw{bottom:14px;inset-inline-start:14px;}.wtop{bottom:14px;inset-inline-end:14px;}}'
  ].join('');
  document.head.appendChild(css);

  var wrap = document.createElement('div');
  wrap.className = 'wsw';
  wrap.innerHTML =
    '<button class="wsw-t" aria-label="تبديل الواجهة" aria-expanded="false">' + svg('menu') + '</button>' +
    '<div class="wsw-p" role="menu"><div class="hd">تنقّل سريع</div>' +
    ITEMS.map(function (it) {
      var on = (it.k === 'index') ? (!at('customer') && !at('merchant') && !at('admin') && !at('plan') &&
                                     !at('architecture') && !at('present') && !at('team') && !at('pricing') && !at('solutions') && !at('preview')) : at(it.k);
      return '<a class="wsw-a' + (on ? ' on' : '') + (it.int ? ' intl' : '') + '" role="menuitem" href="' + it.href + '">' +
             svg(it.ic) + '<span>' + it.l + '</span></a>';
    }).join('') + '</div>';
  document.body.appendChild(wrap);

  var btn = wrap.querySelector('.wsw-t');
  btn.addEventListener('click', function (e) {
    e.stopPropagation();
    var open = wrap.classList.toggle('open');
    btn.setAttribute('aria-expanded', open ? 'true' : 'false');
  });
  document.addEventListener('click', function () {
    wrap.classList.remove('open'); btn.setAttribute('aria-expanded', 'false');
  });
  wrap.querySelector('.wsw-p').addEventListener('click', function (e) { e.stopPropagation(); });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') { wrap.classList.remove('open'); btn.setAttribute('aria-expanded', 'false'); }
  });

  /* زر العودة لأعلى — للصفحات الطويلة فقط */
  if (document.body.scrollHeight > innerHeight * 1.8) {
    var top = document.createElement('button');
    top.className = 'wtop'; top.setAttribute('aria-label', 'العودة لأعلى');
    top.innerHTML = svg('up');
    top.addEventListener('click', function () { window.scrollTo({ top: 0, behavior: 'smooth' }); });
    document.body.appendChild(top);
    window.addEventListener('scroll', function () {
      top.classList.toggle('show', window.scrollY > 500);
    }, { passive: true });
  }
})();
