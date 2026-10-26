"""학년별 차시 계획 원본(plans/elementary/G0N.txt)을 데이터와 목차로 바꾼다.

  python3 -I tools/plan/build_plan.py

- plans/elementary/plan.json : 차시마다 ID·학년·계통·학년 항목·단원 폴더·순서·연결 단원·제목·목표·형식·우선순위·선수 차시·파일 이름·원본 경로·상태
- plans/초등_차시계획.md      : 사람이 읽는 전체 계획과 제작 현황

검사: 학년 항목·단원 ID가 curriculum/에 있는지, 단원의 연결 학년에 그 학년이 있는지,
선수 차시가 계획 안에 있는지, 선수 관계에 순환이 없는지.
"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLAN_DIR = ROOT / "plans" / "elementary"
PRIORITY = {"KOR": 1, "MAT": 1, "ENG": 1, "SCI": 2, "SOC": 2}
ACT_STRANDS = {"ART", "PHE", "TEC", "CAR", "ENV"}
BAD_FILENAME = re.compile(r'[\\/:*?"<>|\s]')


def lesson_path(L):
    return f"lessons/{L['grade']}_{L['grade_label']}/{L['strand']}_{L['strand_label']}/{L['folder']}/{L['id']}.json"


def main():
    meta = json.loads((ROOT / "curriculum" / "meta.json").read_text(encoding="utf-8"))
    items = {i["id"]: i for i in json.loads((ROOT / "curriculum" / "grade_items.json").read_text(encoding="utf-8"))}
    units = {u["unit_id"]: u for u in json.loads((ROOT / "curriculum" / "units.json").read_text(encoding="utf-8"))}
    grades = {g["code"]: g for g in meta["grades"]}
    strands = {s["code"]: s for s in meta["strands"]}

    errors, lessons = [], []
    code_count = Counter()
    for f in sorted(PLAN_DIR.glob("G0*.txt")):
        grade = f.stem
        header = None
        folder_seq = Counter()
        prev_in_item = None
        for n, raw in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            where = f"{f.name}:{n}"
            parts = [p.strip() for p in line[1:].split("|")]
            if line.startswith("@"):
                item_short, folder, unit_ids = parts[0], parts[1], parts[2].split()
                opts = parts[3:]
                strand = item_short.split("-")[0]
                item_id = f"KR22-{grade}-{item_short}"
                if item_id not in items:
                    errors.append(f"{where}: 학년 항목 {item_id} 없음")
                for u in unit_ids:
                    if u not in units:
                        errors.append(f"{where}: 단원 {u} 없음")
                    elif grade not in units[u]["grades"]:
                        errors.append(f"{where}: 단원 {u}({units[u]['grades_text']})에 {grades[grade]['label']} 없음")
                    elif units[u]["strand"] != strand:
                        errors.append(f"{where}: 단원 {u}는 {strand} 계통이 아님")
                fmt = "act" if strand in ACT_STRANDS else "ppt"
                pri = PRIORITY.get(strand, 3)
                for o in opts:
                    if o in ("ppt", "act"):
                        fmt = o
                    elif o.startswith("pri"):
                        pri = int(o.split()[1])
                if BAD_FILENAME.search(folder):
                    errors.append(f"{where}: 폴더 이름에 쓸 수 없는 글자: {folder}")
                header = dict(item=item_id, strand=strand, folder=folder, units=unit_ids, fmt=fmt, pri=pri)
                prev_in_item = None
                continue
            if not line.startswith("-") or header is None:
                errors.append(f"{where}: 해석할 수 없는 줄")
                continue
            code, title, objective = parts[0], parts[1], parts[2]
            fmt, pre = header["fmt"], []
            for extra in parts[3:]:
                if extra in ("ppt", "act"):
                    fmt = extra
                elif extra.startswith("pre"):
                    pre += [p.strip() for p in extra[3:].split(",") if p.strip()]
                else:
                    errors.append(f"{where}: 알 수 없는 항목 '{extra}'")
            strand = header["strand"]
            key = (grade, strand, code)
            code_count[key] += 1
            lid = f"KR22-{grade}-{strand}-{code}-L{code_count[key]:02d}"
            folder_seq[header["folder"]] += 1
            g, s = grades[grade], strands[strand]
            stem_title = BAD_FILENAME.sub("", title).replace("(", "").replace(")", "")
            L = {
                "id": lid, "concept_id": f"{strand}-{code}", "grade": grade, "grade_label": g["label"], "band": g["band"],
                "strand": strand, "strand_label": s["label"], "grade_item": header["item"],
                "folder": header["folder"], "sequence": folder_seq[header["folder"]], "units": header["units"],
                "title": title, "objective": objective, "format": fmt, "priority": header["pri"],
                "pre": ([prev_in_item] if prev_in_item else []) + [f"KR22-{p}" if not p.startswith("KR22-") else p for p in pre],
            }
            L["file_stem"] = f"{g['label']}_{s['label']}_{header['folder']}_{L['sequence']:02d}_{stem_title}"
            L["source"] = lesson_path(L)
            lessons.append(L)
            prev_in_item = lid

    by_id = {L["id"]: L for L in lessons}
    # 'G01-MAT-NUM9' 처럼 L 번호 없이 적은 선수 차시는 L01로 본다
    for L in lessons:
        resolved = []
        for p in L["pre"]:
            pid = p if re.search(r"-L\d{2}$", p) else p + "-L01"
            if pid not in by_id:
                errors.append(f"{L['id']}: 선수 차시 {p} 가 계획에 없음")
            elif pid not in resolved:
                resolved.append(pid)
        L["pre"] = resolved
    # 순환 검사
    state = {}
    def visit(lid, stack):
        if state.get(lid) == 1:
            errors.append(f"선수 관계 순환: {' → '.join(stack + [lid])}")
            return
        if state.get(lid) == 2:
            return
        state[lid] = 1
        for p in by_id[lid]["pre"]:
            if p in by_id:
                visit(p, stack + [lid])
        state[lid] = 2
    for L in lessons:
        visit(L["id"], [])

    # 제작 상태: 원본이 있으면 그 상태를 읽는다
    for L in lessons:
        src = ROOT / L["source"]
        L["status"] = json.loads(src.read_text(encoding="utf-8")).get("status", "원고 완료") if src.exists() else "계획"

    if errors:
        print("\n".join(f"✗ {e}" for e in errors))
        sys.exit(1)

    (PLAN_DIR / "plan.json").write_text(json.dumps(lessons, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    write_markdown(lessons, meta, items)
    done = sum(1 for L in lessons if L["status"] != "계획")
    print(f"차시 {len(lessons)}개 (제작 {done}) · 학년 항목 {len({L['grade_item'] for L in lessons})}개 연결")


def write_markdown(lessons, meta, items):
    strands = [s["code"] for s in meta["strands"]]
    label = {s["code"]: s["label"] for s in meta["strands"]}
    grades = [g for g in meta["grades"] if g["code"] <= "G06"]
    count = defaultdict(int)
    done = defaultdict(int)
    for L in lessons:
        count[(L["grade"], L["strand"])] += 1
        done[(L["grade"], L["strand"])] += L["status"] != "계획"
    out = ["# 초등 전체 차시 계획", "",
           "`plans/elementary/G0N.txt` 에서 `tools/plan/build_plan.py` 가 만드는 파일입니다. 직접 고치지 마세요.", "",
           "한 차시는 집에서 부모가 아이와 1:1로 하는 약 40분 수업입니다. 학교 수업 시수를 그대로 옮긴 것이 아니라 "
           "학년 항목마다 꼭 다뤄야 할 핵심 개념을 차시로 나눈 것입니다. 학년 배치는 2022 개정 교육과정 계열의 권장안입니다.", "",
           f"- 전체 {len(lessons)}차시, 제작 {sum(done.values())}차시",
           "- 우선순위 1 = 국어·수학·영어(누적형), 2 = 과학·사회, 3 = 그 밖",
           "- 형식 ppt = 설명·연습 중심, act = 화면은 짧은 안내이고 활동지가 관찰·실천 기록인 활동 중심", "",
           "## 학년·과목별 차시 수 (제작/계획)", "",
           "| 과목 | " + " | ".join(g["label"] for g in grades) + " | 합계 |",
           "|---|" + "---|" * (len(grades) + 1)]
    for s in strands:
        row = [f"{done[(g['code'], s)]}/{count[(g['code'], s)]}" if count[(g["code"], s)] else "—" for g in grades]
        tot = sum(count[(g["code"], s)] for g in grades)
        tdone = sum(done[(g["code"], s)] for g in grades)
        out.append(f"| {label[s]} | " + " | ".join(row) + f" | {tdone}/{tot} |")
    out.append("")
    by_id = {L["id"]: L for L in lessons}
    for g in grades:
        out += [f"## {g['name']}", "", f"학년 목표: {g['goal']}", ""]
        for s in strands:
            rows = [L for L in lessons if L["grade"] == g["code"] and L["strand"] == s]
            if not rows:
                continue
            out += [f"### {label[s]}", "", "| 차시 | 제목 | 목표 | 선수 차시 | 형식 | 상태 |", "|---|---|---|---|---|---|"]
            for L in rows:
                pre = ", ".join(f"{by_id[p]['grade_label']} {by_id[p]['title']}" for p in L["pre"]) or "—"
                out.append(f"| {L['folder']} {L['sequence']} | {L['title']} | {L['objective']} | {pre} | {L['format']} | {L['status']} |")
            out.append("")
    (ROOT / "plans" / "초등_차시계획.md").write_text("\n".join(out), encoding="utf-8")


if __name__ == "__main__":
    main()
