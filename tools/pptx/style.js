// 모든 장이 함께 쓰는 글꼴·색·글자 크기.
const FONT = "맑은 고딕";
const LANG = "ko-KR";

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
  onDark: "32606F", support: "F4F7F6", onDarkMuted: "C9DCD8", grid: "CBD5E1",
};

// 학년군별 글자 크기(pt). 화면 투사 기준 본문 24~30pt, 저학년은 더 크게.
const BAND = {
  E12: { title: 44, body: 32, small: 26 },
  E34: { title: 40, body: 30, small: 24 },
  E56: { title: 40, body: 28, small: 22 },
  M: { title: 36, body: 26, small: 20 },
  H: { title: 36, body: 24, small: 20 },
};

// 내용 영역(제목 아래, 바닥글 위)
const AREA = { x: 0.6, y: 1.45, w: 12.13, h: 5.35 };

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

module.exports = { FONT, LANG, THEME, P, TINT, BAND, AREA, textOpts, sizeOf, colorOf };
