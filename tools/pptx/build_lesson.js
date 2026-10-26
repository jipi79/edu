// 수업 원본(JSON)에서 편집 가능한 PPTX 두 벌을 만든다.
//   수업용(부모·교사용): 모든 장 + 발표자 노트
//   학생용: teacher_only 장·블록과 노트를 실제로 제거한 파일
//
//   node tools/pptx/build_lesson.js <lesson.json> [--out <dir>]
//
// 장은 두 가지 방식으로 쓸 수 있다.
//   kind   : 내용만 쓰면 kinds.js가 자동으로 배치한다(기본).
//   blocks : 좌표를 직접 주는 방식(특수한 그림이 필요할 때).
// 그림(분수 막대, 수직선, 시계 등)은 모두 PowerPoint 도형·표·차트로 그려 수량이 정확하고 고칠 수 있다.
// 글이 상자에 들어가지 않으면 빌드가 실패한다. 원고의 문장을 줄이거나 장을 나눈다.
const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");
const JSZip = require(require.resolve("jszip", { paths: [require.resolve("pptxgenjs")] }));
const { FONT, LANG, THEME, P, TINT, BAND, textOpts, sizeOf, colorOf } = require("./style");
const { heightOf, widthIn } = require("./fit");
const { KINDS } = require("./kinds");

function parseArgs(argv) {
  const args = { lesson: null, out: null };
  for (let i = 2; i < argv.length; i++) {
    if (argv[i] === "--out") args.out = argv[++i];
    else args.lesson = argv[i];
  }
  if (!args.lesson) throw new Error("사용법: node tools/pptx/build_lesson.js <lesson.json> [--out <dir>]");
  return args;
}

function defaultOutDir(lesson) {
  return path.join("dist", lesson.grade_label, lesson.strand_label, lesson.unit_folder);
}

const DEFAULT_LAYOUT = { cover: "cover", summary: "closing" };

class Deck {
  constructor(lesson, variant) {
    this.lesson = lesson;
    this.variant = variant;
    this.style = BAND[lesson.band] || BAND.E56;
    this.font = FONT;
    this.alt = new Map(); // objectName → 대체 설명
    this.problems = [];
    this.pres = new pptxgen();
    this.pres.layout = "LAYOUT_WIDE";
    this.pres.theme = { headFontFace: FONT, bodyFontFace: FONT };
    this.pres.title = `${lesson.grade_label} ${lesson.strand_label} ${lesson.title}`;
    this.pres.subject = lesson.id;
    this.pres.author = "education-ppt";
    this.defineLayouts();
  }

  defineLayouts() {
    const s = this.style;
    const L = this.lesson;
    const footer = `${L.grade_label} ${L.strand_label} · ${L.title}`;
    const titlePh = (color) => ({
      placeholder: {
        options: {
          name: "title", type: "title", x: 0.6, y: 0.35, w: 12.1, h: 0.95,
          fontFace: FONT, fontSize: s.title, bold: true, color, valign: "middle", align: "left", margin: 0,
        },
        text: "",
      },
    });
    const footerText = (color, text) => ({
      text: { text, options: { x: 0.6, y: 6.98, w: 9.5, h: 0.35, fontFace: FONT, fontSize: 12, color, margin: 0 } },
    });
    const slideNumber = (color) => ({ x: 11.9, y: 6.98, w: 0.8, h: 0.35, fontFace: FONT, fontSize: 12, color, align: "right" });

    this.pres.defineSlideMaster({
      title: "COVER",
      background: { color: P.dk2 },
      objects: [
        {
          placeholder: {
            options: {
              name: "title", type: "title", x: 0.8, y: 0.7, w: 7.3, h: 1.3,
              fontFace: FONT, fontSize: s.title + 6, bold: true, color: P.lt1, valign: "middle", align: "left", margin: 0,
            },
            text: "",
          },
        },
        {
          placeholder: {
            options: {
              name: "subtitle", type: "body", x: 0.8, y: 2.1, w: 7.3, h: 1.8,
              fontFace: FONT, fontSize: s.body, color: TINT.onDarkMuted, valign: "top", margin: 0,
            },
            text: "",
          },
        },
        footerText(TINT.onDarkMuted, `${L.grade_label} ${L.strand_label} · ${L.unit_folder} · ${L.sequence}차시`),
      ],
    });
    this.pres.defineSlideMaster({
      title: "CONTENT",
      background: { color: P.lt1 },
      objects: [titlePh(P.dk1), footerText(P.accent6, footer)],
      slideNumber: slideNumber(P.accent6),
    });
    this.pres.defineSlideMaster({
      title: "CLOSING",
      background: { color: P.dk2 },
      objects: [titlePh(P.lt1), footerText(TINT.onDarkMuted, footer)],
      slideNumber: slideNumber(TINT.onDarkMuted),
    });
    this.pres.defineSlideMaster({
      title: "SUPPORT",
      background: { color: TINT.support },
      objects: [titlePh(P.dk1), footerText(P.accent6, `보충 자료 · ${footer}`)],
      slideNumber: slideNumber(P.accent6),
    });
  }

  name(slideId, kind) {
    this.counter = (this.counter || 0) + 1;
    return `${slideId}-${kind}${this.counter}`;
  }

  // ---------- 글자 맞춤 ----------

  textH(text, w, pt) {
    return heightOf([{ text: String(text), pt }], w);
  }

  // 들어가는 가장 큰 크기를 고른다. 없으면 문제로 기록하고 가장 작은 크기를 쓴다.
  checkFit(sid, text, w, h, sizes) {
    for (const pt of sizes) if (this.textH(text, w, pt) <= h + 0.02) return pt;
    const pt = sizes[sizes.length - 1];
    this.problems.push(`${sid}: 글이 넘친다(${pt}pt, 필요 ${this.textH(text, w, pt).toFixed(2)}in > 공간 ${h.toFixed(2)}in): "${String(text).slice(0, 40)}…"`);
    return pt;
  }

  para(slide, sid, text, box, opts = {}) {
    const pt = this.checkFit(sid, text, box.w, box.h, opts.sizes || [this.style.body, this.style.small]);
    slide.addText(String(text), textOpts({
      x: box.x, y: box.y, w: box.w, h: box.h, fontSize: pt, bold: !!opts.bold, color: colorOf(opts.color),
      align: opts.align || "left", valign: opts.valign || "top", margin: 0, objectName: this.name(sid, "text"),
    }));
    return pt;
  }

  cardParas(c, pt) {
    const s = this.style;
    const paras = [];
    if (c.title) paras.push({ text: c.title, pt: pt.title });
    if (c.text) paras.push({ text: c.text, pt: c.title ? pt.text : pt.lead });
    (c.items || []).forEach((t) => paras.push({ text: t, pt: pt.item }));
    return paras;
  }

  cardSizes() {
    const s = this.style;
    return [
      { title: s.body, lead: s.body, text: s.small, item: s.small },
      { title: s.small, lead: s.small, text: Math.max(16, s.small - 2), item: Math.max(16, s.small - 2) },
    ];
  }

  // 카드의 자연스러운 높이(가장 큰 글자 크기 기준, 최소 0.95in)
  cardHeight(c, w) {
    const paras = this.cardParas(c, this.cardSizes()[0]);
    return Math.max(0.95, heightOf(paras, w - 0.6) + 0.36);
  }

  cardFit(slide, sid, box, c) {
    const tones = { tint: TINT.tint, accent: TINT.accent, onDark: TINT.onDark, info: TINT.info, good: TINT.good, bad: TINT.bad };
    const fill = tones[c.tone || "tint"];
    slide.addShape(this.pres.shapes.ROUNDED_RECTANGLE, {
      x: box.x, y: box.y, w: box.w, h: box.h, rectRadius: 0.12, fill: { color: fill }, line: { color: fill, width: 0 },
      objectName: this.name(sid, "card"),
    });
    const innerW = box.w - 0.6;
    const innerH = box.h - 0.3;
    const sizes = this.cardSizes();
    let chosen = sizes.find((pt) => heightOf(this.cardParas(c, pt), innerW) <= innerH + 0.02);
    if (!chosen) {
      chosen = sizes[sizes.length - 1];
      this.problems.push(`${sid}: 카드 글이 넘친다: "${String(c.title || c.text || (c.items || [])[0]).slice(0, 40)}…"`);
    }
    const paras = this.cardParas(c, chosen);
    const runs = paras.map((p, i) => ({
      text: p.text, options: { fontSize: p.pt, bold: !!c.title && i === 0, breakLine: i < paras.length - 1 },
    }));
    const onlyTitle = c.title && !c.text && !(c.items || []).length;
    slide.addText(runs, textOpts({
      x: box.x + 0.3, y: box.y + 0.15, w: innerW, h: innerH, color: c.tone === "onDark" ? P.lt1 : P.dk1,
      valign: onlyTitle ? "top" : "middle", margin: 0, paraSpaceAfter: 6, objectName: this.name(sid, "cardtext"),
    }));
  }

  passageBox(slide, sid, box, title, paras) {
    slide.addShape(this.pres.shapes.ROUNDED_RECTANGLE, {
      x: box.x, y: box.y, w: box.w, h: box.h, rectRadius: 0.1, fill: { color: P.lt1 }, line: { color: P.dk2, width: 1.5 },
      objectName: this.name(sid, "passagebox"),
    });
    const s = this.style;
    const innerW = box.w - 0.6;
    const innerH = box.h - 0.4;
    const sizes = [s.body, s.body - 2, s.small, Math.max(16, s.small - 2), Math.max(16, s.small - 4)];
    const build = (pt) => [...(title ? [{ text: title, pt: pt + 2 }] : []), ...paras.map((t) => (typeof t === "string" ? { text: t, pt } : { text: t.text, pt, align: t.align }))];
    let pt = sizes.find((p) => heightOf(build(p), innerW, 8) <= innerH + 0.02);
    if (!pt) {
      pt = sizes[sizes.length - 1];
      this.problems.push(`${sid}: 지문이 넘친다. 지문을 줄이거나 두 장으로 나눈다`);
    }
    const list = build(pt);
    slide.addText(list.map((p, i) => ({ text: p.text, options: { fontSize: p.pt, bold: !!title && i === 0, align: p.align || "left", breakLine: i < list.length - 1 } })), textOpts({
      x: box.x + 0.3, y: box.y + 0.2, w: innerW, h: innerH, color: P.dk1, valign: "top", margin: 0, paraSpaceAfter: 8, lineSpacingMultiple: 1.05,
      objectName: this.name(sid, "passage"),
    }));
  }

  stepNo(slide, sid, n, x, y, d) {
    slide.addText(String(n), textOpts({
      shape: this.pres.shapes.OVAL, x, y, w: d, h: d, fill: { color: P.dk2 }, line: { color: P.dk2, width: 0 },
      fontSize: Math.min(this.style.small, 24), bold: true, color: P.lt1, align: "center", valign: "middle", margin: 0,
      objectName: this.name(sid, "stepno"),
    }));
  }

  // ---------- 좌표 블록(blocks 방식) ----------

  text(slide, sid, b) {
    const s = this.style;
    slide.addText(b.text, textOpts({
      x: b.x, y: b.y, w: b.w, h: b.h, fontSize: sizeOf(s, b.size, "body"), bold: !!b.bold,
      color: colorOf(b.color), align: b.align || "left", valign: b.valign || "middle", margin: 0,
      objectName: this.name(sid, "text"),
    }));
  }

  card(slide, sid, b) {
    this.cardFit(slide, sid, b, b);
  }

  chip(slide, sid, b) {
    const s = this.style;
    const tones = {
      label: [P.dk2, P.lt1], accent: [TINT.accent, P.dk1], info: [TINT.info, P.dk1],
      good: [TINT.good, P.dk1], bad: [TINT.bad, P.dk1],
      goodOnDark: [P.accent2, P.lt1], badOnDark: [P.accent3, P.lt1],
    };
    const [fill, fg] = tones[b.tone || "info"];
    const sizes = b.tone === "label" ? [sizeOf(s, b.size, "body")] : [sizeOf(s, b.size, "small"), Math.max(16, s.small - 2)];
    const pad = b.tone === "label" ? 0 : 0.4;
    const pt = b.tone === "label" ? sizes[0] : this.checkFit(sid, b.text, b.w - pad, b.h - 0.1, sizes);
    slide.addText(b.text, textOpts({
      shape: this.pres.shapes.ROUNDED_RECTANGLE, rectRadius: Math.min(0.16, b.h / 2.5),
      x: b.x, y: b.y, w: b.w, h: b.h, fill: { color: fill }, line: { color: fill, width: 0 },
      fontSize: pt, bold: true, color: fg, align: b.tone === "label" ? "center" : "left",
      valign: "middle", margin: b.tone === "label" ? 0 : [14, 14, 0, 0], objectName: this.name(sid, "chip"),
    }));
  }

  // shaded: true(진한 색) · "light"(옅은 색, 두 겹 색칠의 첫째 겹) · false
  cell(slide, sid, x, y, w, h, shaded, kind) {
    slide.addShape(this.pres.shapes.RECTANGLE, {
      x, y, w, h, fill: { color: shaded === "light" ? TINT.accent : shaded ? P.accent1 : P.lt1 }, line: { color: P.dk1, width: 1.5 },
      objectName: this.name(sid, kind),
    });
  }

  outline(slide, sid, b, alt) {
    const name = this.name(sid, "figure");
    slide.addShape(this.pres.shapes.RECTANGLE, {
      x: b.x, y: b.y, w: b.w, h: b.h, fill: { color: P.lt1, transparency: 100 }, line: { color: P.dk1, width: 2.25 },
      objectName: name,
    });
    if (alt) this.alt.set(name, alt);
  }

  bar(slide, sid, b) {
    const widths = b.widths || Array.from({ length: b.parts }, () => 1 / b.parts);
    const shaded = new Set(b.shaded || []);
    let x = b.x;
    widths.forEach((f, i) => {
      const w = i === widths.length - 1 ? b.x + b.w - x : b.w * f;
      this.cell(slide, sid, x, b.y, w, b.h, shaded.has(i), "cell");
      x += w;
    });
    this.outline(slide, sid, b, b.alt);
  }

  grid(slide, sid, b) {
    const shaded = new Set((b.shaded || []).map(([r, c]) => `${r},${c}`));
    const light = new Set((b.light || []).map(([r, c]) => `${r},${c}`));
    const cw = b.w / b.cols;
    const ch = b.h / b.rows;
    for (let r = 0; r < b.rows; r++) {
      for (let c = 0; c < b.cols; c++) {
        const k = `${r},${c}`;
        this.cell(slide, sid, b.x + c * cw, b.y + r * ch, cw, ch, shaded.has(k) ? true : light.has(k) ? "light" : false, "cell");
      }
    }
    this.outline(slide, sid, b, b.alt);
  }

  fracMetrics(pt, n, d) {
    const lh = (pt * 1.18) / 72;
    const digits = Math.max(String(n ?? "0").length, String(d ?? "0").length);
    const w = Math.max((0.58 * pt * digits) / 72 + 0.18, (pt * 1.05) / 72 + 0.12);
    return { w, h: lh * 2 + 0.08, lh };
  }

  // 식의 한 항목 폭: [n, d] 분수, [w, n, d] 대분수, 글자
  eqItemWidth(it, pt) {
    if (!Array.isArray(it)) return this.opWidth(it, pt);
    if (it.length === 3) return this.wholeWidth(it[0], pt) + this.fracMetrics(pt, it[1], it[2]).w;
    return this.fracMetrics(pt, ...it).w;
  }

  wholeWidth(w, pt) {
    return w === null || w === undefined ? (pt * 1.18 * 0.74) / 72 + 0.08 : widthIn(String(w), pt) + 0.06;
  }

  // 분수가 들어 있으면 두 줄 높이, 아니면 한 줄 높이
  eqHeight(items, pt) {
    return items.some((it) => Array.isArray(it)) ? this.fracMetrics(pt, 1, 1).h : (pt * 1.3) / 72;
  }

  opWidth(text, pt) {
    return Math.max(widthIn(String(text), pt) + 0.28, 0.4);
  }

  frac(slide, sid, b) {
    const pt = b.size || this.style.body;
    const m = this.fracMetrics(pt, b.n, b.d);
    const color = colorOf(b.color);
    const slot = (value, y) => {
      if (value === null || value === undefined) {
        const box = m.lh * 0.74;
        slide.addShape(this.pres.shapes.RECTANGLE, {
          x: b.x + (m.w - box) / 2, y: y + (m.lh - box) / 2, w: box, h: box,
          fill: { color: P.lt1, transparency: color === P.lt1 ? 100 : 0 }, line: { color, width: 1.75 }, objectName: this.name(sid, "blank"),
        });
      } else {
        slide.addText(String(value), textOpts({
          x: b.x, y, w: m.w, h: m.lh, fontSize: pt, bold: true, color, align: "center", valign: "middle", margin: 0,
          objectName: this.name(sid, "num"),
        }));
      }
    };
    slot(b.n, b.y);
    slide.addShape(this.pres.shapes.LINE, {
      x: b.x + 0.04, y: b.y + m.lh + 0.04, w: m.w - 0.08, h: 0, line: { color, width: Math.max(1.5, pt / 16) },
      objectName: this.name(sid, "fracbar"),
    });
    slot(b.d, b.y + m.lh + 0.08);
    return m;
  }

  op(slide, sid, text, x, y, pt, h, color) {
    const w = this.opWidth(text, pt);
    if (text === "□") {
      const box = (pt * 1.18 * 0.74) / 72;
      // 어두운 바탕(밝은 글자)에서는 빈칸 속을 비워 테두리만 보이게 한다.
      slide.addShape(this.pres.shapes.RECTANGLE, {
        x: x + (w - box) / 2, y: y + (h - box) / 2, w: box, h: box, fill: { color: P.lt1, transparency: color === P.lt1 ? 100 : 0 }, line: { color, width: 1.75 },
        objectName: this.name(sid, "blank"),
      });
      return w;
    }
    slide.addText(String(text), textOpts({
      x, y, w, h, fontSize: pt, bold: true, color, align: "center", valign: "middle", margin: 0,
      objectName: this.name(sid, "op"),
    }));
    return w;
  }

  // items: [1,2] 분수, [null,6] 빈칸 있는 분수, "=" 같은 글자, "□" 빈칸
  eq(slide, sid, b) {
    const pt = b.size || this.style.body;
    const color = colorOf(b.color);
    const h = this.eqHeight(b.items, pt);
    let x = b.x;
    for (const item of b.items) {
      if (Array.isArray(item) && item.length === 3) {
        // 대분수: 자연수 부분을 분수 바로 왼쪽에 붙여 쓴다(빈칸이면 네모).
        const ww = this.wholeWidth(item[0], pt);
        if (item[0] === null || item[0] === undefined) {
          const box = (pt * 1.18 * 0.74) / 72;
          slide.addShape(this.pres.shapes.RECTANGLE, { x, y: b.y + (h - box) / 2, w: box, h: box, fill: { color: P.lt1, transparency: color === P.lt1 ? 100 : 0 }, line: { color, width: 1.75 }, objectName: this.name(sid, "blank") });
        } else {
          slide.addText(String(item[0]), textOpts({ x, y: b.y, w: ww, h, fontSize: pt, bold: true, color, align: "right", valign: "middle", margin: 0, objectName: this.name(sid, "num") }));
        }
        x += ww + this.frac(slide, sid, { x: x + ww, y: b.y, n: item[1], d: item[2], size: pt, color: b.color }).w + 0.12;
      } else if (Array.isArray(item)) {
        x += this.frac(slide, sid, { x, y: b.y, n: item[0], d: item[1], size: pt, color: b.color }).w + 0.12;
      } else {
        x += this.op(slide, sid, item, x, b.y, pt, h, color) + 0.12;
      }
    }
    return x - b.x;
  }

  // 분수 A → 분수 B 변환: 위아래 화살표에 같은 연산을 적는다.
  eqx(slide, sid, b) {
    const pt = b.size || this.style.body;
    const color = colorOf(b.color);
    const a = this.fracMetrics(pt, ...b.from);
    const c = this.fracMetrics(pt, ...b.to);
    const join = b.join || "=";
    const jw = this.opWidth(join, pt);
    const xa = b.x;
    const xj = xa + a.w + 0.12;
    const xb = xj + jw + 0.12;
    this.frac(slide, sid, { x: xa, y: b.y, n: b.from[0], d: b.from[1], size: pt, color: b.color });
    this.op(slide, sid, join, xj, b.y, pt, a.h, color);
    this.frac(slide, sid, { x: xb, y: b.y, n: b.to[0], d: b.to[1], size: pt, color: b.color });
    const ca = xa + a.w / 2;
    const cb = xb + c.w / 2;
    const lpt = this.style.small;
    const lh = (lpt * 1.25) / 72;
    const arrow = (y) => slide.addShape(this.pres.shapes.LINE, {
      x: ca, y, w: cb - ca, h: 0, line: { color: P.accent4, width: 2, endArrowType: "triangle" },
      objectName: this.name(sid, "arrow"),
    });
    const label = (y) => slide.addText(b.op, textOpts({
      x: ca, y, w: cb - ca, h: lh, fontSize: lpt, bold: true, color: P.accent4, align: "center", valign: "middle", margin: 0,
      objectName: this.name(sid, "oplabel"),
    }));
    const top = b.y - 0.16;
    const bottom = b.y + a.h + 0.16;
    arrow(top);
    label(top - lh - 0.02);
    arrow(bottom);
    label(bottom + 0.02);
  }

  vline(slide, sid, b) {
    slide.addShape(this.pres.shapes.LINE, {
      x: b.x, y: b.y1, w: 0, h: b.y2 - b.y1, line: { color: P.accent4, width: 2, dashType: "dash" },
      objectName: this.name(sid, "guide"),
    });
  }

  steps(slide, sid, b) {
    const s = this.style;
    const d = 0.62;
    b.items.forEach((t, i) => {
      const y = b.y + i * b.step;
      this.stepNo(slide, sid, i + 1, b.x, y + 0.04, d);
      slide.addText(t, textOpts({
        x: b.x + d + 0.25, y, w: b.w - d - 0.25, h: b.step - 0.12, fontSize: sizeOf(s, b.size, "body"),
        color: P.dk1, valign: "top", margin: 0, objectName: this.name(sid, "steptext"),
      }));
    });
  }

  // ---------- 장 ----------

  addSlide(spec, sectionTitle) {
    const layout = spec.layout || DEFAULT_LAYOUT[spec.kind] || "content";
    const master = { cover: "COVER", content: "CONTENT", closing: "CLOSING", support: "SUPPORT" }[layout];
    const slide = this.pres.addSlide({ masterName: master, sectionTitle });
    // 제목은 한 줄. 굵은 큰 글자는 어림보다 넓게 그려지므로 여유(×1.1)를 두고, 넘치면 글자를 줄인다.
    const base = layout === "cover" ? this.style.title + 6 : this.style.title;
    const room = layout === "cover" ? 7.3 : 12.1;
    let tpt = base;
    while (tpt > base - 12 && widthIn(spec.title, tpt) * 1.1 > room) tpt -= 2;
    if (widthIn(spec.title, tpt) * 1.1 > room) this.problems.push(`${spec.id}: 제목이 한 줄에 들어가지 않는다: "${spec.title}"`);
    // 자리 표시자의 글꼴 크기가 상자 옵션보다 우선하므로, 줄인 크기는 글자 단위(run)에 준다.
    slide.addText([{ text: spec.title, options: tpt < base ? { fontSize: tpt } : {} }], { placeholder: "title", fontFace: FONT, lang: LANG });
    const subtitle = spec.subtitle || spec.question;
    if (layout === "cover" && subtitle) {
      this.checkFit(spec.id, subtitle, 7.3, 1.8, [this.style.body]);
      slide.addText(subtitle, { placeholder: "subtitle", fontFace: FONT, lang: LANG });
    }
    if (spec.kind && spec.kind !== "blocks") {
      if (!KINDS[spec.kind]) throw new Error(`${spec.id}: 알 수 없는 장 종류 ${spec.kind}`);
      KINDS[spec.kind](this, slide, this.variant === "student" ? stripTeacher(spec) : spec);
    }
    for (const b of spec.blocks || []) {
      if (b.teacher_only && this.variant === "student") continue;
      if (!this[b.type]) throw new Error(`${spec.id}: 알 수 없는 블록 종류 ${b.type}`);
      this[b.type](slide, spec.id, b);
    }
    if (this.variant === "teacher" && spec.notes) slide.addNotes(formatNotes(spec));
  }

  build() {
    const slides = this.lesson.slides.filter((s) => !(s.teacher_only && this.variant === "student"));
    let section = null;
    for (const spec of slides) {
      if (spec.section !== section) {
        section = spec.section;
        this.pres.addSection({ title: section });
      }
      this.addSlide(spec, section);
    }
    return slides.length;
  }
}

// 학생용에서는 장 안의 교사 전용 항목(예: 정답이 적힌 카드)을 뺀다
function stripTeacher(spec) {
  const out = { ...spec };
  for (const k of ["key", "hint", "question"]) if (out[k] && out[k].teacher_only) delete out[k];
  return out;
}

function formatNotes(spec) {
  const n = spec.notes;
  const lines = [`[${spec.id} · ${spec.purpose}]`];
  if (n.목적) lines.push(`목적: ${n.목적}`);
  if (n.시간) lines.push(`시간: ${n.시간}`);
  const list = (label, items) => {
    if (!items || !items.length) return;
    lines.push("", label);
    items.forEach((t) => lines.push(`- ${t}`));
  };
  list("이렇게 말해 보세요", n.말하기);
  list("예상 답", n.예상답);
  list("정답", n.정답);
  list("막히면", n.막히면);
  list("주의", n.주의);
  return lines.join("\n");
}

function escapeXml(s) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

// pptxgenjs가 쓰지 못하는 두 가지를 저장 후에 넣는다: 테마 색, 도형의 대체 설명.
async function finalize(file, alt) {
  const zip = await JSZip.loadAsync(fs.readFileSync(file));
  const themePart = "ppt/theme/theme1.xml";
  const slots = ["dk1", "lt1", "dk2", "lt2", "accent1", "accent2", "accent3", "accent4", "accent5", "accent6", "hlink", "folHlink"];
  const scheme = `<a:clrScheme name="${THEME.name}">` + slots.map((k) => `<a:${k}><a:srgbClr val="${THEME.colors[k]}"/></a:${k}>`).join("") + "</a:clrScheme>";
  const theme = (await zip.file(themePart).async("string"))
    .replace(/<a:clrScheme\b[\s\S]*?<\/a:clrScheme>/, () => scheme)
    .replace(/(<a:(?:theme|fontScheme)\b[^>]*?\bname=")[^"]*"/g, (_, head) => `${head}${THEME.name}"`);
  zip.file(themePart, theme);
  for (const part of Object.keys(zip.files).filter((f) => /^ppt\/slides\/slide\d+\.xml$/.test(f))) {
    let xml = await zip.file(part).async("string");
    // 한글 낱말이 중간에서 끊기지 않게(어절 단위 줄바꿈) 한다. 글 맞춤 계산도 어절 단위다.
    xml = xml.replace(/<a:pPr(?![^>]*eaLnBrk)/g, '<a:pPr eaLnBrk="0"').replace(/<a:p>(?!<a:pPr)/g, '<a:p><a:pPr eaLnBrk="0"/>');
    // 한글 없이 영어로만 된 글은 영어로 표시해 맞춤법 검사·읽어 주기가 영어로 동작하게 한다.
    xml = xml.replace(/<a:rPr lang="ko-KR"([^>]*)>((?:(?!<\/a:rPr>)[\s\S])*)<\/a:rPr><a:t>([^<]*)<\/a:t>/g, (m, attrs, inner, t) =>
      /[A-Za-z]/.test(t) && !/[\u1100-\u11ff\u3130-\u318f\uac00-\ud7af]/.test(t)
        ? `<a:rPr lang="en-US"${attrs.replace(/altLang="[^"]*"/, 'altLang="ko-KR"')}>${inner}</a:rPr><a:t>${t}</a:t>`
        : m);
    for (const [name, text] of alt) {
      xml = xml.replace(`name="${name}">`, `name="${name}" descr="${escapeXml(text)}">`);
    }
    zip.file(part, xml);
  }
  fs.writeFileSync(file, await zip.generateAsync({ type: "nodebuffer", compression: "DEFLATE" }));
}

async function main() {
  const args = parseArgs(process.argv);
  const lesson = JSON.parse(fs.readFileSync(args.lesson, "utf-8"));
  const outDir = args.out || defaultOutDir(lesson);
  fs.mkdirSync(outDir, { recursive: true });
  for (const [variant, suffix] of [["teacher", ""], ["student", "_학생용"]]) {
    const deck = new Deck(lesson, variant);
    const count = deck.build();
    if (deck.problems.length) {
      throw new Error(`배치 문제 ${deck.problems.length}건 (${lesson.id}):\n  ` + [...new Set(deck.problems)].join("\n  "));
    }
    const file = path.join(outDir, `${lesson.file_stem}${suffix}.pptx`);
    await deck.pres.writeFile({ fileName: file });
    await finalize(file, deck.alt);
    console.log(`${file} (${count}장)`);
  }
}

main().catch((err) => {
  console.error(err.message || err);
  process.exit(1);
});
