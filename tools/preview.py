"""수업용 PPTX를 렌더링해 한눈에 보는 미리보기(3×3 격자 JPG)를 만든다.

  python3 -I tools/preview.py <lesson.json> <출력 폴더>

출력: <출력 폴더>/<수업 ID>-sheet-1.jpg … (장 번호가 왼쪽 위에 적힘), slide-NN.jpg(장별 원본)
LibreOffice 명령은 환경 변수 SOFFICE(기본 soffice)로 바꿀 수 있다. 미리보기는 맑은 고딕 대신 나눔고딕으로 그려진다.
"""
import json
import os
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw


def main(lesson_path, out_dir):
    L = json.loads(Path(lesson_path).read_text(encoding="utf-8"))
    pptx = Path("dist") / L["grade_label"] / L["strand_label"] / L["unit_folder"] / f"{L['file_stem']}.pptx"
    if not pptx.exists():
        sys.exit(f"{pptx} 가 없다. 먼저 tools/build_one.sh 로 빌드한다(빌드가 실패했다면 그 오류를 고친다).")
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob(f"{L['id']}-*.jpg"):
        old.unlink()
    with tempfile.TemporaryDirectory() as tmp:
        soffice = shlex.split(os.environ.get("SOFFICE", "soffice"))
        subprocess.run(soffice + ["--headless", "--convert-to", "pdf", "--outdir", tmp, str(pptx)], check=True, capture_output=True)
        pdf = Path(tmp) / f"{L['file_stem']}.pdf"
        subprocess.run(["pdftoppm", "-jpeg", "-r", "60", str(pdf), str(out / f"{L['id']}-slide")], check=True)
    slides = sorted(out.glob(f"{L['id']}-slide-*.jpg"))
    per = 9
    for k in range(0, len(slides), per):
        ims = [Image.open(f) for f in slides[k:k + per]]
        w, h = ims[0].size
        sheet = Image.new("RGB", (w * 3 + 20, h * ((len(ims) + 2) // 3) + 10 * ((len(ims) + 2) // 3)), "white")
        for i, im in enumerate(ims):
            x, y = (i % 3) * (w + 10), (i // 3) * (h + 10)
            sheet.paste(im, (x, y))
            d = ImageDraw.Draw(sheet)
            d.rectangle([x, y, x + 34, y + 20], fill="black")
            d.text((x + 4, y + 4), f"S{k + i + 1:02d}", fill="white")
        name = out / f"{L['id']}-sheet-{k // per + 1}.jpg"
        sheet.save(name, quality=82)
        print(name)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
