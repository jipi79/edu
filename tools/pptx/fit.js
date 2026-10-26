// 글자 상자에 문장이 들어가는지 어림한다. PowerPoint가 실제로 줄을 나누는 방식(어절 단위)과
// 맑은 고딕의 글자 폭을 넉넉하게 잡아 계산한다. 넘치면 빌드가 실패하도록 해서 원고를 줄이게 한다.

const HANGUL = /[ᄀ-ᇿ㄰-㆏가-힯一-鿿　-〿＀-￯①-⑳○●□■△▲◇◆★☆→←↑↓×÷≠≤≥·…]/;

function charEm(ch) {
  if (HANGUL.test(ch)) return 0.98;
  if (ch === " ") return 0.3;
  if (/[A-Z0-9]/.test(ch)) return 0.64;
  if (/[a-z]/.test(ch)) return 0.55;
  return 0.42;
}

function widthIn(text, pt) {
  let em = 0;
  for (const ch of text) em += charEm(ch);
  return (em * pt) / 72;
}

// 어절 단위로 줄을 채운다. 한 어절이 줄보다 길면 글자 단위로 나눈다.
function countLines(text, boxW, pt) {
  let lines = 0;
  for (const para of String(text).split("\n")) {
    let cur = 0;
    let n = 1;
    for (const word of para.split(" ")) {
      const w = widthIn(word, pt);
      const sp = cur > 0 ? widthIn(" ", pt) : 0;
      if (cur + sp + w <= boxW) {
        cur += sp + w;
      } else if (w <= boxW) {
        n += 1;
        cur = w;
      } else {
        // 긴 어절: 글자 단위로 넘긴다
        for (const ch of word) {
          const cw = widthIn(ch, pt);
          if (cur + cw > boxW) { n += 1; cur = 0; }
          cur += cw;
        }
      }
    }
    lines += n;
  }
  return lines;
}

function lineH(pt) {
  return (pt * 1.22) / 72;
}

// 여러 문단(각각 크기 pt)을 상자 폭 w에 넣을 때 필요한 높이
function heightOf(paras, w, gapPt = 6) {
  let h = 0;
  paras.forEach((p, i) => {
    h += countLines(p.text, w, p.pt) * lineH(p.pt);
    if (i < paras.length - 1) h += gapPt / 72;
  });
  return h;
}

module.exports = { widthIn, countLines, lineH, heightOf };
