// 수업 원본(JSON)에서 편집 가능한 PPTX 두 벌을 만든다.
//   수업용(부모·교사용): 모든 장 + 발표자 노트
//   학생용: teacher_only 장·블록과 노트를 실제로 제거한 파일
//
//   node tools/pptx/build_lesson.js <lesson.json> [--out <dir>]
//
// 그림(분수 막대, 격자, 분수 표기)은 모두 PowerPoint 도형과 텍스트 상자로 그려서
// 수량과 눈금이 정확하고 PowerPoint에서 바로 고칠 수 있게 한다.
const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");
const JSZip = require(require.resolve("jszip", { paths: [require.resolve("pptxgenjs")] }));

const FONT = "맑은 고딕";
const LANG = "ko-KR";
const W = 13.333;
const H = 7.5;

const THEME = {
  name: "Education Classroom",
  colors: {
    dk1: "1F2937", lt1: "FFFFFF", dk2: "264653", lt2: "EAF3F1",
    accent1: "E9762B", accent2: "2A9D8F", accent3: "C8434E", accent4: "3D5A80",
    accent5: "F2C14E", accent6: "4B5563", hlink: "3D5A80", folHlink: "7A4E8A",
  },
};
const P = THEME.colors;
// 테마 슬롯에 없는 옅은 색. 카드와 칩의 배경에만 쓴다.
const TINT = {
  tint: P.lt2, accent: "FDEBDD", good: "E3F4F1", bad: "FBE6E7", info: "E6ECF4",
  onDark: "32606F", support: "F4F7F6", onDarkMuted: "C9DCD8",
};

// 학년군별 글자 크기(pt). 화면 투사 기준 본문 24~30pt, 저학년은 더 크게.
const BAND = {
  E12: { title: 44, body: 32, small: 26 },
  E34: { title: 40, body: 30, small: 24 },
  E56: { title: 40, body: 28, small: 22 },
  M: { title: 36, body: 26, small: 20 },
  H: { title: 36, body: 24, small: 20 },
};

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

// ---------- 텍스트 공통 ----------

// margin: pt 단위. 배열이면 [왼쪽, 오른쪽, 아래, 위] 순서다(pptxgenjs).
function textOpts(extra) {
  return { fontFace: FONT, lang: LANG, isTextBox: true, ...extra };
}

function sizeOf(style, size, fallback) {
  if (typeof size === "number") return size;
  return style[size || fallback];
}

function colorOf(name) {
  const map = {
    ink: P.dk1, muted: P.accent6, onDark: P.lt1, onDarkMuted: TINT.onDarkMuted,
    accent: P.accent1, good: P.accent2, bad: P.accent3, info: P.accent4,
  };
  return map[name || "ink"] || name;
}

// ---------- 분수 표기 ----------

function fracMetrics(pt, n, d) {
  const lh = (pt * 1.18) / 72;
  const digits = Math.max(String(n ?? "0").length, String(d ?? "0").length);
  const w = Math.max((0.58 * pt * digits) / 72 + 0.18, (pt * 1.05) / 72 + 0.12);
  return { w, h: lh * 2 + 0.08, lh };
}

function opWidth(text, pt) {
  return ((0.62 * pt) / 72) * Math.max(1, [...text].length) + 0.28;
}

class Deck {
  constructor(lesson, variant) {
    this.lesson = lesson;
    this.variant = variant;
    this.style = BAND[lesson.band] || BAND.E56;
    this.alt = new Map(); // objectName → 대체 설명
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
              name: "title", type: "title", x: 0.8, y: 0.7, w: 7.2, h: 1.3,
              fontFace: FONT, fontSize: s.title + 8, bold: true, color: P.lt1, valign: "middle", align: "left", margin: 0,
            },
            text: "",
          },
        },
        {
          placeholder: {
            options: {
              name: "subtitle", type: "body", x: 0.8, y: 2.1, w: 7.2, h: 1.8,
              fontFace: FONT, fontSize: s.body + 2, color: TINT.onDarkMuted, valign: "top", margin: 0,
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

  // ---------- 블록 ----------

  text(slide, sid, b) {
    const s = this.style;
    slide.addText(b.text, textOpts({
      x: b.x, y: b.y, w: b.w, h: b.h, fontSize: sizeOf(s, b.size, "body"), bold: !!b.bold,
      color: colorOf(b.color), align: b.align || "left", valign: b.valign || "middle", margin: 0,
      objectName: this.name(sid, "text"),
    }));
  }

  card(slide, sid, b) {
    const s = this.style;
    const dark = b.tone === "onDark";
    const fill = { tint: TINT.tint, accent: TINT.accent, onDark: TINT.onDark }[b.tone || "tint"];
    const fg = dark ? P.lt1 : P.dk1;
    slide.addShape(this.pres.shapes.ROUNDED_RECTANGLE, {
      x: b.x, y: b.y, w: b.w, h: b.h, rectRadius: 0.12, fill: { color: fill }, line: { color: fill, width: 0 },
      objectName: this.name(sid, "card"),
    });
    const pad = 0.3;
    const runs = [];
    if (b.title) runs.push({ text: b.title, options: { bold: true, fontSize: s.body, breakLine: !!(b.text || b.items) } });
    if (b.text) runs.push({ text: b.text, options: { fontSize: b.title ? s.small : s.body } });
    (b.items || []).forEach((t, i, arr) => runs.push({ text: t, options: { fontSize: s.small, breakLine: i < arr.length - 1 } }));
    if (!runs.length) return;
    const onlyTitle = b.title && !b.text && !b.items;
    slide.addText(runs, textOpts({
      x: b.x + pad, y: b.y + (onlyTitle ? 0.2 : 0.12), w: b.w - 2 * pad, h: onlyTitle ? 0.7 : b.h - 0.24,
      color: fg, valign: onlyTitle ? "top" : "middle", margin: 0, paraSpaceAfter: 6, objectName: this.name(sid, "cardtext"),
    }));
  }

  chip(slide, sid, b) {
    const s = this.style;
    const tones = {
      label: [P.dk2, P.lt1], accent: [TINT.accent, P.dk1], info: [TINT.info, P.dk1],
      good: [TINT.good, P.dk1], bad: [TINT.bad, P.dk1],
      goodOnDark: [P.accent2, P.lt1], badOnDark: [P.accent3, P.lt1],
    };
    const [fill, fg] = tones[b.tone || "info"];
    const size = sizeOf(s, b.size, b.tone === "label" ? "body" : "small");
    slide.addText(b.text, textOpts({
      shape: this.pres.shapes.ROUNDED_RECTANGLE, rectRadius: Math.min(0.16, b.h / 2.5),
      x: b.x, y: b.y, w: b.w, h: b.h, fill: { color: fill }, line: { color: fill, width: 0 },
      fontSize: size, bold: true, color: fg, align: b.tone === "label" ? "center" : "left",
      valign: "middle", margin: b.tone === "label" ? 0 : [14, 14, 0, 0], objectName: this.name(sid, "chip"),
    }));
  }

  cell(slide, sid, x, y, w, h, shaded, kind) {
    slide.addShape(this.pres.shapes.RECTANGLE, {
      x, y, w, h, fill: { color: shaded ? P.accent1 : P.lt1 }, line: { color: P.dk1, width: 1.5 },
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
    const cw = b.w / b.cols;
    const ch = b.h / b.rows;
    for (let r = 0; r < b.rows; r++) {
      for (let c = 0; c < b.cols; c++) {
        this.cell(slide, sid, b.x + c * cw, b.y + r * ch, cw, ch, shaded.has(`${r},${c}`), "cell");
      }
    }
    this.outline(slide, sid, b, b.alt);
  }

  frac(slide, sid, b) {
    const pt = b.size || this.style.body;
    const m = fracMetrics(pt, b.n, b.d);
    const color = colorOf(b.color);
    const slot = (value, y) => {
      if (value === null || value === undefined) {
        const box = m.lh * 0.74;
        slide.addShape(this.pres.shapes.RECTANGLE, {
          x: b.x + (m.w - box) / 2, y: y + (m.lh - box) / 2, w: box, h: box,
          fill: { color: P.lt1 }, line: { color, width: 1.75 }, objectName: this.name(sid, "blank"),
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
    const w = opWidth(text, pt);
    slide.addText(text, textOpts({
      x, y, w, h, fontSize: pt, bold: true, color, align: "center", valign: "middle", margin: 0,
      objectName: this.name(sid, "op"),
    }));
    return w;
  }

  eq(slide, sid, b) {
    const pt = b.size || this.style.body;
    const color = colorOf(b.color);
    const h = fracMetrics(pt, 1, 1).h;
    let x = b.x;
    for (const item of b.items) {
      if (Array.isArray(item)) {
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
    const a = fracMetrics(pt, ...b.from);
    const c = fracMetrics(pt, ...b.to);
    const join = b.join || "=";
    const jw = opWidth(join, pt);
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
      slide.addText(String(i + 1), textOpts({
        shape: this.pres.shapes.OVAL, x: b.x, y: y + 0.04, w: d, h: d, fill: { color: P.dk2 }, line: { color: P.dk2, width: 0 },
        fontSize: s.small, bold: true, color: P.lt1, align: "center", valign: "middle", margin: 0,
        objectName: this.name(sid, "stepno"),
      }));
      slide.addText(t, textOpts({
        x: b.x + d + 0.25, y, w: b.w - d - 0.25, h: b.step - 0.12, fontSize: sizeOf(s, b.size, "body"),
        color: P.dk1, valign: "top", margin: 0, objectName: this.name(sid, "steptext"),
      }));
    });
  }

  // ---------- 장 ----------

  addSlide(spec, sectionTitle) {
    const master = { cover: "COVER", content: "CONTENT", closing: "CLOSING", support: "SUPPORT" }[spec.layout || "content"];
    const slide = this.pres.addSlide({ masterName: master, sectionTitle });
    slide.addText(spec.title, { placeholder: "title", fontFace: FONT, lang: LANG });
    if (spec.subtitle) slide.addText(spec.subtitle, { placeholder: "subtitle", fontFace: FONT, lang: LANG });
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
