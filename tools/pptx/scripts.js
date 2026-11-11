// 유니코드 위첨자·아래 첨자 문자를 보통 글자로 바꾸는 도우미(슬라이드·활동지·그림이 함께 쓴다).
// 위첨자: 2³, x², Na⁺, O²⁻ / 아래 첨자: H₂O, CO₂, C₆H₁₂O₆, aₙ, ₙPᵣ, ₙCᵣ, aᵢⱼ / 여집합: Aᶜ
const SUP = { "⁰": "0", "¹": "1", "²": "2", "³": "3", "⁴": "4", "⁵": "5", "⁶": "6", "⁷": "7", "⁸": "8", "⁹": "9", "⁺": "+", "⁻": "\u2212", "ⁿ": "n", "ᵐ": "m", "ˣ": "x", "ᶜ": "c" };
const SUB = { "₀": "0", "₁": "1", "₂": "2", "₃": "3", "₄": "4", "₅": "5", "₆": "6", "₇": "7", "₈": "8", "₉": "9", "₊": "+", "₋": "\u2212", "ₐ": "a", "ₑ": "e", "ₒ": "o", "ₓ": "x", "ₕ": "h", "ₖ": "k", "ₗ": "l", "ₘ": "m", "ₙ": "n", "ₚ": "p", "ₛ": "s", "ₜ": "t", "ᵢ": "i", "ᵣ": "r", "ⱼ": "j" };
const SUP_CH = Object.keys(SUP).join("");
const SUB_CH = Object.keys(SUB).join("");
const SCRIPT_ANY = new RegExp(`[${SUP_CH}${SUB_CH}]`);
const SCRIPT_SPLIT = new RegExp(`([${SUP_CH}]+|[${SUB_CH}]+)`);
const SCRIPT_RUNS = new RegExp(`[${SUP_CH}]+|[${SUB_CH}]+`, "g");

function scriptKind(s) {
  if (new RegExp(`^[${SUP_CH}]+$`).test(s)) return "sup";
  if (new RegExp(`^[${SUB_CH}]+$`).test(s)) return "sub";
  return null;
}

function plainScript(s) {
  return [...s].map((c) => SUP[c] ?? SUB[c] ?? c).join("");
}

module.exports = { SUP, SUB, SCRIPT_ANY, SCRIPT_SPLIT, SCRIPT_RUNS, scriptKind, plainScript };
