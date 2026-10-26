"""생성된 PPTX 두 벌(수업용·학생용)을 원본과 대조해 검사한다.

  python3 .claude/skills/education-ppt/scripts/check_output.py <lesson.json> [--dir <출력 폴더>]

- 장 수: 수업용 = 원본 전체, 학생용 = 교사 전용 장을 뺀 수
- 모든 장에 제목이 있고, 모든 도형이 슬라이드 경계 안에 있다
- 수업용은 모든 장에 노트가 있고, 학생용에는 노트와 교사 전용 장·블록이 실제로 없다
- 그림(막대·격자)마다 대체 설명이 있다
"""
import json
import sys
from pathlib import Path

from pptx import Presentation
from pptx.enum.shapes import PP_PLACEHOLDER
from pptx.util import Emu


def slide_ids(prs):
    ids = []
    for slide in prs.slides:
        names = {sh.name.split("-")[0] for sh in slide.shapes if sh.name and sh.name[:1] == "S" and "-" in sh.name}
        ids.append(sorted(names)[0] if names else None)
    return ids


def check_deck(path, lesson, variant):
    errors = []
    prs = Presentation(path)
    W, H = prs.slide_width, prs.slide_height
    expected = [s for s in lesson["slides"] if not (variant == "student" and s.get("teacher_only"))]
    if len(prs.slides) != len(expected):
        errors.append(f"장 수 {len(prs.slides)} ≠ 원본 {len(expected)}")
    teacher_only = {s["id"] for s in lesson["slides"] if s.get("teacher_only")}
    for idx, slide in enumerate(prs.slides, 1):
        # PowerPoint는 type="title" 개체 틀을 제목으로 본다(pptxgenjs는 idx=100으로 쓴다).
        title = next((sh for sh in slide.placeholders if sh.placeholder_format.type == PP_PLACEHOLDER.TITLE), None)
        if title is None or not title.text_frame.text.strip():
            errors.append(f"{idx}장: 제목이 없다")
        for sh in slide.shapes:
            if sh.left is None:
                continue
            if sh.left < 0 or sh.top < 0 or sh.left + sh.width > W + Emu(9525) or sh.top + sh.height > H + Emu(9525):
                errors.append(f"{idx}장: '{sh.name}'이 슬라이드 밖으로 나간다")
            if variant == "student" and sh.name.split("-")[0] in teacher_only:
                errors.append(f"{idx}장: 학생용에 교사 전용 요소 '{sh.name}'이 남아 있다")
            if "figure" in sh.name and not sh._element.xpath("./p:nvSpPr/p:cNvPr/@descr"):
                errors.append(f"{idx}장: 그림 '{sh.name}'에 대체 설명이 없다")
        notes = slide.notes_slide.notes_text_frame.text.strip() if slide.has_notes_slide else ""
        if variant == "teacher" and not notes:
            errors.append(f"{idx}장: 발표자 노트가 없다")
        if variant == "student" and notes:
            errors.append(f"{idx}장: 학생용에 노트가 남아 있다")
    return errors


def main(argv):
    out_dir = Path(argv[argv.index("--dir") + 1]) if "--dir" in argv else None
    lessons = [a for i, a in enumerate(argv) if a != "--dir" and (i == 0 or argv[i - 1] != "--dir")]
    failed = False
    for lesson_path in lessons:
        lesson = json.loads(Path(lesson_path).read_text(encoding="utf-8"))
        out = out_dir or Path("dist") / lesson["grade_label"] / lesson["strand_label"] / lesson["unit_folder"]
        for variant, suffix in (("teacher", ""), ("student", "_학생용")):
            path = out / f"{lesson['file_stem']}{suffix}.pptx"
            errors = check_deck(path, lesson, variant) if path.exists() else ["파일이 없다"]
            print(f"[{'통과' if not errors else f'실패 {len(errors)}건'}] {path}")
            for e in errors:
                print(f"  ✗ {e}")
            failed |= bool(errors)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main(sys.argv[1:])
