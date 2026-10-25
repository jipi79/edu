#!/usr/bin/env bash
# 한 차시를 검사 → PPTX 두 벌 → 미리보기 → 활동지·부모용 안내 PDF → 출력 검사 → 목차 순서로 만든다.
#
#   tools/build.sh <lesson.json>
#
# SOFFICE: LibreOffice 실행 명령(기본값 soffice). 없으면 부모용 안내서의 장 미리보기만 빠진다.
set -euo pipefail
cd "$(dirname "$0")/.."
LESSON="$1"
CHECKS=.claude/skills/education-ppt/scripts
SOFFICE="${SOFFICE:-soffice}"

python3 -I "$CHECKS/check_lesson.py" "$LESSON"
node tools/pptx/build_lesson.js "$LESSON"

read -r OUT STEM < <(python3 -I -c 'import json,sys; L=json.load(open(sys.argv[1],encoding="utf-8")); print("/".join(["dist",L["grade_label"],L["strand_label"],L["unit_folder"]]), L["file_stem"])' "$LESSON")
THUMBS=$(mktemp -d)
trap 'rm -rf "$THUMBS"' EXIT
if $SOFFICE --headless --convert-to pdf --outdir "$THUMBS" "$OUT/$STEM.pptx" >/dev/null 2>&1; then
  pdftoppm -jpeg -r 60 "$THUMBS/$STEM.pdf" "$THUMBS/slide"
else
  echo "LibreOffice가 없어 안내서 미리보기를 건너뜁니다." >&2
fi
node tools/handouts/build_handouts.js "$LESSON" --thumbs "$THUMBS"

python3 -I "$CHECKS/check_output.py" "$LESSON"
python3 -I "$CHECKS/build_index.py"
