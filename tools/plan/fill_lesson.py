"""차시 뼈대 JSON에 내용 JSON(objectives·slides·worksheet 등)을 합친다: python3 -I tools/plan/fill_lesson.py <뼈대> <내용>"""
import json, sys
from pathlib import Path
base = Path(sys.argv[1])
L = json.loads(base.read_text(encoding="utf-8"))
L.update(json.loads(Path(sys.argv[2]).read_text(encoding="utf-8")))
L.pop("plan_objective", None)
base.write_text(json.dumps(L, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("merged", base)
