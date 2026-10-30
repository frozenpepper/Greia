  /* ---------- shared timeline (timeline.json is also read by tools/mix.py) ---------- */
  const TL = {{TIMELINE_JSON}};
  const SC = TL.scene, CUT = TL.cut, W = TL.word, VO = TL.vo;
  // Scene pauses: later sections are authored on the raw timeline and moved by timeline.json "shifts" (picture and sound identically).
  const SH = { on: false };
  const shift = (t) => { let d = 0; for (const [b, dl] of TL.shifts) if (t >= b - 1e-9) d += dl; return t + d; };
  ["to", "fromTo", "set", "from"].forEach((m) => { const f = tl[m].bind(tl); const pi = m === "fromTo" ? 3 : 2; tl[m] = (...a) => { const p = a[pi]; if (p && typeof p === "object") a[pi] = p.abs; else if (SH.on && typeof p === "number") a[pi] = shift(p); return f(...a); }; });
  const ABS = (t) => ({ abs: t });
  const wordsAt = (spans, t0, offs, dur) => wordIn(spans, offs.map((o) => t0 + o), dur);

  /* ======================================== S1  night + logo ======================================== */
  sky($("#s1stars"), 95, 640, 1, 0.2, 5);
  flies($("#s1flies"), 14, 1, 0.8);
  tl.fromTo("#s1cam", { scale: 1.0, x: 0, y: 0 }, { scale: 1.09, x: -22, y: 12, duration: 5.7, ease: "none" }, 0);
  tl.fromTo("#blackIn", { opacity: 1 }, { opacity: 0, duration: 1.2, ease: "power2.out" }, 0);
  mkLogo($("#logo1"), "a", 0, 1, true);
  tl.fromTo("#logo1", { y: 10 }, { y: 0, duration: 4.6, ease: E.soft }, 0.2);
  { const ka = words($("#k1a"), "Not an app.", ""), kb = words($("#k1b"), "A whole operating system.", "");
    tl.set("#s1kick", { opacity: 1 }, 0);
    wordIn(ka, [VO.vo01n - 0.05, VO.vo01n + 0.3, VO.vo01n + 0.5], 0.5); wordIn(kb, [VO.vo01n + 1.05, VO.vo01n + 1.2, VO.vo01n + 1.4, VO.vo01n + 1.75], 0.5);
    tl.to("#s1kick", { opacity: 0, y: -14, duration: 0.35, ease: "power2.in" }, 4.4); }
  tl.fromTo("#sunDisc", { width: 18, height: 18, x: -9, y: -9, opacity: 0 }, { width: 330, height: 330, x: -165, y: -165, opacity: 1, duration: 0.55, ease: inExp(3.2) }, 4.28);

  /* ======================================== S2  the old netbook, and what it runs on (final-frame times) ======================================== */
  function quadMatrix(w, h, q) {
    const [x0, y0] = q[0], [x1, y1] = q[1], [x2, y2] = q[2], [x3, y3] = q[3];
    const dx1 = x1 - x2, dx2 = x3 - x2, dx3 = x0 - x1 + x2 - x3, dy1 = y1 - y2, dy2 = y3 - y2, dy3 = y0 - y1 + y2 - y3;
    const det = dx1 * dy2 - dx2 * dy1, g = (dx3 * dy2 - dx2 * dy3) / det, hh = (dx1 * dy3 - dx3 * dy1) / det;
    const a = x1 - x0 + g * x1, b = x3 - x0 + hh * x3, c = x0, d = y1 - y0 + g * y1, e = y3 - y0 + hh * y3, f = y0;
    return `matrix3d(${a / w},${d / w},0,${g / w},${b / h},${e / h},0,${hh / h},0,0,1,0,${c},${f},0,1)`;
  }
  // screen corners measured on the photo with OpenCV (tools/ notes in BREAKDOWN), pushed out 2 px to cover the original glass edge
  const QUAD = [[299, 173], [941, 131], [999, 510], [357, 585]];
  $("#screenQuad").style.transform = quadMatrix(1843, 1080, QUAD);
  $("#screenImg").style.left = "-38px"; $("#screenImg").style.width = "1920px"; $("#screenImg").style.objectFit = "fill";
  tl.set("#iris", { clipPath: "circle(160px at 1079px 441px)" }, 0);
  tl.fromTo("#iris", { clipPath: "circle(160px at 1079px 441px)" }, { clipPath: "circle(2500px at 1079px 441px)", duration: 1.05, ease: bez(0.5, 0, 0.12, 1) }, 4.8);
  tl.fromTo("#sunFill", { opacity: 1 }, { opacity: 0, duration: 0.55, ease: "power2.out" }, 4.86);
  tl.fromTo("#ring", { width: 320, height: 320, opacity: 1 }, { width: 5000, height: 5000, opacity: 0, duration: 1.15, ease: bez(0.5, 0, 0.12, 1) }, 4.8);
  tl.set("#sunDisc", { opacity: 0 }, 4.82);
  // drawer -> warm light -> the room
  tl.fromTo("#drawer", { scale: 1.0, x: 0, y: 0, filter: "brightness(0.82) saturate(0.78)" }, { scale: 1.15, x: -30, y: -12, filter: "brightness(1) saturate(1)", duration: 2.2, ease: "none" }, 4.8);
  { const r = mulberry32(31); for (let i = 0; i < 46; i++) { const m = el("div", "twk", `left:${r() * 1920}px;top:${300 + r() * 700}px;width:${2 + r() * 3}px;height:${2 + r() * 3}px;background:#fff1c9;opacity:0`, $("#motes")); tl.to(m, { opacity: 0.2 + r() * 0.6, duration: 0.8 + r(), ease: "sine.inOut", yoyo: true, repeat: 2 }, 4.9 + r() * 1.2); tl.to(m, { y: -90 - r() * 120, x: (r() - 0.5) * 80, duration: 2.2, ease: "none" }, 4.8); } }
  tl.fromTo("#world", { opacity: 0 }, { opacity: 1, duration: 0.55, ease: bez(0.4, 0, 0.2, 1), immediateRender: true }, 6.0);
  tl.to("#drawer", { opacity: 0, duration: 0.2 }, 6.55);
  tl.fromTo("#bloom", { opacity: 0 }, { opacity: 0.75, duration: 0.32, ease: bez(0.2, 0.6, 0.3, 1), immediateRender: false }, 5.8);
  tl.to("#bloom", { opacity: 0, duration: 0.8, ease: "power2.inOut" }, 6.12);
  // camera: one long push (never stops), then the zoom-through into the screen once Greia has been on it for a good while
  const ZT = 16.6;
  tl.fromTo("#world", { scale: 1.33, x: 214.5, y: 94.2 }, { scale: 1.5, x: 250, y: 74, duration: ZT - 4.8, ease: E.drift, immediateRender: true }, 4.8);
  tl.to("#world", { scale: 3.06, duration: 1.0, ease: inExp(2.6) }, ZT);
  tl.to("#world", { x: 310, y: 194, duration: 0.95, ease: bez(0.3, 0.7, 0.3, 1) }, ZT);
  // headline on the VO
  const h1 = words($("#h1"), "Old computers", ""), h2 = words($("#h2"), "deserve another childhood.", "");
  wordIn([h1[0], h1[1]], [VO.vo02b - 0.05, VO.vo02b + 0.4], 0.55); wordIn(h2, [VO.vo02b + 0.95, VO.vo02b + 1.7, VO.vo02b + 2.25], 0.6);
  tl.to("#s2shade", { opacity: 0.9, duration: 0.01 }, 5.0);
  fadeOut("#s2head", 9.1, 0.4); tl.to("#s2shade", { opacity: 0, duration: 0.6, ease: "power2.inOut" }, 9.15);
  // the machine is switched off: what it is (annotations)
  [[1, 7.0], [3, 7.5]].forEach(([n, t]) => {
    tl.fromTo("#cd" + n, { scale: 0, opacity: 0 }, { scale: 1, opacity: 1, duration: 0.45, ease: "back.out(3)" }, t);
    tl.fromTo("#cl" + n, { scaleX: 0 }, { scaleX: 1, duration: 0.5, ease: E.out }, t + 0.1);
    tl.fromTo("#ct" + n, { opacity: 0, x: -20, scale: 0.92 }, { opacity: 1, x: 0, scale: 1, duration: 0.5, ease: E.out }, t + 0.32);
    tl.to(["#cd" + n, "#cl" + n, "#ct" + n], { opacity: 0, duration: 0.3, ease: "power2.in" }, 8.8);
  });
  // a USB stick plugs in, then the screen boots the real Greia splash and the real Shell, and stays on for the rest of the scene
  tl.fromTo("#usb", { opacity: 0, x: -200 }, { opacity: 1, x: 0, duration: 0.7, ease: E.out }, 8.3);
  tl.to("#usb", { x: 70, duration: 0.2, ease: "power2.in" }, 9.1);
  tl.fromTo("#usbPing", { opacity: 0.9, scale: 0.3 }, { opacity: 0, scale: 2.6, duration: 0.7, ease: E.out }, 9.3);
  tl.fromTo("#ctu", { opacity: 0, y: 16 }, { opacity: 1, y: 0, duration: 0.5, ease: E.out }, 8.8);
  tl.to(["#usb", "#ctu"], { opacity: 0, duration: 0.3, ease: "power2.in" }, 11.8);
  tl.fromTo("#bootImg", { opacity: 0 }, { opacity: 1, duration: 0.01, immediateRender: true }, 9.5);
  tl.fromTo("#screenWake", { opacity: 1 }, { opacity: 0, duration: 0.3, ease: bez(0.1, 0.9, 0.2, 1) }, 9.5);
  tl.to("#bootImg", { opacity: 0, duration: 0.5, ease: "power1.inOut" }, 11.5);
  // ...and what it can run on: almost anything
  const hw = $("#hwRow"); const hk = el("div", "kicker hwkick", "", $("#iris")); hk.innerHTML = "<span>One operating system · almost any computer</span>";
  tl.fromTo(hk, { opacity: 0, y: -10 }, { opacity: 1, y: 0, duration: 0.5, ease: E.out }, 12.2);
  [["Old netbooks", "#f9d65c"], ["Raspberry Pi 400 · 500", "#ff756c"], ["Modern PCs", "#9cebd1"]].forEach(([lbl, col], i) => {
    const c = el("div", "hwchip", "", hw); c.innerHTML = `<i style="background:${col}"></i>${lbl}`;
    tl.fromTo(c, { opacity: 0, scale: 0.6, y: -16 }, { opacity: 1, scale: 1, y: 0, duration: 0.55, ease: "back.out(2.6)" }, 12.4 + i * 0.25);
    tl.to(c, { opacity: 0, duration: 0.25, ease: "power2.in" }, ZT - 0.5);
  });
  tl.to(hk, { opacity: 0, duration: 0.25, ease: "power2.in" }, ZT - 0.5);

  SH.on = true;
  /* ======================================== S3  the Shell ======================================== */
  const spriteMeta = {{ICONS_JSON}};
  const sp = {};
  ["creations", "explore", "create", "play", "learn", "greia", "chip", "star", "mascot"].forEach((k) => {
    const m = spriteMeta[k];
    const im = el("img", "sprite", `left:${m.x}px;top:${m.y}px;width:${m.w}px;height:${m.h}px;opacity:0`, $("#s3sprites"));
    im.src = `assets/shots/icon_${k}.png`; sp[k] = im;
    im.style.transformOrigin = ["chip", "star", "mascot"].includes(k) ? "50% 50%" : "125px 150px";
  });
  const s3t1 = words($("#s3l1"), "Every child gets", ""), s3t2 = words($("#s3l2"), "a world of their own.", "");
  tl.set("#s3text", { fontSize: 80 }, 0);
  tl.fromTo("#s3prof", { opacity: 0 }, { opacity: 1, duration: 0.32, ease: "power1.out" }, 11.45);
  tl.set("#s3clean", { opacity: 0 }, 0); tl.set("#s3clean", { opacity: 1 }, 13.2);
  tl.fromTo("#s3cam", { scale: 1.0 }, { scale: 1.055, x: -16, y: -8, duration: 5.6, ease: "none" }, 11.2);
  wordsAt(s3t1, VO.vo03e - 0.05, [0, 0.54, 0.94], 0.5); wordsAt(s3t2, VO.vo03e - 0.05, [1.22, 1.46, 1.72, 2.0, 2.24], 0.5);
  fadeOut("#s3text", 14.9, 0.4);
  tl.set("#cur", { x: 1500, y: 860, opacity: 0 }, 0);
  tl.to("#cur", { opacity: 1, duration: 0.2 }, 12.0);
  tl.to("#cur", { x: 954, duration: 1.0, ease: bez(0.3, 0, 0.12, 1) }, 12.0);
  tl.to("#cur", { y: 551, duration: 1.0, ease: bez(0.15, 0.6, 0.2, 1) }, 12.0);
  tl.fromTo("#cur", { scale: 1 }, { scale: 0.8, duration: 0.09, ease: "power2.in" }, 13.1);
  tl.to("#cur", { scale: 1, duration: 0.3, ease: "back.out(3)" }, 13.19);
  tl.fromTo("#rip1", { opacity: 0.95, scale: 0.4 }, { opacity: 0, scale: 2.4, duration: 0.7, ease: E.out }, 13.12);
  tl.to("#s3prof", { opacity: 0, scale: 1.12, duration: 0.5, ease: bez(0.5, 0, 0.5, 1) }, 13.2);
  tl.set("#s3prof", { transformOrigin: "960px 555px" }, 0);
  [["creations", 13.3], ["explore", 13.38], ["create", 13.56], ["play", 13.68], ["learn", 13.8], ["greia", 13.92], ["chip", 14.06], ["star", 14.12], ["mascot", 14.18]].forEach(([k, t]) => {
    tl.fromTo(sp[k], { opacity: 0, scale: 0.55 }, { opacity: 1, scale: 1, duration: 0.5, ease: "back.out(2.4)" }, t);
  });
  tl.to("#cur", { x: 680, duration: 1.05, ease: bez(0.2, 0, 0.15, 1) }, 14.4);
  tl.to("#cur", { y: 346, duration: 1.05, ease: bez(0.4, 0.5, 0.2, 1) }, 14.4);
  tl.to(sp.create, { scale: 1.07, duration: 0.3, ease: E.out }, 15.2);
  tl.fromTo("#cur", { scale: 1 }, { scale: 0.8, duration: 0.09, ease: "power2.in" }, 15.55);
  tl.to("#cur", { scale: 1, duration: 0.3, ease: "back.out(3)" }, 15.64);
  tl.fromTo("#rip2", { opacity: 0.95, scale: 0.4 }, { opacity: 0, scale: 2.0, duration: 0.6, ease: E.out }, 15.57);
  // the Create icon opens: it comes to the front, loses its label, and the rest of the Shell steps back
  tl.set(sp.create, { zIndex: 30 }, 15.6);
  tl.set(sp.create, { webkitMaskImage: "linear-gradient(to bottom, #000 0%, #000 74%, transparent 80%)", maskImage: "linear-gradient(to bottom, #000 0%, #000 74%, transparent 80%)" }, 15.64);
  tl.to(sp.create, { scale: 14, duration: 0.74, ease: inExp(4.2) }, 15.7);
  tl.to("#cur", { opacity: 0, duration: 0.12 }, 15.8);
  tl.to("#coralFill", { opacity: 1, duration: 0.15, ease: "power1.in" }, 16.3);

  /* ======================================== S4  montage ======================================== */
  const bigIn = (id, t, rot) => { tl.fromTo(id, { opacity: 0, scale: 1.45, rotation: rot - 5, x: -30 }, { opacity: 1, scale: 1, rotation: rot, x: 0, duration: 0.34, ease: bez(0.2, 1.3, 0.3, 1) }, t); };
  bigIn("#bw_paint", W.paint, -2); fadeOut("#bw_paint", CUT.count - 0.1, 0.1);
  bigIn("#bw_count", W.count, 1.5); fadeOut("#bw_count", CUT.listen - 0.1, 0.1);
  bigIn("#bw_listen", W.listen, -1.5); fadeOut("#bw_listen", CUT.build - 0.08, 0.08);
  bigIn("#bw_build", W.build, 2); fadeOut("#bw_build", CUT.orca - 0.08, 0.08);
  bigIn("#bw_discover", W.discover, -2); fadeOut("#bw_discover", CUT.mosaic - 0.12, 0.12);
  tl.set("#stillBuild", { opacity: 1 }, CUT.build); tl.set("#stillBuild", { opacity: 0 }, CUT.orca);
  tl.fromTo("#stillBuild", { scale: 1.0 }, { scale: 1.07, duration: CUT.orca - CUT.build, ease: "none" }, CUT.build);
  // the 45-tile mosaic
  const tiles = {{TILES_JSON}};
  const mo = $("#mosaic"); const COLS = 9, TW = 200, TH = 118, GX = 9, GY = 8, M0 = CUT.mosaic;
  const order = tiles.map((n, i) => i).sort((a, b) => { const ca = (a % COLS) - 4, ra = Math.floor(a / COLS) - 2, cb = (b % COLS) - 4, rb = Math.floor(b / COLS) - 2; return (ca * ca + ra * ra) - (cb * cb + rb * rb) || a - b; });
  tiles.forEach((n, i) => {
    const c = i % COLS, r = Math.floor(i / COLS);
    const t = el("div", "tile", `left:${24 + c * (TW + GX)}px;top:${9 + r * (TH + GY)}px;opacity:0`, mo);
    const im = el("img", "", "", t); im.src = `assets/shots/tiles/${n}.jpg`;
    const rank = order.indexOf(i);
    tl.fromTo(t, { opacity: 0, scale: 0.5, rotation: (R() - 0.5) * 12 }, { opacity: 1, scale: 1, rotation: 0, duration: 0.4, ease: "back.out(2)" }, M0 + 0.1 + rank * 0.02);
    tl.to(t, { opacity: 0, scale: 0.3, duration: 0.35, ease: "power2.in" }, 25.5 + (44 - rank) * 0.01);
  });
  tl.fromTo("#mosaic", { scale: 1.0, transformOrigin: "50% 50%" }, { scale: 1.035, duration: 2.8, ease: "none" }, M0);
  tl.fromTo("#sheen", { x: 0, opacity: 0 }, { x: 2800, opacity: 1, duration: 1.0, ease: bez(0.5, 0, 0.3, 1) }, M0 + 1.45);
  tl.set("#sheen", { opacity: 0 }, M0 + 2.5);
  tl.set("#mosaicBg", { opacity: 1 }, M0);
  tl.set("#flash", { opacity: 0 }, 0); tl.fromTo("#flash", { opacity: 0.55 }, { opacity: 0, duration: 0.35, ease: "power2.out", immediateRender: false }, M0);
  const NUM = { n: 0 };
  tl.set("#bigNum", { opacity: 1 }, M0 + 0.05);
  tl.fromTo("#bigNum", { scale: 1.12, x: -20, transformOrigin: "0% 50%" }, { scale: 1, x: 0, duration: 0.6, ease: E.out }, M0 + 0.05);
  tl.fromTo(NUM, { n: 0 }, { n: 45, duration: 0.8, ease: bez(0.3, 0, 0.1, 1), immediateRender: false, onUpdate: () => { $("#bigNum").textContent = String(Math.round(NUM.n)); } }, M0 + 0.05);
  tl.fromTo("#numSub", { opacity: 0, x: -30 }, { opacity: 1, x: 0, duration: 0.5, ease: E.out }, M0 + 0.5);
  tl.fromTo("#numSub2", { opacity: 0, x: -30 }, { opacity: 1, x: 0, duration: 0.5, ease: E.out }, M0 + 0.85);
  tl.fromTo("#chipAge", { opacity: 0, scale: 0.6, rotation: -6 }, { opacity: 1, scale: 1, rotation: -2, duration: 0.5, ease: "back.out(2.6)" }, M0 + 0.45);
  tl.set("#mosaicBg", { opacity: 1 }, 25.3); tl.to("#mosaicBg", { opacity: 0, duration: 0.01 }, 26.6);
  ["#bigNum", "#numSub", "#numSub2", "#chipAge"].forEach((s, i) => tl.to(s, { opacity: 0, duration: 0.3, ease: "power2.in" }, 25.2 + i * 0.05));

  /* ======================================== S5  no reading needed, every Activity speaks, four languages ======================================== */
  tl.set("#s5", { clipPath: "circle(0px at 960px 1260px)" }, 0);
  tl.fromTo("#s5", { clipPath: "circle(0px at 960px 1260px)" }, { clipPath: "circle(2500px at 960px 1260px)", duration: 0.95, ease: bez(0.5, 0, 0.12, 1) }, 25.7);
  tl.fromTo("#s5sun", { scale: 0.7 }, { scale: 1.05, duration: 5.7, ease: "none" }, 25.7);
  const s5a = words($("#s5l1"), "No reading", ""), s5b = words($("#s5l2"), "needed.", "");
  wordIn(s5a, [W.s5_no - 0.05, W.s5_reading - 0.05], 0.55); wordIn(s5b, [W.s5_needed - 0.05], 0.6);
  const CAST = [["lilli", 1.18], ["leo", 1], ["flash", 1], ["tito", 1], ["momo", 1], ["dani", 1]];
  const castRow = $("#castRow"); const wv = [];
  CAST.forEach(([n, sc], i) => {
    const cx = 215 + i * 298, cy = 830;
    const w = el("div", "cast", `left:${cx - 195}px;top:${cy - 390}px;opacity:0`, castRow);
    const im = el("img", "", "", w); im.src = `assets/svg/${n}_pose_${i % 2 ? "wave" : "cheer"}.svg`;
    const t0 = 26.35 + i * 0.12;
    tl.fromTo(w, { opacity: 0, scale: 0, y: 120, rotation: i % 2 ? 14 : -14 }, { opacity: 1, scale: sc, y: 0, rotation: 0, duration: 0.9, ease: "elastic.out(1,0.5)" }, t0);
    tl.to(w, { y: -16, duration: 0.6, ease: "sine.inOut", yoyo: true, repeat: 6 }, t0 + 0.9 + i * 0.1);
    if (i === 0) wv.push([cx, cy - 290]);
  });
  [W.s5_no, W.s5_reading, W.s5_needed, W.speaks, W.speaks + 0.4, W.lang1, W.lang2, W.lang3, W.lang4].forEach((t) => {
    const w = el("div", "wave", `left:${wv[0][0]}px;top:${wv[0][1]}px`, castRow);
    tl.fromTo(w, { opacity: 0.85, scale: 0.4 }, { opacity: 0, scale: 5.2, duration: 0.9, ease: E.out }, t);
  });
  [["Hello", "English", "#f9d65c", W.lang1], ["Ciao", "Italiano", "#9cebd1", W.lang2], ["Bonjour", "Français", "#ff9a90", W.lang3], ["Hola", "Español", "#c9b6ff", W.lang4]].forEach(([g, n, col, t], i) => {
    const c = el("div", "lang", `left:${108 + i * 436}px;background:${col};opacity:0`, $("#langs"));
    c.innerHTML = `<b>${g}</b><span>${n}</span>`;
    tl.fromTo(c, { opacity: 0, scale: 0.5, y: 40, rotation: -5 + i * 3 }, { opacity: 1, scale: 1, y: 0, rotation: 0, duration: 0.55, ease: "back.out(2.4)" }, t - 0.05);
  });
  ["#s5title", "#castRow", "#langs"].forEach((s) => fadeOut(s, 31.0, 0.25));

  /* ======================================== S6  home + what is not there ======================================== */
  const H0 = SC.s6a;
  tl.fromTo("#s6acam", { scale: 1, transformOrigin: "0px 0px" }, { scale: 2.4, duration: 1.8, ease: bez(0.25, 0.05, 0.35, 1) }, H0);
  tl.set("#homeShot2", { opacity: 1 }, H0 + 0.35); tl.set("#homeShot3", { opacity: 1 }, H0 + 0.7);
  [[H0 + 0.1, "#homeRing"], [H0 + 0.35, "#homeRing2"], [H0 + 0.7, "#homeRing"], [W.home, "#homeRing2"]].forEach(([t, id]) => tl.fromTo(id, { opacity: 0.95, scale: 0.5 }, { opacity: 0, scale: 2.4, duration: 0.8, ease: E.out, immediateRender: false }, t));
  tl.set("#homeRing", { opacity: 0 }, 0); tl.set("#homeRing2", { opacity: 0 }, 0);
  tl.fromTo("#homeTag", { opacity: 0, x: -24 }, { opacity: 1, x: 0, duration: 0.5, ease: E.out }, H0 + 0.4);
  tl.to("#homeFlash", { opacity: 1, duration: 0.14, ease: "power1.in" }, W.home);
  tl.set("#homeDest", { opacity: 1 }, W.home + 0.02);
  tl.to("#homeFlash", { opacity: 0, duration: 0.5, ease: "power2.out" }, W.home + 0.17);
  const GL = {
    desktop: '<svg class="g" viewBox="0 0 190 190"><rect x="14" y="26" width="162" height="112" rx="14" fill="none" stroke="#fff8e9" stroke-width="10"/><rect x="34" y="48" width="40" height="30" rx="5" fill="#fff8e9"/><rect x="86" y="58" width="64" height="50" rx="5" fill="none" stroke="#fff8e9" stroke-width="8"/><path d="M62 160 H128 M95 140 V160" stroke="#fff8e9" stroke-width="10" stroke-linecap="round"/></svg>',
    browser: '<svg class="g" viewBox="0 0 190 190"><rect x="12" y="30" width="166" height="130" rx="16" fill="none" stroke="#fff8e9" stroke-width="10"/><path d="M12 62 H178" stroke="#fff8e9" stroke-width="10"/><circle cx="36" cy="46" r="6" fill="#fff8e9"/><circle cx="58" cy="46" r="6" fill="#fff8e9"/><rect x="40" y="86" width="110" height="14" rx="7" fill="#fff8e9"/><rect x="40" y="114" width="70" height="14" rx="7" fill="#fff8e9"/></svg>',
    ads: '<svg class="g" viewBox="0 0 190 190"><rect x="10" y="36" width="170" height="118" rx="18" fill="none" stroke="#fff8e9" stroke-width="10"/><path d="M60 118 L84 66 L108 118 M68 102 H100" fill="none" stroke="#fff8e9" stroke-width="10" stroke-linecap="round" stroke-linejoin="round"/><path d="M124 66 V118 M124 66 C150 66 150 118 124 118" fill="none" stroke="#fff8e9" stroke-width="10" stroke-linecap="round"/></svg>',
  };
  tl.set("#s6b", { backgroundColor: "#0a1427" }, 0);
  [["desktop", "Desktop", 120, W.nodesktop], ["browser", "Browser", 720, W.nobrowser], ["ads", "Ads", 1320, W.noads]].forEach(([k, lbl, x, t]) => {
    const c = el("div", "nocard", `left:${x}px;top:260px;opacity:0;width:480px`, $("#noRow"));
    c.innerHTML = GL[k] + `<div class="lbl">${lbl}</div><div class="xline"></div>`;
    const xl = c.querySelector(".xline");
    tl.fromTo(c, { opacity: 0, scale: 0.86, y: 30 }, { opacity: 1, scale: 1, y: 0, duration: 0.45, ease: E.out }, t - 0.2);
    tl.fromTo(xl, { scaleX: 0 }, { scaleX: 1, duration: 0.3, ease: bez(0.6, 0, 0.1, 1) }, t + 0.1);
  });

  /* ======================================== S7  parents choose ======================================== */
  sky($("#s7stars"), 70, 1000, 7, SC.s7, 43);
  const p1 = words($("#s7l1"), "What they see,", ""), p2 = words($("#s7l2"), "and for how long.", "");
  wordIn(p1, [VO.vo07 + 0.8, VO.vo07 + 1.05, VO.vo07 + 1.3], 0.55); wordIn(p2, [VO.vo07 + 2.3, VO.vo07 + 2.5, VO.vo07 + 2.75, VO.vo07 + 3.0], 0.55);
  // a daily limit, drawn like the real Parents rings
  tl.fromTo("#limitPill", { opacity: 0, x: -40 }, { opacity: 1, x: 0, duration: 0.55, ease: E.out }, W.long - 0.25);
  tl.fromTo("#limitArc", { attr: { "stroke-dashoffset": 150.8 } }, { attr: { "stroke-dashoffset": 40 }, duration: 0.9, ease: bez(0.3, 0, 0.1, 1) }, W.long);
  // a science week, then a writing week, made from real Activities
  const weeks = [
    { label: "This week", title: "Science", t: W.science, out: W.writing - 0.1, tiles: [["piccola_serra", "Plants"], ["quattro_stagioni", "Seasons"], ["enciclopedia_greia", "Encyclopedia"], ["sottomarino_giramondo", "Oceans"]] },
    { label: "Next week", title: "Writing", t: W.writing, out: 43.0, tiles: [["alfabeto_leo", "Letters"], ["sillabe_magiche", "Syllables"], ["writing", "Writing"], ["posta_di_leo", "Letters to Leo"]] },
  ];
  weeks.forEach((wk, wi) => {
    const wrap = el("div", "", "position:absolute;left:0;top:0;width:1000px;height:400px;opacity:0", $("#weekPanel"));
    const lab = el("div", "kicker", "position:absolute;left:0;top:0;color:#f9d65c", wrap); lab.textContent = wk.label;
    const tt = el("div", "display", "position:absolute;left:0;top:34px;font-size:96px;color:#fff8e9", wrap); tt.textContent = wk.title;
    wk.tiles.forEach(([n, cap], i) => {
      const t = el("div", "wtile", `left:${i * 264}px;top:190px`, wrap);
      el("img", "", "", t).src = `assets/shots/tiles/${n}.jpg`; const em = el("em", "", "", t); em.textContent = cap;
      tl.fromTo(t, { opacity: 0, rotationX: 80, y: 30 }, { opacity: 1, rotationX: 0, y: 0, duration: 0.5, ease: "back.out(1.8)" }, wk.t + 0.2 + i * 0.1);
      tl.to(t, { opacity: 0, rotationX: -70, duration: 0.3, ease: "power2.in" }, wk.out + (wi === 0 ? i * 0.04 : 0));
    });
    tl.fromTo(wrap, { opacity: 0, x: -30 }, { opacity: 1, x: 0, duration: 0.5, ease: E.out }, wk.t - 0.1);
    tl.to(wrap, { opacity: 0, duration: 0.25, ease: "power2.in" }, wk.out + 0.1);
  });
  tl.fromTo("#parentKick", { opacity: 0 }, { opacity: 0.66, duration: 0.6, ease: E.out }, SC.s7 + 0.9);
  // the phone is the REAL Greia Parents iOS app, recorded in the simulator
  tl.set("#phoneRoot", { opacity: 0 }, 0);
  tl.fromTo("#phoneRoot", { opacity: 0, x: 320, rotation: 7, y: 40 }, { opacity: 1, x: 0, rotation: 0, y: 0, duration: 0.95, ease: bez(0.12, 0.9, 0.2, 1) }, SC.s7 + 0.3);
  tl.to("#phoneRoot", { opacity: 0, duration: 0.25, ease: "power2.in" }, ABS(shift(43.4) - 0.4));
  tl.fromTo("#soonBadge", { opacity: 0, scale: 0.4, rotation: -8 }, { opacity: 1, scale: 1, rotation: -2, duration: 0.7, ease: "elastic.out(1,0.55)" }, W.soon);
  ["#s7head", "#soonBadge", "#limitPill", "#parentKick"].forEach((s) => tl.to(s, { opacity: 0, duration: 0.25, ease: "power2.in" }, ABS(shift(43.4) - 0.4)));

  /* ======================================== S8  tell an agent, with the voices ======================================== */
  const A0 = SC.s8;
  sky($("#s8stars"), 60, 1000, 8, A0, 50);
  const gw = $("#gridWrap"); const gridNames = ["alfabeto_leo", "acquario_magico", "orchestra_animali", "painting", "pasticceria_magica", "stelle_incantate"];
  gridNames.forEach((n, i) => {
    const c = i % 3, r = Math.floor(i / 3);
    const g = el("div", "gridtile", `left:${1020 + c * 279}px;top:${300 + r * 171}px;opacity:0`, gw);
    el("img", "", "", g).src = `assets/shots/tiles/${n}.jpg`;
    tl.fromTo(g, { opacity: 0, scale: 0.7, rotation: (r + c) % 2 ? 4 : -4 }, { opacity: 1, scale: 1, rotation: 0, duration: 0.5, ease: "back.out(2.2)" }, W.easy + i * 0.09);
  });
  const hw8 = el("div", "display", "position:absolute;left:96px;top:70px;font-size:118px;color:#fff8e9;width:1700px", $("#s8"));
  const a1 = words(hw8, "New Activities are easy to make.", "");
  wordIn(a1, [VO.vo08 - 0.05, VO.vo08 + 0.25, VO.vo08 + 0.65, VO.vo08 + 1.15, VO.vo08 + 1.38, VO.vo08 + 1.55], 0.55);
  tl.to(hw8, { opacity: 0, y: -30, duration: 0.35, ease: "power2.in" }, W.agent - 0.45);
  tl.fromTo("#wishKick", { opacity: 0, x: -20 }, { opacity: 1, x: 0, duration: 0.5, ease: E.out }, W.agent - 0.05);
  const WISH = "“Make something about trains. For Mia, who is three.”";
  const WP = { n: 0 };
  tl.set("#wish", { top: 130, fontSize: 80 }, 0);
  tl.set("#caret", { opacity: 0 }, 0);
  tl.fromTo(WP, { n: 0 }, { n: WISH.length, duration: 1.5, ease: "none", immediateRender: false, onUpdate: () => { $("#wishText").textContent = WISH.slice(0, Math.floor(WP.n)); } }, W.agent + 0.1);
  const CT = { t: 0 };
  tl.fromTo(CT, { t: 0 }, { t: 1.8, duration: 1.8, ease: "none", immediateRender: false, onUpdate: () => { $("#caret").style.opacity = Math.floor(CT.t * 5) % 2 ? 0 : 1; } }, W.agent - 0.05);
  tl.set("#caret", { opacity: 0 }, W.agent + 1.75);
  // the train, as a constellation
  const tsv = $("#trainSvg");
  const trainPath = sv("path", { d: "M40 330 L40 200 L260 200 L260 330 M260 200 L330 200 L330 110 L470 110 L470 330 L590 330 M120 200 L120 140 L170 140 L170 200", fill: "none", stroke: "#fff8e4", "stroke-width": 5, "stroke-linecap": "round", "stroke-linejoin": "round", pathLength: 1, "stroke-dasharray": 1, "stroke-dashoffset": 1 }, tsv);
  const wheels = [[130, 360], [250, 360], [400, 360], [520, 360]].map(([cx, cy]) => sv("circle", { cx, cy, r: 34, fill: "none", stroke: "#fff8e4", "stroke-width": 5, pathLength: 1, "stroke-dasharray": 1, "stroke-dashoffset": 1 }, tsv));
  [[40, 200, "#f7cf73"], [260, 200, "#9ee9da"], [330, 110, "#c69cef"], [470, 110, "#f7cf73"], [590, 330, "#9ee9da"], [40, 330, "#c69cef"], [120, 140, "#f7cf73"], [170, 140, "#9ee9da"]].forEach(([x, y, c], i) => {
    const g = sv("g", { transform: `translate(${x} ${y})` }, tsv); const inn = sv("g", {}, g);
    sv("circle", { r: 15, fill: c, opacity: 0.35 }, inn); sv("polygon", { points: "0,-8 1.4,-1.4 8,0 1.4,1.4 0,8 -1.4,1.4 -8,0 -1.4,-1.4", fill: c, stroke: c, "stroke-width": 4, "stroke-linejoin": "round" }, inn); sv("circle", { r: 7, fill: "#fffdf2" }, inn);
    tl.fromTo(inn, { opacity: 0, scale: 0 }, { opacity: 1, scale: 1, duration: 0.45, ease: "back.out(3)" }, W.agent + 0.4 + i * 0.1);
  });
  tl.fromTo(trainPath, { attr: { "stroke-dashoffset": 1 } }, { attr: { "stroke-dashoffset": 0 }, duration: 1.0, ease: bez(0.4, 0, 0.2, 1) }, W.agent + 0.55);
  wheels.forEach((w, i) => tl.fromTo(w, { attr: { "stroke-dashoffset": 1 } }, { attr: { "stroke-dashoffset": 0 }, duration: 0.45, ease: E.out }, W.agent + 1.2 + i * 0.1));
  // open tools
  [["Activity skill", 96], ["Voice engine", 460], ["Validator", 786]].forEach(([lbl, x], i) => {
    const c = el("div", "toolchip", `left:${x}px;top:960px`, $("#toolChips")); c.innerHTML = `<i></i>${lbl}`;
    tl.fromTo(c, { opacity: 0, scale: 0.6, y: 20 }, { opacity: 1, scale: 1, y: 0, duration: 0.5, ease: "back.out(2.4)" }, W.tools + i * 0.28);
  });
  // the constellation becomes a real Activity tile
  tl.set("#newTile", { left: 1299, top: 640 }, 0);
  tl.to("#trainSvg", { scale: 0.2, x: 1100, y: 250, opacity: 0, duration: 0.5, ease: inExp(2.5) }, W.voices - 0.65);
  tl.fromTo("#newTile", { opacity: 0, scale: 0.2 }, { opacity: 1, scale: 1, duration: 0.7, ease: "elastic.out(1,0.55)" }, W.voices - 0.3);
  tl.set("#flash2", { opacity: 0 }, 0); tl.fromTo("#flash2", { opacity: 0.35 }, { opacity: 0, duration: 0.5, ease: "power2.out", immediateRender: false }, W.voices - 0.3);
  // ...and the characters give it a voice
  const vr = $("#voiceRow"); const VCH = ["lilli", "leo", "flash", "tito", "momo", "dani"];
  VCH.forEach((n, i) => {
    const x = 1020 + i * 142, y = 840;
    const c = el("div", "vchar", `left:${x}px;top:${y}px`, vr); el("img", "", "", c).src = `assets/svg/${n}_pose_${i % 2 ? "wave" : "cheer"}.svg`;
    const t = W.voices + i * 0.16;
    tl.fromTo(c, { opacity: 0, scale: 0, y: 40 }, { opacity: 1, scale: 1, y: 0, duration: 0.6, ease: "elastic.out(1,0.5)" }, t);
    const wave = el("div", "vwave", `left:${x + 66}px;top:${y + 20}px`, vr);
    tl.fromTo(wave, { opacity: 0.9, scale: 0.4 }, { opacity: 0, scale: 3.6, duration: 0.9, ease: E.out, immediateRender: false }, t + 0.25);
    tl.set(wave, { opacity: 0 }, 0);
    tl.to(c, { y: -10, duration: 0.5, ease: "sine.inOut", yoyo: true, repeat: 3 }, t + 0.7);
  });
  tl.fromTo("#s8note", { opacity: 0 }, { opacity: 1, duration: 0.6, ease: E.out }, A0 + 1.0);
  ["#toolChips", "#voiceRow", "#gridWrap", "#newTile", "#s8note", "#wishKick", "#wish"].forEach((s) => tl.to(s, { opacity: 0, duration: 0.3, ease: "power2.in" }, ABS(shift(51.4) - 0.5)));

  /* ======================================== S9  close: built at home, open to every child, built to grow ======================================== */
  const Z = SC.s9;
  sky($("#s9stars"), 95, 640, 9, Z, 55);
  flies($("#s9flies"), 14, 9, Z + 0.2);
  tl.fromTo("#s9", { opacity: 0 }, { opacity: 1, duration: 0.7, ease: "power1.out" }, Z);
  tl.fromTo("#s9cam", { scale: 1.02, x: 10, y: 0 }, { scale: 1.1, x: -20, y: 14, duration: 9.0, ease: "none" }, Z);
  mkLogo($("#logo9"), "b", Z + 0.3, 0.4, true);
  const c1 = words($("#c1"), "Built for our daughters.", ""), c2 = words($("#c2"), "Now free and open source.", "");
  wordIn(c1, [W.daughters - 0.05, W.daughters + 0.25, W.daughters + 0.5, W.daughters + 0.8], 0.6);
  tl.to("#cl1txt", { opacity: 0, y: -24, duration: 0.4, ease: "power2.in" }, W.open - 0.45);
  wordIn(c2, [W.open - 0.05, W.open + 0.4, W.open + 0.7, W.open + 1.05, W.open + 1.4], 0.6);
  c2.slice(1).forEach((w) => (w.style.color = "#f9d65c"));
  tl.to("#cl2txt", { opacity: 0, y: -24, duration: 0.4, ease: "power2.in" }, W.fam - 0.3);
  { const c3 = words($("#c3"), "For every family.", ""); wordIn(c3, [W.fam, W.fam + 0.3, W.fam + 0.55], 0.55); tl.to("#cl3txt", { opacity: 0, y: -24, duration: 0.4, ease: "power2.in" }, W.grow - 0.35); }
  // built to grow: small constellations (one per new Activity) light up across the night
  const gsv = $("#grow"); const gr = mulberry32(555);
  [[260, 220], [1580, 170], [420, 520], [1640, 470], [150, 400], [1760, 330], [610, 120], [1320, 120], [90, 150], [1840, 560]].forEach(([cx, cy], k) => {
    const pts = []; let x = cx, y = cy; const n = 4 + Math.floor(gr() * 3);
    for (let i = 0; i < n; i++) { pts.push([x, y]); x += (gr() - 0.3) * 120; y += (gr() - 0.5) * 110; }
    const d = "M" + pts.map((p) => p.join(" ")).join(" L");
    const path = sv("path", { d, fill: "none", stroke: "#fff8e4", "stroke-width": 2.5, "stroke-linecap": "round", "stroke-linejoin": "round", pathLength: 1, "stroke-dasharray": 1, "stroke-dashoffset": 1, opacity: 0.75 }, gsv);
    const t0 = W.grow - 1.1 + k * 0.22;
    tl.fromTo(path, { attr: { "stroke-dashoffset": 1 } }, { attr: { "stroke-dashoffset": 0 }, duration: 0.8, ease: bez(0.4, 0, 0.2, 1) }, t0 + 0.2);
    pts.forEach(([px, py], i) => {
      const col = ["#f7cf73", "#9ee9da", "#c69cef"][(k + i) % 3];
      const g = sv("g", { transform: `translate(${px} ${py})` }, gsv); const inn = sv("g", {}, g);
      sv("circle", { r: 9, fill: col, opacity: 0.3 }, inn); sv("polygon", { points: "0,-5.2 0.92,-0.92 5.2,0 0.92,0.92 0,5.2 -0.92,0.92 -5.2,0 -0.92,-0.92", fill: col, stroke: col, "stroke-width": 3, "stroke-linejoin": "round" }, inn); sv("circle", { r: 3.4, fill: "#fffdf2" }, inn);
      tl.fromTo(inn, { opacity: 0, scale: 0 }, { opacity: 1, scale: 1, duration: 0.4, ease: "back.out(3)" }, t0 + i * 0.12);
    });
  });
  const tg = words($("#tg1"), "Built to grow.", "");
  wordIn(tg, [W.grow - 0.05, W.grow + 0.3, W.grow + 0.55], 0.6);
  tg.forEach((w) => (w.style.color = "#f9d65c"));
  $("#fp1").textContent = "Open source · In active development · frozenpepper.it/greia";
  tl.fromTo("#fp1", { opacity: 0, y: 10 }, { opacity: 1, y: 0, duration: 0.6, ease: E.out }, W.open + 0.7);
  tl.to("#fadeOut", { opacity: 1, duration: 0.7, ease: "power2.in" }, TL.durationRaw - 0.75);

  /* ---------- film grain: seeded jitter every 2 frames ---------- */
  const gc = $("#grain"), gx = gc.getContext("2d"); const gi = gx.createImageData(480, 270); const gr2 = mulberry32(99);
  for (let i = 0; i < gi.data.length; i += 4) { const v = gr2() * 255; gi.data[i] = gi.data[i + 1] = gi.data[i + 2] = v; gi.data[i + 3] = 255; }
  gx.putImageData(gi, 0, 0);
  const GJ = { t: 0 };
  SH.on = false;
  tl.to(GJ, { t: TL.duration, duration: TL.duration, ease: "none", onUpdate: () => { const f = Math.floor(GJ.t * 15); const a = mulberry32(f + 5); gc.style.transform = `translate(${(a() * 80 - 40).toFixed(1)}px,${(a() * 80 - 40).toFixed(1)}px)`; } }, 0);

  window.__timelines["main"] = tl;
})();
