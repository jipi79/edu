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
LABELS = "가나다라마바"
OPEN = re.compile(r"또는|예:|예\)|예를 들어|가운데|등\b|처럼|자유|여러|다양|모두 맞|어느 것이든|아무|골라도|정해진 답|정답이 하나가 아닙|정답은 하나가 아닙|정답이 정해져 있지 않|정답은 따로 없|까닭을 봅니다|어떤 낱말이든|하면 맞습니다|면 맞음|하면 됩니다")
NUM = r"−?\d+(?:\.\d+)?"


# ── 정답 풀기 ──────────────────────────────────────────────

def main_answer(a):
    """‘6 (1 + 2 = 3, …)’ → (‘6’, ‘1 + 2 = 3, …’). 첫 괄호나 첫 문장 앞까지가 답이다."""
    a = clean(a)
    m = re.match(r"^(.*?)\s*\((.*)\)\s*\.?$", a)
    if m and m.group(1):
        return m.group(1).strip(), m.group(2).strip()
    m = re.match(r"^(.*?[^0-9])\.\s+(.*)$", a)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return a.rstrip("."), ""


def number_unit(s):
    m = re.fullmatch(rf"({NUM})\s*([가-힣]{{1,3}})?", s.strip())
    return (m.group(1), m.group(2) or "") if m else (None, None)


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


def classify(prob, ans_text):
    """입력 종류와 정답. (input, answer, unit, why)"""
    main, note = main_answer(ans_text)
    if not main:
        return "parent", None, "", "정답 없음", note
    if OPEN.search(ans_text):
        return "parent", main, "", "열린 답(예·또는·가운데)", note
    n, unit = number_unit(main)
    if n is not None:
        return "numpad", n, unit, "", note
    if len(main) <= 8 and " " not in main.strip() and re.fullmatch(r"[가-힣A-Za-z]+", main):
        return "short", main, "", "", note
    return "parent", main, "", "말·글·식으로 답함", note


def find_criterion(notes):
    """노트 정답이 없을 때 예상답·주의에서 맞음 기준 문장을 찾는다."""
    for key in ("예상답", "주의", "막히면"):
        for line in notes.get(key, []) or []:
            for sent in re.split(r"(?<=[.다])\s+", clean(line)):
                if re.search(r"맞습니다|맞음|됩니다|정답이 하나가 아닙|정답은 하나가 아닙|정답이 정해져 있지 않|기준:", sent):
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


def problem_items(L, s, key, issues, seen):
    probs = s.get(key) or []
    raw = s.get("notes", {}).get("정답", [])
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
    examples = split_answers(notes.get("예상답", []), len(probs)) if notes.get("예상답") else [""] * len(probs)
    notes_text = " ".join(" ".join(v) if isinstance(v, list) else str(v) for v in s.get("notes", {}).values())
    for k, (p, a) in enumerate(zip(probs, answers)):
        prompt = render_item(p)
        if criterion is not None and not a:
            inp, ans, unit, why, note = "parent", None, "", "열린 답(기준으로 판단)", ""
        else:
            inp, ans, unit, why, note = classify(p, a)
        rec = {"id": item_id(L["id"], s["id"], f"{s['id']}|{prompt}", seen), "slide": s["id"], "n": k + 1,
               "prompt": prompt, "input": inp, "answer": ans}
        if unit:
            rec["unit"] = unit
        if note:
            rec["note"] = note
        if why:
            rec["why"] = why
        if criterion:
            rec["criterion"] = criterion
        if examples[k] and inp == "parent":
            rec["examples"] = examples[k]
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
    rec = {"id": item_id(L["id"], s["id"], f"{s['id']}|{s.get('question', '')}|{'|'.join(opts)}", seen),
           "slide": s["id"], "prompt": clean(s.get("question") or s.get("text") or s.get("title", "")),
           "input": "choice", "options": opts, "answer": None}
    lab = LABELS[:len(opts)]
    order = re.match(rf"^([{lab}])(?:\s*→\s*([{lab}]))+", raw)
    match = re.findall(rf"(\S+)\s*→\s*([{lab}])(?![가-힣])", raw)
    multi = re.match(rf"^([{lab}])(?:\([^)]*\))?(?:\s*,\s*([{lab}])(?:\([^)]*\))?)+[.\s(]", raw + " ")
    each = re.findall(rf"(?:^|\s)([{lab}])\s+({NUM})(?=[\s(,.]|$)", raw)
    more = re.search(rf"([{lab}])(?:\([^)]*\))?가 더 (크|많|작|적|길|짧|무겁|가볍)", raw)
    first = re.match(rf"^([{lab}])(?:[(\s.,]|$)", raw)
    if len(each) >= 2 and len({x for x, _ in each}) == len(each):
        rec.update(input="numpad_each", answer={x: v for x, v in each})
        if more:
            rec["then_choice"] = LABELS.index(more.group(1))  # 읽은 뒤 더 큰(많은) 쪽 고르기
    elif order and len(re.findall("→", order.group(0))) >= 2:
        seq = re.findall(rf"[{lab}]", order.group(0))
        rec.update(input="order", answer=[LABELS.index(x) for x in seq])
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
    if raw:
        rec["note"] = raw
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
    if not re.search(r"누가|누구|어느|맞|바르|옳|좋", q):
        rec.update(input="parent", why="말로 설명하는 견주기(고르는 물음이 아님)")
    elif re.match(r"^(왼쪽|오른쪽)", first):
        rec["answer"] = 0 if first.startswith("왼쪽") else 1
    elif s.get("claim") and re.search(r"바르게|맞(나요|을까|는지)|맞는지", q) and re.match(r"^(바르지 않|틀렸|아니|.{0,12}(틀렸|바르지 않))", first):
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
    rec["say_why"] = True  # 고른 뒤 까닭을 말하게 한다(부모 판정)
    return rec


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
            for v in w["values"]:
                if it.get("answer") is not None and str(it["answer"]).replace(" ", "") == v.replace(" ", ""):
                    issues.append(("오답이 정답과 같음", s["id"], f"{CIRCLED[w['n'] - 1]} ‘{v}’"))
            it.setdefault("wrong", []).append({"values": w["values"], **entry})
        else:
            it = next((i for i in items if i.get("options")), None)
            if it is None:
                issues.append(("틀리면 대상 없음", s["id"], f"‘{w['pick']}를 고르면’ — 고르는 문항이 없다"))
                continue
            opts = it["options"]
            idx = "가나다라마바".index(w["pick"]) if w["pick"] in "가나다라마바"[:len(opts)] else next(
                (i for i, o in enumerate(opts) if w["pick"] in o.split()), None)
            if idx is None:
                issues.append(("틀리면 대상 없음", s["id"], f"‘{w['pick']}’이 보기에 없다"))
                continue
            if it.get("answer") == idx:
                issues.append(("오답이 정답과 같음", s["id"], f"‘{w['pick']}를 고르면’인데 그것이 정답이다"))
            it.setdefault("wrong", []).append({"option": idx, **entry})


# ── 차시 ────────────────────────────────────────────────────

SCREEN_SKIP = ("notes", "purpose", "section")


def export(L):
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
