// 교육용 그림 라이브러리. 모든 그림은 PowerPoint 도형·표·차트로 그려 수량이 정확하고 고칠 수 있다.
// 각 함수는 주어진 상자 box={x,y,w,h} 안에 들어가도록 크기를 정하고 가운데에 놓는다.
const { P, TINT, textOpts, colorOf } = require("./style");
const { widthIn } = require("./fit");

const INK = P.dk1;

function segment(deck, slide, sid, x1, y1, x2, y2, line) {
  // 기본 선은 왼쪽 위 → 오른쪽 아래로 그려진다. 다른 방향은 뒤집기로 나타낸다.
  const opts = {
    x: Math.min(x1, x2), y: Math.min(y1, y2), w: Math.abs(x2 - x1), h: Math.abs(y2 - y1),
    line, objectName: deck.name(sid, "line"),
  };
  const right = x2 >= x1;
  const down = y2 >= y1;
  if (right && !down) opts.flipV = true;
  if (!right && down) opts.flipH = true;
  if (!right && !down) { opts.flipH = true; opts.flipV = true; }
  slide.addShape(deck.pres.shapes.LINE, opts);
}

function label(deck, slide, sid, text, x, y, w, h, pt, extra = {}) {
  slide.addText(String(text), textOpts({
    x, y, w, h, fontSize: pt, color: colorOf(extra.color), bold: extra.bold !== false, align: extra.align || "center",
    valign: extra.valign || "middle", margin: 0, objectName: deck.name(sid, "label"),
  }));
}

function shadedSet(spec, total) {
  if (Array.isArray(spec)) return new Set(spec);
  return new Set(Array.from({ length: spec || 0 }, (_, i) => i).filter((i) => i < total));
}

// ---------- 분수 막대 ----------
function bars(deck, slide, sid, fig, box) {
  const list = fig.type === "bar" ? [fig] : fig.bars;
  const hasLabel = list.some((b) => b.label !== undefined);
  const labelW = hasLabel ? 1.15 : 0;
  const gap = 0.28;
  const barH = Math.min(fig.height || 0.9, (box.h - gap * (list.length - 1) - 0.3) / list.length);
  const barW = Math.min(box.w - labelW, fig.maxWidth || 11);
  const total = list.length * barH + (list.length - 1) * gap;
  const x0 = box.x + (box.w - labelW - barW) / 2 + labelW;
  let y = box.y + (box.h - total) / 2;
  const top = y;
  let guideX = null;
  list.forEach((b, i) => {
    const parts = b.widths ? b.widths.length : b.parts;
    const widths = b.widths || Array.from({ length: parts }, () => 1 / parts);
    const shaded = shadedSet(b.shaded, parts);
    if (b.label !== undefined) {
      if (Array.isArray(b.label)) {
        const pt = Math.min(28, Math.max(16, Math.floor(((barH + 0.2) * 72) / 2.6)));
        const m = deck.fracMetrics(pt, ...b.label);
        deck.frac(slide, sid, { x: x0 - labelW + (labelW - 0.15 - m.w) / 2, y: y + (barH - m.h) / 2, n: b.label[0], d: b.label[1], size: pt });
      } else {
        label(deck, slide, sid, b.label, x0 - labelW, y, labelW - 0.15, barH, deck.style.small);
      }
    }
    deck.bar(slide, sid, { x: x0, y, w: barW, h: barH, widths, shaded: [...shaded],
      alt: b.alt || `똑같이 ${parts}칸으로 나눈 띠${shaded.size ? `, ${shaded.size}칸 색칠` : ""}` });
    if (i === 0 && fig.guide) {
      const sorted = [...shaded].sort((a, c) => a - c);
      if (sorted.length && sorted.every((v, k) => v === k)) guideX = x0 + barW * widths.slice(0, sorted.length).reduce((s, v) => s + v, 0);
    }
    y += barH + gap;
  });
  if (guideX !== null && list.length > 1) deck.vline(slide, sid, { x: guideX, y1: top - 0.15, y2: y - gap + 0.15 });
}

// ---------- 격자 ----------
function grid(deck, slide, sid, fig, box) {
  const cell = Math.min(box.w / fig.cols, box.h / fig.rows, fig.cell || 1.1);
  const w = cell * fig.cols;
  const h = cell * fig.rows;
  const x = box.x + (box.w - w) / 2;
  const y = box.y + (box.h - h) / 2;
  let shaded = fig.shaded || [];
  if (typeof shaded === "number") shaded = Array.from({ length: shaded }, (_, k) => [Math.floor(k / fig.cols), k % fig.cols]);
  const total = shaded.length;
  deck.grid(slide, sid, { x, y, w, h, rows: fig.rows, cols: fig.cols, shaded,
    alt: fig.alt || `${fig.rows * fig.cols}칸 격자, ${total}칸 색칠` });
  if (fig.axis === "v") deck.vline(slide, sid, { x: x + w / 2, y1: y - 0.25, y2: y + h + 0.25 });
  if (fig.axis === "h") segment(deck, slide, sid, x - 0.25, y + h / 2, x + w + 0.25, y + h / 2, { color: P.accent4, width: 2, dashType: "dash" });
}

// ---------- 원 나누기 ----------
function pie(deck, slide, sid, fig, box) {
  const d = Math.min(box.w, box.h, fig.size || 3.2);
  const x = box.x + (box.w - d) / 2;
  const y = box.y + (box.h - d) / 2;
  const shaded = shadedSet(fig.shaded, fig.parts);
  for (let i = 0; i < fig.parts; i++) {
    const a0 = (270 + (i * 360) / fig.parts) % 360;
    const a1 = (270 + ((i + 1) * 360) / fig.parts) % 360;
    slide.addShape(deck.pres.shapes.PIE, {
      x, y, w: d, h: d, angleRange: [a0, a1], fill: { color: shaded.has(i) ? P.accent1 : P.lt1 },
      line: { color: INK, width: 1.5 }, objectName: deck.name(sid, "sector"),
    });
  }
  const name = deck.name(sid, "figure");
  slide.addShape(deck.pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color: P.lt1, transparency: 100 }, line: { color: INK, width: 2.25 }, objectName: name });
  deck.alt.set(name, fig.alt || `원을 똑같이 ${fig.parts}조각으로 나누고 ${shaded.size}조각 색칠`);
}

// ---------- 분수·식 ----------
function scaledPt(deck, fig, box, measure) {
  let pt = fig.size || deck.style.body + 4;
  while (pt > 16) {
    const m = measure(pt);
    if (m.w <= box.w && m.h <= box.h) return pt;
    pt -= 2;
  }
  return pt;
}

function eqWidth(deck, items, pt) {
  return items.reduce((s, it) => s + (Array.isArray(it) ? deck.fracMetrics(pt, ...it).w : deck.opWidth(it, pt)) + 0.12, -0.12);
}

function eq(deck, slide, sid, fig, box) {
  const lines = fig.lines || [fig.items];
  const gap = 0.35;
  // 분수가 없는 식은 한 줄 글자로 쓴다(□는 빈칸 글자)
  if (lines.every((l) => l.every((it) => !Array.isArray(it)))) {
    const txt = lines.map((l) => l.join(" ")).join("\n");
    const top = fig.size || deck.style.body + 4;
    const pt = deck.checkFit(sid, txt, box.w, box.h, [top, deck.style.body, deck.style.small, 16].filter((p, i, a) => p <= top && a.indexOf(p) === i));
    slide.addText(txt, textOpts({
      x: box.x, y: box.y, w: box.w, h: box.h, fontSize: pt, bold: true, color: colorOf(fig.color),
      align: fig.align === "left" ? "left" : "center", valign: "middle", margin: 0, objectName: deck.name(sid, "eqtext"),
    }));
    return;
  }
  const pt = scaledPt(deck, fig, box, (p) => ({
    w: Math.max(...lines.map((l) => eqWidth(deck, l, p))),
    h: lines.reduce((s, l) => s + deck.eqHeight(l, p), 0) + (lines.length - 1) * gap,
  }));
  const h1 = Math.max(...lines.map((l) => deck.eqHeight(l, pt)));
  const totalH = lines.length * h1 + (lines.length - 1) * gap;
  let y = box.y + (box.h - totalH) / 2;
  for (const items of lines) {
    const w = eqWidth(deck, items, pt);
    const x = fig.align === "left" ? box.x : box.x + (box.w - w) / 2;
    deck.eq(slide, sid, { x, y, size: pt, items, color: fig.color });
    y += h1 + gap;
  }
}

function eqx(deck, slide, sid, fig, box) {
  const lh = (deck.style.small * 1.25) / 72;
  const pt = scaledPt(deck, fig, box, (p) => ({
    w: deck.fracMetrics(p, ...fig.from).w + deck.opWidth(fig.join || "=", p) + deck.fracMetrics(p, ...fig.to).w + 0.24,
    h: deck.fracMetrics(p, 1, 1).h + 2 * (lh + 0.2),
  }));
  const w = deck.fracMetrics(pt, ...fig.from).w + deck.opWidth(fig.join || "=", pt) + deck.fracMetrics(pt, ...fig.to).w + 0.24;
  const h = deck.fracMetrics(pt, 1, 1).h;
  deck.eqx(slide, sid, { ...fig, x: box.x + (box.w - w) / 2, y: box.y + (box.h - h) / 2, size: pt });
}

function frac(deck, slide, sid, fig, box) {
  const pt = scaledPt(deck, fig, box, (p) => deck.fracMetrics(p, fig.n, fig.d));
  const m = deck.fracMetrics(pt, fig.n, fig.d);
  deck.frac(slide, sid, { x: box.x + (box.w - m.w) / 2, y: box.y + (box.h - m.h) / 2, n: fig.n, d: fig.d, size: pt, color: fig.color });
}

// ---------- 수직선 ----------
function numberline(deck, slide, sid, fig, box) {
  const step = fig.step || 1;
  const n = Math.round((fig.max - fig.min) / step);
  const x0 = box.x + 0.45;
  const x1 = box.x + box.w - 0.45;
  const pos = (v) => x0 + ((v - fig.min) / (fig.max - fig.min)) * (x1 - x0);
  const pt = Math.max(16, Math.min(deck.style.small, Math.floor(((x1 - x0) / (n + 1)) * 72 / 1.6)));
  const lh = (pt * 1.3) / 72;
  const jumps = fig.jumps || [];
  const hasAbove = jumps.length || (fig.marks || []).some((m) => m.label);
  const yLine = hasAbove ? box.y + Math.min(box.h - lh - 0.4, box.h * 0.62) : box.y + box.h / 2 - lh / 2;
  segment(deck, slide, sid, x0 - 0.3, yLine, x1 + 0.3, yLine, { color: INK, width: 2.25, beginArrowType: fig.arrows === false ? undefined : "triangle", endArrowType: fig.arrows === false ? undefined : "triangle" });
  const labels = fig.labels || "all";
  for (let i = 0; i <= n; i++) {
    const v = +(fig.min + i * step).toFixed(6);
    const major = fig.major ? Math.abs(v / fig.major - Math.round(v / fig.major)) < 1e-6 : true;
    segment(deck, slide, sid, pos(v), yLine - (major ? 0.16 : 0.09), pos(v), yLine + (major ? 0.16 : 0.09), { color: INK, width: 1.75 });
    const show = labels === "all" ? major : labels === "ends" ? i === 0 || i === n : Array.isArray(labels) && labels.includes(v);
    if (show) label(deck, slide, sid, fig.format ? fig.format(v) : v, pos(v) - 0.5, yLine + 0.2, 1.0, lh, pt, { bold: false });
  }
  for (const m of fig.marks || []) {
    const d = 0.2;
    slide.addShape(deck.pres.shapes.OVAL, { x: pos(m.at) - d / 2, y: yLine - d / 2, w: d, h: d, fill: { color: P.accent1 }, line: { color: P.accent1, width: 0 }, objectName: deck.name(sid, "mark") });
    if (m.label) label(deck, slide, sid, m.label, pos(m.at) - 0.6, yLine - 0.25 - lh, 1.2, lh, pt, { color: P.accent1 });
  }
  jumps.forEach((j, k) => {
    const yj = yLine - 0.42 - (fig.stackJumps ? k * 0.35 : 0);
    segment(deck, slide, sid, pos(j.from), yLine - 0.05, pos(j.from), yj, { color: P.accent4, width: 1.5 });
    segment(deck, slide, sid, pos(j.from), yj, pos(j.to), yj, { color: P.accent4, width: 2, endArrowType: "triangle" });
    if (j.label) label(deck, slide, sid, j.label, Math.min(pos(j.from), pos(j.to)), yj - lh - 0.02, Math.abs(pos(j.to) - pos(j.from)), lh, pt, { color: P.accent4 });
  });
  const name = deck.name(sid, "figure");
  slide.addShape(deck.pres.shapes.RECTANGLE, { x: x0 - 0.3, y: yLine - 0.2, w: x1 - x0 + 0.6, h: 0.4, fill: { color: P.lt1, transparency: 100 }, line: { color: P.lt1, transparency: 100, width: 0 }, objectName: name });
  deck.alt.set(name, fig.alt || `${fig.min}부터 ${fig.max}까지 ${step}씩 눈금이 있는 수직선`);
}

// ---------- 점 배열·십 칸·수 모형 ----------
function array(deck, slide, sid, fig, box) {
  // cell을 주면 여러 배열의 점 크기를 같게 맞출 수 있다(양 비교 그림에서 필요)
  const cell = Math.min(box.w / fig.cols, box.h / fig.rows, fig.cell || 0.75);
  const w = cell * fig.cols;
  const h = cell * fig.rows;
  const x = box.x + (box.w - w) / 2;
  const y = box.y + (box.h - h) / 2;
  const d = cell * 0.62;
  const count = fig.count ?? fig.rows * fig.cols;
  const crossedFrom = count - (fig.crossed || 0);
  for (let r = 0; r < fig.rows; r++) {
    for (let c = 0; c < fig.cols; c++) {
      if (r * fig.cols + c >= count) continue;
      slide.addShape(deck.pres.shapes.OVAL, {
        x: x + c * cell + (cell - d) / 2, y: y + r * cell + (cell - d) / 2, w: d, h: d,
        fill: { color: fig.color ? colorOf(fig.color) : P.accent1 }, line: { color: INK, width: 1 }, objectName: deck.name(sid, "dot"),
      });
      if (r * fig.cols + c >= crossedFrom) {
        const cx = x + c * cell + cell / 2;
        const cy = y + r * cell + cell / 2;
        const k = d * 0.62;
        segment(deck, slide, sid, cx - k, cy - k, cx + k, cy + k, { color: P.accent3, width: 3.5 });
        segment(deck, slide, sid, cx - k, cy + k, cx + k, cy - k, { color: P.accent3, width: 3.5 });
      }
    }
  }
  if (fig.group === "row") {
    for (let r = 0; r < fig.rows; r++) slide.addShape(deck.pres.shapes.ROUNDED_RECTANGLE, { x: x + 0.03, y: y + r * cell + 0.04, w: w - 0.06, h: cell - 0.08, rectRadius: 0.12, fill: { color: P.lt1, transparency: 100 }, line: { color: P.accent4, width: 2 }, objectName: deck.name(sid, "group") });
  } else if (fig.group === "col") {
    for (let c = 0; c < fig.cols; c++) slide.addShape(deck.pres.shapes.ROUNDED_RECTANGLE, { x: x + c * cell + 0.04, y: y + 0.03, w: cell - 0.08, h: h - 0.06, rectRadius: 0.12, fill: { color: P.lt1, transparency: 100 }, line: { color: P.accent4, width: 2 }, objectName: deck.name(sid, "group") });
  }
  const name = deck.name(sid, "figure");
  slide.addShape(deck.pres.shapes.RECTANGLE, { x, y, w, h, fill: { color: P.lt1, transparency: 100 }, line: { color: P.lt1, transparency: 100, width: 0 }, objectName: name });
  deck.alt.set(name, fig.alt || `점 ${count}개를 ${fig.rows}줄 ${fig.cols}개씩 놓은 배열${fig.crossed ? `, 그중 ${fig.crossed}개에 × 표시` : ""}`);
}

function tenframe(deck, slide, sid, fig, box) {
  const frames = fig.frames || (fig.count > 10 ? 2 : 1);
  const gap = 0.35;
  const cell = Math.min((box.w - (frames - 1) * gap) / (5 * frames), box.h / 2, 0.85);
  const fw = cell * 5;
  const x = box.x + (box.w - (fw * frames + gap * (frames - 1))) / 2;
  const y = box.y + (box.h - cell * 2) / 2;
  let left = fig.count;
  // split: [a, b] 이면 앞의 a개는 주황, 다음 b개는 파랑(예: 8과 옮겨 온 2)
  const split = fig.split || null;
  let placed = 0;
  for (let f = 0; f < frames; f++) {
    const fx = x + f * (fw + gap);
    for (let k = 0; k < 10; k++) {
      const cx = fx + (k % 5) * cell;
      const cy = y + Math.floor(k / 5) * cell;
      deck.cell(slide, sid, cx, cy, cell, cell, false, "cell");
      if (left > 0) {
        const d = cell * 0.66;
        const second = split && placed >= split[0];
        slide.addShape(deck.pres.shapes.OVAL, { x: cx + (cell - d) / 2, y: cy + (cell - d) / 2, w: d, h: d, fill: { color: second ? P.accent4 : P.accent1 }, line: { color: INK, width: 1 }, objectName: deck.name(sid, "dot") });
        left -= 1;
        placed += 1;
      }
    }
    deck.outline(slide, sid, { x: fx, y, w: fw, h: cell * 2 }, `${frames}개의 십 칸 틀 중 ${f + 1}번째: 모두 ${fig.count}개`);
  }
}

function blocks10(deck, slide, sid, fig, box) {
  const hund = fig.hundreds || 0;
  const tens = fig.tens || 0;
  const ones = fig.ones || 0;
  // 단위 정육면체 한 칸의 크기 u: 백 모형 10u, 십 모형 10u 높이
  const widthUnits = hund * 10.6 + tens * 1.6 + Math.ceil(ones / 5) * 1.3 + 1;
  const u = Math.min(box.h / 10.4, box.w / widthUnits, fig.unit || 0.38);
  let x = box.x + (box.w - u * (widthUnits - 1)) / 2;
  const y = box.y + (box.h - u * 10) / 2;
  const line = { color: INK, width: 0.75 };
  for (let k = 0; k < hund; k++) {
    slide.addShape(deck.pres.shapes.RECTANGLE, { x, y, w: u * 10, h: u * 10, fill: { color: "FBD3B4" }, line: { color: INK, width: 1.5 }, objectName: deck.name(sid, "flat") });
    for (let i = 1; i < 10; i++) {
      segment(deck, slide, sid, x + i * u, y, x + i * u, y + 10 * u, line);
      segment(deck, slide, sid, x, y + i * u, x + 10 * u, y + i * u, line);
    }
    x += u * 10.6;
  }
  for (let k = 0; k < tens; k++) {
    slide.addShape(deck.pres.shapes.RECTANGLE, { x, y, w: u, h: u * 10, fill: { color: "FBD3B4" }, line: { color: INK, width: 1.5 }, objectName: deck.name(sid, "rod") });
    for (let i = 1; i < 10; i++) segment(deck, slide, sid, x, y + i * u, x + u, y + i * u, line);
    x += u * 1.6;
  }
  for (let k = 0; k < ones; k++) {
    const col = Math.floor(k / 5);
    const row = k % 5;
    slide.addShape(deck.pres.shapes.RECTANGLE, { x: x + col * u * 1.3, y: y + 10 * u - (row + 1) * u * 1.25, w: u, h: u, fill: { color: "FBD3B4" }, line: { color: INK, width: 1.5 }, objectName: deck.name(sid, "unit") });
  }
  const name = deck.name(sid, "figure");
  slide.addShape(deck.pres.shapes.RECTANGLE, { x: box.x, y, w: 0.01, h: 0.01, fill: { color: P.lt1, transparency: 100 }, line: { color: P.lt1, transparency: 100, width: 0 }, objectName: name });
  deck.alt.set(name, fig.alt || `수 모형: 백 ${hund}개, 십 ${tens}개, 일 ${ones}개`);
}

// ---------- 표 ----------
function table(deck, slide, sid, fig, box) {
  const cols = (fig.headers || fig.rows[0]).length;
  const rows = fig.rows.length + (fig.headers ? 1 : 0);
  let pt = fig.size || deck.style.small;
  const rowH = () => Math.max(0.5, (pt * 1.6) / 72);
  while (pt > 16 && rows * rowH() > box.h) pt -= 2;
  const w = Math.min(box.w, fig.width || Math.max(cols * 1.8, 4));
  const colW = fig.widths ? fig.widths.map((f) => w * f) : Array.from({ length: cols }, () => w / cols);
  const cell = (t, head) => ({
    text: String(t), options: { bold: !!head, fill: { color: head ? P.lt2 : P.lt1 }, color: INK, align: fig.align || "center", valign: "middle", fontFace: deck.font, fontSize: pt },
  });
  // 칸마다 글이 들어가는지 본다(칸 높이에 두 줄까지)
  const allRows = [...(fig.headers ? [fig.headers] : []), ...fig.rows];
  allRows.forEach((r) => r.forEach((t, i) => deck.checkFit(sid, String(t), colW[i] - 0.1, Math.max(rowH(), (pt * 2.5) / 72), [pt])));
  const data = [];
  if (fig.headers) data.push(fig.headers.map((t) => cell(t, true)));
  fig.rows.forEach((r) => data.push(r.map((t, i) => cell(t, fig.firstColHead && i === 0))));
  const h = rows * rowH();
  slide.addTable(data, {
    x: box.x + (box.w - w) / 2, y: box.y + (box.h - h) / 2, w, colW, rowH: rowH(),
    border: { type: "solid", pt: 1, color: "94A3B8" }, margin: 3, objectName: deck.name(sid, "table"),
  });
}

function placevalue(deck, slide, sid, fig, box) {
  table(deck, slide, sid, { headers: fig.headers, rows: fig.rows, size: fig.size || deck.style.body, width: Math.min(box.w, fig.headers.length * 1.7) }, box);
}

// ---------- 시계 ----------
function clock(deck, slide, sid, fig, box) {
  const d = Math.min(box.w, box.h, fig.size || 3.4);
  const cx = box.x + box.w / 2;
  const cy = box.y + box.h / 2;
  const r = d / 2;
  const name = deck.name(sid, "figure");
  slide.addShape(deck.pres.shapes.OVAL, { x: cx - r, y: cy - r, w: d, h: d, fill: { color: P.lt1 }, line: { color: INK, width: 3 }, objectName: name });
  deck.alt.set(name, fig.alt || `시계: ${fig.h}시${fig.m ? ` ${fig.m}분` : ""}`);
  for (let k = 0; k < 60; k++) {
    const a = (k * 6 * Math.PI) / 180;
    const len = k % 5 === 0 ? 0.11 * r : 0.05 * r;
    segment(deck, slide, sid, cx + Math.sin(a) * (r - 0.04), cy - Math.cos(a) * (r - 0.04), cx + Math.sin(a) * (r - 0.04 - len), cy - Math.cos(a) * (r - 0.04 - len), { color: INK, width: k % 5 === 0 ? 2 : 0.75 });
  }
  const pt = Math.max(12, Math.round(r * 15));
  for (let k = 1; k <= 12; k++) {
    const a = (k * 30 * Math.PI) / 180;
    const lr = r * 0.74;
    label(deck, slide, sid, k, cx + Math.sin(a) * lr - 0.3, cy - Math.cos(a) * lr - 0.2, 0.6, 0.4, pt);
  }
  if (fig.h !== undefined) {
    const m = fig.m || 0;
    const ha = (((fig.h % 12) + m / 60) * 30 * Math.PI) / 180;
    const ma = (m * 6 * Math.PI) / 180;
    segment(deck, slide, sid, cx, cy, cx + Math.sin(ha) * r * 0.5, cy - Math.cos(ha) * r * 0.5, { color: P.accent3, width: 7 });
    segment(deck, slide, sid, cx, cy, cx + Math.sin(ma) * r * 0.78, cy - Math.cos(ma) * r * 0.78, { color: INK, width: 4 });
  }
  const dot = 0.12;
  slide.addShape(deck.pres.shapes.OVAL, { x: cx - dot / 2, y: cy - dot / 2, w: dot, h: dot, fill: { color: INK }, line: { color: INK, width: 0 }, objectName: deck.name(sid, "pin") });
}

// ---------- 도형 ----------
const SHAPE = {
  circle: ["ellipse", 1], triangle: ["triangle", 1.1], rtriangle: ["rtTriangle", 1.1], square: ["rect", 1], rect: ["rect", 1.6],
  pentagon: ["pentagon", 1.05], hexagon: ["hexagon", 1.15], parallelogram: ["parallelogram", 1.6], trapezoid: ["trapezoid", 1.5],
  rhombus: ["diamond", 0.8], cube: ["cube", 1], cuboid: ["cube", 1.5], cylinder: ["can", 0.75], sphere: ["ellipse", 1],
};
function shapes(deck, slide, sid, fig, box) {
  const n = fig.items.length;
  const pt = deck.style.small;
  const lh = fig.items.some((s) => s.label) ? (pt * 1.4) / 72 : 0;
  const slotW = box.w / n;
  const size = Math.min(slotW * 0.72, box.h - lh - 0.15, fig.size || 2.2);
  fig.items.forEach((s, i) => {
    const [preset, aspect] = SHAPE[s.shape] || SHAPE.square;
    let w = aspect >= 1 ? size : size * aspect;
    let h = aspect >= 1 ? size / aspect : size;
    if (s.shape === "cylinder") { w = size * 0.75; h = size; }
    const x = box.x + slotW * i + (slotW - w) / 2;
    const y = box.y + (box.h - lh - 0.15 - h) / 2;
    const name = deck.name(sid, "figure");
    const fill = s.fill === false ? P.lt1 : s.shaded ? P.accent1 : TINT.accent;
    if (s.shape === "cone") {
      slide.addShape("triangle", { x, y, w: size * 0.8, h: size, fill: { color: fill }, line: { color: INK, width: 2 }, objectName: name });
      slide.addShape(deck.pres.shapes.OVAL, { x, y: y + size - 0.18, w: size * 0.8, h: 0.36, fill: { color: fill }, line: { color: INK, width: 2 }, objectName: deck.name(sid, "base") });
    } else {
      slide.addShape(preset, { x, y, w, h, fill: { color: fill }, line: { color: INK, width: 2 }, objectName: name });
    }
    deck.alt.set(name, s.alt || s.label || s.shape);
    if (s.label) label(deck, slide, sid, s.label, box.x + slotW * i, box.y + box.h - lh, slotW, lh, pt);
  });
}

// ---------- 각 ----------
function angle(deck, slide, sid, fig, box) {
  const L = Math.min(box.w * 0.7, box.h * 1.3, 3.2);
  const rad = (fig.deg * Math.PI) / 180;
  const height = Math.max(Math.sin(rad), 0.25) * L;
  const vx = box.x + (box.w - L * Math.max(1, 1 - Math.cos(rad))) / 2 + (fig.deg > 90 ? -Math.cos(rad) * L : 0);
  const vy = box.y + (box.h + height) / 2;
  const r = Math.min(0.75, L * 0.3);
  slide.addShape(deck.pres.shapes.PIE, { x: vx - r, y: vy - r, w: 2 * r, h: 2 * r, angleRange: [360 - fig.deg, 0], fill: { color: P.accent5 }, line: { color: P.accent5, width: 0 }, objectName: deck.name(sid, "arcmark") });
  segment(deck, slide, sid, vx, vy, vx + L, vy, { color: INK, width: 2.5 });
  segment(deck, slide, sid, vx, vy, vx + Math.cos(rad) * L, vy - Math.sin(rad) * L, { color: INK, width: 2.5 });
  const name = deck.name(sid, "figure");
  slide.addShape(deck.pres.shapes.OVAL, { x: vx - 0.06, y: vy - 0.06, w: 0.12, h: 0.12, fill: { color: INK }, line: { color: INK, width: 0 }, objectName: name });
  deck.alt.set(name, fig.alt || `크기가 ${fig.deg}°인 각`);
  if (fig.label !== false) {
    const mid = rad / 2;
    label(deck, slide, sid, fig.label || `${fig.deg}°`, vx + Math.cos(mid) * (r + 0.5) - 0.6, vy - Math.sin(mid) * (r + 0.5) - 0.22, 1.2, 0.44, deck.style.small);
  }
}

// ---------- 차트 ----------
function chart(deck, slide, sid, fig, box) {
  const type = { bar: deck.pres.charts.BAR, line: deck.pres.charts.LINE, pie: deck.pres.charts.PIE }[fig.chart || "bar"];
  const data = [{ name: fig.series || fig.title || "자료", labels: fig.labels.map(String), values: fig.values }];
  const pt = Math.max(14, deck.style.small - 4);
  const opts = {
    x: box.x, y: box.y, w: box.w, h: box.h, objectName: deck.name(sid, "chart"),
    showTitle: !!fig.title, title: fig.title, titleFontFace: "+mn-lt", titleFontSize: pt, titleColor: INK,
    showLegend: fig.chart === "pie", legendPos: "r", legendFontFace: "+mn-lt", legendFontSize: pt,
    showValue: fig.showValue !== false, dataLabelFontFace: "+mn-lt", dataLabelFontSize: pt, dataLabelColor: INK,
    catAxisLabelFontFace: "+mn-lt", catAxisLabelFontSize: pt, catAxisLabelColor: INK,
    valAxisLabelFontFace: "+mn-lt", valAxisLabelFontSize: pt, valAxisLabelColor: P.accent6,
    valGridLine: { color: "D1D5DB", size: 0.75 }, catGridLine: { style: "none" },
    chartColors: fig.chart === "pie" ? [P.accent1, P.accent2, P.accent4, P.accent5, P.accent3, P.accent6] : [P.accent1],
  };
  if (fig.chart === "bar" || !fig.chart) { opts.barDir = "col"; opts.dataLabelPosition = "outEnd"; opts.barGapWidthPct = 60; }
  if (fig.chart === "line") { opts.lineDataSymbol = "circle"; opts.lineDataSymbolSize = 9; opts.lineSize = 3; opts.dataLabelPosition = "t"; }
  if (fig.chart === "pie") { opts.dataLabelPosition = "bestFit"; opts.showPercent = !!fig.percent; opts.showValue = !fig.percent; }
  if (fig.max !== undefined) opts.valAxisMaxVal = fig.max;
  if (fig.valueTitle) { opts.showValAxisTitle = true; opts.valAxisTitle = fig.valueTitle; opts.valAxisTitleFontFace = "+mn-lt"; opts.valAxisTitleFontSize = pt; }
  slide.addChart(type, data, opts);
}

// ---------- 흐름도·연표 ----------
function flow(deck, slide, sid, fig, box) {
  const n = fig.items.length;
  const pt = fig.size || deck.style.small;
  const arrowW = 0.45;
  const bw = Math.min((box.w - (n - 1) * arrowW) / n, 3.2);
  const bh = Math.min(box.h - (fig.cycle ? 0.6 : 0), fig.boxHeight || 1.5);
  const total = n * bw + (n - 1) * arrowW;
  const x0 = box.x + (box.w - total) / 2;
  const y = box.y + (box.h - bh - (fig.cycle ? 0.5 : 0)) / 2;
  fig.items.forEach((t, i) => {
    const x = x0 + i * (bw + arrowW);
    const fpt = deck.checkFit(sid, String(t), bw - 0.25, bh - 0.15, [pt, pt - 2, pt - 4].filter((p) => p >= 16));
    slide.addText(String(t), textOpts({
      shape: deck.pres.shapes.ROUNDED_RECTANGLE, rectRadius: 0.12, x, y, w: bw, h: bh, fill: { color: i === fig.highlight ? TINT.accent : P.lt2 },
      line: { color: P.dk2, width: 1.5 }, fontSize: fpt, bold: true, color: INK, align: "center", valign: "middle", margin: [6, 6, 4, 4],
      objectName: deck.name(sid, "step"),
    }));
    if (i < n - 1) segment(deck, slide, sid, x + bw + 0.06, y + bh / 2, x + bw + arrowW - 0.06, y + bh / 2, { color: P.accent4, width: 2.5, endArrowType: "triangle" });
  });
  if (fig.cycle) {
    const yb = y + bh + 0.35;
    const xs = x0 + bw / 2;
    const xe = x0 + total - bw / 2;
    segment(deck, slide, sid, xe, y + bh, xe, yb, { color: P.accent4, width: 2.5 });
    segment(deck, slide, sid, xe, yb, xs, yb, { color: P.accent4, width: 2.5 });
    segment(deck, slide, sid, xs, yb, xs, y + bh + 0.02, { color: P.accent4, width: 2.5, endArrowType: "triangle" });
  }
}

function timeline(deck, slide, sid, fig, box) {
  const n = fig.events.length;
  const pt = fig.size || deck.style.small;
  const lh = (pt * 1.25) / 72;
  const y = box.y + box.h / 2;
  const x0 = box.x + 0.3;
  const x1 = box.x + box.w - 0.3;
  segment(deck, slide, sid, x0, y, x1, y, { color: P.dk2, width: 3, endArrowType: "triangle" });
  const slot = (x1 - x0) / n;
  fig.events.forEach((e, i) => {
    const cx = x0 + slot * (i + 0.5);
    slide.addShape(deck.pres.shapes.OVAL, { x: cx - 0.13, y: y - 0.13, w: 0.26, h: 0.26, fill: { color: P.accent1 }, line: { color: P.lt1, width: 1.5 }, objectName: deck.name(sid, "event") });
    const lines = (e.label.match(/\n/g) || []).length + 1;
    label(deck, slide, sid, e.label, cx - slot / 2 + 0.05, y - 0.25 - lh * (lines + 0.3), slot - 0.1, lh * (lines + 0.3), pt, { valign: "bottom" });
    if (e.sub) {
      const spt = Math.max(14, pt - 4);
      const slines = Math.max(1, Math.ceil(widthIn(e.sub, spt) / (slot - 0.1)));
      label(deck, slide, sid, e.sub, cx - slot / 2 + 0.05, y + 0.25, slot - 0.1, (spt * 1.3 * slines) / 72 + 0.05, spt, { bold: false, color: "muted", valign: "top" });
    }
  });
}

// ---------- 글자 타일·낱말 카드·큰 글자 ----------
function letters(deck, slide, sid, fig, box) {
  const n = fig.items.length;
  const perRow = fig.perRow || Math.min(n, 8);
  const rows = Math.ceil(n / perRow);
  const hasSub = !!fig.sub;
  const gap = 0.22;
  const subH = hasSub ? 0.5 : 0;
  const tile = Math.min((box.w - (perRow - 1) * gap) / perRow, (box.h - (rows - 1) * gap) / rows - subH, fig.tile || 1.5);
  const totalW = perRow * tile + (perRow - 1) * gap;
  const totalH = rows * (tile + subH) + (rows - 1) * gap;
  const hi = new Set(fig.highlight || []);
  fig.items.forEach((ch, i) => {
    const r = Math.floor(i / perRow);
    const c = i % perRow;
    const inRow = Math.min(perRow, n - r * perRow);
    const rowW = inRow * tile + (inRow - 1) * gap;
    const x = box.x + (box.w - totalW) / 2 + (totalW - rowW) / 2 + c * (tile + gap);
    const y = box.y + (box.h - totalH) / 2 + r * (tile + subH + gap);
    slide.addText(String(ch), textOpts({
      shape: deck.pres.shapes.ROUNDED_RECTANGLE, rectRadius: 0.14, x, y, w: tile, h: tile,
      fill: { color: hi.has(i) ? TINT.accent : P.lt1 }, line: { color: hi.has(i) ? P.accent1 : P.dk2, width: hi.has(i) ? 3 : 1.5 },
      fontSize: Math.round(tile * 72 * (String(ch).length > 2 ? 0.32 : 0.55)), bold: true, color: INK, align: "center", valign: "middle", margin: 0,
      objectName: deck.name(sid, "tile"),
    }));
    if (hasSub && fig.sub[i] !== undefined) label(deck, slide, sid, fig.sub[i], x - gap / 2, y + tile + 0.04, tile + gap, subH - 0.06, Math.max(14, deck.style.small - 4), { bold: false, color: "muted" });
  });
}

function words(deck, slide, sid, fig, box) {
  const n = fig.items.length;
  const perRow = fig.perRow || Math.min(n, 4);
  const rows = Math.ceil(n / perRow);
  const gap = 0.3;
  const cw = (box.w - (perRow - 1) * gap) / perRow;
  const ch = Math.min((box.h - (rows - 1) * gap) / rows, 1.9);
  const pt = deck.style.body;
  fig.items.forEach((it, i) => {
    const r = Math.floor(i / perRow);
    const c = i % perRow;
    const x = box.x + c * (cw + gap);
    const y = box.y + (box.h - (rows * ch + (rows - 1) * gap)) / 2 + r * (ch + gap);
    const wpt = deck.checkFit(sid, it.word, cw - 0.3, ch * (it.sub ? 0.55 : 0.9), [pt + 4, pt, pt - 4].filter((p) => p >= 16));
    if (it.sub) deck.checkFit(sid, it.sub, cw - 0.3, ch * 0.45, [deck.style.small - 2, 16]);
    const runs = [{ text: it.word, options: { fontSize: wpt, bold: true, breakLine: !!it.sub } }];
    if (it.sub) runs.push({ text: it.sub, options: { fontSize: deck.style.small - 2, color: P.accent6 } });
    slide.addText(runs, textOpts({
      shape: deck.pres.shapes.ROUNDED_RECTANGLE, rectRadius: 0.14, x, y, w: cw, h: ch, fill: { color: it.highlight ? TINT.accent : P.lt2 },
      line: { color: it.highlight ? P.accent1 : P.lt2, width: it.highlight ? 2.5 : 0 }, color: INK, align: "center", valign: "middle",
      margin: [6, 6, 4, 4], objectName: deck.name(sid, "word"),
    }));
  });
}

function text(deck, slide, sid, fig, box) {
  slide.addText(fig.text, textOpts({
    x: box.x, y: box.y, w: box.w, h: box.h, fontSize: fig.size || 54, bold: true, color: colorOf(fig.color),
    align: "center", valign: "middle", margin: 0, objectName: deck.name(sid, "bigtext"),
  }));
}


// ---------- 가르기·모으기 ----------
function bond(deck, slide, sid, fig, box) {
  const pt = fig.size || deck.style.body + 4;
  const d = Math.min((pt * 2.1) / 72, box.h / 2.4, box.w / 3.4);
  const fs = Math.round(d * 72 * 0.5);
  const gapY = Math.min(box.h - 2 * d, d * 1.1);
  const top = box.y + (box.h - (2 * d + gapY)) / 2;
  const cx = box.x + box.w / 2;
  const spread = Math.min(box.w / 2 - d / 2, d * 1.4);
  const merge = !!fig.merge;
  const yWhole = merge ? top + d + gapY : top;
  const yParts = merge ? top : top + d + gapY;
  const nodes = [[cx, yWhole, fig.whole, true], [cx - spread, yParts, fig.parts[0], false], [cx + spread, yParts, fig.parts[1], false]];
  // 선을 먼저 그려 원 아래에 깔리게 한다
  for (const [px] of [nodes[1], nodes[2]]) {
    const x1 = cx, y1 = merge ? yWhole : yWhole + d;
    const x2 = px, y2 = merge ? yParts + d : yParts;
    segment(deck, slide, sid, x1, y1, x2, y2, { color: INK, width: 2.5 });
  }
  const name = deck.name(sid, "figure");
  nodes.forEach(([x, y, v, whole], i) => {
    const blank = v === null || v === undefined;
    slide.addText(blank ? "" : String(v), textOpts({
      shape: deck.pres.shapes.OVAL, x: x - d / 2, y, w: d, h: d,
      fill: { color: blank ? P.lt1 : whole ? TINT.accent : P.lt2 }, line: { color: whole ? P.accent1 : P.dk2, width: 2.5, dashType: blank ? "dash" : "solid" },
      fontSize: fs, bold: true, color: INK, align: "center", valign: "middle", margin: 0, objectName: i === 0 ? name : deck.name(sid, "bondpart"),
    }));
  });
  const say = (v) => (v === null || v === undefined ? "빈칸" : v);
  deck.alt.set(name, fig.alt || `${say(fig.whole)}을(를) ${say(fig.parts[0])}와(과) ${say(fig.parts[1])}(으)로 ${merge ? "모으기" : "가르기"}`);
}

const FIGURES = { bond, bar: bars, bars, grid, pie, eq, eqx, frac, numberline, array, tenframe, blocks10, table, placevalue, clock, shapes, angle, chart, flow, timeline, letters, words, text };

// 그림 하나 또는 여러 개(가로로 나란히, 각각 caption 가능)를 상자에 그린다.
function drawFigures(deck, slide, sid, figs, box) {
  const list = Array.isArray(figs) ? figs : [figs];
  const gap = 0.35;
  const w = (box.w - gap * (list.length - 1)) / list.length;
  list.forEach((fig, i) => {
    const fn = FIGURES[fig.type];
    if (!fn) throw new Error(`${sid}: 알 수 없는 그림 종류 ${fig.type}`);
    const capH = fig.caption ? (deck.style.small * 1.35) / 72 + 0.08 : 0;
    const b = { x: box.x + i * (w + gap), y: box.y, w, h: box.h - capH };
    fn(deck, slide, sid, fig, b);
    if (fig.caption) {
      const lines = deck.checkFit(sid, fig.caption, w, capH, [deck.style.small]);
      label(deck, slide, sid, fig.caption, b.x, b.y + b.h + 0.08, w, capH - 0.08, lines, { bold: true });
    }
  });
}

// 그림이 가로로 넓은 종류인지(위아래 배치) 아닌지(좌우 배치)
const WIDE = new Set(["bar", "bars", "numberline", "timeline", "flow", "table", "chart", "letters", "words", "eq", "eqx", "blocks10", "tenframe"]);
function isWide(figs) {
  const list = Array.isArray(figs) ? figs : [figs];
  return list.length > 1 || list.some((f) => WIDE.has(f.type) || (f.type === "shapes" && f.items.length > 2) || (f.type === "grid" && f.cols >= f.rows * 2.5));
}

module.exports = { drawFigures, isWide, FIGURES, segment };
