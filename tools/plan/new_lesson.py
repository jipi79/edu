"""계획(plan.json)에서 차시 원본의 뼈대를 만든다. 메타데이터·교육과정 연결·선수 차시가 채워지고
목표·장·활동지는 비어 있다(채워야 할 곳에 TODO).

  python3 -I tools/plan/new_lesson.py <수업 ID> [--force]
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main(argv):
    lid = argv[0]
    plan = {L["id"]: L for L in json.loads((ROOT / "plans" / "elementary" / "plan.json").read_text(encoding="utf-8"))}
    if lid not in plan:
        sys.exit(f"계획에 없는 ID: {lid}")
    L = plan[lid]
    out = ROOT / L["source"]
    if out.exists() and "--force" not in argv:
        sys.exit(f"이미 있다: {out}")
    lesson = {
        "id": L["id"], "concept_id": L["concept_id"], "title": L["title"],
        "grade": L["grade"], "grade_label": L["grade_label"], "band": L["band"],
        "strand": L["strand"], "strand_label": L["strand_label"], "unit_folder": L["folder"],
        "sequence": L["sequence"], "file_stem": L["file_stem"], "format": L["format"],
        "minutes": 40, "mode": "home-1to1", "status": "계획",
        "curriculum": {
            "version": "2022 개정 / 권장 학년 배치 v1", "grade_items": [L["grade_item"]], "units": L["units"],
            "standard_code": None, "link_status": "부분 확인",
            "note": "권장 배치이다. 공식 성취기준 코드는 원문으로 확인하지 않았으므로 기록하지 않는다.",
        },
        "plan_objective": L["objective"],
        "prerequisites": [{"text": plan[p]["title"], "lesson": p, "grade_item": plan[p]["grade_item"]} for p in L["pre"]],
        "objectives": [{"id": "A", "text": "TODO", "evidence": "TODO", "success": "TODO"}],
        "materials": [],
        "boundary": "TODO",
        "misconceptions": [],
        "checks": [],
        "slides": [],
        "worksheet": {"title": f"{L['title']} 활동지", "items": [], "record": []},
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(lesson, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(out.relative_to(ROOT))


if __name__ == "__main__":
    main(sys.argv[1:])
