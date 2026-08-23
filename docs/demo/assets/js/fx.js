/* ولائي — حركة ثلاثية الأبعاد: إمالة بالمؤشر · بارالاكس · ظهور بالتمرير */
(function () {
  var reduce = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---------- ظهور بالتمرير ---------- */
  var items = [].slice.call(document.querySelectorAll('[data-r]'));
  if (reduce || !('IntersectionObserver' in window)) {
    items.forEach(function (el) { el.classList.add('in'); });
  } else {
    var seen = new WeakMap();
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (!e.isIntersecting) return;
        var g = seen.get(e.target.parentNode) || 0;
        e.target.style.setProperty('--d', Math.min(g, 6) * 0.07 + 's');
        seen.set(e.target.parentNode, g + 1);
        e.target.classList.add('in');
        io.unobserve(e.target);
      });
    }, { threshold: 0.12, rootMargin: '0px 0px -8% 0px' });
    items.forEach(function (el) { io.observe(el); });
  }
  if (reduce) return;

  /* ---------- إمالة البطاقة مع المؤشر ---------- */
  var tilts = [].slice.call(document.querySelectorAll('[data-tilt]'));
  tilts.forEach(function (el) {
    var box = null, raf = 0, tx = 0, ty = 0;
    var max = parseFloat(el.dataset.tilt) || 9;

    function apply() {
      raf = 0;
      el.style.transform =
        'perspective(1000px) rotateY(' + tx.toFixed(2) + 'deg) rotateX(' +
        ty.toFixed(2) + 'deg) translateZ(16px)';
    }
    el.addEventListener('pointerenter', function () {
      box = el.getBoundingClientRect();
      el.classList.add('tilting');
    });
    el.addEventListener('pointermove', function (e) {
      if (!box) box = el.getBoundingClientRect();
      var px = (e.clientX - box.left) / box.width - 0.5;
      var py = (e.clientY - box.top) / box.height - 0.5;
      tx = px * max; ty = -py * max;
      el.style.setProperty('--gx', (px * 100 + 50).toFixed(1) + '%');
      el.style.setProperty('--gy', (py * 100 + 50).toFixed(1) + '%');
      if (!raf) raf = requestAnimationFrame(apply);
    });
    el.addEventListener('pointerleave', function () {
      box = null; tx = ty = 0;
      if (raf) { cancelAnimationFrame(raf); raf = 0; }
      el.style.transform = '';
      el.classList.remove('tilting');
    });
  });

  /* ---------- بارالاكس بالمؤشر ---------- */
  var px = [].slice.call(document.querySelectorAll('[data-px]'));
  if (px.length) {
    var mx = 0, my = 0, pr = 0;
    function move() {
      pr = 0;
      px.forEach(function (el) {
        var d = parseFloat(el.dataset.px) || 1;
        el.style.transform = 'translate3d(' + (mx * d * 26).toFixed(1) + 'px,' +
                             (my * d * 26).toFixed(1) + 'px,0)';
      });
    }
    window.addEventListener('pointermove', function (e) {
      mx = e.clientX / innerWidth - 0.5;
      my = e.clientY / innerHeight - 0.5;
      if (!pr) pr = requestAnimationFrame(move);
    }, { passive: true });
  }

  /* ---------- عمق عند التمرير ---------- */
  var depth = [].slice.call(document.querySelectorAll('[data-depth]'));
  if (depth.length) {
    var sr = 0;
    function onScroll() {
      sr = 0;
      var y = window.scrollY;
      depth.forEach(function (el) {
        var d = parseFloat(el.dataset.depth) || 1;
        el.style.transform = 'translate3d(0,' + (y * d * -0.04).toFixed(1) + 'px,0)';
      });
    }
    window.addEventListener('scroll', function () {
      if (!sr) sr = requestAnimationFrame(onScroll);
    }, { passive: true });
  }
})();
