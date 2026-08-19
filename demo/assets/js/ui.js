/* ولائي — أدوات واجهة مشتركة (Router / Toast / Modal / Charts) */
(function (g) {
  var UI = {};

  /* ---------- DOM ---------- */
  UI.$  = function (s, r) { return (r || document).querySelector(s); };
  UI.$$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  UI.html = function (el, h) { if (el) el.innerHTML = h; return el; };

  /* ---------- Toast ---------- */
  UI.toast = function (msg, kind) {
    var t = UI.$('#toast');
    if (!t) { t = document.createElement('div'); t.id = 'toast'; document.body.appendChild(t); }
    t.className = kind === 'warn' ? 'warn' : '';
    t.innerHTML = ICO(kind === 'warn' ? 'warn' : 'checkc') + '<span>' + msg + '</span>';
    void t.offsetWidth; t.classList.add('show');
    clearTimeout(UI._tt);
    UI._tt = setTimeout(function () { t.classList.remove('show'); }, 2600);
  };

  /* ---------- Modal ---------- */
  UI.modal = function (title, body, foot) {
    var ov = UI.$('#ov');
    if (!ov) {
      ov = document.createElement('div'); ov.id = 'ov'; ov.className = 'ov';
      document.body.appendChild(ov);
      ov.addEventListener('click', function (e) { if (e.target === ov) UI.closeModal(); });
    }
    ov.innerHTML =
      '<div class="card">' +
        '<div class="card-hd"><h3>' + title + '</h3>' +
          '<button class="btn btn-line btn-sm" onclick="UI.closeModal()">' + ICO('x') + '</button></div>' +
        '<div class="card-p">' + body + '</div>' +
        (foot ? '<div class="card-p" style="border-top:1px solid var(--line-2);display:flex;gap:10px;justify-content:flex-end">' + foot + '</div>' : '') +
      '</div>';
    void ov.offsetWidth; ov.classList.add('show');
  };
  UI.closeModal = function () { var o = UI.$('#ov'); if (o) o.classList.remove('show'); };

  /* ---------- Router (hash-less, screen swapping) ---------- */
  UI.router = function (root, screens, onChange) {
    var cur = null;
    function go(name, arg) {
      if (!screens[name]) { console.warn('screen غير موجود:', name); return; }
      cur = name;
      root.innerHTML = screens[name](arg);
      root.scrollTop = 0;
      var sc = root.querySelector('[data-scroll]'); if (sc) sc.scrollTop = 0;
      if (onChange) onChange(name, arg);
      UI.$$('[data-anim]', root).forEach(function (el, i) {
        el.classList.add('anim'); el.style.animationDelay = (i * 0.045) + 's';
      });
    }
    return { go: go, current: function () { return cur; } };
  };

  /* ---------- تنسيق الأرقام العربية ---------- */
  var AR = ['٠','١','٢','٣','٤','٥','٦','٧','٨','٩'];
  UI.ar = function (n) {
    return String(n).replace(/\d/g, function (d) { return AR[+d]; });
  };
  UI.arNum = function (n) {
    return UI.ar(Number(n).toLocaleString('en-US'));
  };

  /* ---------- رسم بياني: أعمدة ---------- */
  UI.barChart = function (data, labels, opt) {
    opt = opt || {};
    var w = opt.w || 640, h = opt.h || 190, pad = 22, gap = 7;
    var max = Math.max.apply(null, data) * 1.12;
    var bw = (w - pad * 2 - gap * (data.length - 1)) / data.length;
    var s = '<svg viewBox="0 0 ' + w + ' ' + (h + 26) + '" style="width:100%;height:auto;overflow:visible">';
    s += '<defs><linearGradient id="bg1" x1="0" y1="0" x2="0" y2="1">' +
         '<stop offset="0" stop-color="#6D3BD6"/><stop offset="1" stop-color="#4B1E9E"/></linearGradient>' +
         '<linearGradient id="bg2" x1="0" y1="0" x2="0" y2="1">' +
         '<stop offset="0" stop-color="#34D399"/><stop offset="1" stop-color="#16A34A"/></linearGradient></defs>';
    for (var gl = 0; gl <= 3; gl++) {
      var gy = pad + (h - pad * 2) * gl / 3;
      s += '<line x1="' + pad + '" y1="' + gy + '" x2="' + (w - pad) + '" y2="' + gy + '" stroke="#EFEBF9" stroke-width="1"/>';
    }
    data.forEach(function (v, i) {
      var bh = (v / max) * (h - pad * 2);
      var x = w - pad - bw - i * (bw + gap);   /* RTL: من اليمين لليسار */
      var y = h - pad - bh;
      s += '<rect x="' + x + '" y="' + y + '" width="' + bw + '" height="' + bh + '" rx="5" fill="url(#' + (opt.green ? 'bg2' : 'bg1') + ')">' +
           '<animate attributeName="height" from="0" to="' + bh + '" dur="0.7s" fill="freeze"/>' +
           '<animate attributeName="y" from="' + (h - pad) + '" to="' + y + '" dur="0.7s" fill="freeze"/></rect>';
      if (labels && labels[i]) {
        s += '<text x="' + (x + bw / 2) + '" y="' + (h - 4) + '" text-anchor="middle" font-size="10" fill="#9A9AB5" font-family="Cairo,sans-serif">' + labels[i] + '</text>';
      }
    });
    return s + '</svg>';
  };

  /* ---------- رسم بياني: خطي ---------- */
  UI.lineChart = function (data, opt) {
    opt = opt || {};
    var w = opt.w || 640, h = opt.h || 150, pad = 14;
    var max = Math.max.apply(null, data) * 1.15, min = 0;
    var step = (w - pad * 2) / (data.length - 1);
    var pts = data.map(function (v, i) {
      var x = w - pad - i * step;  /* RTL */
      var y = h - pad - ((v - min) / (max - min)) * (h - pad * 2);
      return [x, y];
    });
    var d = pts.map(function (p, i) { return (i ? 'L' : 'M') + p[0].toFixed(1) + ' ' + p[1].toFixed(1); }).join(' ');
    var area = d + ' L' + pts[pts.length - 1][0] + ' ' + (h - pad) + ' L' + pts[0][0] + ' ' + (h - pad) + ' Z';
    var s = '<svg viewBox="0 0 ' + w + ' ' + h + '" style="width:100%;height:auto">';
    s += '<defs><linearGradient id="ar1" x1="0" y1="0" x2="0" y2="1">' +
         '<stop offset="0" stop-color="#6D3BD6" stop-opacity=".28"/>' +
         '<stop offset="1" stop-color="#6D3BD6" stop-opacity="0"/></linearGradient></defs>';
    s += '<path d="' + area + '" fill="url(#ar1)"/>';
    s += '<path d="' + d + '" fill="none" stroke="#4B1E9E" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>';
    pts.forEach(function (p, i) {
      if (i === 0) s += '<circle cx="' + p[0] + '" cy="' + p[1] + '" r="4.5" fill="#fff" stroke="#4B1E9E" stroke-width="2.5"/>';
    });
    return s + '</svg>';
  };

  /* ---------- حلقة تقدم ---------- */
  UI.ring = function (pct, size, stroke, color) {
    size = size || 120; stroke = stroke || 10; color = color || '#4B1E9E';
    var r = (size - stroke) / 2, c = 2 * Math.PI * r, off = c * (1 - pct / 100);
    return '<svg width="' + size + '" height="' + size + '" viewBox="0 0 ' + size + ' ' + size + '">' +
      '<circle cx="' + size / 2 + '" cy="' + size / 2 + '" r="' + r + '" fill="none" stroke="rgba(255,255,255,.22)" stroke-width="' + stroke + '"/>' +
      '<circle cx="' + size / 2 + '" cy="' + size / 2 + '" r="' + r + '" fill="none" stroke="' + color + '" stroke-width="' + stroke + '" ' +
      'stroke-linecap="round" stroke-dasharray="' + c + '" stroke-dashoffset="' + c + '" ' +
      'transform="rotate(-90 ' + size / 2 + ' ' + size / 2 + ')">' +
      '<animate attributeName="stroke-dashoffset" from="' + c + '" to="' + off + '" dur="1.1s" fill="freeze" calcMode="spline" keySplines="0.4 0 0.2 1"/>' +
      '</circle></svg>';
  };

  /* ---------- QR وهمي (شبكة عشوائية ثابتة) ---------- */
  UI.qr = function (seed, size, dark) {
    size = size || 168; dark = dark || '#14142B';
    var n = 21, cell = size / n, s = '<svg width="' + size + '" height="' + size + '" viewBox="0 0 ' + size + ' ' + size + '" style="border-radius:8px">';
    s += '<rect width="' + size + '" height="' + size + '" fill="#fff"/>';
    function rnd(i) { var x = Math.sin(seed * 9973 + i * 137.7) * 43758.5453; return x - Math.floor(x); }
    function finder(cx, cy) {
      var o = '';
      o += '<rect x="' + cx * cell + '" y="' + cy * cell + '" width="' + cell * 7 + '" height="' + cell * 7 + '" fill="' + dark + '" rx="3"/>';
      o += '<rect x="' + (cx + 1) * cell + '" y="' + (cy + 1) * cell + '" width="' + cell * 5 + '" height="' + cell * 5 + '" fill="#fff" rx="2"/>';
      o += '<rect x="' + (cx + 2) * cell + '" y="' + (cy + 2) * cell + '" width="' + cell * 3 + '" height="' + cell * 3 + '" fill="' + dark + '" rx="1.5"/>';
      return o;
    }
    for (var y = 0; y < n; y++) for (var x = 0; x < n; x++) {
      var inF = (x < 8 && y < 8) || (x > n - 9 && y < 8) || (x < 8 && y > n - 9);
      if (inF) continue;
      if (rnd(y * n + x) > 0.52) s += '<rect x="' + x * cell + '" y="' + y * cell + '" width="' + cell + '" height="' + cell + '" fill="' + dark + '"/>';
    }
    s += finder(0, 0) + finder(n - 7, 0) + finder(0, n - 7);
    return s + '</svg>';
  };


  /* ---------- عدّاد رقمي متحرك ---------- */
  UI.count = function (el, to, opt) {
    opt = opt || {};
    var dur = opt.dur || 900, dec = opt.dec || 0, pre = opt.pre || '', suf = opt.suf || '';
    var t0 = null, from = opt.from || 0;
    function step(ts) {
      if (!t0) t0 = ts;
      var p = Math.min((ts - t0) / dur, 1), e = 1 - Math.pow(1 - p, 3);
      var v = (from + (to - from) * e).toFixed(dec);
      el.textContent = pre + UI.ar(Number(v).toLocaleString('en-US')) + suf;
      if (p < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  };
  UI.countAll = function (root) {
    UI.$$('[data-n]', root || document).forEach(function (el) {
      if (el.dataset.done) return; el.dataset.done = '1';
      UI.count(el, parseFloat(el.dataset.n), {
        dec: +(el.dataset.dec || 0), pre: el.dataset.pre || '', suf: el.dataset.suf || '',
        dur: +(el.dataset.dur || 900)
      });
    });
  };

  /* ---------- خط بياني مصغّر (Sparkline) ---------- */
  UI.spark = function (data, opt) {
    opt = opt || {};
    var w = opt.w || 100, h = opt.h || 30, c = opt.color || '#4B1E9E', fill = opt.fill !== false;
    var max = Math.max.apply(null, data), min = Math.min.apply(null, data);
    var rng = (max - min) || 1, step = w / (data.length - 1);
    var pts = data.map(function (v, i) {
      return [w - i * step, h - 2 - ((v - min) / rng) * (h - 6)];   /* RTL */
    });
    var d = pts.map(function (p, i) { return (i ? 'L' : 'M') + p[0].toFixed(1) + ' ' + p[1].toFixed(1); }).join(' ');
    var id = 'sp' + Math.floor(Math.abs(data[0] * 977 + data.length * 31));
    var s = '<svg viewBox="0 0 ' + w + ' ' + h + '" style="width:100%;height:' + h + 'px;overflow:visible">';
    if (fill) {
      s += '<defs><linearGradient id="' + id + '" x1="0" y1="0" x2="0" y2="1">' +
           '<stop offset="0" stop-color="' + c + '" stop-opacity=".3"/>' +
           '<stop offset="1" stop-color="' + c + '" stop-opacity="0"/></linearGradient></defs>' +
           '<path d="' + d + ' L' + pts[pts.length - 1][0] + ' ' + h + ' L' + pts[0][0] + ' ' + h + ' Z" fill="url(#' + id + ')"/>';
    }
    s += '<path d="' + d + '" fill="none" stroke="' + c + '" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" ' +
         'pathLength="1" style="stroke-dasharray:1;stroke-dashoffset:1;animation:draw .9s cubic-bezier(.4,0,.2,1) forwards"/>';
    s += '<circle cx="' + pts[0][0] + '" cy="' + pts[0][1] + '" r="2.6" fill="' + c + '"/>';
    return s + '</svg>';
  };

  /* ---------- احتفال (Confetti) ---------- */
  UI.confetti = function (host, n) {
    n = n || 26;
    var cols = ['#F97316', '#16A34A', '#6D3BD6', '#FDBA74', '#4ADE80', '#fff'];
    var box = document.createElement('div');
    box.className = 'cfti';
    var h = '';
    for (var i = 0; i < n; i++) {
      var x = Math.random() * 100, d = (Math.random() * .5).toFixed(2),
          r = (Math.random() * 360) | 0, sz = 5 + Math.random() * 6,
          c = cols[i % cols.length], sq = Math.random() > .5;
      h += '<i style="left:' + x.toFixed(1) + '%;width:' + sz.toFixed(1) + 'px;height:' + (sz * (sq ? 1 : 1.7)).toFixed(1) +
           'px;background:' + c + ';animation-delay:' + d + 's;transform:rotate(' + r + 'deg);' +
           (sq ? 'border-radius:2px' : 'border-radius:50%') + '"></i>';
    }
    box.innerHTML = h;
    (host || document.body).appendChild(box);
    setTimeout(function () { box.remove(); }, 2600);
  };

  /* ---------- لوحة جانبية (Drawer) ---------- */
  UI.drawer = function (title, body, foot) {
    var d = UI.$('#drw');
    if (!d) {
      d = document.createElement('div'); d.id = 'drw'; d.className = 'drw';
      document.body.appendChild(d);
      d.addEventListener('click', function (e) { if (e.target === d) UI.closeDrawer(); });
    }
    d.innerHTML = '<aside><header><h3>' + title + '</h3>' +
      '<button class="btn btn-line btn-sm" onclick="UI.closeDrawer()">' + ICO('x') + '</button></header>' +
      '<div class="dbody">' + body + '</div>' +
      (foot ? '<footer>' + foot + '</footer>' : '') + '</aside>';
    void d.offsetWidth; d.classList.add('show');
    UI.countAll(d);
  };
  UI.closeDrawer = function () { var d = UI.$('#drw'); if (d) d.classList.remove('show'); };

  /* ---------- هيكل تحميل (Skeleton) ---------- */
  UI.skel = function (rows, h) {
    var o = '';
    for (var i = 0; i < (rows || 3); i++) o += '<div class="sk" style="height:' + (h || 54) + 'px"></div>';
    return '<div class="skwrap">' + o + '</div>';
  };

  /* ---------- تموّج عند الضغط (Ripple) ---------- */
  UI.ripple = function (e) {
    var t = e.currentTarget, r = t.getBoundingClientRect();
    var i = document.createElement('span');
    i.className = 'rpl';
    var size = Math.max(r.width, r.height);
    i.style.width = i.style.height = size + 'px';
    i.style.left = (e.clientX - r.left - size / 2) + 'px';
    i.style.top = (e.clientY - r.top - size / 2) + 'px';
    t.appendChild(i);
    setTimeout(function () { i.remove(); }, 620);
  };

  /* ---------- وقت نسبي ---------- */
  UI.ago = function (mins) {
    if (mins < 1) return 'الآن';
    if (mins < 60) return 'منذ ' + UI.ar(mins) + ' دقيقة';
    if (mins < 1440) return 'منذ ' + UI.ar(Math.floor(mins / 60)) + ' ساعة';
    return 'منذ ' + UI.ar(Math.floor(mins / 1440)) + ' يوم';
  };

  g.UI = UI;
})(window);
