/* Greia launch video: one paused GSAP timeline, every value a pure function of time. 100 BPM -> 0.6 s per beat. */
(function () {
  const tl = gsap.timeline({ paused: true });
  const $ = (s) => document.querySelector(s);
  const NS = "http://www.w3.org/2000/svg";

  /* ---------- seeded randomness + easing library (each element picks its own curve) ---------- */
  function mulberry32(a) { return function () { a |= 0; a = (a + 0x6d2b79f5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
  const R = mulberry32(20261017);
  function bez(x1, y1, x2, y2) {
    const cx = 3 * x1, bx = 3 * (x2 - x1) - cx, ax = 1 - cx - bx, cy = 3 * y1, by = 3 * (y2 - y1) - cy, ay = 1 - cy - by;
    const sx = (t) => ((ax * t + bx) * t + cx) * t, sy = (t) => ((ay * t + by) * t + cy) * t;
    return (x) => { if (x <= 0) return 0; if (x >= 1) return 1; let lo = 0, hi = 1, t = x; for (let i = 0; i < 40; i++) { const v = sx(t); if (Math.abs(v - x) < 1e-6) break; if (v < x) lo = t; else hi = t; t = (lo + hi) / 2; } return sy(t); };
  }
  const inExp = (k) => (t) => (Math.exp(k * t) - 1) / (Math.exp(k) - 1);   // starts already moving (cut-in on motion)
  const E = {
    out: bez(0.16, 1, 0.3, 1), snap: bez(0.2, 0.9, 0.1, 1), soft: bez(0.22, 0.61, 0.36, 1), io: bez(0.65, 0, 0.35, 1),
    inn: bez(0.7, 0, 0.84, 0), drift: bez(0.25, 0.4, 0.75, 0.6), glide: bez(0.3, 0, 0.1, 1), lazy: bez(0.4, 0.1, 0.2, 1),
  };
  const el = (tag, cls, css, parent) => { const e = document.createElement(tag); if (cls) e.className = cls; if (css) e.style.cssText = css; if (parent) parent.appendChild(e); return e; };
  const sv = (tag, attrs, parent) => { const e = document.createElementNS(NS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); if (parent) parent.appendChild(e); return e; };
  function words(host, text, cls) { host.innerHTML = ""; return text.split(" ").map((w, i, a) => { const s = el("span", "word" + (cls ? " " + cls : ""), "", host); s.textContent = w + (i < a.length - 1 ? " " : ""); return s; }); }
  function wordIn(spans, times, dur = 0.5) {
    spans.forEach((s, i) => tl.fromTo(s, { opacity: 0, y: 26, filter: "blur(10px)" }, { opacity: 1, y: 0, filter: "blur(0px)", duration: dur, ease: E.out, immediateRender: true }, times[i]));
  }
  function fadeOut(sel, t, d = 0.3) { tl.to(sel, { opacity: 0, duration: d, ease: "power2.in" }, t); }

  /* ---------- the constellation G (original Greia mark) ---------- */
  const GP = "M166 142 C130 131 91 131 53 143 C37 179 34 226 42 268 C46 292 49 308 54 314 C88 332 133 332 169 315 C180 289 184 263 180 232 C158 236 134 242 112 247";
  const WORD_D = "{{WORDMARK_D}}";
  const STARS = [[166, 142, "#9ee9da", 10.1], [53, 143, "#f7cf73", 11.4], [54, 314, "#c69cef", 10.6], [169, 315, "#f7cf73", 11.2], [180, 232, "#c69cef", 11.0], [112, 247, "#9ee9da", 10.8], [142, 346, "#ae86e8", 0]];
  const SEG = [[[166, 142], [130, 131], [91, 131], [53, 143]], [[53, 143], [37, 179], [34, 226], [42, 268]], [[42, 268], [46, 292], [49, 308], [54, 314]], [[54, 314], [88, 332], [133, 332], [169, 315]], [[169, 315], [180, 289], [184, 263], [180, 232]], [[180, 232], [158, 236], [134, 242], [112, 247]]];
  const bz = (p, t) => { const u = 1 - t; return [u * u * u * p[0][0] + 3 * u * u * t * p[1][0] + 3 * u * t * t * p[2][0] + t * t * t * p[3][0], u * u * u * p[0][1] + 3 * u * u * t * p[1][1] + 3 * u * t * t * p[2][1] + t * t * t * p[3][1]]; };
  const segLen = SEG.map((s) => { let L = 0, prev = bz(s, 0); for (let i = 1; i <= 120; i++) { const q = bz(s, i / 120); L += Math.hypot(q[0] - prev[0], q[1] - prev[1]); prev = q; } return L; });
  const totalLen = segLen.reduce((a, b) => a + b, 0);
  const FR = [0]; segLen.forEach((l) => FR.push(FR[FR.length - 1] + l / totalLen));
  const STAR_FRAC = [FR[0], FR[1], FR[3], FR[4], FR[5], FR[6]];           // TR, TL, BL, BR, VR, inner
  const KEYS = [0.3, 0.9, 1.95, 3.0, 3.54, 4.02];                           // star times, matched to the celesta notes

  function mkLogo(svg, id, t0, k, withWord) {
    const defs = sv("defs", {}, svg);
    const cp = sv("clipPath", { id: "wm-" + id }, defs); const rect = sv("rect", { x: 25, y: 364, width: 0, height: 60 }, cp);
    const glowPath = sv("path", { d: GP, pathLength: 1, fill: "none", stroke: "#f7cf73", "stroke-width": 11, "stroke-linecap": "round", "stroke-dasharray": 1, "stroke-dashoffset": 1, opacity: 0 }, svg);
    const gp = sv("path", { d: GP, pathLength: 1, fill: "none", stroke: "#fff8e4", "stroke-width": 4.5, "stroke-linecap": "round", "stroke-linejoin": "round", "stroke-dasharray": 1, "stroke-dashoffset": 1, opacity: 0 }, svg);
    const wm = sv("path", { d: WORD_D, fill: "#fff8e4", stroke: "#fff8e4", "stroke-width": 1.4, "stroke-linejoin": "round", "fill-rule": "evenodd", "clip-path": "url(#wm-" + id + ")" }, svg);
    const stars = STARS.map((s, i) => {
      const g = sv("g", { transform: `translate(${s[0]} ${s[1]})` }, svg);
      const flare = sv("circle", { r: 7, fill: "none", stroke: s[2], "stroke-width": 1.6, opacity: 0 }, g);
      const inner = sv("g", {}, g);
      if (s[3]) sv("circle", { r: s[3], fill: s[2], opacity: 0.38 }, inner);
      sv("polygon", { points: "0,-5.2 0.92,-0.92 5.2,0 0.92,0.92 0,5.2 -0.92,0.92 -5.2,0 -0.92,-0.92", fill: s[2], stroke: s[2], "stroke-width": 3.2, "stroke-linejoin": "round" }, inner);
      sv("circle", { r: 5.2, fill: "#fffdf2" }, inner);
      return { g, inner, flare };
    });
    // dim stars wait in the sky first, exactly like the boot animation
    stars.forEach((s, i) => { tl.set(s.inner, { opacity: 0, scale: 0.7 }, 0); tl.to(s.inner, { opacity: 0.34, scale: 0.8, duration: 0.7 * k + 0.2, ease: "sine.out" }, t0 + (0.1 + i * 0.04) * k); });
    // light each star as the line reaches it
    const T = KEYS.map((x) => t0 + x * k); T.push(t0 + 4.26 * k);
    stars.forEach((s, i) => {
      tl.fromTo(s.inner, { opacity: 0.34, scale: 0.8 }, { opacity: 1, scale: 1, duration: 0.55, ease: "back.out(3)" }, T[i]);
      tl.fromTo(s.inner, { scale: 2.1 }, { scale: 1, duration: 0.5, ease: E.out, immediateRender: false }, T[i]);
      tl.fromTo(s.flare, { opacity: 0.95, attr: { r: 6 } }, { opacity: 0, attr: { r: 34 }, duration: 0.85, ease: E.out }, T[i]);
    });
    // the line itself: one continuous draw, per-segment speed so each arrival lands on its star
    const P = { p: 0 };
    const draw = () => { const o = P.p < 0.002 ? 0 : 1; gp.setAttribute("opacity", o); glowPath.setAttribute("opacity", o * 0.22); gp.setAttribute("stroke-dashoffset", 1 - P.p); glowPath.setAttribute("stroke-dashoffset", 1 - P.p); };
    for (let j = 1; j < STAR_FRAC.length; j++) tl.fromTo(P, { p: STAR_FRAC[j - 1] }, { p: STAR_FRAC[j], duration: (KEYS[j] - KEYS[j - 1]) * k, ease: "none", onUpdate: draw, immediateRender: j === 1 }, t0 + KEYS[j - 1] * k);
    // the word lands last
    if (withWord) tl.fromTo(rect, { attr: { width: 0 } }, { attr: { width: 174 }, duration: 0.7 * k + 0.1, ease: E.out }, t0 + 4.12 * k);
    else tl.set(rect, { attr: { width: 0 } }, 0);
    return { T, stars };
  }

  /* ---------- reusable night sky: twinkles + fireflies ---------- */
  function sky(host, n, ymax, seedShift, tStart, tEnd) {
    const r = mulberry32(777 + seedShift);
    for (let i = 0; i < n; i++) {
      const s = 2 + r() * 3, x = r() * 1920, y = Math.pow(r(), 0.85) * ymax;
      const d = el("div", "twk", `left:${x}px;top:${y}px;width:${s}px;height:${s}px;opacity:0`, host);
      const peak = 0.25 + r() * 0.65, dur = 1.1 + r() * 1.7;
      tl.set(d, { opacity: 0 }, 0);
      tl.to(d, { opacity: peak, duration: dur, ease: "sine.inOut", yoyo: true, repeat: 5 }, tStart + r() * 2.2);
    }
  }
  function flies(host, n, seedShift, tStart) {
    const r = mulberry32(4242 + seedShift);
    for (let i = 0; i < n; i++) {
      const x = 180 + r() * 1560, y = 700 + r() * 220;
      const f = el("div", "fly", `left:${x}px;top:${y}px;opacity:0`, host);
      tl.to(f, { opacity: 0.9, duration: 1.4 + r() * 1.2, ease: "sine.inOut", yoyo: true, repeat: 3 }, tStart + r() * 2.4);
      tl.to(f, { x: (r() - 0.5) * 120, y: -40 - r() * 70, duration: 6.5, ease: "sine.inOut" }, tStart);
    }
  }

