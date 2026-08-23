/* ولائي — محرك العرض التقديمي ثلاثي الأبعاد */
(function (g) {
  var slides = [], i = 0, autoT = null, hudT = null;

  var D = {
    init: function () {
      slides = Array.prototype.slice.call(document.querySelectorAll('.slide'));
      D.buildOverview();
      D.stagger();
      D.parallax();

      /* من الرابط: #5 */
      var h = parseInt((location.hash || '').replace('#', ''), 10);
      D.go(isNaN(h) ? 0 : h - 1, true);

      /* لوحة المفاتيح */
      document.addEventListener('keydown', function (e) {
        var k = e.key;
        if (k === 'ArrowLeft' || k === 'ArrowDown' || k === 'PageDown' || k === ' ') { e.preventDefault(); D.next(); }
        else if (k === 'ArrowRight' || k === 'ArrowUp' || k === 'PageUp') { e.preventDefault(); D.prev(); }
        else if (k === 'Home') D.go(0);
        else if (k === 'End') D.go(slides.length - 1);
        else if (k === 'o' || k === 'O') D.overview();
        else if (k === 'f' || k === 'F') D.full();
        else if (k === 'p' || k === 'P') D.auto();
        else if (k === 'Escape') D.closeOverview();
        else if (k >= '1' && k <= '9') D.go(+k - 1);
      });

      /* عجلة الماوس */
      var lock = false;
      window.addEventListener('wheel', function (e) {
        if (lock || document.querySelector('.ovl.show')) return;
        if (Math.abs(e.deltaY) < 18) return;
        lock = true; setTimeout(function () { lock = false; }, 780);
        if (e.deltaY > 0) D.next(); else D.prev();
      }, { passive: true });

      /* اللمس */
      var x0 = null;
      window.addEventListener('touchstart', function (e) { x0 = e.touches[0].clientX; }, { passive: true });
      window.addEventListener('touchend', function (e) {
        if (x0 === null) return;
        var dx = e.changedTouches[0].clientX - x0;
        if (Math.abs(dx) > 55) { if (dx > 0) D.next(); else D.prev(); }  /* RTL */
        x0 = null;
      }, { passive: true });

      /* إخفاء شريط التحكم عند السكون */
      ['mousemove', 'keydown', 'touchstart'].forEach(function (ev) {
        window.addEventListener(ev, D.wake, { passive: true });
      });
      D.wake();

      /* شريط التقدم قابل للنقر */
      var tr = document.querySelector('.hud .track');
      if (tr) tr.addEventListener('click', function (e) {
        var r = tr.getBoundingClientRect();
        var p = 1 - (e.clientX - r.left) / r.width;      /* RTL */
        D.go(Math.round(p * (slides.length - 1)));
      });
    },

    /* ---- تأخير ظهور العناصر بالتتابع ---- */
    stagger: function () {
      slides.forEach(function (s) {
        Array.prototype.slice.call(s.querySelectorAll('[data-r]')).forEach(function (el, n) {
          el.style.setProperty('--d', (0.09 + n * 0.075).toFixed(2) + 's');
        });
      });
    },

    /* ---- تأثير المنظور مع حركة الماوس ---- */
    parallax: function () {
      var orbs = Array.prototype.slice.call(document.querySelectorAll('.bgfx .orb'));
      var leaves = Array.prototype.slice.call(document.querySelectorAll('.leafx'));
      window.addEventListener('mousemove', function (e) {
        var x = (e.clientX / innerWidth - .5), y = (e.clientY / innerHeight - .5);
        orbs.forEach(function (o, n) {
          var k = (n + 1) * 26;
          o.style.transform = 'translate3d(' + (-x * k) + 'px,' + (-y * k) + 'px,0)';
        });
        leaves.forEach(function (l, n) {
          var k = (n % 3 + 1) * 15;
          l.style.transform = 'translate3d(' + (x * k) + 'px,' + (y * k) + 'px,0) rotate(' + (x * 9) + 'deg)';
        });
        var on = slides[i];
        if (on) {
          var inner = on.querySelector('.inner');
          if (inner) inner.style.transform = 'rotateY(' + (x * 2.6) + 'deg) rotateX(' + (-y * 1.8) + 'deg)';
        }
      }, { passive: true });
    },

    /* ---- التنقل ---- */
    go: function (n, silent) {
      if (n < 0) n = 0;
      if (n > slides.length - 1) n = slides.length - 1;
      i = n;
      slides.forEach(function (s, k) {
        s.classList.toggle('on', k === i);
        s.classList.toggle('done', k < i);
        if (k === i) { D.counters(s); D.frames(s); }
      });
      var t = slides[i].dataset.title || '';
      var c = document.querySelector('.hud .count');
      if (c) c.innerHTML = '<b>' + (i + 1) + '</b> / ' + slides.length;
      var tt = document.querySelector('.hud .ttl2'); if (tt) tt.textContent = t;
      var pr = document.querySelector('.hud .track i');
      if (pr) pr.style.width = ((i + 1) / slides.length * 100) + '%';
      Array.prototype.slice.call(document.querySelectorAll('.ovc')).forEach(function (c2, k) {
        c2.classList.toggle('on', k === i);
      });
      if (!silent) location.hash = i + 1;
      D.wake();
    },
    next: function () { if (i < slides.length - 1) D.go(i + 1); else if (autoT) D.auto(); },
    prev: function () { D.go(i - 1); },

    /* ---- عدّادات رقمية متحركة ---- */
    counters: function (s) {
      Array.prototype.slice.call(s.querySelectorAll('[data-count]')).forEach(function (el) {
        var to = parseFloat(el.dataset.count), dec = (el.dataset.dec | 0);
        var pre = el.dataset.pre || '', suf = el.dataset.suf || '';
        var t0 = null, dur = 1250;
        function step(ts) {
          if (!t0) t0 = ts;
          var p = Math.min((ts - t0) / dur, 1);
          var e = 1 - Math.pow(1 - p, 3);
          var v = (to * e).toFixed(dec);
          el.textContent = pre + UI.ar(Number(v).toLocaleString('en-US')) + suf;
          if (p < 1) requestAnimationFrame(step);
        }
        el.textContent = pre + '٠' + suf;
        requestAnimationFrame(step);
      });
    },

    /* ---- تحميل الإطارات الحية عند الحاجة فقط ---- */
    frames: function (s) {
      Array.prototype.slice.call(s.querySelectorAll('iframe[data-src]')).forEach(function (f) {
        if (!f.src) { f.src = f.dataset.src; }
      });
    },

    /* ---- عرض الشرائح ---- */
    buildOverview: function () {
      var tones = ['#8B5CF6', '#4ADE80', '#FDBA74', '#93C5FD', '#FCA5A5'];
      var html = slides.map(function (s, n) {
        return '<button class="ovc" style="color:' + tones[n % 5] + '" onclick="DECK.jump(' + n + ')">' +
          '<div class="n">شريحة ' + UI.ar(n + 1) + '</div>' +
          '<b>' + (s.dataset.title || '—') + '</b>' +
          '<div class="st2"></div></button>';
      }).join('');
      var el = document.querySelector('.ovgrid');
      if (el) el.innerHTML = html;
    },
    overview: function () { document.querySelector('.ovl').classList.toggle('show'); },
    closeOverview: function () { document.querySelector('.ovl').classList.remove('show'); },
    jump: function (n) { D.closeOverview(); D.go(n); },

    /* ---- ملء الشاشة ---- */
    full: function () {
      if (!document.fullscreenElement) {
        (document.documentElement.requestFullscreen || function () {}).call(document.documentElement);
      } else { document.exitFullscreen(); }
    },

    /* ---- تشغيل تلقائي ---- */
    auto: function () {
      var b = document.getElementById('autoBtn');
      if (autoT) { clearInterval(autoT); autoT = null; if (b) b.classList.remove('act'); UI.toast('تم إيقاف التشغيل التلقائي'); }
      else {
        autoT = setInterval(function () {
          if (i >= slides.length - 1) { clearInterval(autoT); autoT = null; if (b) b.classList.remove('act'); return; }
          D.next();
        }, 8500);
        if (b) b.classList.add('act');
        UI.toast('تشغيل تلقائي — ٨.٥ ثانية للشريحة');
      }
    },

    /* ---- إظهار/إخفاء شريط التحكم ---- */
    wake: function () {
      var h = document.querySelector('.hud'), k = document.querySelector('.keys');
      if (h) h.classList.remove('hide');
      if (k) k.classList.remove('hide');
      clearTimeout(hudT);
      hudT = setTimeout(function () {
        if (document.querySelector('.ovl.show')) return;
        if (h) h.classList.add('hide');
        if (k) k.classList.add('hide');
      }, 3600);
    }
  };

  g.DECK = D;
  document.addEventListener('DOMContentLoaded', D.init);
})(window);
