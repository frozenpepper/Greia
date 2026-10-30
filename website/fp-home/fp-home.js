// FrozenPepper home badge: the 3D logo linking back to www.frozenpepper.it, for the project sites
// hosted under it (greia/, synthasia/…). It turns once when pointed at, like the header logo on the
// main site. Source: Main-website/theme/assets/fp-home/; copy this folder into a site and add
//
//   <a class="fp-home" href="https://www.frozenpepper.it/" title="FrozenPepper" aria-label="FrozenPepper home page">
//     <img src="fp-home/mark.webp" width="44" height="44" alt=""></a>
//   <script src="fp-home/fp-home.js" defer></script>
//
// The link and the still logo work without JavaScript; this adds the turn (frames: mark-spin.webp,
// next to the still, loaded on first hover). Size it from the site's CSS (.fp-home { width; height }).
(() => {
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const css = document.createElement('style');
  css.textContent = `.fp-home{position:relative;display:inline-block;flex:none;width:44px;height:44px;line-height:0}
.fp-home img,.fp-home canvas{position:absolute;inset:0;width:100%;height:100%;-webkit-user-drag:none}
.fp-home canvas{visibility:hidden;will-change:transform}
.fp-home.turning canvas{visibility:visible}.fp-home.turning img{visibility:hidden}
.fp-home:focus-visible{outline:2px solid currentColor;outline-offset:4px;border-radius:6px}`;
  document.head.prepend(css);   // first, so the site's own rules win

  // anticipation at the start, overshoot at the end
  const backInOut = (x, s = 1.25) => {
    const c = s * 1.525;
    return x < .5 ? (Math.pow(2 * x, 2) * ((c + 1) * 2 * x - c)) / 2 : (Math.pow(2 * x - 2, 2) * ((c + 1) * (2 * x - 2) + c) + 2) / 2;
  };

  document.querySelectorAll('a.fp-home').forEach((link) => {
    const still = link.querySelector('img');
    if (!still) return;
    const cv = document.createElement('canvas');
    cv.width = cv.height = 120;
    cv.setAttribute('aria-hidden', 'true');
    link.append(cv);
    const ctx = cv.getContext('2d'), n = 60, turnMs = 1300;
    let strip = null, ready = null, raf = 0, t0 = 0;
    const load = () => ready || (ready = new Promise((res) => {
      const im = new Image();
      im.onload = () => { strip = im; res(true); };
      im.onerror = () => res(false);
      im.src = still.src.replace(/mark\.webp(\?.*)?$/, 'mark-spin.webp');
    }));
    // frame floor(a), with frame floor(a)+1 faded in: smooth at any speed
    const draw = (a) => {
      const fw = strip.naturalHeight, i = Math.floor(a), f = a - i, A = ((i % n) + n) % n, B = (A + 1) % n;
      ctx.clearRect(0, 0, 120, 120);
      ctx.drawImage(strip, A * fw, 0, fw, fw, 0, 0, 120, 120);
      if (f > .02) { ctx.globalAlpha = f; ctx.drawImage(strip, B * fw, 0, fw, fw, 0, 0, 120, 120); ctx.globalAlpha = 1; }
    };
    // a little wind-back, a quick spin, an overshoot and a springy settle, with squash and stretch
    const frame = (t) => {
      const x = Math.min(1, (t - t0) / turnMs);
      const wind = x < .2 ? Math.sin((x / .2) * Math.PI) : 0, spin = x >= .2 && x < .8 ? Math.sin(((x - .2) / .6) * Math.PI) : 0;
      const land = x >= .8 ? Math.sin(((x - .8) / .2) * Math.PI) : 0;
      cv.style.transform = `translateY(${-3 * spin}%) scale(${1 + .05 * wind - .03 * spin + .04 * land}, ${1 - .06 * wind + .05 * spin - .05 * land})`;
      draw(x >= 1 ? 0 : n * backInOut(x));
      if (x < 1) { raf = requestAnimationFrame(frame); return; }
      raf = 0; cv.style.transform = ''; link.classList.remove('turning');
    };
    const play = () => {
      if (reduced || raf) return;
      load().then((ok) => {
        if (!ok || raf) return;
        link.classList.add('turning'); t0 = performance.now(); raf = requestAnimationFrame(frame);
      });
    };
    link.addEventListener('pointerenter', (e) => { if (e.pointerType === 'mouse') play(); });
    link.addEventListener('focus', play);
  });
})();
