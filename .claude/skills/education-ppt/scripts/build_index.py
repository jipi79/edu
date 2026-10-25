"""lessons/ 아래 모든 수업 원본을 읽어 학년별 목차(lessons/INDEX.md)를 만든다.

  python3 .claude/skills/education-ppt/scripts/build_index.py

목차에는 수업 ID, 제목, 목표, 선수 학습, 권장 시간, 연결된 학년 항목, 제작 상태, 파일 링크를 적는다.
"""
import json
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[4]


def main():
    meta = json.loads((ROOT / "curriculum" / "meta.json").read_text(encoding="utf-8"))
    items = json.loads((ROOT / "curriculum" / "grade_items.json").read_text(encoding="utf-8"))
    lessons = [json.loads(p.read_text(encoding="utf-8")) | {"_path": p}
               for p in sorted((ROOT / "lessons").rglob("KR22-*.json"))]
    covered = {g for L in lessons for g in L["curriculum"]["grade_items"]}
    strands = {s["code"]: s["label"] for s in meta["strands"]}

    out = ["# 수업 목차", "",
           "`tools/build.sh`가 수업 원본(JSON)에서 자동으로 만드는 파일입니다. 직접 고치지 마세요.", "",
           f"- 제작된 수업: {len(lessons)}차시",
           f"- 수업이 하나 이상 연결된 학년 항목: {len(covered)} / {len(items)}", "",
           "상태: 계획 → 원고 완료 → 제작 완료(자동 검사 통과) → 검토 완료(사람이 확인) → 배포. "
           "실제 아이에게 수업한 효과는 별도로 기록합니다.", ""]
    for g in meta["grades"]:
        group = [L for L in lessons if L["grade"] == g["code"]]
        if not group:
            continue
        out += [f"## {g['name']}", "", f"학년 목표: {g['goal']}", ""]
        for code in [s["code"] for s in meta["strands"]]:
            rows = sorted((L for L in group if L["strand"] == code), key=lambda L: (L["unit_folder"], L["sequence"]))
            if not rows:
                continue
            out += [f"### {strands[code]}", "",
                    "| 순서 | 수업 ID | 제목 | 목표 | 선수 학습 | 시간 | 학년 항목 | 상태 | 파일 |",
                    "|---|---|---|---|---|---|---|---|---|"]
            for L in rows:
                d = f"dist/{L['grade_label']}/{L['strand_label']}/{L['unit_folder']}/{L['file_stem']}"
                link = lambda suffix, label: f"[{label}](../{quote(d + suffix)})"
                files = " · ".join([link(".pptx", "수업용"), link("_학생용.pptx", "학생용"),
                                    link("_활동지.pdf", "활동지"), link("_부모용안내.pdf", "부모용 안내")])
                goals = "<br>".join(f"{o['id']}. {o['text']}" for o in L["objectives"])
                pre = "<br>".join(p["text"] for p in L["prerequisites"]) or "—"
                out.append(f"| {L['unit_folder']} {L['sequence']} | `{L['id']}` | {L['title']} | {goals} | {pre} | "
                           f"{L['minutes']}분 | {', '.join(L['curriculum']['grade_items'])} | {L['status']} | {files} |")
            out.append("")
    (ROOT / "lessons" / "INDEX.md").write_text("\n".join(out), encoding="utf-8")
    print(f"lessons/INDEX.md ({len(lessons)}차시)")


if __name__ == "__main__":
    main()
