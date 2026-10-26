// 수업 원본(JSON)에서 인쇄용 PDF 두 개를 만든다.
//   활동지: 아이가 쓰는 종이(정답 없음)
//   부모용 진행 안내: 장별 발문·예상 답·정답·막힐 때 대응, 활동지 정답, 기록표
//
//   node tools/handouts/build_handouts.js <lesson.json> [--out <dir>] [--thumbs <dir>]
//
// --thumbs 에 수업용 PPTX를 렌더링한 slide-01.jpg … 가 있으면 안내서에 장 미리보기를 넣는다.
// 집에서는 아이와 같은 화면을 보므로, 정답이 든 발표자 노트 대신 이 안내서를 부모가 따로 본다.
const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");
const GEO = require("../pptx/geo");

function parseArgs(argv) {
  const args = { lesson: null, out: null, thumbs: null };
  for (let i = 2; i < argv.length; i++) {
    if (argv[i] === "--out") args.out = argv[++i];
    else if (argv[i] === "--thumbs") args.thumbs = argv[++i];
    else args.lesson = argv[i];
  }
  if (!args.lesson) throw new Error("사용법: node tools/handouts/build_handouts.js <lesson.json> [--out <dir>] [--thumbs <dir>]");
  return args;
}

const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

const CSS = `
  @page { size: A4; margin: 16mm 15mm 16mm 15mm; }
  * { box-sizing: border-box; }
  body { font-family: "Malgun Gothic", "맑은 고딕", "NanumGothic", sans-serif; color: #1F2937; font-size: 11pt; line-height: 1.55; margin: 0; word-break: keep-all; }
  .jamo { font-size: 1.45em; }
  h1 { font-size: 20pt; margin: 0 0 2mm; }
  h2 { font-size: 13.5pt; margin: 7mm 0 2.5mm; color: #264653; }
  .sub { color: #4B5563; font-size: 10pt; margin-bottom: 5mm; }
  .frac { display: inline-flex; flex-direction: column; align-items: center; vertical-align: middle; margin: 0 1.2mm; font-weight: 700; }
  .frac > span { display: block; min-width: 7mm; text-align: center; line-height: 1.15; }
  .frac > span + span { border-top: 2px solid currentColor; }
  .blank { display: inline-block; width: 7mm; height: 7mm; border: 1.6px solid #1F2937; margin: 0.8mm auto; }
  .op { font-weight: 700; margin: 0 1.5mm; vertical-align: middle; }
  .eq { font-size: 17pt; margin: 2mm 0; }
  .item { break-inside: avoid; margin-bottom: 6mm; }
  .no { display: inline-flex; width: 7.5mm; height: 7.5mm; border-radius: 50%; background: #264653; color: #fff; font-weight: 700; align-items: center; justify-content: center; margin-right: 2mm; font-size: 10.5pt; }
  .prompt { font-size: 12pt; font-weight: 700; white-space: pre-wrap; }
  .figrow { display: flex; align-items: center; gap: 3mm; margin: 2mm 0 2mm 9.5mm; }
  .line { border-bottom: 1px solid #9CA3AF; height: 9mm; margin-left: 9.5mm; }
  .linelabel { margin: 3mm 0 0 9.5mm; white-space: pre-wrap; }
  .head { display: flex; justify-content: space-between; align-items: flex-end; border-bottom: 2px solid #264653; padding-bottom: 2mm; margin-bottom: 5mm; }
  .name { font-size: 11pt; }
  .box { background: #EAF3F1; border-radius: 3mm; padding: 3.5mm 4.5mm; margin: 2mm 0; break-inside: avoid; }
  .warn { background: #FDEBDD; }
  table { border-collapse: collapse; width: 100%; font-size: 10pt; }
  th, td { border: 1px solid #CBD5E1; padding: 1.6mm 2.2mm; text-align: left; vertical-align: top; }
  th { background: #EAF3F1; }
  .slide { display: flex; gap: 4mm; break-inside: avoid; border-top: 1px solid #CBD5E1; padding: 3mm 0; }
  .slide img { width: 62mm; border: 1px solid #CBD5E1; flex: none; align-self: flex-start; }
  .slide .body { flex: 1; font-size: 10pt; }
  .slide .body b.k { color: #264653; }
  .slide ul { margin: 0.5mm 0 1.5mm; padding-left: 5mm; }
  .tag { display: inline-block; background: #264653; color: #fff; border-radius: 2mm; padding: 0 2mm; font-size: 9pt; margin-right: 1.5mm; }
  .tag.t { background: #C8434E; }
`;

function fracHtml(item) {
  const slot = (v) => (v === null || v === undefined ? '<span><i class="blank"></i></span>' : `<span>${esc(v)}</span>`);
  return `<span class="frac">${slot(item[0])}${slot(item[1])}</span>`;
}

function eqHtml(items) {
  return `<div class="eq">${items.map((it) => (Array.isArray(it) ? fracHtml(it) : `<span class="op">${esc(it)}</span>`)).join("")}</div>`;
}

function barSvg(bar, widthMm = 120, heightMm = 12) {
  const parts = bar.parts;
  const shaded = new Set(bar.shaded || []);
  const cw = widthMm / parts;
  let cells = "";
  for (let i = 0; i < parts; i++) {
    cells += `<rect x="${i * cw}" y="0" width="${cw}" height="${heightMm}" fill="${shaded.has(i) ? "#E9762B" : "#FFFFFF"}" stroke="#1F2937" stroke-width="0.4"/>`;
  }
  return `<svg width="${widthMm}mm" height="${heightMm}mm" viewBox="-0.4 -0.4 ${widthMm + 0.8} ${heightMm + 0.8}" role="img" aria-label="${parts}칸 띠">${cells}<rect x="0" y="0" width="${widthMm}" height="${heightMm}" fill="none" stroke="#1F2937" stroke-width="0.7"/></svg>`;
}


function clockSvg(c, d = 46) {
  const r = d / 2;
  let g = `<circle cx="${r}" cy="${r}" r="${r - 0.6}" fill="#fff" stroke="#1F2937" stroke-width="0.9"/>`;
  for (let k = 0; k < 60; k++) {
    const a = (k * 6 * Math.PI) / 180;
    const l = k % 5 === 0 ? 2.6 : 1.2;
    g += `<line x1="${r + Math.sin(a) * (r - 1)}" y1="${r - Math.cos(a) * (r - 1)}" x2="${r + Math.sin(a) * (r - 1 - l)}" y2="${r - Math.cos(a) * (r - 1 - l)}" stroke="#1F2937" stroke-width="${k % 5 === 0 ? 0.6 : 0.25}"/>`;
  }
  for (let k = 1; k <= 12; k++) {
    const a = (k * 30 * Math.PI) / 180;
    g += `<text x="${r + Math.sin(a) * r * 0.72}" y="${r - Math.cos(a) * r * 0.72 + 1.6}" font-size="4.6" text-anchor="middle" font-weight="700">${k}</text>`;
  }
  if (c.h !== undefined) {
    const m = c.m || 0;
    const ha = (((c.h % 12) + m / 60) * 30 * Math.PI) / 180;
    const ma = (m * 6 * Math.PI) / 180;
    g += `<line x1="${r}" y1="${r}" x2="${r + Math.sin(ha) * r * 0.5}" y2="${r - Math.cos(ha) * r * 0.5}" stroke="#C8434E" stroke-width="1.8" stroke-linecap="round"/>`;
    g += `<line x1="${r}" y1="${r}" x2="${r + Math.sin(ma) * r * 0.78}" y2="${r - Math.cos(ma) * r * 0.78}" stroke="#1F2937" stroke-width="1.1" stroke-linecap="round"/>`;
  }
  g += `<circle cx="${r}" cy="${r}" r="1" fill="#1F2937"/>`;
  return `<svg width="${d}mm" height="${d}mm" viewBox="0 0 ${d} ${d}">${g}</svg>`;
}

function numberlineSvg(n, w = 160) {
  const step = n.step || 1;
  const count = Math.round((n.max - n.min) / step);
  const x0 = 6, x1 = w - 6, y = 8;
  let g = `<line x1="2" y1="${y}" x2="${w - 2}" y2="${y}" stroke="#1F2937" stroke-width="0.6"/>`;
  for (let i = 0; i <= count; i++) {
    const v = +(n.min + i * step).toFixed(6);
    const x = x0 + ((x1 - x0) * i) / count;
    g += `<line x1="${x}" y1="${y - 2}" x2="${x}" y2="${y + 2}" stroke="#1F2937" stroke-width="0.5"/>`;
    const show = !n.labels || n.labels === "all" || (n.labels === "ends" && (i === 0 || i === count)) || (Array.isArray(n.labels) && n.labels.includes(v));
    if (show) g += `<text x="${x}" y="${y + 7}" font-size="4" text-anchor="middle">${v}</text>`;
  }
  return `<svg width="${w}mm" height="16mm" viewBox="0 0 ${w} 16">${g}</svg>`;
}

function gridSvg(gr, cell = 10) {
  let shaded = gr.shaded || [];
  if (typeof shaded === "number") shaded = Array.from({ length: shaded }, (_, k) => [Math.floor(k / gr.cols), k % gr.cols]);
  const set = new Set(shaded.map(([r, c]) => `${r},${c}`));
  let g = "";
  for (let r = 0; r < gr.rows; r++) for (let c = 0; c < gr.cols; c++) {
    g += `<rect x="${c * cell}" y="${r * cell}" width="${cell}" height="${cell}" fill="${set.has(`${r},${c}`) ? "#E9762B" : "#fff"}" stroke="#1F2937" stroke-width="0.4"/>`;
  }
  return `<svg width="${gr.cols * cell}mm" height="${gr.rows * cell}mm" viewBox="-0.4 -0.4 ${gr.cols * cell + 0.8} ${gr.rows * cell + 0.8}">${g}</svg>`;
}

function arraySvg(a, cell = 8) {
  let g = "";
  const count = a.count ?? a.rows * a.cols;
  for (let r = 0; r < a.rows; r++) for (let c = 0; c < a.cols; c++) {
    if (r * a.cols + c < count) g += `<circle cx="${c * cell + cell / 2}" cy="${r * cell + cell / 2}" r="${cell * 0.3}" fill="#E9762B" stroke="#1F2937" stroke-width="0.3"/>`;
  }
  return `<svg width="${a.cols * cell}mm" height="${a.rows * cell}mm" viewBox="0 0 ${a.cols * cell} ${a.rows * cell}">${g}</svg>`;
}

function pieSvg(pc, d = 36) {
  const r = d / 2 - 0.6;
  const set = Array.isArray(pc.shaded) ? new Set(pc.shaded) : new Set(Array.from({ length: pc.shaded || 0 }, (_, i) => i));
  let g = "";
  for (let i = 0; i < pc.parts; i++) {
    const a0 = (i / pc.parts) * 2 * Math.PI;
    const a1 = ((i + 1) / pc.parts) * 2 * Math.PI;
    const p = (a) => `${d / 2 + Math.sin(a) * r},${d / 2 - Math.cos(a) * r}`;
    g += `<path d="M${d / 2},${d / 2} L${p(a0)} A${r},${r} 0 ${a1 - a0 > Math.PI ? 1 : 0} 1 ${p(a1)} Z" fill="${set.has(i) ? "#E9762B" : "#fff"}" stroke="#1F2937" stroke-width="0.4"/>`;
  }
  return `<svg width="${d}mm" height="${d}mm" viewBox="0 0 ${d} ${d}">${g}</svg>`;
}

// 낱자(ㄱ, ㅏ)는 글꼴에서 작게 그려지므로 키운다
function jamo(html) {
  return html.replace(/[\u3131-\u318E]+/g, (m) => `<span class="jamo">${m}</span>`);
}

function tableHtml(t) {
  const head = t.headers ? `<tr>${t.headers.map((h) => `<th>${jamo(esc(h))}</th>`).join("")}</tr>` : "";
  const rows = t.rows.map((r) => `<tr>${r.map((c) => `<td style="height:9mm; min-width:18mm; text-align:center">${jamo(esc(c))}</td>`).join("")}</tr>`).join("");
  return `<table style="width:auto; min-width:90mm; font-size:${t.size || 11.5}pt">${head}${rows}</table>`;
}


function tenframeSvg(t, cell = 9) {
  const frames = t.frames || (t.count > 10 ? 2 : 1);
  let g = "";
  let left = t.count || 0;
  for (let f = 0; f < frames; f++) {
    const ox = f * (cell * 5 + 6);
    for (let k = 0; k < 10; k++) {
      const x = ox + (k % 5) * cell, y = Math.floor(k / 5) * cell;
      g += `<rect x="${x}" y="${y}" width="${cell}" height="${cell}" fill="#fff" stroke="#1F2937" stroke-width="0.4"/>`;
      if (left > 0) { g += `<circle cx="${x + cell / 2}" cy="${y + cell / 2}" r="${cell * 0.32}" fill="#E9762B" stroke="#1F2937" stroke-width="0.3"/>`; left -= 1; }
    }
  }
  const w = frames * cell * 5 + (frames - 1) * 6;
  return `<svg width="${w}mm" height="${cell * 2}mm" viewBox="-0.4 -0.4 ${w + 0.8} ${cell * 2 + 0.8}">${g}</svg>`;
}

function bondSvg(b, d = 13) {
  const W = d * 4.2, H = d * 2.8;
  const merge = !!b.merge;
  const yw = merge ? H - d / 2 - 0.5 : d / 2 + 0.5, yp = merge ? d / 2 + 0.5 : H - d / 2 - 0.5;
  const pts = [[W / 2, yw, b.whole], [d * 0.7, yp, b.parts[0]], [W - d * 0.7, yp, b.parts[1]]];
  let g = "";
  for (const [x, y] of pts.slice(1)) g += `<line x1="${W / 2}" y1="${yw}" x2="${x}" y2="${y}" stroke="#1F2937" stroke-width="0.6"/>`;
  for (const [x, y, v] of pts) {
    const blank = v === null || v === undefined;
    g += `<circle cx="${x}" cy="${y}" r="${d / 2}" fill="#fff" stroke="#264653" stroke-width="0.6" ${blank ? 'stroke-dasharray="1.5 1"' : ""}/>`;
    if (!blank) g += `<text x="${x}" y="${y + 2.2}" font-size="6.5" font-weight="700" text-anchor="middle">${v}</text>`;
  }
  return `<svg width="${W}mm" height="${H}mm" viewBox="0 0 ${W} ${H}">${g}</svg>`;
}

function figureHtml(it) {
  const parts = [];
  if (it.clock) parts.push(...[].concat(it.clock).map((c) => clockSvg(c)));
  if (it.numberline) parts.push(numberlineSvg(it.numberline));
  if (it.grid) parts.push(...[].concat(it.grid).map((g) => gridSvg(g)));
  if (it.array) parts.push(...[].concat(it.array).map((a) => arraySvg(a)));
  if (it.pie) parts.push(...[].concat(it.pie).map((pc) => pieSvg(pc)));
  if (it.table) parts.push(tableHtml(it.table));
  if (it.tenframe) parts.push(...[].concat(it.tenframe).map((t) => tenframeSvg(t)));
  if (it.bond) parts.push(...[].concat(it.bond).map((b) => bondSvg(b)));
  for (const type of ["geo", "ruler", "protractor"]) if (it[type]) parts.push(...[].concat(it[type]).map((g) => GEO.toSvg({ ...g, type })));
  return parts.length ? `<div class="figrow" style="flex-wrap:wrap; gap:8mm">${parts.join("")}</div>` : "";
}

function worksheetHtml(L) {
  const ws = L.worksheet;
  const items = ws.items.map((it) => {
    let h = it.new_page ? `<div style="break-before: page"></div>${it.heading ? `<h2 style="margin-top:0">${esc(it.heading)}</h2>` : ""}` : "";
    h += `<div class="item"><div><span class="no">${it.no}</span><span class="prompt">${esc(it.prompt)}</span></div>`;
    for (const bar of it.bars || []) {
      h += `<div class="figrow">${bar.label ? `<span style="font-size:13pt">${fracHtml(bar.label)}</span>` : ""}${barSvg(bar)}</div>`;
    }
    if (it.read) h += `<div class="box" style="margin-left:9.5mm; font-size:13pt">${esc(it.read).replace(/\n/g, "<br>")}</div>`;
    h += figureHtml(it);
    if (it.choices) h += `<div style="margin:1.5mm 0 0 9.5mm; display:flex; flex-wrap:wrap; gap:2mm 9mm; font-size:12pt">${it.choices.map((c) => `<span>☐ ${esc(c)}</span>`).join("")}</div>`;
    if (it.big) h += `<div style="margin:2mm 0 0 9.5mm; font-size:${it.big_size || 26}pt; letter-spacing:4mm; font-weight:700; white-space:pre-wrap">${jamo(esc(it.big))}</div>`;
    if (it.eq) h += `<div style="margin-left:9.5mm">${eqHtml(it.eq)}</div>`;
    if (it.eqs) h += `<div style="margin-left:9.5mm; display:flex; gap:16mm">${it.eqs.map(eqHtml).join("")}</div>`;
    if (it.box) h += `<div style="margin:2mm 0 0 9.5mm; height:${it.box}mm; border:1.2px dashed #9CA3AF; border-radius:2mm"></div>`;
    if (it.line_label) h += `<div class="linelabel">${esc(it.line_label)}</div>`;
    for (let i = 0; i < (it.lines || 0); i++) h += '<div class="line"></div>';
    return h + "</div>";
  });
  return `<!doctype html><html lang="ko"><head><meta charset="utf-8"><style>${CSS}</style></head><body>
    <div class="head"><div><h1>${esc(ws.title)}</h1><div class="sub" style="margin:0">${esc(L.grade_label)} ${esc(L.strand_label)} · ${esc(L.unit_folder)} ${L.sequence}차시</div></div>
    <div class="name">이름 ______________ &nbsp; 날짜 ____________</div></div>
    ${items.join("")}
  </body></html>`;
}

function listHtml(label, items, cls = "") {
  if (!items || !items.length) return "";
  return `<b class="k ${cls}">${label}</b><ul>${items.map((t) => `<li>${esc(t)}</li>`).join("")}</ul>`;
}


// 선수 확인 장과 보충 장이 있으면 어디로 가야 하는지 알려 준다
function supportLine(L) {
  const prior = L.slides.find((s) => s.role === "prior");
  const support = L.slides.find((s) => s.role === "support");
  const pre = L.prerequisites.filter((p) => p.lesson).map((p) => esc(p.text));
  let t = "";
  if (prior && support) t += `${esc(prior.id)}에서 흔들리면 ${esc(support.id)}(보충)를 먼저 합니다. `;
  if (pre.length) t += `보충으로도 어려우면 앞 차시(${pre.join(", ")})부터 다시 다지는 것이 좋습니다.`;
  return t ? `<div>${t}</div>` : "";
}

function guideHtml(L, thumbs) {
  const slides = L.slides.map((s, i) => {
    const n = s.notes;
    const img = thumbs[i] ? `<img src="${thumbs[i]}" alt="${esc(s.id)} 미리보기">` : "";
    const tags = `<span class="tag">${esc(s.id)}</span>${s.teacher_only ? '<span class="tag t">학생용에서 빠짐</span>' : ""}`;
    return `<div class="slide">${img}<div class="body">
      <div>${tags}<b>${esc(s.title)}</b> · ${esc(s.purpose)} · ${esc(n.시간 || "")}</div>
      <div>${esc(n.목적 || "")}</div>
      ${listHtml("이렇게 말해 보세요", n.말하기)}${listHtml("예상 답", n.예상답)}${listHtml("정답", n.정답)}
      ${listHtml("막히면", n.막히면)}${listHtml("주의", n.주의)}
    </div></div>`;
  });
  const rows = L.slides.map((s) => `<tr><td>${esc(s.id)}</td><td>${esc(s.purpose)}</td><td>${esc(s.notes.시간 || "")}</td><td>${esc(s.objectives.join(", ") || "—")}</td></tr>`).join("");
  const ws = L.worksheet;
  const answers = ws ? `<h2>활동지 정답</h2><table><tr><th style="width:12mm">번호</th><th>정답</th></tr>${ws.items.map((it) => `<tr><td>${it.no}</td><td>${esc(it.answer)}</td></tr>`).join("")}</table>` : "";
  const record = ws && ws.record ? `<h2>오늘의 기록</h2><div class="box">${ws.record.map((r) => `<div>${esc(r)}</div>`).join("")}<div style="margin-top:2mm">메모: ______________________________________________</div></div>` : "";
  return `<!doctype html><html lang="ko"><head><meta charset="utf-8"><style>${CSS}</style></head><body>
    <h1>부모용 진행 안내 · ${esc(L.title)}</h1>
    <div class="sub">${esc(L.grade_label)} ${esc(L.strand_label)} · ${esc(L.unit_folder)} ${L.sequence}차시 · 약 ${L.minutes}분 · 수업 ID ${esc(L.id)}</div>
    <div class="box warn"><b>시작 전에</b><ul style="margin:1mm 0 0">
      <li>아이에게는 PPT를 <b>슬라이드 쇼</b>로 보여 주세요. 일반 보기 화면 아래쪽 노트에는 정답이 있습니다. 진행은 이 안내서를 보며 합니다.</li>
      <li>준비물: ${esc(L.materials.join(", "))}</li>
      <li>정답을 바로 알려 주기보다 “어떻게 알았어?”라고 묻고 아이가 설명하게 하세요. 막히면 각 장의 ‘막히면’을 따르세요.</li>
      ${L.break_after ? `<li>아이가 지치면 ${esc(L.break_after)} 뒤에서 나누어 이틀에 해도 됩니다.</li>` : ""}
      ${L.format === "act" ? "<li>활동 중심 차시입니다. 화면은 짧은 안내이고, 실제 활동과 관찰 기록이 중심입니다.</li>" : ""}
    </ul></div>
    <h2>오늘의 목표와 확인 방법</h2>
    ${L.objectives.map((o) => `<div class="box"><b>목표 ${esc(o.id)}</b> ${esc(o.text)}<br><b class="k">확인</b> ${esc(o.evidence)}<br><b class="k">성공 기준</b> ${esc(o.success)}</div>`).join("")}
    <h2>먼저 알고 있어야 할 것</h2>
    <ul>${L.prerequisites.map((p) => `<li>${esc(p.text)}</li>`).join("")}</ul>
    ${supportLine(L)}
    <h2>자주 나오는 오해</h2>
    <table><tr><th style="width:45%">아이가 이렇게 생각하면</th><th>이렇게 도와주세요</th></tr>
    ${L.misconceptions.map((m) => `<tr><td>${esc(m.text)}</td><td>${esc(m.response)}</td></tr>`).join("")}</table>
    <div style="margin-top:2mm"><b>오늘 다루지 않는 것</b> ${esc(L.boundary)}</div>
    <h2>진행 순서</h2>
    <table><tr><th style="width:12mm">장</th><th>하는 일</th><th style="width:18mm">시간</th><th style="width:16mm">목표</th></tr>${rows}</table>
    <h2 style="break-before: page; margin-top: 0">장별 안내</h2>
    ${slides.join("")}
    ${answers}${record}
  </body></html>`;
}

async function toPdf(browser, html, file) {
  const page = await browser.newPage();
  await page.setContent(html, { waitUntil: "load" });
  await page.pdf({ path: file, format: "A4", printBackground: true, preferCSSPageSize: true });
  await page.close();
}

async function main() {
  const args = parseArgs(process.argv);
  const L = JSON.parse(fs.readFileSync(args.lesson, "utf-8"));
  const outDir = args.out || path.join("dist", L.grade_label, L.strand_label, L.unit_folder);
  fs.mkdirSync(outDir, { recursive: true });
  let thumbs = [];
  if (args.thumbs && fs.existsSync(args.thumbs)) {
    thumbs = fs.readdirSync(args.thumbs).filter((f) => /^slide-\d+\.jpg$/.test(f)).sort()
      .map((f) => "data:image/jpeg;base64," + fs.readFileSync(path.join(args.thumbs, f)).toString("base64"));
  }
  const browser = await chromium.launch();
  try {
    if (L.worksheet) {
      const ws = path.join(outDir, `${L.file_stem}_활동지.pdf`);
      await toPdf(browser, worksheetHtml(L), ws);
      console.log(ws);
    }
    const guide = path.join(outDir, `${L.file_stem}_부모용안내.pdf`);
    await toPdf(browser, guideHtml(L, thumbs), guide);
    console.log(guide);
  } finally {
    await browser.close();
  }
}

main().catch((err) => {
  console.error(err.message || err);
  process.exit(1);
});
