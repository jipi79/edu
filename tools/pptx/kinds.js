// 장 종류(kind)별 자동 배치. 원고에는 내용만 쓰고 위치는 여기서 정한다.
// 글이 상자에 들어가지 않으면 deck.problems에 기록되어 빌드가 실패한다(원고를 줄이라는 뜻).
const { AREA, P, TINT } = require("./style");
const { drawFigures, isWide } = require("./figures");

const GAP = 0.25;
const LABELS = ["①", "②", "③", "④", "⑤", "⑥", "⑦", "⑧"];
const CHOICE = ["가", "나", "다", "라", "마", "바"];

function area() {
  return { ...AREA };
}

// 맨 위 안내 문장
function takeTop(deck, slide, sid, text, r, color) {
  if (!text) return r;
  const pt = deck.style.body;
  const h = Math.max(0.55, Math.min(deck.textH(text, r.w, pt), 1.5));
  deck.para(slide, sid, text, { x: r.x, y: r.y, w: r.w, h }, { sizes: [pt, deck.style.small], color, valign: "middle" });
  return { ...r, y: r.y + h + 0.2, h: r.h - h - 0.2 };
}

// 맨 아래 카드(핵심 문장, 질문, 도움말)
function takeBottom(deck, slide, sid, card, r, tone = "accent") {
  if (!card) return r;
  const c = typeof card === "string" ? { text: card, tone } : { tone, ...card };
  const h = deck.cardHeight(c, r.w);
  deck.cardFit(slide, sid, { x: r.x, y: r.y + r.h - h, w: r.w, h }, c);
  return { ...r, h: r.h - h - GAP };
}

function split(r, ratio, gap = 0.4) {
  const lw = (r.w - gap) * ratio;
  return [{ ...r, w: lw }, { ...r, x: r.x + lw + gap, w: r.w - lw - gap }];
}

function asCard(p) {
  return typeof p === "string" ? { text: p } : p;
}

// 카드 여러 장을 행으로(가로) 또는 열로(세로) 놓는다
function cardRow(deck, slide, sid, items, r, tone = "tint") {
  const n = items.length;
  const w = (r.w - GAP * (n - 1)) / n;
  const h = Math.max(...items.map((c) => deck.cardHeight({ tone, ...asCard(c) }, w)));
  const hh = Math.min(h, r.h);
  items.forEach((c, i) => deck.cardFit(slide, sid, { x: r.x + i * (w + GAP), y: r.y + r.h - hh, w, h: hh }, { tone, ...asCard(c) }));
  return hh;
}

function cardColumn(deck, slide, sid, items, r, tone = "tint") {
  const hs = items.map((c) => deck.cardHeight({ tone, ...asCard(c) }, r.w));
  const total = hs.reduce((s, v) => s + v, 0) + GAP * (items.length - 1);
  if (total > r.h + 0.01) deck.problems.push(`${sid}: 카드 ${items.length}장이 세로로 들어가지 않는다(필요 ${total.toFixed(2)}in, 공간 ${r.h.toFixed(2)}in)`);
  let y = r.y + Math.max(0, (r.h - total) / 2);
  items.forEach((c, i) => {
    deck.cardFit(slide, sid, { x: r.x, y, w: r.w, h: hs[i] }, { tone, ...asCard(c) });
    y += hs[i] + GAP;
  });
}

function figureOf(spec) {
  return spec.figure || spec.figures;
}

// 문제 하나(식·글·그림)를 상자 안에 그린다
function problem(deck, slide, sid, p, box, label) {
  const chip = 0.62;
  deck.chip(slide, sid, { x: box.x, y: box.y + (box.h - chip) / 2, w: chip, h: chip, text: p.label || label, tone: "label", size: "small" });
  const inner = { x: box.x + chip + 0.25, y: box.y, w: box.w - chip - 0.25, h: box.h };
  if (p.eq) drawFigures(deck, slide, sid, { type: "eq", items: p.eq, align: "left", size: p.size }, inner);
  else if (p.figure) drawFigures(deck, slide, sid, p.figure, { ...inner, w: Math.min(inner.w, p.wide ? inner.w : 6) });
  if (p.text) {
    if (p.eq || p.figure) deck.problems.push(`${sid}: 문제에는 eq·figure·text 중 하나만 쓴다`);
    deck.para(slide, sid, p.text, inner, { sizes: [deck.style.body, deck.style.small], valign: "middle" });
  }
}

const KINDS = {
  cover(deck, slide, spec) {
    if (figureOf(spec)) drawFigures(deck, slide, spec.id, figureOf(spec), { x: 8.4, y: 0.7, w: 4.3, h: 3.2 });
    if (spec.goals) {
      const c = { tone: "onDark", title: "오늘 할 수 있게 될 것", items: spec.goals };
      const h = Math.max(1.6, deck.cardHeight(c, 11.73));
      deck.cardFit(slide, spec.id, { x: 0.8, y: 6.7 - h, w: 11.73, h }, c);
    }
  },

  concept(deck, slide, spec) {
    let r = takeTop(deck, slide, spec.id, spec.text, area());
    r = takeBottom(deck, slide, spec.id, spec.key, r, "accent");
    const figs = figureOf(spec);
    const points = spec.points;
    if (figs && points) {
      if (isWide(figs)) {
        const w = (r.w - GAP * (points.length - 1)) / points.length;
        const ph = Math.max(...points.map((c) => deck.cardHeight({ tone: "tint", ...asCard(c) }, w)));
        cardRow(deck, slide, spec.id, points, { ...r, y: r.y + r.h - ph, h: ph });
        drawFigures(deck, slide, spec.id, figs, { ...r, h: r.h - ph - GAP });
      } else {
        const [left, right] = split(r, spec.figureRatio || 0.5);
        drawFigures(deck, slide, spec.id, figs, left);
        cardColumn(deck, slide, spec.id, points, right);
      }
    } else if (figs) {
      drawFigures(deck, slide, spec.id, figs, r);
    } else if (points) {
      cardColumn(deck, slide, spec.id, points, r);
    }
  },

  steps(deck, slide, spec, region) {
    let r = takeTop(deck, slide, spec.id, spec.text, region || area());
    r = takeBottom(deck, slide, spec.id, spec.key, r, "accent");
    if (spec.problem) {
      const ph = 1.25;
      if (spec.problem.eq) drawFigures(deck, slide, spec.id, { type: "eq", items: spec.problem.eq, align: "left" }, { ...r, h: ph });
      else deck.para(slide, spec.id, spec.problem.text || spec.problem, { ...r, h: ph }, { sizes: [deck.style.body], bold: true, valign: "middle" });
      r = { ...r, y: r.y + ph + 0.15, h: r.h - ph - 0.15 };
    }
    let left = r;
    if (figureOf(spec)) {
      const [l, right] = split(r, spec.figureRatio ? 1 - spec.figureRatio : 0.56);
      left = l;
      drawFigures(deck, slide, spec.id, figureOf(spec), right);
    }
    const items = spec.steps.map((s) => (typeof s === "string" ? { text: s } : s));
    const d = 0.6;
    const tw = (it) => left.w - d - 0.25 - (it.eq ? left.w * 0.42 : 0);
    const pt = [deck.style.body, deck.style.small].find((p) => {
      const tot = items.reduce((s, it) => s + Math.max(deck.textH(it.text, tw(it), p), it.eq ? deck.eqHeight(it.eq, p) : 0, d), 0) + 0.18 * (items.length - 1);
      return tot <= left.h;
    }) || deck.style.small;
    const hs = items.map((it) => Math.max(deck.textH(it.text, tw(it), pt), it.eq ? deck.eqHeight(it.eq, pt) : 0, d));
    const total = hs.reduce((s, v) => s + v, 0) + 0.18 * (items.length - 1);
    if (total > left.h + 0.01) deck.problems.push(`${spec.id}: 단계 ${items.length}개가 들어가지 않는다`);
    let y = left.y + Math.max(0, (left.h - total) / 2);
    items.forEach((it, i) => {
      deck.stepNo(slide, spec.id, i + 1, left.x, y + Math.min(0.05, (hs[i] - d) / 2), d);
      deck.para(slide, spec.id, it.text, { x: left.x + d + 0.25, y, w: tw(it), h: hs[i] }, { sizes: [pt], valign: it.eq ? "middle" : "top" });
      if (it.eq) drawFigures(deck, slide, spec.id, { type: "eq", items: it.eq, size: pt, align: "left" }, { x: left.x + left.w * 0.58, y, w: left.w * 0.42, h: hs[i] });
      y += hs[i] + 0.18;
    });
  },

  practice(deck, slide, spec) {
    let r = takeTop(deck, slide, spec.id, spec.text, area());
    r = takeBottom(deck, slide, spec.id, spec.hint, r, "info");
    let box = r;
    if (figureOf(spec)) {
      const [l, right] = split(r, 0.5);
      box = l;
      if (spec.aidTitle) {
        const t = { tone: "tint", title: spec.aidTitle };
        deck.cardFit(slide, spec.id, right, t);
        drawFigures(deck, slide, spec.id, figureOf(spec), { x: right.x + 0.3, y: right.y + 0.75, w: right.w - 0.6, h: right.h - 0.95 });
      } else {
        drawFigures(deck, slide, spec.id, figureOf(spec), right);
      }
    }
    const probs = spec.problems;
    const cols = figureOf(spec) || probs.length <= 3 ? 1 : 2;
    const rows = Math.ceil(probs.length / cols);
    const cw = (box.w - 0.4 * (cols - 1)) / cols;
    const rh = (box.h - 0.2 * (rows - 1)) / rows;
    probs.forEach((p, i) => {
      const c = cols === 1 ? 0 : i % cols;
      const row = cols === 1 ? i : Math.floor(i / cols);
      // 그림 문제는 칸 높이를 다 쓰고, 글·식 문제는 1.6in까지만 쓴다
      problem(deck, slide, spec.id, p, { x: box.x + c * (cw + 0.4), y: box.y + row * (rh + 0.2), w: cw, h: p.figure ? rh : Math.min(rh, 1.6) }, LABELS[i]);
    });
  },

  choice(deck, slide, spec) {
    let r = takeTop(deck, slide, spec.id, spec.text, area());
    r = takeBottom(deck, slide, spec.id, spec.question, r, "tint");
    const n = spec.options.length;
    const cols = n === 4 ? 2 : n;
    const rows = Math.ceil(n / cols);
    const cw = (r.w - 0.4 * (cols - 1)) / cols;
    const rh = (r.h - 0.3 * (rows - 1)) / rows;
    const chip = 0.62;
    spec.options.forEach((o, i) => {
      const x = r.x + (i % cols) * (cw + 0.4);
      const y = r.y + Math.floor(i / cols) * (rh + 0.3);
      if (rows === 1) {
        deck.chip(slide, spec.id, { x: x + (cw - chip) / 2, y, w: chip, h: chip, text: o.label || CHOICE[i], tone: "label" });
        const inner = { x, y: y + chip + 0.15, w: cw, h: rh - chip - 0.15 };
        if (o.figure) drawFigures(deck, slide, spec.id, o.figure, inner);
        else deck.cardFit(slide, spec.id, inner, { tone: "tint", text: o.text });
      } else {
        deck.chip(slide, spec.id, { x, y: y + (rh - chip) / 2, w: chip, h: chip, text: o.label || CHOICE[i], tone: "label" });
        const inner = { x: x + chip + 0.25, y, w: cw - chip - 0.25, h: rh };
        if (o.figure) drawFigures(deck, slide, spec.id, o.figure, inner);
        else deck.cardFit(slide, spec.id, inner, { tone: "tint", text: o.text });
      }
    });
  },

  compare(deck, slide, spec) {
    let r = area();
    if (spec.claim) {
      const c = { tone: "tint", text: spec.claim };
      const h = deck.cardHeight(c, r.w);
      deck.cardFit(slide, spec.id, { x: r.x, y: r.y, w: r.w, h }, c);
      r = { ...r, y: r.y + h + GAP, h: r.h - h - GAP };
    }
    r = takeBottom(deck, slide, spec.id, spec.question, r, "accent");
    const panes = [spec.left, spec.right];
    const [lb, rb] = split(r, 0.5);
    [lb, rb].forEach((b, i) => {
      const p = panes[i];
      const tone = p.mark === "o" ? "good" : p.mark === "x" ? "bad" : "info";
      const prefix = p.mark === "o" ? "○ " : p.mark === "x" ? "× " : "";
      deck.chip(slide, spec.id, { x: b.x, y: b.y, w: b.w, h: 0.62, text: prefix + p.title, tone });
      const inner = { x: b.x, y: b.y + 0.8, w: b.w, h: b.h - 0.8 };
      if (p.figure) {
        const th = p.text ? Math.min(1.2, deck.textH(p.text, b.w, deck.style.small) + 0.1) : 0;
        drawFigures(deck, slide, spec.id, p.figure, { ...inner, h: inner.h - th });
        if (p.text) deck.para(slide, spec.id, p.text, { x: b.x, y: inner.y + inner.h - th, w: b.w, h: th }, { sizes: [deck.style.small] });
      } else if (p.eq) {
        drawFigures(deck, slide, spec.id, { type: "eq", items: p.eq }, inner);
      } else {
        deck.para(slide, spec.id, p.text, inner, { sizes: [deck.style.body, deck.style.small] });
      }
    });
  },

  passage(deck, slide, spec) {
    let r = takeTop(deck, slide, spec.id, spec.text, area());
    r = takeBottom(deck, slide, spec.id, spec.question, r, "accent");
    let box = r;
    if (figureOf(spec)) {
      const [l, right] = split(r, 0.62);
      box = l;
      drawFigures(deck, slide, spec.id, figureOf(spec), right);
    }
    const p = spec.passage;
    const paras = (p.paragraphs || [p.text]).map((t, i) => {
      const text = typeof t === "string" ? t : t.text;
      const shown = p.numbered ? `${LABELS[i]} ${text}` : text;
      return typeof t === "string" ? shown : { text: shown, align: t.align };
    });
    deck.passageBox(slide, spec.id, box, p.title, paras);
  },

  cards(deck, slide, spec) {
    let r = takeTop(deck, slide, spec.id, spec.text, area());
    r = takeBottom(deck, slide, spec.id, spec.key, r, "accent");
    const items = spec.cards;
    const n = items.length;
    if (n <= 3) {
      const w = (r.w - GAP * (n - 1)) / n;
      const h = Math.max(...items.map((c) => deck.cardHeight({ tone: "tint", ...asCard(c) }, w)));
      const hh = Math.min(Math.max(h, Math.min(r.h, 2.4)), r.h);
      items.forEach((c, i) => deck.cardFit(slide, spec.id, { x: r.x + i * (w + GAP), y: r.y + (r.h - hh) / 2, w, h: hh }, { tone: c.tone || "tint", ...asCard(c) }));
    } else {
      const cols = n === 4 ? 2 : 3;
      const rows = Math.ceil(n / cols);
      const w = (r.w - GAP * (cols - 1)) / cols;
      const h = (r.h - GAP * (rows - 1)) / rows;
      items.forEach((c, i) => deck.cardFit(slide, spec.id, { x: r.x + (i % cols) * (w + GAP), y: r.y + Math.floor(i / cols) * (h + GAP), w, h }, { tone: c.tone || "tint", ...asCard(c) }));
    }
  },

  table(deck, slide, spec) {
    let r = takeTop(deck, slide, spec.id, spec.text, area());
    r = takeBottom(deck, slide, spec.id, spec.key, r, "accent");
    drawFigures(deck, slide, spec.id, { type: "table", ...spec.table }, r);
  },

  chart(deck, slide, spec) {
    let r = takeTop(deck, slide, spec.id, spec.text, area());
    r = takeBottom(deck, slide, spec.id, spec.question || spec.key, r, "accent");
    drawFigures(deck, slide, spec.id, { type: "chart", ...spec.chart }, r);
  },

  activity(deck, slide, spec) {
    let r = takeTop(deck, slide, spec.id, spec.text, area());
    if (spec.safety) r = takeBottom(deck, slide, spec.id, { text: `안전: ${spec.safety}` }, r, "accent");
    let left = r;
    if (spec.criteria) {
      const [l, right] = split(r, 0.55);
      left = l;
      deck.cardFit(slide, spec.id, right, { tone: "tint", title: spec.criteriaTitle || "이렇게 하면 잘한 거예요", items: spec.criteria.map((c) => `☐ ${c}`) });
    } else if (figureOf(spec)) {
      const [l, right] = split(r, 0.55);
      left = l;
      drawFigures(deck, slide, spec.id, figureOf(spec), right);
    }
    KINDS.steps(deck, slide, { id: spec.id, steps: spec.steps }, left);
  },

  answers(deck, slide, spec) {
    let r = area();
    r = takeBottom(deck, slide, spec.id, spec.explain ? { text: spec.explain } : null, r, "tint");
    const sides = [[spec.good, "○ 정답", "good"], [spec.bad, "× 흔한 실수", "bad"]].filter(([l]) => l && l.length);
    const boxes = sides.length === 2 ? split(r, 0.5) : [r];
    sides.forEach(([list, title, tone], k) => {
      const b = boxes[k];
      deck.chip(slide, spec.id, { x: b.x, y: b.y, w: b.w, h: 0.6, text: title, tone, size: "small" });
      const rh = Math.min(1.35, (b.h - 0.8 - 0.15 * (list.length - 1)) / list.length);
      list.forEach((it, i) => {
        const y = b.y + 0.8 + i * (rh + 0.15);
        const ew = it.note ? b.w * 0.5 : b.w;
        if (it.eq) drawFigures(deck, slide, spec.id, { type: "eq", items: it.eq, align: "left", size: deck.style.small + 4 }, { x: b.x, y, w: ew, h: rh });
        else deck.para(slide, spec.id, it.text, { x: b.x, y, w: ew, h: rh }, { sizes: [deck.style.body, deck.style.small], valign: "middle" });
        if (it.note) deck.para(slide, spec.id, it.note, { x: b.x + ew + 0.15, y, w: b.w - ew - 0.15, h: rh }, { sizes: [deck.style.small], valign: "middle" });
      });
    });
  },

  summary(deck, slide, spec) {
    const r = area();
    let y = r.y;
    const key = { tone: "onDark", text: spec.key };
    const kh = deck.cardHeight(key, r.w);
    deck.cardFit(slide, spec.id, { x: r.x, y, w: r.w, h: kh }, key);
    y += kh + GAP;
    if (spec.do || spec.dont) {
      const chips = [];
      if (spec.do) chips.push([`○ ${spec.do}`, "goodOnDark"]);
      if (spec.dont) chips.push([`× ${spec.dont}`, "badOnDark"]);
      const w = (r.w - GAP * (chips.length - 1)) / chips.length;
      chips.forEach(([t, tone], i) => deck.chip(slide, spec.id, { x: r.x + i * (w + GAP), y, w, h: 0.65, text: t, tone, size: "small" }));
      y += 0.65 + GAP;
    }
    const nextH = spec.next ? 0.55 : 0;
    if (spec.review && spec.review.length) {
      deck.para(slide, spec.id, "다음 수업을 시작할 때 다시 풀어요", { x: r.x, y, w: r.w, h: 0.5 }, { sizes: [deck.style.small], bold: true, color: "onDark" });
      y += 0.55;
      const h = r.y + r.h - y - nextH - 0.15;
      const n = spec.review.length;
      const w = (r.w - GAP * (n - 1)) / n;
      spec.review.forEach((p, i) => {
        const b = { x: r.x + i * (w + GAP), y, w, h };
        if (p.eq) drawFigures(deck, slide, spec.id, { type: "eq", items: [LABELS[i], ...p.eq], color: "onDark", align: "left", size: deck.style.small + 4 }, b);
        else deck.para(slide, spec.id, `${LABELS[i]} ${p.text || p}`, b, { sizes: [deck.style.small], color: "onDark", valign: "middle" });
      });
    }
    if (spec.next) deck.para(slide, spec.id, `다음 시간: ${spec.next}`, { x: r.x, y: r.y + r.h - nextH, w: r.w, h: nextH }, { sizes: [deck.style.small, 18], color: "onDarkMuted", valign: "middle" });
  },
};
KINDS.check = KINDS.practice;
KINDS.support = KINDS.concept;

module.exports = { KINDS };
