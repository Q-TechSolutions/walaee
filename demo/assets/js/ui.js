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

  g.UI = UI;
})(window);
