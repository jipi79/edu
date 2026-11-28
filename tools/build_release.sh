#!/usr/bin/env bash
# 릴리스용 자료 묶음: 학년마다 모든 차시를 새로 만들고 학년별 zip을 만든다.
#
#   tools/build_release.sh <판 이름> G01 G02 …     → release/edu-<판 이름>-G01.zip …
#
# zip 이름에는 ASCII만 쓴다. GitHub은 릴리스 자산 이름에서 한글을 지우므로 '…-초1.zip'·'…-중1.zip'·
# '…-고1.zip'이 모두 '…-.1.zip'이 되어 서로 덮어쓴다(v0.2.0에서 초1~3·중1~3이 이렇게 빠졌다).
# 학년 이름은 zip 옆 '<zip>.label' 에 적고, 워크플로가 이것을 릴리스 목록에 보이는 이름으로 붙인다.
#
# JOBS(기본: CPU 수)개 차시를 동시에 만든다. 한 차시라도 검사·빌드에 실패하면 멈춘다.
# SOFFICE: LibreOffice 실행 명령(tools/build_one.sh 와 같음). 동시에 여러 개를 돌리므로
# 실행마다 다른 사용자 프로필을 쓰는 명령을 준다(.github/workflows/release.yml 참고).
set -euo pipefail
cd "$(dirname "$0")/.."
LABEL="$1"; shift
JOBS="${JOBS:-$(nproc)}"
LOGS=$(mktemp -d)
mkdir -p release

for g in "$@"; do
  mapfile -t files < <(ls lessons/${g}_*/*/*/KR22-*.json)
  label=$(python3 -I -c 'import json,sys; print(json.load(open(sys.argv[1],encoding="utf-8"))["grade_label"])' "${files[0]}")
  rm -rf "dist/$label"   # 지난 빌드의 남은 파일이 묶음에 들어가지 않게
  echo "== $label: ${#files[@]}차시"
  printf '%s\0' "${files[@]}" | xargs -0 -P "$JOBS" -I{} bash -c '
    log="$1/$(basename "$2" .json).log"
    tools/build_one.sh "$2" > "$log" 2>&1 || { echo "실패: $2"; tail -30 "$log"; exit 1; }' _ "$LOGS" {}
  # 차시마다 네 파일(수업용·학생용 PPTX, 활동지·부모용 안내 PDF)이 다 있는지 센다
  made=$(find "dist/$label" -type f \( -name '*.pptx' -o -name '*.pdf' \) | wc -l)
  [ "$made" -eq $(( ${#files[@]} * 4 )) ] || { echo "파일 수가 맞지 않는다: $made / $(( ${#files[@]} * 4 ))"; exit 1; }
  out="edu-$LABEL-$g.zip"
  rm -f "release/$out"   # zip -r 는 있던 묶음에 덧붙이므로
  (cd dist && zip -qr "../release/$out" "$label")
  printf '%s %s\n' "$LABEL" "$label" > "release/$out.label"
  echo "   → release/$out ($label, $made개 파일)"
done
rm -rf "$LOGS"
