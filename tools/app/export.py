"""수업 원본에서 앱용 학습 데이터(임시 형식 0판)를 뽑고, 뽑지 못한 곳을 보고서로 낸다.

  python3 tools/app/export.py G01                 # 초1 → build/app/G01/<ID>.json, build/app/G01/report.md
  python3 tools/app/export.py G01 --ids KR22-G01-MAT-ADD3-L01

원본은 고치지 않는다. 보고서의 항목은 원본(노트 정답, 보기, 검산)을 고칠 곳이다.
앱 데이터는 다시 뽑으면 되므로 저장소에 넣지 않는다(build/ 는 .gitignore).
형식은 시제품 전의 임시판이다(docs/app-design.md).

문항마다 뽑는 것:
  id(내용으로 만든 바뀌지 않는 이름), 장, 문제, 정답(answer)·단위·풀이(note),
  입력 종류(input: numpad, choice, short, parent, none), 근거(why), 노트가 가리키는 오개념(misconceptions)
"""
import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "plan"))
from diagnose import CIRCLED, clean, render_item, split_answers  # noqa: E402
sys.path.insert(0, str(ROOT / ".claude" / "skills" / "education-ppt" / "scripts"))
import wrong_line  # noqa: E402

FORMAT_VERSION = 0
GRADE = "G01"  # export()가 차시마다 바꾼다(학년에 따라 다르게 읽는 규칙에 씀)
STRAND = ""
LABELS = "가나다라마바"
LISTEN = re.compile(r"듣고|들려주|불러 주|받아쓰|받아 쓰|말하는 소리")   # 부모가 읽어 주고 아이가 답함(소리 파일 없음)
SPEAK = re.compile(r"소리 내어 읽고|소리 내어 읽어요|소리 내어 읽기")       # 아이가 소리 내는 과제: 부모 판정
COVER = re.compile(r"가리고 쓰")                                            # 보고 나서 가리고 쓰기


def mode_flags(rec, text):
    """듣기·말하기·가리고 쓰기 표시. 말하기는 부모 판정으로 돌린다."""
    ans = rec.get("answer")
    if (rec["input"] not in ("parent", "none") and SPEAK.search(text) and isinstance(ans, (str, list))
            and all(str(x) in rec["prompt"] for x in (ans if isinstance(ans, list) else [ans])) and "/" not in rec["prompt"]):
        # 화면의 낱말을 소리 내어 읽는 과제: 그 낱말을 다시 치게 하면 읽기를 재지 못한다
        rec.update(input="parent", why="소리 내어 읽기(부모가 듣고 판단)")
    if LISTEN.search(text):
        rec["parent_reads"] = True  # 부모가 노트의 낱말·글을 읽어 준 뒤 아이가 답한다
    if COVER.search(text):
        rec["cover"] = True  # 화면의 낱말을 본 뒤 가리고 쓴다
OPEN = re.compile(r"또는|예:|예\)|예를 들어|가운데|(?<![가-힣0-9])등(?=[\s.,)]|$)|처럼|자유롭|자유로운|자유 답|여러|다양|모두 맞|어느 것이든|아무|골라도|정해진 답|정답이 하나가 아닙|정답은 하나가 아닙|정답이 정해져 있지 않|정답은 따로 없|까닭을 봅니다|어떤 낱말이든|하면 맞습니다|면 맞음|하면 됩니다")
NUM = r"−?\d+(?:\.\d+)?"


# ── 정답 풀기 ──────────────────────────────────────────────

ABBR = ("p.m.", "a.m.", "Mr.", "Mrs.", "Ms.", "Dr.", "e.g.", "i.e.", "etc.", "St.")


def _guard(t):
    for k, w in enumerate(ABBR):
        t = t.replace(w, f"\x01{k}\x01")
    return t


def _unguard(t):
    return re.sub(r"\x01(\d+)\x01", lambda m: ABBR[int(m.group(1))], t)


def main_answer(a):
    """‘6 (1 + 2 = 3, …)’ → (‘6’, ‘1 + 2 = 3, …’). 첫 괄호나 첫 문장 앞까지가 답이다(p.m.·Mr. 같은 줄임말의 점은 문장 끝이 아님)."""
    m, n = _main_answer(_guard(clean(a).replace("\xa0", " ")))
    return _unguard(m), _unguard(n)


def _main_answer(a):
    m = re.match(r"^(.*?)\s*\((.*)\)\s*\.?$", a)
    if m and m.group(1):
        first = re.match(r"^([^(]*)\(([^()]*)\)", a)
        inner = re.sub(r"분의", "", first.group(2)) if first else ""
        if (first and not re.search(r"[가-힣=]", inner) and re.search(r"[0-9A-Za-z]", inner)
                and not re.search(r"\d\s+[A-Za-zΩμ°/%²³]+$", first.group(1))   # ‘50 g(1 g/mL × 50 mL)’: 단위 뒤 괄호는 풀이
                and (re.search(r"[/×·+\-−√^]$", first.group(1).rstrip())   # 2/(x − 2), −(3분의 1), √(…)
                     or (re.search(r"(?:^|[^A-Za-z])[A-Za-z]′?$", first.group(1))      # N(200, 10²), B(600, 0.3), P(A)
                         and not re.search(r"\d\s*[A-Za-z]$", first.group(1)))          # 49 N(9.8 × 5)의 N은 단위
                     or (re.search(r"[0-9A-Za-z)²³′⁰¹⁴-⁹₀-₉Σ∫]$", first.group(1))
                         and re.search(r"(?<![A-Za-z])[a-zA-Z](?![A-Za-z])", inner)))):  # 3(x + 2), f(x)
            # 수식의 괄호(3(x + 2), f(x) = …)는 답의 일부: 한글이 든 첫 괄호부터가 풀이
            h = re.match(r"^(.*?)\s+\(([^()]*[가-힣=][^()]*)\)\s*(.*)$", a)
            if h and h.group(1).strip():
                return h.group(1).strip(), (h.group(2) + " " + h.group(3)).strip()
            return a.rstrip("."), ""
        return m.group(1).strip(), m.group(2).strip()
    m = re.match(r"^(.*?[^0-9])\.\s+(.*)$", a)
    if m and re.fullmatch(r"[A-Za-z][A-Za-z ,'’]*", m.group(1)) and re.match(r"[A-Z]", m.group(2)):
        return a.rstrip("."), ""  # 영어 여러 문장은 한 답(첫 문장만 떼지 않는다)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return a.rstrip("."), ""


UNIT = r"(?:만\s?원|억\s?원|[가-힣]{1,3}|cm²|m²|km²|cm³|m³|g/cm³|kg/m³|g/mL|m/s²|mm|cm|km|m|kg|mg|g|mL|L|km/h|m/s|mol/L|mol|M|kJ|kcal|J|W|kW|kWh|N|Pa|hPa|V|A|Ω|Hz|°C|°|%p|%|t)"


def number_unit(s):
    s = s.replace("\xa0", " ").strip()
    m = re.fullmatch(rf"({NUM}|\d{{1,3}}(?:,\d{{3}})+)\s*({UNIT})?", s)
    return (m.group(1).replace(",", ""), m.group(2) or "") if m else (None, None)


def korean_fraction(s):
    """‘5분의 2’ → ‘2/5’, ‘1과 2분의 1’ → ‘1 1/2’. 아니면 None."""
    s = s.replace("\xa0", " ").strip()
    m = re.fullmatch(r"(?:(\d+)\s*(?:과|와)\s*)?(\d+)\s*분의\s*(\d+)", s)
    if not m:
        r = re.fullmatch(r"([−\-]?)(\d+|√\d+|\d+√\d+)\s*분의\s*(\d+|√\d+|\d+√\d+)", s)  # ‘2분의 √3’
        return f"{r.group(1)}{r.group(3)}/{r.group(2)}" if r else None
    whole, den, num = m.group(1), m.group(2), m.group(3)
    return f"{whole} {num}/{den}" if whole else f"{num}/{den}"


# ── 식 검산 (□ 하나가 든 사칙 계산) ──────────────────────────

def to_py(tok):
    if isinstance(tok, list) and len(tok) == 2:
        return f"Fraction({tok[0]},{tok[1]})"
    t = str(tok).replace("−", "-").replace("×", "*").replace("÷", "/")
    return t


def eq_value(items):
    """[…'=', '□'] 꼴이면 □의 값. □가 다른 자리여도 0~1000에서 찾는다. 못 풀면 None."""
    toks = [t for t in items if t is not None]
    if sum(1 for t in items if t is None or t == "□") != 1 or "=" not in toks:
        return None
    if any(isinstance(t, list) for t in items):
        return None  # 분수 식은 원본 checks가 검산한다
    if any(not re.fullmatch(r"−?\d+|[+−×÷=□()]|", str(t)) for t in items if t is not None):
        return None
    expr = " ".join("□" if t is None else str(t) for t in items)
    left, _, right = expr.partition("=")
    for v in range(0, 1001):
        try:
            l = eval(to_py(left.replace("□", str(v))).replace(" ", ""), {"Fraction": Fraction})
            r = eval(to_py(right.replace("□", str(v))).replace(" ", ""), {"Fraction": Fraction})
        except Exception:
            return None
        if l == r:
            return str(v)
    return None


# ── 문항 만들기 ─────────────────────────────────────────────

def item_id(lid, slide_id, prompt, seen):
    h = hashlib.sha1(f"{lid}|{prompt}".encode()).hexdigest()[:8]
    base = f"{lid.removeprefix('KR22-')}-{h}"
    seen[base] += 1
    return base if seen[base] == 1 else f"{base}-{seen[base]}"


def misconception_refs(text):
    return sorted(set(re.findall(r"M\d+", text)))


def accepted(note):
    """풀이에 적힌 다른 맞는 답: ‘교실도 맞음’, ‘놀이터, 강당도 맞음’, ‘강당이라고 해도 맞음’, ‘(현관)’."""
    out = []
    # 따옴표로 묶은 답(마침표·쉼표가 있어도 한 답): ‘…’, ‘…’도 맞음 / ‘…’이라고 해도 맞음
    for run in re.finditer(r"((?:‘[^’]+’\s*(?:,|이나|나|또는)?\s*)+)(?:이라고|라고)?\s*(?:해도|도)\s*(?:까닭이 맞으면\s*)?맞", note):
        out += [x.strip() for x in re.findall(r"‘([^’]+)’", run.group(1))]
    note = re.sub(r"(?:‘[^’]+’\s*(?:,|이나|나|또는)?\s*)+(?:이라고|라고)?\s*(?:해도|도)\s*(?:까닭이 맞으면\s*)?맞(?:음|습니다)?", "", note)
    note = _guard(note)
    for m in re.finditer(r"([^.()]+?)(?:이라고|라고)?\s*(?:해도|도)\s*(?:까닭이 맞으면\s*)?맞", note):
        chunk = re.split(r"면\s+|(?<![A-Za-z])\.\s+|니까\s+", m.group(1))[-1]
        if re.search(r"[‘“][^’”]+[’”]", chunk):  # 따옴표로 묶은 답은 쉼표·가운뎃점에서 가르지 않는다
            out += [x.strip(" ‘’“”,") for x in re.findall(r"[‘“]([^’”]+)[’”]", chunk)]  # 따옴표로 묶은 영어 문장은 쉼표에서 가르지 않는다
        else:
            out += [x.strip(" ‘’“”") for x in re.split(r",\s*|·", chunk) if x.strip()]

    return [_unguard(x) for x in out]


def classify(prob, ans_text):
    """입력 종류와 정답. (input, answer, unit, why)"""
    main, note = main_answer(ans_text)
    if not main:
        return "parent", None, "", "정답 없음", note
    if GRADE >= "G07" and re.search(r"[=<>]", main) and "분의" in main:  # 식 속 ‘2분의 1’ → 1/2
        main = re.sub(r"(√?\d+)\s*분의\s*(√?\d+)", r"\2/\1", main)
    MATHRUN = r"(?:[0-9A-Za-zπ√∛²³⁴⁵⁶⁷⁸⁹⁰¹ⁿˣʸ₀-₉′'±+\-−×÷·=()\[\]{}.,/ ∠°<>≤≥≠∞|^:]|또는)+"
    roots = GRADE >= "G07" and re.fullmatch(MATHRUN, main.strip()) and re.search(r"[=<>≤≥]", main) and "또는" in main
    if OPEN.search(ans_text) and not (roots and not OPEN.search(re.sub(r"또는", "", ans_text))):
        return "parent", main, "", "열린 답(예·또는·가운데)", note
    if roots:  # ‘x = √13 또는 x = −√13’: 근을 모두 쓰는 답(또는 = 그리고)
        return "expr", main.strip(), "", "근·해를 모두(차례 무관)", note
    approx = re.fullmatch(r"약\s*(" + NUM + r")\s*(" + UNIT + r")?", main.strip())
    if approx:
        return "numpad", approx.group(1), approx.group(2) or "", "어림값(반올림 자리 확인)", note
    several = re.fullmatch(r"([가-힣]{1,4})\([^)]*\)(?:,\s*[가-힣]{1,4}\([^)]*\))+\.?", clean(ans_text))
    if several:
        return "short_all", re.findall(r"([가-힣]{1,4})\(", clean(ans_text)), "", "", ""
    if re.search(r"위에 점|순환\s*마디|마디\s*\d", ans_text):
        return "parent", main, "", "순환소수(점 표기는 부모 확인)", note
    if re.search(r"집에서 정한|정한 곳|정한 제자리", ans_text):
        return "parent", main, "", "집마다 답이 다름", note
    if re.search(r"\((?:아이|자기|본인)(?:의|가)?\s*[^()\s]{0,6}\)|\((?:아이|자기)가 (?:고른|정한|쓴)", ans_text):
        return "parent", main, "", "아이마다 답이 다름(아이의 시각·이름 등)", note
    tail = re.fullmatch(r"(.*=\s*([^=,]+?)),\s+((?:\d{1,3}(?:,\d{3})+|" + NUM + r")\s*" + UNIT + r"?)", main.strip())
    if (tail and number_unit(tail.group(3))[0] is not None
            and number_unit(tail.group(2))[0] == number_unit(tail.group(3))[0]):  # ‘10 × 3.14 = 31.4, 31.4 cm’: 풀이 끝 값을 다시 쓴 답
        note = (tail.group(1) + ("; " + note if note else "")).strip()
        main = tail.group(3)
    t = re.fullmatch(r"(\d{1,2})시(?:\s*(\d{1,2})분|\s*반)?", main.strip())
    if t:
        mm = t.group(2) or ("30" if main.strip().endswith("반") else "00")
        return "time", f"{int(t.group(1))}:{int(mm):02d}", "", "", note
    if main.strip() in (">", "<", "=", "＞", "＜"):
        return "symbol", main.strip().replace("＞", ">").replace("＜", "<"), "", "", note
    n, unit = number_unit(main)
    if n is not None and unit == "t" and (STRAND == "MAT" or not re.search(r"\st$", main.strip())):
        n = None  # 수학의 ‘2t’는 식(매개변수 t), 톤은 ‘3 t’처럼 띄어 쓴다
    if n is not None:
        u = re.match(r"^(?:단위\s*)?(" + UNIT + r")(?:\s*[,;]\s*|$)", note) if not unit and note else None
        if u and not re.fullmatch(r"[가-힣]{1,3}", u.group(1)) or u and re.fullmatch(r"만\s?원|억\s?원|원|개|명|권|살|쪽|번|장|마리|자루|켤레|대|송이|그루|칸|층|kg|g|cm", u.group(1)):
            unit, note = u.group(1), note[u.end():].strip()  # ‘12(만 원, 300 × 4 ÷ 100)’
        return "numpad", n, unit, "", note
    # 분수: ‘5분의 2’, ‘1과 2분의 1’, 여러 개(‘15분의 10, 15분의 9’), 식이면 마지막 값(‘8분의 6 = 4분의 3’)
    segs = [x.strip() for x in re.split(r"\s*=\s*", main)]
    fr = korean_fraction(segs[-1])
    if fr and all(korean_fraction(x) or number_unit(x)[0] for x in segs):
        return "expr", fr, "", "", note + ("; " if note else "") + (main if len(segs) > 1 else "")
    many = [korean_fraction(x) for x in re.split(r",\s*", main)]
    if len(many) > 1 and all(many):
        return "expr_all", many, "", "", note
    m = re.fullmatch(r"(\d+)\s*:\s*(\d+)", main.strip())
    if m:
        return "expr", f"{m.group(1)}:{m.group(2)}", "", "", note
    # 수식·식·좌표·범위(중·고): ‘x = −5’, ‘y = 3x − 1’, ‘(−4, −1)’, ‘6√2’, ‘−1 < x < 1’, ‘x = 2 또는 x = 3’
    mm = main.strip()
    if (len(mm) <= 40 and re.fullmatch(r"(?:[0-9A-Za-zα-ωπ√∛²³⁴⁵⁶⁷⁸⁹⁰¹ⁿˣʸ₀-₉′'±+\-−×÷·=()\[\]{}.,/ ∠°<>≤≥≠∞|^:]|또는)+", mm)
            and re.search(r"[0-9πxyzabn√=<>≤≥(]", mm)
            and not re.fullmatch(r"[A-Za-z][A-Za-z'’ ,.?!]*", mm)
            and not [w for w in re.findall(r"[A-Za-z]{3,}", mm) if w.lower() not in
                     ("log", "sin", "cos", "tan", "lim", "max", "min", "mod", "cm", "mm", "km", "kg", "mol", "kcal", "kwh")]):
        return "expr", mm, "", "식·값(같은 값의 다른 꼴도 맞음)", note
    # 과학의 원소 기호·화학식(Ca, Ag, H₂O, NaCl, CO₂): 대소문자를 구별한다(CA는 틀림)
    if STRAND == "SCI" and re.fullmatch(r"(?:[A-Z][a-z]?[₀-₉0-9⁺⁻²³]*)+", main.strip()):
        return "short_case", main.strip(), "", "원소 기호·화학식(대소문자 구별)", note
    # 대문자 이름 목록(모서리·점·선분: ‘CG, DH, EH, FG’)은 차례와 상관없이 모두
    if re.fullmatch(r"[A-Z]{1,3}′?(?:,\s*[A-Z]{1,3}′?)+", main.strip()):
        return "short_all", [x.strip() for x in main.split(",")], "", "이름 목록(차례 무관)", note
    # 영어: 낱말·짧은 말(세 낱말까지)은 자동, 문장은 부모 판정
    if re.fullmatch(r"[A-Za-z][A-Za-z'’]*(?:\s[A-Za-z'’]+){0,2}[.?!]?", main.strip()):
        return "short", main.strip(), "", "영어(대소문자·끝 부호 무시)", note
    if re.fullmatch(r"[A-Z][A-Za-z'’]*(?:,?\s[A-Za-z0-9'’]+){3,9}[.?!]?", main.strip()):
        return "short", main.strip(), "", "영어 문장(대소문자·끝 부호 무시, 다른 맞는 문장은 accept)", note
    if re.fullmatch(r"[A-Za-z](?:,\s*[A-Za-z])+", main.strip()):
        return "short_all", [x.strip() for x in main.split(",")], "", "", note
    if len(main) <= 8 and " " not in main.strip() and re.fullmatch(r"[가-힣A-Za-z]+", main):
        return "short", main, "", "", note
    # 중·고의 두 낱말 용어(‘국제 연맹’, ‘이산화 탄소’): 띄어쓰기와 상관없이 채점. 문장 끝(~요, ~다)과 ‘A과 B’ 꼴은 뺀다
    if (GRADE >= "G07" and re.fullmatch(r"[가-힣]{1,6} [가-힣]{1,6}", main.strip())
            and not re.search(r"(요|다|까|니다)$", main.strip()) and not re.search(r"[가-힣](과|와) ", main)):
        return "short", main.strip(), "", "용어(띄어쓰기 무시)", note
    if re.fullmatch(r"[가-힣A-Za-z]{1,6}(?:,\s*[가-힣A-Za-z]{1,6})+", main):
        return "short_all", [x.strip() for x in main.split(",")], "", "", note
    return "parent", main, "", "말·글·식으로 답함", note


def find_criterion(notes):
    """노트 정답이 없을 때 예상답·주의에서 맞음 기준 문장을 찾는다."""
    for key in ("예상답", "주의", "막히면"):
        for line in notes.get(key, []) or []:
            for sent in re.split(r"(?<=[.다])\s+", clean(line)):
                if (re.search(r"맞습니다|맞음|정답이 하나가 아니|정답은 하나가 아니|정답이 정해져 있지 않|기준:", sent)
                        or re.search(r"면 됩니다", sent)):  # ‘…면 됩니다’는 기준, ‘…도 됩니다’는 허락이라 기준이 아님
                    return sent
    return None


def sort_answer(raw, n):
    """‘개인정보: ① ③ ④ / 아닌 것: ②’ → {갈래: [문항 번호…]}"""
    text = clean(" / ".join(raw))
    groups = re.findall(rf"([^:/①-⑩]{{1,20}}):\s*((?:[{CIRCLED}][^{CIRCLED}/:]*)+)", text)
    if len(groups) < 2:
        return None
    out, used = {}, []
    for name, body in groups:
        nums = [CIRCLED.index(c) + 1 for c in re.findall(rf"[{CIRCLED}]", body)]
        out[name.strip()] = nums
        used += nums
    return out if sorted(used) == list(range(1, n + 1)) else None


def expand_shared(raw):
    """‘②③ 집의 물건에 따라 다릅니다…’처럼 여러 번호가 한 답을 함께 쓰는 줄을 번호마다 한 줄로 편다."""
    out = []
    for line in raw:
        m = re.match(rf"^\s*([{CIRCLED}]{{2,}})\s+(.*)$", clean(line))  # ‘①②③을 …’(가리키는 말)은 펴지 않는다
        if m:
            out += [f"{c} {m.group(2)}" for c in m.group(1)]
        else:
            out.append(line)
    return out


def problem_items(L, s, key, issues, seen):
    probs = s.get(key) or []
    raw = expand_shared(s.get("notes", {}).get("정답", []))
    out = []
    notes = s.get("notes", {})
    criterion = None
    sorted_ = sort_answer(raw, len(probs)) if raw else None
    lone = re.fullmatch(rf"([{CIRCLED}])(\.\s.*|\.?)", clean(raw[0])) if raw else None
    if sorted_:
        return [{"id": item_id(L["id"], s["id"], f"{s['id']}|sort", seen), "slide": s["id"],
                 "prompt": clean(s.get("text") or s.get("title", "")), "input": "sort",
                 "cards": [render_item(p) for p in probs], "answer": sorted_}]
    if lone and len(probs) > 1 and len(raw) <= 2:
        k = CIRCLED.index(lone.group(1))
        return [{"id": item_id(L["id"], s["id"], f"{s['id']}|pick", seen), "slide": s["id"],
                 "prompt": clean(s.get("text") or s.get("title", "")), "input": "choice",
                 "options": [render_item(p) for p in probs], "answer": k, "note": clean(" ".join(raw))}]
    if not raw:
        criterion = find_criterion(notes)
        if criterion:
            answers = [""] * len(probs)
        else:
            issues.append(("정답·기준 없음", s["id"], f"문항 {len(probs)}개에 노트 정답도 맞음 기준도 없다"))
            answers = [""] * len(probs)
    else:
        answers = split_answers(raw, len(probs))
        if len(probs) > 1 and len(raw) != len(probs) and answers[1:] == [""] * (len(probs) - 1):
            if OPEN.search(" ".join(raw)):
                criterion, answers = clean(" ".join(raw)), [""] * len(probs)
            else:
                issues.append(("정답 짝 불명", s["id"],
                               f"문항 {len(probs)}개, 노트 정답 {len(raw)}줄을 문항별로 나눌 수 없다: {clean(' / '.join(raw))[:120]}"))
    examples = [""] * len(probs)
    exp = notes.get("예상답") or []
    if exp and key != "review":  # 정리 장의 예상답은 말하기 물음의 답이지 복습 문항의 답이 아니다
        ex = split_answers(exp, len(probs))
        lumped = len(probs) > 1 and ex[1:] == [""] * (len(probs) - 1)
        if not lumped:
            examples = ex
    notes_text = " ".join(" ".join(v) if isinstance(v, list) else str(v) for v in s.get("notes", {}).values())
    for k, (p, a) in enumerate(zip(probs, answers)):
        prompt = render_item(p)
        if criterion is not None and not a:
            inp, ans, unit, why, note = "parent", None, "", "열린 답(기준으로 판단)", ""
        else:
            inp, ans, unit, why, note = classify(p, a)
            ask = prompt + " " + clean(str(s.get("text") or s.get("title") or ""))
            if inp == "short" and re.search(r"띄어|붙여 쓰|띄어쓰기", ask):
                inp, why = "short_exact", "띄어쓰기를 묻는 문항(띄어쓰기 그대로 채점)"
        if inp == "short" and isinstance(ans, str) and len(re.findall(r"_{3,}", prompt)) == 1:
            # ‘(play) I ______ badminton yesterday.’: 빈칸에 들어갈 말만 치게 하고, 문장 전체도 받는다
            m = re.fullmatch(r"(.*?)_{3,}(.*)", prompt)
            pre = re.sub(r"^\([^)]*\)\s*", "", re.split(r"(?:[.?!→:]\s)", m.group(1))[-1]).strip()
            post = re.sub(r"\s*\(.*$", "", m.group(2)).strip().rstrip(".?!").strip()
            fill, full = ans.rstrip("."), ans.rstrip(".")
            if pre and fill.lower().startswith(pre.lower() + " "):
                fill = fill[len(pre):].strip()
            if post and re.match(r"[A-Za-z]", post) and fill.lower().endswith(" " + post.lower()):
                fill = fill[: -len(post)].strip()
            if fill and fill != full and (not pre or full.lower().startswith(pre.lower())):
                ans = fill
                note = (note + "; " if note else "") + f"‘{full}’도 맞음"
        rec = {"id": item_id(L["id"], s["id"], f"{s['id']}|{prompt}", seen), "slide": s["id"], "n": k + 1,
               "prompt": prompt, "input": inp, "answer": ans}
        mode_flags(rec, prompt + " " + str(s.get("title", "")) + " " + str(s.get("text", "")))
        inp = rec["input"]
        if inp == "parent" and a:
            rec["answer"], note = clean(a).rstrip("."), ""  # 부모가 보는 답은 노트 정답 줄 그대로(괄호 속 까닭까지)
        elif inp == "short" and isinstance(rec["answer"], str):
            rec["answer"] = rec["answer"].rstrip(".")
        if key in ("problems", "review") and not s.get("_embedded"):
            rec["problem_index"] = k  # 화면(screen)의 problems/review k번째: 그림·식이 거기 있다
        acc = accepted(note) if inp in ("short", "short_case", "short_exact", "numpad", "expr") else []
        if inp == "short":  # 예·아니요 답은 같은 뜻의 말을 함께 받는다
            for group in (("아니다", "아니요", "아니오", "아니에요", "아님", "틀렸다", "틀렸습니다", "틀려요", "틀렸어요", "바르지 않다", "바르지 않습니다"),
                          ("그렇다", "예", "네", "맞다", "맞아요", "그래요", "맞습니다", "맞았다", "바르다", "바릅니다")):
                if str(ans).rstrip(".") in group:
                    acc = acc + [g for g in group if g != str(ans).rstrip(".") and g not in acc]
        if inp == "expr":
            acc = [korean_fraction(a) or a for a in acc]
        acc = [x.rstrip(".") if inp == "short" else x for x in acc]
        acc = [x for i, x in enumerate(acc) if x and x != rec["answer"] and x not in acc[:i]]
        if acc:
            rec["accept"] = acc
        if unit:
            rec["unit"] = unit
        if note:
            rec["note"] = note
        if why and "why" not in rec:
            rec["why"] = why
        if criterion:
            rec["criterion"] = criterion
        if examples[k] and inp == "parent":
            rec["examples"] = examples[k]
        if inp == "parent" and not (ans or criterion or rec.get("examples") or note):
            issues.append(("부모 판정 근거 없음", s["id"], f"{CIRCLED[k]} {prompt[:60]}: 정답·기준·예시가 없다"))
        if "figure" in p:
            rec["figure"] = True
        mine = [m for m in misconception_refs(notes_text) if re.search(rf"[{CIRCLED[k]}][^{CIRCLED}]*?{m}", notes_text)]
        if mine:
            rec["misconceptions"] = mine
        # 검산
        eq = p.get("eq")
        if isinstance(eq, dict):
            eq = eq.get("items")
        if isinstance(eq, list):
            v = eq_value(eq)
            if v is not None:
                rec["checked"] = True
                if inp == "numpad" and v != ans:
                    issues.append(("정답 검산 불일치", s["id"], f"{CIRCLED[k]} {prompt} → 계산 {v}, 노트 정답 {ans}"))
            elif inp == "numpad":
                rec["checked"] = False
        out.append(rec)
    return out


def choice_item(L, s, issues, seen):
    opts = [render_item(o) for o in s.get("options", [])]
    raw = clean(" ".join(s.get("notes", {}).get("정답", [])))
    prompt = clean(s.get("question") or s.get("text") or s.get("title", ""))
    title = clean(s.get("title", ""))
    if re.match(r"^(어떻게 알았|왜 그렇게|까닭|왜요|어떻게 생각)", prompt) and title.endswith("?") and title not in prompt:
        prompt = f"{title} {prompt}"  # ‘어떻게 알았는지 말해 보세요.’는 뒷물음: 장 제목이 본 물음
    rec = {"id": item_id(L["id"], s["id"], f"{s['id']}|{s.get('question', '')}|{'|'.join(opts)}", seen),
           "slide": s["id"], "prompt": prompt,
           "input": "choice", "options": opts, "answer": None}
    lab = LABELS[:len(opts)]
    order = re.match(rf"^([{lab}])(?:\s*→\s*([{lab}]))+", raw)
    match = [(a.strip(), b) for a, b in re.findall(rf"(?:^|[).,→]\s*)([^→().,]{{1,24}}?)\s*→\s*([{lab}])(?![가-힣])", raw)]
    match = [(re.split(r"\s*→\s*", a)[-1], b) for a, b in match]
    multi = re.match(rf"^([{lab}])(?:\([^)]*\))?(?:\s*(?:,|와|과)\s*([{lab}])(?:\([^)]*\))?)+(?:가|이|는|을|를)?[.\s(]", raw + " ")
    each = re.findall(rf"(?:^|\s)([{lab}])\s+({NUM})(?=[\s(,.]|$)", raw)
    more = re.search(rf"([{lab}])(?:\([^)]*\))?가 더 (크|큽|많|작|적|길|짧|무겁|가볍)", raw)
    first = re.match(rf"^([{lab}])(?:[(\s.,]|$)", raw) or re.match(rf"^([{lab}])(?:가|이)\s*(?:맞|옳|알맞|바르)", raw)
    latin = re.match(r"^([A-F]|[ⓐ-ⓕ])(?:[(\s.,]|$)", raw)  # 보기 이름이 A·B·C 또는 ⓐ·ⓑ·ⓒ인 장
    if latin and not first:
        k = "ABCDEF".index(latin.group(1)) if latin.group(1) in "ABCDEF" else "ⓐⓑⓒⓓⓔⓕ".index(latin.group(1))
        if k < len(opts):
            first = None
            rec["answer"] = k
    if rec["answer"] is not None:
        pass
    elif re.match(r"^(무엇을|어느 것을|아무것이나|아무거나)\s*골라도|^.{0,15}골라도 맞", raw):
        rec.update(input="parent", why="무엇을 골라도 맞음(까닭을 봄)")
    elif len(each) >= 2 and len({x for x, _ in each}) == len(each):
        rec.update(input="numpad_each", answer={x: v for x, v in each})
        if more:
            rec["then_choice"] = LABELS.index(more.group(1))  # 읽은 뒤 더 큰(많은) 쪽 고르기
    elif order and len(re.findall("→", order.group(0))) >= 2:
        seq = re.findall(rf"[{lab}]", order.group(0))
        rec.update(input="order", answer=[LABELS.index(x) for x in seq])
        if re.search(r"다른 (차례|순서)", raw):
            rec["other_ok_with_reason"] = True  # 다른 차례도 까닭이 맞으면 맞음 → 부모 판정으로 넘김
    elif len(match) >= 2 and not raw.startswith(tuple(lab)):
        rec.update(input="match", answer=[{"prompt": a, "option": LABELS.index(b)} for a, b in match])
    elif len(match) == 1 and raw.startswith(match[0][0]):
        rec["answer"] = LABELS.index(match[0][1])
    elif multi:
        rec.update(input="multi", answer=[LABELS.index(x) for x in re.findall(rf"[{lab}]", multi.group(0))])
    elif more:
        rec["answer"] = LABELS.index(more.group(1))
    elif first:
        rec["answer"] = LABELS.index(first.group(1))
    else:
        hits = [i for i, o in enumerate(opts) if o and o in raw]
        if len(hits) == 1:
            rec["answer"] = hits[0]
        elif OPEN.search(raw) or re.match(rf"^[{lab}](와|과|는|도) ", raw):
            rec.update(input="parent", why="고른 까닭을 보는 열린 고르기")
        else:
            issues.append(("고르기 정답 불명", s["id"], f"보기 {len(opts)}개, 노트 정답에서 고른 보기를 찾지 못함: {raw[:100]}"))
            rec["why"] = "정답 보기 불명"
    mode_flags(rec, rec["prompt"] + " " + clean(str(s.get("title", ""))))
    if raw:
        rec["note"] = raw
        if rec["input"] == "parent" and rec.get("answer") is None:
            rec["answer"] = raw
    return rec


def side_names(side):
    t = clean(side.get("title", ""))
    names = [x for x in re.split(r"[:：]|\s{2,}", t) if x.strip()]
    return [x.strip() for x in names] or [""]


def compare_item(L, s, issues, seen):
    left, right = side_names(s.get("left", {})), side_names(s.get("right", {}))
    raw = clean(" ".join(s.get("notes", {}).get("정답", [])))
    first = re.split(r"(?<=[.다])\s", raw)[0]
    q = clean(s.get("question") or s.get("title", ""))
    rec = {"id": item_id(L["id"], s["id"], f"{s['id']}|{left}|{right}", seen), "slide": s["id"],
           "prompt": q, "input": "choice", "options": [" ".join(left), " ".join(right)], "answer": None}

    def mentions(names):
        return any(n and re.search(rf"(^|[^가-힣]){re.escape(n)}", first) for n in names)
    judged = re.search(r"맞|옳|알맞|더 |바르|잘|좋", first)
    side_word = re.search(r"(왼쪽|오른쪽)(처럼|이|가|의 말이|은|는)?\s?\S*\s?(맞|바른|옳)", raw) or re.search(r"(왼쪽|오른쪽)처럼", raw)
    if re.search(r"공감|마음에 드|더 좋아|하고 싶|되고 싶", q):
        rec.update(input="parent", why="생각·마음을 고르는 물음(정답보다 까닭을 봄)")
    elif not re.search(r"누가|누구|어느|맞|바르|옳|좋", q):
        rec.update(input="parent", why="말로 설명하는 견주기(고르는 물음이 아님)")
    elif re.match(r"^(왼쪽|오른쪽)", first) and not ("왼쪽" in first and "오른쪽" in first):
        rec["answer"] = 0 if first.startswith("왼쪽") else 1
    elif mentions(left) != mentions(right) and judged:
        rec["answer"] = 0 if mentions(left) else 1
    elif s.get("claim") and re.search(r"바르게|맞(나요|을까|는지)|맞는지", q) and (re.match(r"^(바르지 않|틀렸|아니|.{0,12}(틀렸|바르지 않))", first) or re.search(r"않았|않습|틀렸|틀립|아닙", first)):
        rec.update(options=["맞아요", "아니에요"], answer=1)
    elif s.get("claim") and re.search(r"바르게|맞(나요|을까|는지)|맞는지", q) and re.match(r"^(바르게|맞습니다|.{0,12}(맞습니다|바르게))", first):
        rec.update(options=["맞아요", "아니에요"], answer=0)
    elif OPEN.search(first):
        rec.update(input="parent", why="판정 없는 견주기(까닭을 봄)")
    elif side_word and not mentions(left) and not mentions(right):
        rec["answer"] = 0 if side_word.group(1) == "왼쪽" else 1
    elif mentions(left) != mentions(right):
        rec["answer"] = 0 if mentions(left) else 1
        if not judged and len(first) > 3:
            rec["why"] = "첫 문장에 판정 낱말 없음(확인)"
    elif mentions(left) and mentions(right) or not raw:
        rec.update(input="parent", why="개념 견주기(양쪽을 설명)")
    else:
        issues.append(("견주기 정답 불명", s["id"], f"‘{' '.join(left)}’·‘{' '.join(right)}’ 중 맞는 쪽을 찾지 못함: {first[:90]}"))
        rec["why"] = "정답 쪽 불명"
    if raw:
        rec["note"] = raw
        if rec["input"] == "parent":
            rec["answer"] = raw  # 부모가 볼 판정(노트 정답 그대로)
    exp = s.get("notes", {}).get("예상답")
    if exp:
        rec["examples"] = clean(" ".join(exp))
    mode_flags(rec, q + " " + clean(str(s.get("title", ""))))
    rec["say_why"] = True  # 고른 뒤 까닭을 말하게 한다(부모 판정)
    return rec


def embedded_items(L, s, issues, seen):
    """문항 목록이 없는 연습·확인 장(물음이 그림·표·지문·카드 안에 있음): 노트 정답의 번호로 문항을 만든다.
    앱은 장 화면(screen)을 그대로 보이고 번호마다 답 칸을 둔다."""
    n = wrong_line.item_count(s)
    key = s.get("key")
    ask = s.get("question") or (key.get("title") if isinstance(key, dict) else key) or s.get("text") or s.get("title", "")
    figs = s.get("figures") or []
    ask = clean(str(ask))
    parts = [x.strip() for x in re.split(rf"[{CIRCLED}]+", ask) if x.strip()]
    per_item = len(parts) == n and n > 1 and re.match(rf"^[{CIRCLED}]", ask)
    one = lambda t: re.match(rf"^[{CIRCLED}](?!\s*~)", t)  # ‘③ 쌓기나무가…’, ‘④는 도전!’: 한 문항만 가리킴
    if not per_item and n > 1 and one(ask):
        for alt_ask in (clean(str(s.get("text") or "")), clean(str(s.get("title") or ""))):
            if alt_ask and not one(alt_ask):
                ask = alt_ask
                break
    probs = []
    for k in range(n):
        alt = figs[k].get("alt") if len(figs) == n and isinstance(figs[k], dict) else None
        if per_item:
            text = f"{CIRCLED[k]} {parts[k]}"
        elif n > 1:
            text = f"{ask} ({CIRCLED[k]})"  # 화면의 ①, ② …에 답한다
        else:
            text = ask
        probs.append({"text": text + (f" ({alt})" if alt else "")})
    items = problem_items(L, dict(s, problems=probs, _embedded=True), "problems", issues, seen)
    for k, it in enumerate(items):
        it["embedded"] = True  # 물음이 화면 안에 있음
        if len(figs) == n:
            it["figure_index"] = k
    return items


def typed_value(it, v):
    """오답 값을 그 문항의 입력 칸에서 나올 꼴로 바꾼다. 칠 수 없는 말이면 None."""
    v = str(v).strip()
    inp = it.get("input")
    if inp == "numpad":
        n, _ = number_unit(v)
        if n is None:
            n, _ = number_unit(re.sub(r"\s*\(.*\)$", "", v))
        return n
    if inp in ("expr", "expr_all"):
        return korean_fraction(v) or v
    if inp == "time":
        t = re.fullmatch(r"(\d{1,2})시(?:\s*(\d{1,2})분|\s*반)?", v)
        if not t:
            return None
        mm = int(t.group(2) or (30 if v.endswith("반") else 0))
        return f"{int(t.group(1))}:{mm:02d}" if mm < 60 and int(t.group(1)) <= 12 else None
    return v


def attach_wrong(s, items, issues):
    """노트 ‘틀리면’ 줄을 문항의 wrong 목록으로 붙인다."""
    for line in (s.get("notes") or {}).get("틀리면", []) or []:
        w = wrong_line.parse(line)
        if w is None:
            issues.append(("틀리면 꼴 오류", s["id"], line[:80]))
            continue
        entry = {k: w[k] for k in ("reason", "feedback", "misconceptions", "goto") if w.get(k)}
        if "n" in w:
            target = [it for it in items if it.get("n") == w["n"]]
            sort = next((it for it in items if it["input"] == "sort"), None)
            if not target and sort:  # 분류 문항: n번 카드를 잘못 넣은 경우
                sort.setdefault("wrong", []).append({"card": w["n"], "values": w["values"], **entry})
                continue
            if not target:
                issues.append(("틀리면 대상 없음", s["id"], f"{CIRCLED[w['n'] - 1]}번 문항이 앱 데이터에 없다"))
                continue
            it = target[0]
            typed, spoken = [], []
            for v in w["values"]:
                t = typed_value(it, v)
                (typed if t is not None else spoken).append(t if t is not None else v)
            for v in typed:
                norm = lambda x: (korean_fraction(str(x)) or number_unit(str(x))[0] or str(x)).replace(" ", "")
                if it.get("answer") is not None and norm(it["answer"]) == norm(v):
                    issues.append(("오답이 정답과 같음", s["id"], f"{CIRCLED[w['n'] - 1]} ‘{v}’"))
            e = {"values": typed, **entry} if typed else dict(entry)
            if spoken:
                e["spoken"] = spoken  # 입력 칸으로는 칠 수 없는 말(부모가 들을 때 씀)
            it.setdefault("wrong", []).append(e)
        elif "seq" in w:
            it = next((i for i in items if i["input"] == "order"), None)
            if it is None:
                issues.append(("틀리면 대상 없음", s["id"], "차례 오답인데 차례 맞추기 문항이 없다"))
                continue
            seq = ["가나다라마바".index(x) for x in w["seq"]]
            if seq == it.get("answer"):
                issues.append(("오답이 정답과 같음", s["id"], f"차례 {' → '.join(w['seq'])}가 정답이다"))
            it.setdefault("wrong", []).append({"order": seq, **entry})
        elif "omit" in w:
            it = next((i for i in items if i["input"] == "multi"), None)
            if it is None or w["omit"] not in "가나다라마바":
                issues.append(("틀리면 대상 없음", s["id"], f"‘{w['omit']}를 빠뜨리면’ — 모두 고르기 문항이 없다"))
                continue
            idx = "가나다라마바".index(w["omit"])
            if idx not in (it.get("answer") or []):
                issues.append(("틀리면 대상 없음", s["id"], f"‘{w['omit']}’는 정답 보기가 아니다"))
            it.setdefault("wrong", []).append({"missing": idx, **entry})
        elif "say" in w:
            it = next((i for i in items if i.get("options")), None)
            yes = re.match(r"^(맞|네|예|응|바르)", w["say"])
            if it is None or it.get("options") != ["맞아요", "아니에요"]:
                issues.append(("틀리면 대상 없음", s["id"], f"‘{w['say']}’라고 하면 — 이 장은 맞아요/아니에요 물음이 아니다"))
                continue
            idx = 0 if yes else 1
            if it.get("answer") == idx:
                issues.append(("오답이 정답과 같음", s["id"], f"‘{w['say']}’가 정답이다"))
            it.setdefault("wrong", []).append({"option": idx, **entry})
        else:
            it = next((i for i in items if i.get("options")), None)
            if it is None:
                issues.append(("틀리면 대상 없음", s["id"], f"‘{w['pick']}를 고르면’ — 고르는 문항이 없다"))
                continue
            opts = it["options"]
            for lab in ("가나다라마바", "ABCDEF", "ⓐⓑⓒⓓⓔⓕ"):
                if w["pick"] in lab[:len(opts)]:
                    w["pick"] = "가나다라마바"[lab.index(w["pick"])]
            idx = "가나다라마바".index(w["pick"]) if w["pick"] in "가나다라마바"[:len(opts)] else next(
                (i for i, o in enumerate(opts) if w["pick"] == o or w["pick"] in o.split()), None)
            if idx is None:
                issues.append(("틀리면 대상 없음", s["id"], f"‘{w['pick']}’이 보기에 없다"))
                continue
            if it.get("answer") == idx:
                issues.append(("오답이 정답과 같음", s["id"], f"‘{w['pick']}를 고르면’인데 그것이 정답이다"))
            it.setdefault("wrong", []).append({"option": idx, **entry})


# ── 차시 ────────────────────────────────────────────────────

SCREEN_SKIP = ("notes", "purpose", "section")


def export(L):
    global GRADE, STRAND
    GRADE, STRAND = L["grade"], L["strand"]
    issues, seen = [], Counter()
    slides = []
    for s in L["slides"]:
        kind = s.get("kind")
        rec = {"id": s["id"], "kind": kind, "role": s.get("role"), "title": clean(s.get("title", "")),
               "objectives": s.get("objectives", []),
               "screen": {k: v for k, v in s.items() if k not in SCREEN_SKIP + ("id", "kind", "role", "title", "objectives")}}
        if s.get("teacher_only"):
            rec["parent_only"] = True
        items = []
        if kind in ("practice", "check"):
            items = problem_items(L, s, "problems", issues, seen)
        elif kind == "summary" and s.get("review"):
            items = problem_items(L, s, "review", issues, seen)
            for it in items:
                it["review_next"] = True
        elif kind == "choice":
            items = [choice_item(L, s, issues, seen)]
        elif kind == "compare":
            items = [compare_item(L, s, issues, seen)]
        elif s.get("role") in ("practice", "check") and kind != "activity":
            items = embedded_items(L, s, issues, seen)
        elif kind == "activity":
            rec["done_button"] = True  # 실물·몸 활동은 ‘다 했어요’ + 부모 기록
        attach_wrong(s, items, issues)
        if items:
            rec["items"] = items
        rec["parent_notes"] = s.get("notes", {})
        slides.append(rec)
    known = {m["id"] for m in L.get("misconceptions", [])}
    for s in slides:
        for it in s.get("items", []):
            for m in it.get("misconceptions", []):
                if m not in known:
                    issues.append(("없는 오개념", s["id"], f"{it['id']}가 {m}을 가리키는데 원본 misconceptions에 없다"))
    data = {"format_version": FORMAT_VERSION, "id": L["id"], "title": L["title"], "grade": L["grade"],
            "subject": L["strand_label"], "unit": L["unit_folder"], "sequence": L["sequence"],
            "minutes": L["minutes"], "split_default": L.get("split_default", False),
            "break_after": L.get("break_after"),
            "objectives": [{"id": o["id"], "text": o["text"]} for o in L["objectives"]],
            "misconceptions": [{"id": m["id"], "text": m["text"]} for m in L.get("misconceptions", [])],
            "prerequisites": [p["lesson"] for p in L["prerequisites"] if p.get("lesson")],
            "slides": slides, "worksheet_paper": True}
    return data, issues


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("grade", help="G01 … G12")
    ap.add_argument("--ids", nargs="*")
    ap.add_argument("--out", default=str(ROOT / "build" / "app"))
    a = ap.parse_args()
    paths = sorted((ROOT / "lessons").glob(f"{a.grade}_*/**/KR22-*.json"))
    out = Path(a.out) / a.grade
    out.mkdir(parents=True, exist_ok=True)
    all_issues, stats = [], Counter()
    for p in paths:
        L = json.loads(p.read_text(encoding="utf-8"))
        if a.ids and L["id"] not in a.ids:
            continue
        data, issues = export(L)
        (out / f"{L['id']}.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        stats["차시"] += 1
        for s in data["slides"]:
            for it in s.get("items", []):
                stats["문항"] += 1
                stats[f"입력 {it['input']}"] += 1
                if it.get("checked"):
                    stats["식 검산함"] += 1
                if it.get("misconceptions"):
                    stats["오개념 연결"] += 1
                if it.get("wrong"):
                    stats["오답 데이터 있는 문항"] += 1
                if it["input"] not in ("parent", "none"):
                    stats["자동 채점 문항"] += 1
        all_issues += [(L["id"], *i) for i in issues]
    kinds = Counter(i[1] for i in all_issues)
    lines = [f"# 앱 데이터 추출 보고서 — {a.grade}", "",
             f"형식 {FORMAT_VERSION}판(임시). 원본을 고친 뒤 다시 돌린다.", "",
             "## 통계", "", "| 항목 | 수 |", "|---|---|"]
    lines += [f"| {k} | {v} |" for k, v in sorted(stats.items())]
    lines += ["", "## 고칠 곳", "", "| 종류 | 수 |", "|---|---|"] + [f"| {k} | {v} |" for k, v in kinds.most_common()]
    for k, _ in kinds.most_common():
        lines += ["", f"### {k}", ""]
        lines += [f"- `{lid}` {sid}: {msg}" for lid, kk, sid, msg in all_issues if kk == k]
    (out / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{out}: {stats['차시']}차시, 문항 {stats['문항']}개, 고칠 곳 {len(all_issues)}건")
    for k, v in kinds.most_common():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
