// 좌표로 그리는 그림: 도형(geo), 자(ruler), 각도기(protractor).
// 그림 설명을 단위 좌표(y는 위쪽이 +)의 기본 도형 목록으로 바꾸고,
// 슬라이드(figures.js)와 활동지(build_handouts.js)가 같은 목록을 각자 그린다.
// 글자 크기에 맞춰야 하는 길이(이름표 간격, 직각 표시 크기)는 em(라벨 글자 높이를 단위 좌표로 바꾼 값)으로 정한다.

const sub = (a, b) => [a[0] - b[0], a[1] - b[1]];
const add = (a, b) => [a[0] + b[0], a[1] + b[1]];
const mul = (a, k) => [a[0] * k, a[1] * k];
const len = (a) => Math.hypot(a[0], a[1]);
const unit = (a) => { const l = len(a); return l < 1e-9 ? [0, 0] : [a[0] / l, a[1] / l]; };
const deg = (a) => (Math.atan2(a[1], a[0]) * 180) / Math.PI;
const polar = (c, r, d) => [c[0] + r * Math.cos((d * Math.PI) / 180), c[1] + r * Math.sin((d * Math.PI) / 180)];
const DIRS = { up: [0, 1], down: [0, -1], left: [-1, 0], right: [1, 0], ul: [-0.7, 0.7], ur: [0.7, 0.7], dl: [-0.7, -0.7], dr: [0.7, -0.7] };

function at(fig, p) {
  if (Array.isArray(p)) return p;
  const v = (fig.points || {})[p];
  if (!v) throw new Error(`geo: 점 '${p}'이(가) points에 없습니다`);
  return v;
}

function arcPts(c, r, a1, a2, n = 48) {
  const out = [];
  for (let i = 0; i <= n; i++) out.push(polar(c, r, a1 + ((a2 - a1) * i) / n));
  return out;
}

// ---------- 도형 ----------
function segEnds(fig, s) {
  let a = at(fig, s.from), b = at(fig, s.to);
  const d = unit(sub(b, a)), e = s.ext ?? 1.2;
  if (s.extend === "end" || s.extend === "both") b = add(b, mul(d, e));
  if (s.extend === "start" || s.extend === "both") a = sub(a, mul(d, e));
  return [a, b];
}

function geoExtent(fig, forGrid = false) {
  const pts = Object.values(fig.points || {});
  for (const pg of fig.polygons || []) pts.push(...pg.pts.map((p) => at(fig, p)));
  for (const s of fig.segments || []) pts.push(...segEnds(fig, s));
  for (const c of fig.circles || []) { const o = at(fig, c.center); pts.push([o[0] - c.r, o[1] - c.r], [o[0] + c.r, o[1] + c.r]); }
  if (fig.grid_range) pts.push(fig.grid_range.slice(0, 2), fig.grid_range.slice(2));
  if (!pts.length) throw new Error("geo: 그릴 점이 없습니다(빈 모눈은 grid_range를 준다)");
  const xs = pts.map((p) => p[0]), ys = pts.map((p) => p[1]);
  let e = [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)];
  const m = Math.round(fig.grid_margin ?? 1);
  if (fig.grid && !fig.grid_range) e = [Math.floor(e[0]) - m, Math.floor(e[1]) - m, Math.ceil(e[2]) + m, Math.ceil(e[3]) + m];
  if (forGrid) return e;
  // 글(texts)은 모눈 범위에는 넣지 않고 그림 전체 범위에만 넣는다(모눈 밖에 쓸 수 있게).
  for (const t of fig.texts || []) {
    const p = at(fig, t.at);
    e = [Math.min(e[0], p[0]), Math.min(e[1], p[1]), Math.max(e[2], p[0]), Math.max(e[3], p[1])];
  }
  return e;
}

function neighbours(fig, name) {
  const out = [];
  const link = (list, i, closed) => {
    const n = list.length;
    if (i > 0 || closed) out.push(list[(i - 1 + n) % n]);
    if (i < n - 1 || closed) out.push(list[(i + 1) % n]);
  };
  for (const pg of fig.polygons || []) pg.pts.forEach((p, i) => { if (p === name) link(pg.pts, i, pg.open !== true); });
  const pts = out.map((q) => at(fig, q));
  for (const s of fig.segments || []) {
    const [a, b] = segEnds(fig, s);
    if (s.from === name) { pts.push(at(fig, s.to)); if (s.extend === "start" || s.extend === "both") pts.push(a); }
    if (s.to === name) { pts.push(at(fig, s.from)); if (s.extend === "end" || s.extend === "both") pts.push(b); }
  }
  return pts;
}

function nameDir(fig, name) {
  const want = (fig.name_dir || {})[name];
  if (want) return unit(DIRS[want] || want);
  const p = at(fig, name);
  const nb = neighbours(fig, name);
  if (nb.length) {
    const s = nb.reduce((acc, q) => add(acc, unit(sub(q, p))), [0, 0]);
    if (len(s) > 0.2) return unit(mul(s, -1));
    const d = unit(sub(nb[0], p)), perp = [-d[1], d[0]];
    return perp[1] >= -1e-9 ? perp : mul(perp, -1);
  }
  const all = Object.values(fig.points);
  const c = mul(all.reduce(add, [0, 0]), 1 / all.length);
  const d = unit(sub(p, c));
  return len(d) ? d : [0, 1];
}

const fillOf = (f) => (f === "none" || f === false ? null : f);

function geoPrims(fig, em) {
  const out = [];
  const centre = (() => { const v = Object.values(fig.points || {}); return v.length ? mul(v.reduce(add, [0, 0]), 1 / v.length) : [0, 0]; })();
  // 모눈 위 도형: 색은 모눈 아래, 테두리는 모눈 위에 그려 칸을 셀 수 있게 한다.
  if (fig.grid) for (const pg of fig.polygons || []) if (!pg.open && fillOf(pg.fill ?? "tint")) out.push({ k: "poly", pts: pg.pts.map((p) => at(fig, p)), closed: true, fill: fillOf(pg.fill ?? "tint"), w: 0 });
  if (fig.grid) {
    const [x0, y0, x1, y1] = geoExtent(fig, true);
    if (fig.grid === "dot") {
      for (let x = x0; x <= x1 + 1e-9; x++) for (let y = y0; y <= y1 + 1e-9; y++) out.push({ k: "dot", c: [x, y], size: 0.35, color: "grid" });
    } else {
      for (let x = x0; x <= x1 + 1e-9; x++) out.push({ k: "line", a: [x, y0], b: [x, y1], w: 0.75, color: "grid" });
      for (let y = y0; y <= y1 + 1e-9; y++) out.push({ k: "line", a: [x0, y], b: [x1, y], w: 0.75, color: "grid" });
    }
  }
  for (const pg of fig.polygons || []) {
    out.push({ k: "poly", pts: pg.pts.map((p) => at(fig, p)), closed: pg.open !== true, fill: pg.open || fig.grid ? null : fillOf(pg.fill ?? "tint"), dash: !!pg.dash, w: pg.width || 2.25, color: pg.color || "ink", main: true });
  }
  for (const c of fig.circles || []) {
    out.push({ k: "circle", c: at(fig, c.center), r: c.r, fill: fillOf(c.fill ?? "none"), dash: !!c.dash, w: c.width || 2.25, color: c.color || "ink", main: true });
  }
  for (const a of [...(fig.angles || []), ...(fig.rights || []).map((r) => ({ from: r[0], at: r[1], to: r[2], right: true }))]) {
    const v = at(fig, a.at), p = at(fig, a.from), q = at(fig, a.to);
    let a1 = deg(sub(p, v)), a2 = deg(sub(q, v));
    let sweep = ((a2 - a1) % 360 + 360) % 360;
    if (sweep > 180) { [a1, a2] = [a2, a1]; sweep = 360 - sweep; }
    const room = 0.35 * Math.min(len(sub(p, v)), len(sub(q, v)));
    if (a.right) {
      const m = Math.min(0.75 * em, room);
      const u = mul(unit(sub(p, v)), m), w = mul(unit(sub(q, v)), m);
      out.push({ k: "poly", pts: [add(v, u), add(add(v, u), w), add(v, w)], closed: false, fill: null, w: 1.75, color: "ink" });
    } else {
      const r = a.r ?? Math.min(1.3 * em, (room * 0.25) / 0.35);
      out.push({ k: "sector", c: v, r, a1, a2: a1 + sweep, fill: a.fill || "yellow" });
      // 좁은 각은 이름표가 두 변에 닿지 않을 만큼 꼭짓점에서 멀리 둔다.
      const half = Math.sin((Math.min(sweep, 179) * Math.PI) / 360);
      const dist = a.label_dist ?? Math.max(r + 0.95 * em, (0.9 * em) / Math.max(half, 0.15));
      if (a.label) out.push({ k: "text", at: polar(v, dist, a1 + sweep / 2), text: a.label, size: "label" });
    }
  }
  for (const s of fig.segments || []) {
    const [a, b] = segEnds(fig, s);
    out.push({ k: "line", a, b, w: s.width || 2.25, color: s.color || "ink", dash: !!s.dash, arrowStart: s.arrow === "start" || s.arrow === "both", arrowEnd: s.arrow === "end" || s.arrow === "both", main: true });
  }
  // 같은 길이 표시(ticks)와 길이 이름표는 모든 변(다각형의 변·선분)에 줄 수 있다.
  const sides = [];
  for (const pg of fig.polygons || []) (pg.sides || []).forEach((sd, i) => { if (sd) { const n = pg.pts.length; sides.push({ a: at(fig, pg.pts[i]), b: at(fig, pg.pts[(i + 1) % n]), ...sd }); } });
  for (const s of fig.segments || []) if (s.label || s.ticks) sides.push({ a: at(fig, s.from), b: at(fig, s.to), label: s.label, ticks: s.ticks, side: s.label_side });
  for (const sd of sides) {
    const mid = mul(add(sd.a, sd.b), 0.5), d = unit(sub(sd.b, sd.a));
    let n = [-d[1], d[0]];
    if (sd.side ? sd.side < 0 : len(sub(add(mid, n), centre)) < len(sub(mid, centre))) n = mul(n, -1);
    for (let t = 0; t < (sd.ticks || 0); t++) {
      const c = add(mid, mul(d, (t - (sd.ticks - 1) / 2) * 0.28 * em));
      out.push({ k: "line", a: add(c, mul(n, 0.3 * em)), b: sub(c, mul(n, 0.3 * em)), w: 1.75, color: "ink" });
    }
    if (sd.label) {
      // 이름표 상자(폭 tw, 높이 th)가 변과 겹치지 않을 만큼 법선 방향으로 띄운다.
      const rows = String(sd.label).split("\n");
      const tw = Math.max(...rows.map((r) => [...r].reduce((s, ch) => s + (/[가-힯ㄱ-ㆎ㈀-㋿]/.test(ch) ? 0.98 : ch === " " ? 0.3 : 0.62), 0))) * em;
      const th = 1.2 * rows.length * em;
      const d = 0.3 * em + Math.abs(n[0]) * tw / 2 + Math.abs(n[1]) * th / 2;
      out.push({ k: "text", at: add(mid, mul(n, d)), text: sd.label, size: "label" });
    }
  }
  const dots = fig.dots === true ? Object.keys(fig.points || {}).filter((n) => !n.startsWith("_")) : fig.dots || [];
  for (const d of dots) out.push({ k: "dot", c: at(fig, d), size: 1, color: "ink" });
  if (fig.names !== false) {
    for (const name of Object.keys(fig.points || {})) {
      if (name.startsWith("_")) continue;
      out.push({ k: "text", at: add(at(fig, name), mul(nameDir(fig, name), 0.8 * em)), text: name, size: "label" });
    }
  }
  for (const t of fig.texts || []) out.push({ k: "text", at: at(fig, t.at), text: t.text, size: t.size || "label", color: t.color, bold: t.bold, bg: !!t.bg });
  return out;
}

// ---------- 자 ----------
// 1단위 = 1 cm. 위쪽 가장자리(y=0)에 눈금, 물건은 그 위(y>0)에 막대로 그린다.
function rulerExtent(fig) {
  const top = (fig.objects || []).length ? 0.25 + 0.6 * fig.objects.length : 0;
  return [-0.4, -1.35, fig.cm + 0.4, top];
}

function rulerPrims(fig, em) {
  const out = [{ k: "poly", pts: [[-0.4, 0], [fig.cm + 0.4, 0], [fig.cm + 0.4, -1.35], [-0.4, -1.35]], closed: true, fill: "paper", w: 1.5, color: "ink", main: true }];
  const step = fig.mm === false ? 0.5 : 0.1;
  for (let i = 0; i <= Math.round(fig.cm / step); i++) {
    const x = i * step, isCm = Math.abs(x - Math.round(x)) < 1e-6, isHalf = Math.abs(x * 2 - Math.round(x * 2)) < 1e-6;
    out.push({ k: "line", a: [x, 0], b: [x, isCm ? -0.5 : isHalf ? -0.35 : -0.22], w: isCm ? 1.5 : 0.75, color: "ink" });
    if (isCm && fig.numbers !== false) out.push({ k: "text", at: [x, -0.5 - 0.6 * em], text: String((fig.start || 0) + Math.round(x)), size: "label" });
  }
  (fig.objects || []).forEach((o, i) => {
    const y0 = 0.25 + 0.6 * i;
    out.push({ k: "poly", pts: [[o.from, y0], [o.to, y0], [o.to, y0 + 0.4], [o.from, y0 + 0.4]], closed: true, fill: o.fill || "accent", w: 1.5, color: "ink" });
    if (o.label) out.push({ k: "text", at: [(o.from + o.to) / 2, y0 + 0.2], text: o.label, size: "label", color: "onFill" });
    if (o.guide !== false) for (const x of [o.from, o.to]) out.push({ k: "line", a: [x, y0], b: [x, 0], w: 1, color: "accent", dash: true });
  });
  return out;
}

// ---------- 각도기 ----------
// 중심 (0,0), 반지름 1. 안쪽 눈금은 오른쪽 0°에서 시계 반대 방향, 바깥쪽 눈금은 왼쪽 0°에서 시계 방향.
function protractorExtent(fig) {
  const r = fig.ray ?? 1.2;
  return [-Math.max(1.05, r), -0.15, Math.max(1.05, r), Math.max(1.05, r)];
}

function protractorPrims(fig, em) {
  const out = [{ k: "poly", pts: [...arcPts([0, 0], 1, 0, 180, 72), [-1, 0]], closed: true, fill: "paper", w: 1.5, color: "ink" }];
  for (let d = 0; d <= 180; d += 5) {
    const long = d % 10 === 0;
    out.push({ k: "line", a: polar([0, 0], 1, d), b: polar([0, 0], long ? 0.88 : 0.93, d), w: long ? 1.25 : 0.75, color: "ink" });
  }
  out.push({ k: "line", a: [-1, 0], b: [1, 0], w: 1.5, color: "ink" });
  out.push({ k: "line", a: [0, 0], b: [0, 0.12], w: 1.5, color: "ink" });
  const base = fig.base || 0, r = fig.ray ?? 1.2;
  if (fig.deg != null) {
    if (fig.mark !== false) out.push({ k: "sector", c: [0, 0], r: 0.3, a1: base, a2: base + fig.deg, fill: "yellow" });
    out.push({ k: "line", a: [0, 0], b: polar([0, 0], r, base), w: 2.5, color: "ink", main: true });
    out.push({ k: "line", a: [0, 0], b: polar([0, 0], r, base + fig.deg), w: 2.5, color: "ink" });
  }
  // 숫자는 변(반직선) 위에 흰 바탕으로 써서 읽어야 할 숫자가 선에 가려지지 않게 한다.
  // 숫자 간격이 좁으면(각도기가 작으면) 20°마다 쓴다. em이 작을수록 각도기가 크다.
  const step = fig.step || (em <= 0.2 ? 10 : 20);
  const scales = fig.scales || "both";
  const lift = (d, p) => (d === 0 || d === 180 ? [p[0], p[1] + 0.55 * em] : p);
  for (let d = 0; d <= 180; d += step) {
    // 0·180은 밑금 위로 올려 쓰므로 흰 바탕이 필요 없다(바탕이 옆 숫자를 가리지 않게).
    const bg = d !== 0 && d !== 180;
    if (scales !== "inner") out.push({ k: "text", at: lift(d, polar([0, 0], 0.8, 180 - d)), text: String(d), size: "tiny", color: "info", bg });
    if (scales !== "outer") out.push({ k: "text", at: lift(d, polar([0, 0], 0.64, d)), text: String(d), size: "tinier", color: "accent", bg });
  }
  out.push({ k: "dot", c: [0, 0], size: 0.8, color: "ink" });
  return out;
}

const KINDS = {
  geo: { extent: geoExtent, prims: geoPrims, maxUnit: 1.0, pad: (f) => (f.names !== false && Object.keys(f.points || {}).some((n) => !n.startsWith("_"))) || (f.angles || []).some((a) => a.label) || (f.segments || []).some((s) => s.label) || (f.polygons || []).some((p) => (p.sides || []).some((s) => s && s.label)) },
  ruler: { extent: rulerExtent, prims: rulerPrims, maxUnit: 1.0, pad: () => false },
  protractor: { extent: protractorExtent, prims: protractorPrims, maxUnit: 3.2, pad: () => false },
};

// 상자(물리 단위: 슬라이드는 인치, 활동지는 mm)에 맞춰 축척을 정하고 기본 도형 목록을 돌려준다.
// labelSize: 라벨 글자 높이(같은 물리 단위). 돌려주는 map(p)는 단위 좌표 → 물리 좌표(y는 아래가 +).
function layout(fig, box, labelSize, maxUnit) {
  const K = KINDS[fig.type];
  const e = K.extent(fig);
  // 이름표 자리: 글자 1.2줄만큼, 단 작은 상자에서는 상자의 20%까지만.
  const pad = K.pad(fig) ? Math.min(labelSize * 1.2, 0.2 * box.w, 0.2 * box.h) : labelSize * 0.3;
  const spanX = Math.max(e[2] - e[0], 1e-6), spanY = Math.max(e[3] - e[1], 1e-6);
  const s = Math.min((box.w - 2 * pad) / spanX, (box.h - 2 * pad) / spanY, maxUnit ?? K.maxUnit);
  if (s <= 0) throw new Error(`${fig.type}: 그림 상자가 너무 작습니다`);
  const ox = box.x + (box.w - spanX * s) / 2 - e[0] * s;
  const oy = box.y + (box.h - spanY * s) / 2 + e[3] * s;
  return { s, prims: K.prims(fig, labelSize / s), map: (p) => [ox + p[0] * s, oy - p[1] * s], used: { w: spanX * s + 2 * pad, h: spanY * s + 2 * pad } };
}

// 활동지용 SVG. 1단위 = unitMm mm(자는 실제 cm 크기 그대로).
function toSvg(fig, opts = {}) {
  const K = KINDS[fig.type];
  const e = K.extent(fig);
  const ptMm = (opts.pt || 11) * 0.3528;
  const pad = K.pad(fig) ? ptMm * 1.6 : ptMm * 0.3;
  const unitMm = fig.type === "ruler" ? 10 : fig.type === "protractor" ? (fig.ws_radius || 45) : fig.ws_unit || 10;
  const maxW = opts.maxW || 170, maxH = fig.ws_max_h || opts.maxH || 80;
  const s = Math.min(unitMm, (maxW - 2 * pad) / Math.max(e[2] - e[0], 1e-6), (maxH - 2 * pad) / Math.max(e[3] - e[1], 1e-6));
  const W = (e[2] - e[0]) * s + 2 * pad, H = (e[3] - e[1]) * s + 2 * pad;
  const X = (p) => (pad + (p[0] - e[0]) * s).toFixed(2), Y = (p) => (pad + (e[3] - p[1]) * s).toFixed(2);
  const C = { ink: "#1F2937", grid: "#B8C2CC", accent: "#E9762B", info: "#3D5A80", good: "#2A9D8F", onFill: "#1F2937" };
  const F = { tint: "#FBE3D2", accent: "#E9762B", good: "#2A9D8F", info: "#3D5A80", yellow: "#F2C14E", paper: "#FFFFFF" };
  const col = (c) => C[c] || (c ? `#${c}` : C.ink);
  const fil = (f) => (f ? F[f] || `#${f}` : "none");
  const sw = (w) => ((w || 1.5) * 0.3528 * 0.8).toFixed(2);
  const prims = K.prims(fig, ptMm / s);
  let g = "";
  for (const q of prims) {
    const dash = q.dash ? ` stroke-dasharray="2 1.4"` : "";
    if (q.k === "line") {
      const mk = `${q.arrowEnd ? ` marker-end="url(#ah)"` : ""}${q.arrowStart ? ` marker-start="url(#ahs)"` : ""}`;
      g += `<line x1="${X(q.a)}" y1="${Y(q.a)}" x2="${X(q.b)}" y2="${Y(q.b)}" stroke="${col(q.color)}" stroke-width="${sw(q.w)}"${dash}${mk}/>`;
    } else if (q.k === "poly") {
      g += `<${q.closed ? "polygon" : "polyline"} points="${q.pts.map((p) => `${X(p)},${Y(p)}`).join(" ")}" fill="${fil(q.fill)}" ${q.w === 0 ? `stroke="none"` : `stroke="${col(q.color)}" stroke-width="${sw(q.w)}"`}${dash}/>`;
    } else if (q.k === "circle") {
      g += `<circle cx="${X(q.c)}" cy="${Y(q.c)}" r="${(q.r * s).toFixed(2)}" fill="${fil(q.fill)}" stroke="${col(q.color)}" stroke-width="${sw(q.w)}"${dash}/>`;
    } else if (q.k === "sector") {
      const pts = [q.c, ...arcPts(q.c, q.r, q.a1, q.a2, 24)];
      g += `<polygon points="${pts.map((p) => `${X(p)},${Y(p)}`).join(" ")}" fill="${fil(q.fill)}" stroke="none"/>`;
    } else if (q.k === "dot") {
      g += `<circle cx="${X(q.c)}" cy="${Y(q.c)}" r="${(0.7 * q.size).toFixed(2)}" fill="${col(q.color)}"/>`;
    } else if (q.k === "text") {
      const size = q.size === "tiny" || q.size === "tinier" ? Math.min(8, Math.max(5.5, s * 0.16)) * (q.size === "tinier" ? 0.88 : 1) : /^[\u3131-\u318E]+$/.test(String(q.text)) ? (opts.pt || 11) * 1.35 : opts.pt || 11;
      String(q.text).split("\n").forEach((line, i, all) => {
        const dy = (i - (all.length - 1) / 2) * size * 0.3528 * 1.2;
        if (q.bg) {
          const tw = String(line).length * 0.6 * size * 0.3528 + 0.6, th = size * 0.3528 * 1.05;
          g += `<rect x="${(Number(X(q.at)) - tw / 2).toFixed(2)}" y="${(Number(Y(q.at)) + dy - th / 2).toFixed(2)}" width="${tw.toFixed(2)}" height="${th.toFixed(2)}" fill="#FFFFFF"/>`;
        }
        g += `<text x="${X(q.at)}" y="${(Number(Y(q.at)) + dy).toFixed(2)}" font-size="${(size * 0.3528).toFixed(2)}" text-anchor="middle" dominant-baseline="central" fill="${col(q.color)}" font-weight="${q.bold === false ? 400 : 700}">${String(line).replace(/&/g, "&amp;").replace(/</g, "&lt;")}</text>`;
      });
    }
  }
  const defs = `<defs><marker id="ah" viewBox="0 0 6 6" refX="5" refY="3" markerWidth="4" markerHeight="4" orient="auto"><path d="M0,0 L6,3 L0,6 z" fill="${C.ink}"/></marker><marker id="ahs" viewBox="0 0 6 6" refX="1" refY="3" markerWidth="4" markerHeight="4" orient="auto"><path d="M6,0 L0,3 L6,6 z" fill="${C.ink}"/></marker></defs>`;
  return `<svg width="${W.toFixed(1)}mm" height="${H.toFixed(1)}mm" viewBox="0 0 ${W.toFixed(2)} ${H.toFixed(2)}">${defs}${g}</svg>`;
}

module.exports = { KINDS, layout, toSvg, arcPts };
