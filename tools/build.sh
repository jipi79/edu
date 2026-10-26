#!/usr/bin/env bash
# 차시 하나 이상을 만들고 목차와 계획 현황을 갱신한다.
#
#   tools/build.sh <lesson.json> [<lesson.json> …]
set -euo pipefail
cd "$(dirname "$0")/.."
for LESSON in "$@"; do
  tools/build_one.sh "$LESSON"
done
python3 -I .claude/skills/education-ppt/scripts/build_index.py
python3 -I tools/plan/build_plan.py
