"""수업 원본(JSON)을 제작 전에 검사한다.

  python3 .claude/skills/education-ppt/scripts/check_lesson.py <lesson.json> [...]

검사 항목
- 스키마(필수 필드, ID 형식), 남은 TODO
- 계획(plans/elementary/plan.json)과의 일치: 제목·폴더·순서·파일 이름·교육과정 연결·선수 차시
- 슬라이드 ID 중복, 모든 장의 제목과 발표자 노트(말하기), 연습·확인 장의 정답 또는 예상 답
- 목표마다 설명(teach)·연습(practice)·확인(check) 장이 있는지, 학생용에도 확인 장이 남는지
- 정답이 학생에게 보이는 장에 새지 않는지(정답 장은 teacher_only)
- 교육과정 연결: 학년 항목·단원 ID가 curriculum/에 있는지, 확인되지 않은 성취기준 코드를 적지 않았는지
- 계산 가능한 정답(checks)을 분수 계산으로 다시 검산. 수학 설명형 차시는 3개 이상
- 그림과 표기의 일치: 분수 표기가 붙은 막대의 색칠 비율, 좌표 블록의 점선 기준선 위치
- 좌표 블록(blocks)이 슬라이드 안전 영역 안에 있는지
"""
import json
import re
import sys
from fractions import Fraction
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[4]
SCHEMA = Path(__file__).resolve().parents[1] / "schemas" / "lesson.schema.json"
SAFE_RIGHT, SAFE_BOTTOM = 12.75, 6.9
ANSWER_LEAK = re.compile(r"정답\s*[:：]")


def frac(text):
    """'3/5', 대분수 '2 3/5', 자연수 '4' 를 분수로 읽는다."""
    m = re.fullmatch(r"\s*(\d+)\s+(\d+)/(\d+)\s*", str(text))
    if m:
        return int(m.group(1)) + Fraction(int(m.group(2)), int(m.group(3)))
    if "/" not in str(text):
        return Fraction(int(str(text).strip()))
    n, d = str(text).split("/")
    return Fraction(int(n), int(d))


def bar_value(b):
    if b["type"] == "grid":
        return Fraction(len(b.get("shaded", [])), b["rows"] * b["cols"])
    if "widths" in b:
        return None  # 똑같이 나누지 않은 막대는 분수가 아니다
    return Fraction(len(b.get("shaded", [])), b["parts"])


def shaded_count(spec):
    return spec if isinstance(spec, int) else len(spec or [])


def shaded_end(b):
    """왼쪽부터 이어서 색칠한 막대의 색칠 끝 x좌표. 이어지지 않으면 None."""
    shaded = sorted(b.get("shaded", []))
    if b["type"] != "bar" or not shaded or shaded != list(range(len(shaded))):
        return None
    widths = b.get("widths") or [1 / b["parts"]] * b["parts"]
    return b["x"] + b["w"] * sum(widths[: len(shaded)])


def exact(expr):
    """숫자·소수·분수와 + - × ÷ ( ) 로 된 식을 분수로 정확히 계산한다."""
    py = re.sub(r"\d+(?:\.\d+)?", lambda m: f"F('{m.group()}')", expr.replace("×", "*").replace("÷", "/").replace("−", "-"))
    return eval(py, {"__builtins__": {}}, {"F": Fraction})


def figure_count(f):
    """점 배열·십 칸·격자·막대·원 그림이 나타내는 개수(색칠·점의 수). 그림이 아니면 None."""
    kind = f.get("type")
    if kind == "array":
        return f.get("count", f["rows"] * f["cols"])
    if kind == "tenframe":
        return f["count"]
    if kind in ("grid", "pie", "bar"):
        return shaded_count(f.get("shaded"))
    if kind == "blocks10":
        return 100 * f.get("hundreds", 0) + 10 * f.get("tens", 0) + f.get("ones", 0)
    return None


def walk(node):
    """notes를 뺀 장 안의 모든 dict를 돌려준다(그림 찾기용)."""
    if isinstance(node, dict):
        yield node
        for k, v in node.items():
            if k != "notes":
                yield from walk(v)
    elif isinstance(node, list):
        for v in node:
            yield from walk(v)


def check(path):
    errors, notes = [], []
    raw = Path(path).read_text(encoding="utf-8")
    lesson = json.loads(raw)
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    for e in jsonschema.Draft202012Validator(schema).iter_errors(lesson):
        errors.append(f"스키마: {'/'.join(map(str, e.path))}: {e.message[:160]}")
    if "TODO" in raw:
        errors.append("TODO가 남아 있다")
    if errors:
        return errors, notes

    # 계획과의 일치
    plan_file = ROOT / "plans" / "elementary" / "plan.json"
    plan = {L["id"]: L for L in json.loads(plan_file.read_text(encoding="utf-8"))} if plan_file.exists() else {}
    if lesson["id"] in plan:
        P = plan[lesson["id"]]
        pairs = [("title", "title"), ("grade", "grade"), ("strand", "strand"), ("unit_folder", "folder"),
                 ("sequence", "sequence"), ("file_stem", "file_stem"), ("band", "band")]
        for mine, theirs in pairs:
            if lesson[mine] != P[theirs]:
                errors.append(f"계획과 다름: {mine}={lesson[mine]!r} (계획 {P[theirs]!r})")
        if lesson["curriculum"]["grade_items"] != [P["grade_item"]] or lesson["curriculum"]["units"] != P["units"]:
            errors.append("계획과 다름: 교육과정 연결(grade_items/units)")
        pre = [p.get("lesson") for p in lesson["prerequisites"] if p.get("lesson")]
        if sorted(pre) != sorted(P["pre"]):
            errors.append(f"계획과 다름: 선수 차시 {pre} (계획 {P['pre']})")
        if Path(path).resolve() != (ROOT / P["source"]).resolve():
            errors.append(f"원본 위치가 계획과 다르다: {P['source']}")
    elif lesson["grade"] <= "G06":
        notes.append("계획에 없는 차시다")

    slides = lesson["slides"]
    ids = [s["id"] for s in slides]
    for dup in {i for i in ids if ids.count(i) > 1}:
        errors.append(f"슬라이드 ID 중복: {dup}")

    # 목표 연결
    objective_ids = {o["id"] for o in lesson["objectives"]}
    for s in slides:
        for o in s["objectives"]:
            if o not in objective_ids:
                errors.append(f"{s['id']}: 없는 목표 {o}")
    for o in sorted(objective_ids):
        roles = {s["role"] for s in slides if o in s["objectives"]}
        for need in ("teach", "practice", "check"):
            if need not in roles:
                errors.append(f"목표 {o}: '{need}' 역할의 장이 없다")
        if not any(o in s["objectives"] and s["role"] == "check" and not s.get("teacher_only") for s in slides):
            errors.append(f"목표 {o}: 학생용에 남는 확인 장이 없다")

    # 정답의 위치
    for s in slides:
        if s.get("teacher_only") and s["role"] != "feedback":
            errors.append(f"{s['id']}: 교사 전용 장은 정답·피드백(feedback) 장이어야 한다")
        if s.get("kind") == "answers" and not s.get("teacher_only"):
            errors.append(f"{s['id']}: 정답(answers) 장은 teacher_only여야 한다")
        visible = {k: v for k, v in s.items() if k != "notes"}
        if not s.get("teacher_only") and ANSWER_LEAK.search(json.dumps(visible, ensure_ascii=False)):
            errors.append(f"{s['id']}: 학생에게 보이는 장에 정답 표기가 있다")
        if s["role"] in ("practice", "check", "prior") and not (s["notes"].get("정답") or s["notes"].get("예상답")):
            errors.append(f"{s['id']}: 연습·확인 장의 노트에 정답이나 예상 답이 없다")

    # 교육과정 연결
    items = {i["id"]: i for i in json.loads((ROOT / "curriculum" / "grade_items.json").read_text(encoding="utf-8"))}
    units = {u["unit_id"]: u for u in json.loads((ROOT / "curriculum" / "units.json").read_text(encoding="utf-8"))}
    cur = lesson["curriculum"]
    for gid in cur["grade_items"]:
        if gid not in items:
            errors.append(f"교육과정: 학년 항목 {gid}가 curriculum/grade_items.json에 없다")
        elif items[gid]["grade"] != lesson["grade"] or items[gid]["strand"] != lesson["strand"]:
            errors.append(f"교육과정: {gid}의 학년·계통이 수업과 다르다")
    for uid in cur["units"]:
        if uid not in units:
            errors.append(f"교육과정: 단원 {uid}가 curriculum/units.json에 없다")
        elif lesson["grade"] not in units[uid]["grades"]:
            errors.append(f"교육과정: 단원 {uid}의 연결 학년({units[uid]['grades_text']})에 {lesson['grade_label']}이 없다")
    if cur["standard_code"] and cur["link_status"] != "확인됨":
        errors.append("교육과정: 원문으로 확인하지 않은 성취기준 코드를 적었다")
    for p in lesson["prerequisites"]:
        if p.get("grade_item") and p["grade_item"] not in items:
            errors.append(f"선수 학습: {p['grade_item']}가 curriculum/grade_items.json에 없다")

    # 계산 가능한 정답 재검산
    checks = lesson.get("checks", [])
    if lesson["strand"] == "MAT" and lesson.get("format", "ppt") == "ppt" and len(checks) < 3:
        errors.append("수학 차시에는 계산으로 검산할 정답(checks)이 3개 이상 있어야 한다")
    by_id = {s["id"]: s for s in slides}
    for c in checks:
        where = c.get("where", "")
        try:
            if c["type"] == "equiv":
                if len({frac(v) for v in c["values"]}) != 1:
                    errors.append(f"정답 검산({where}): {' = '.join(c['values'])} 가 성립하지 않는다")
            elif c["type"] == "not_equiv":
                a, b = (frac(v) for v in c["values"])
                if a == b:
                    errors.append(f"정답 검산({where}): {c['values'][0]} ≠ {c['values'][1]} 가 성립하지 않는다")
            elif c["type"] == "blank":
                expr = c["expr"].replace("□", str(c["answer"])).replace("−", "-")
                left, right = (side.strip() for side in expr.split("="))
                if not re.fullmatch(r"[\d\s+\-×÷*/().]+", left + right):
                    errors.append(f"정답 검산({where}): 계산할 수 없는 식 {c['expr']}")
                elif exact(left) != exact(right):
                    errors.append(f"정답 검산({where}): {c['expr']} 에 {c['answer']}를 넣으면 성립하지 않는다")
            elif c["type"] == "compare":
                a, b = (exact(v) for v in c["values"])
                ok = {"<": a < b, ">": a > b, "=": a == b}[c["rel"]]
                if not ok:
                    errors.append(f"정답 검산({where}): {c['values'][0]} {c['rel']} {c['values'][1]} 가 성립하지 않는다")
            elif c["type"] == "bond":
                w, (p, q) = c["whole"], c["parts"]
                if w != p + q:
                    errors.append(f"정답 검산({where}): {p}와 {q}를 모으면 {w}가 아니다")
            elif c["type"] == "count":
                counts = [figure_count(b) for b in walk(by_id[c["slide"]])]
                if c["value"] not in counts:
                    errors.append(f"그림 검사({where}): {c['slide']}에 {c['value']}개를 나타내는 그림이 없다")
            elif c["type"] == "bar":
                found = [b for b in walk(by_id[c["slide"]])
                         if b.get("type") in ("bar",) and b.get("parts") == c["parts"] and shaded_count(b.get("shaded")) == c["shaded"]]
                found += [x for b in walk(by_id[c["slide"]]) if b.get("type") == "bars" for x in b["bars"]
                          if x.get("parts") == c["parts"] and shaded_count(x.get("shaded")) == c["shaded"]]
                if not found:
                    errors.append(f"그림 검사({where}): {c['parts']}칸 중 {c['shaded']}칸 색칠한 막대가 없다")
                elif Fraction(c["shaded"], c["parts"]) != frac(c["value"]):
                    errors.append(f"그림 검사({where}): 막대가 {c['value']}이 아니다")
        except (ValueError, KeyError, SyntaxError, ZeroDivisionError) as e:
            errors.append(f"정답 검산({where}): 식을 읽을 수 없다 ({e})")

    # 그림과 표기의 일치
    for s in slides:
        for node in walk({k: v for k, v in s.items() if k != "blocks"}):
            bars = node["bars"] if node.get("type") == "bars" else [node] if node.get("type") == "bar" else []
            for b in bars:
                if isinstance(b.get("label"), list) and "widths" not in b:
                    v = Fraction(shaded_count(b.get("shaded")), b["parts"])
                    if v != Fraction(*b["label"]):
                        errors.append(f"{s['id']}: 분수 {b['label'][0]}/{b['label'][1]} 표기와 막대의 색칠 비율 {v}이 다르다")
        blocks = s.get("blocks", [])
        figures = [b for b in blocks if b["type"] in ("bar", "grid")]
        for b in blocks:
            if b["type"] != "frac" or b.get("n") is None or b.get("d") is None:
                continue
            beside = [f for f in figures if f["x"] > b["x"] and abs(f["y"] - b["y"]) < 0.35]
            if beside:
                f = min(beside, key=lambda f: f["x"])
                v = bar_value(f)
                if v is not None and v != Fraction(b["n"], b["d"]):
                    errors.append(f"{s['id']}: 분수 {b['n']}/{b['d']} 옆 그림의 색칠 비율이 {v}이다")
        for g in (b for b in blocks if b["type"] == "vline"):
            crossed = [f for f in figures if f["type"] == "bar" and g["y1"] <= f["y"] and f["y"] + f["h"] <= g["y2"] and f["x"] < g["x"] < f["x"] + f["w"]]
            if crossed:
                end = shaded_end(min(crossed, key=lambda f: f["y"]))
                if end is not None and abs(end - g["x"]) > 0.02:
                    errors.append(f"{s['id']}: 점선 기준선(x={g['x']})이 첫 막대의 색칠 끝(x={end:.2f})과 맞지 않는다")
        for b in blocks:
            if "w" in b and "h" in b:
                if b["x"] < 0.5 or b["x"] + b["w"] > SAFE_RIGHT + 0.001 or b["y"] + b["h"] > SAFE_BOTTOM + 0.001:
                    errors.append(f"{s['id']}: {b['type']} 블록이 안전 영역을 벗어난다")

    return errors, notes


def main(paths):
    failed = False
    for p in paths:
        errors, notes = check(p)
        status = "통과" if not errors else f"실패 {len(errors)}건"
        print(f"[{status}] {p}")
        for e in errors:
            print(f"  ✗ {e}")
        for n in notes:
            print(f"  · {n}")
        failed |= bool(errors)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main(sys.argv[1:])
