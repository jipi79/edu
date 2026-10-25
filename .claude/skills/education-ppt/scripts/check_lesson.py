"""수업 원본(JSON)을 제작 전에 검사한다.

  python3 .claude/skills/education-ppt/scripts/check_lesson.py <lesson.json> [...]

검사 항목
- 스키마(필수 필드, ID 형식)
- 슬라이드 ID 중복, 모든 장의 제목과 발표자 노트
- 목표마다 설명(teach)·연습(practice)·확인(check) 장이 있는지, 학생용에서도 확인 장이 남는지
- 교육과정 연결: 학년 항목·단원 ID가 curriculum/에 있는지, 확인되지 않은 성취기준 코드를 적지 않았는지
- 계산 가능한 정답(checks)을 분수 계산으로 다시 검산
- 그림과 표기의 일치: 분수 표기 옆 막대·격자의 색칠 비율, 점선 기준선과 색칠 끝의 위치
- 블록이 슬라이드 안전 영역(가장자리 여백, 바닥글) 안에 있는지
"""
import json
import re
import sys
from fractions import Fraction
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[4]
SCHEMA = Path(__file__).resolve().parents[1] / "schemas" / "lesson.schema.json"
SLIDE_W, SAFE_RIGHT, SAFE_BOTTOM = 13.333, 12.75, 6.9


def frac(text):
    n, d = str(text).split("/")
    return Fraction(int(n), int(d))


def bar_value(b):
    if b["type"] == "grid":
        return Fraction(len(b.get("shaded", [])), b["rows"] * b["cols"])
    if "widths" in b:
        return None  # 똑같이 나누지 않은 막대는 분수가 아니다
    return Fraction(len(b.get("shaded", [])), b["parts"])


def shaded_end(b):
    """왼쪽부터 이어서 색칠한 막대의 색칠 끝 x좌표. 이어지지 않으면 None."""
    shaded = sorted(b.get("shaded", []))
    if b["type"] != "bar" or not shaded or shaded != list(range(len(shaded))):
        return None
    widths = b.get("widths") or [1 / b["parts"]] * b["parts"]
    return b["x"] + b["w"] * sum(widths[: len(shaded)])


def check(path):
    errors, notes = [], []
    lesson = json.loads(Path(path).read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    for e in jsonschema.Draft202012Validator(schema).iter_errors(lesson):
        errors.append(f"스키마: {'/'.join(map(str, e.path))}: {e.message}")
    if errors:
        return errors, notes

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
    for s in slides:
        if s.get("teacher_only") and s["role"] not in ("feedback",):
            errors.append(f"{s['id']}: 교사 전용 장은 정답·피드백(feedback) 장이어야 한다")
        for b in s.get("blocks", []):
            if b["type"] in ("text", "card", "chip") and re.search(r"정답\s*[:：]", json.dumps(b, ensure_ascii=False)) and not (s.get("teacher_only") or b.get("teacher_only")):
                errors.append(f"{s['id']}: 학생에게 보이는 블록에 정답 표기가 있다")

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
    by_id = {s["id"]: s for s in slides}
    for c in lesson["checks"]:
        where = c.get("where", "")
        if c["type"] == "equiv":
            vals = {frac(v) for v in c["values"]}
            if len(vals) != 1:
                errors.append(f"정답 검산({where}): {' = '.join(c['values'])} 가 성립하지 않는다")
        elif c["type"] == "not_equiv":
            a, b = (frac(v) for v in c["values"])
            if a == b:
                errors.append(f"정답 검산({where}): {c['values'][0]} ≠ {c['values'][1]} 가 성립하지 않는다")
        elif c["type"] == "blank":
            expr = c["expr"].replace("□", str(c["answer"]))
            left, right = (frac(side.strip()) for side in expr.split("="))
            if left != right:
                errors.append(f"정답 검산({where}): {c['expr']} 에 {c['answer']}를 넣으면 성립하지 않는다")
        elif c["type"] == "bar":
            found = [b for b in by_id[c["slide"]].get("blocks", [])
                     if b["type"] == "bar" and b.get("parts") == c["parts"] and len(b.get("shaded", [])) == c["shaded"]]
            if not found:
                errors.append(f"그림 검사({where}): {c['parts']}칸 중 {c['shaded']}칸 색칠한 막대가 없다")
            elif Fraction(c["shaded"], c["parts"]) != frac(c["value"]):
                errors.append(f"그림 검사({where}): 막대가 {c['value']}이 아니다")

    # 그림과 표기의 일치
    for s in slides:
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
        for key in ("말하기",):
            if not s["notes"].get(key):
                notes.append(f"{s['id']}: 노트에 '{key}'가 없다")

    if lesson.get("worksheet"):
        for it in lesson["worksheet"]["items"]:
            if not it.get("answer"):
                errors.append(f"활동지 {it['no']}: 정답(부모용)이 없다")
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
