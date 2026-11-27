"""어디서부터 다시 배울지 찾는 진단지와 학습 경로를 만든다.

  python3 tools/plan/diagnose.py KR22-G05-MAT-FRAC-COMPARE-L01            # 진단지
  python3 tools/plan/diagnose.py KR22-G05-MAT-FRAC-COMPARE-L01 \\
          --passed KR22-G05-MAT-FRAC-REDUCE-L01                           # 통과한 차시를 빼고 경로
  옵션: --depth N (선수 학습을 몇 단계까지 거슬러 갈지, 기본 3)
        --out 파일.md (기본: 화면에 출력) · --html 파일.html (인쇄용)

진단 문항은 새로 만들지 않고, 각 선수 차시 ‘오늘 배운 것’ 장의 복습 문항(review)과
노트의 정답을 그대로 가져온다. 대상 차시의 ‘지난 시간 기억하기’(role: prior) 장도 넣는다.

판단 규칙: 한 차시의 문항을 모두 맞히면 그 차시는 통과로 보고 그 아래(더 앞의 선수 학습)는 묻지 않는다.
하나라도 틀리면 그 차시를 경로에 넣고, 그 차시의 선수 학습 문항으로 내려간다.
경로는 통과하지 못한 차시를 선수 학습이 먼저 오도록 늘어놓은 것이다(마지막이 대상 차시).
"""
import argparse
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CIRCLED = "①②③④⑤⑥⑦⑧⑨⑩"


def load():
    lessons = {}
    for p in sorted((ROOT / "lessons").rglob("KR22-*.json")):
        L = json.loads(p.read_text(encoding="utf-8"))
        lessons[L["id"]] = L
    return lessons


def prereqs(L):
    return [p["lesson"] for p in L["prerequisites"] if p.get("lesson")]


def clean(s):
    if isinstance(s, dict):  # {title, text} 꼴의 물음
        s = " ".join(str(s.get(k, "")) for k in ("title", "text") if s.get(k))
    s = str(s)
    return s.replace("⟦", "").replace("⟧", "").replace("\n", " ").strip()


def render_eq(items):
    out = []
    for e in items:
        if e is None:
            out.append("□")
        elif isinstance(e, list) and len(e) == 2:
            n, d = ("□" if x is None else x for x in e)
            out.append(f"{n}/{d}")
        elif isinstance(e, list) and len(e) == 3:
            w, n, d = ("□" if x is None else x for x in e)
            out.append(f"{w} {n}/{d}")
        else:
            out.append(str(e))
    return " ".join(out)


def render_item(r):
    if "eq" in r:
        eq = r["eq"]["items"] if isinstance(r["eq"], dict) else r["eq"]
        return render_eq(eq)
    if "text" in r:
        return clean(r["text"])
    return "(그림 문항 — 수업용 PPT의 해당 장을 보여 주세요)"


def split_answers(answers, n):
    """노트 정답이 ‘① … ② … ③ …’ 한 줄로 합쳐 있으면 문항별로 나눈다."""
    answers = [clean(a) for a in answers]
    if len(answers) == n:
        return [re.sub(rf"^[{CIRCLED}]\s*", "", a) for a in answers]
    # 줄마다 ①②③으로 시작하고 덧붙인 설명 줄이 따로 있으면 번호 줄만 쓴다
    numbered = [a for a in answers if a[:1] in CIRCLED]
    if len(numbered) == n and [a[0] for a in numbered] == list(CIRCLED[:n]):
        return [a[1:].strip() for a in numbered]
    # 번호가 든 줄만 가른다(‘네모 2개, 세모 2개입니다.’ 같은 덧붙인 설명 줄은 뺀다)
    with_num = [a for a in answers if re.search(rf"[{CIRCLED}]", a)]
    if with_num and len(with_num) < len(answers):
        answers = with_num
    joined = " ".join(answers)
    # ①, ②, ③을 차례로 찾는다(답 안에 ‘①의 낱말’처럼 번호가 다시 나와도 순서로 가른다)
    pos, at = [], 0
    for k in range(n):
        at = joined.find(CIRCLED[k], at)
        if at < 0:
            return [joined] + [""] * (n - 1)
        pos.append(at)
    pos.append(len(joined))
    return [joined[pos[k] + 1:pos[k + 1]].strip() for k in range(n)]


def items_from(slide):
    probs = slide.get("review") or slide.get("problems") or []
    ans = split_answers(slide.get("notes", {}).get("정답", []), len(probs))
    return [(render_item(r), a) for r, a in zip(probs, ans)]


def legacy_items(slide):
    """블록으로 직접 배치한 옛 형식 장: ‘①’로 시작하는 식·글 블록을 문항으로 읽는다."""
    probs = []
    for b in slide.get("blocks", []):
        if b.get("type") == "eq" and b.get("items") and str(b["items"][0]) in CIRCLED:
            probs.append({"eq": b["items"][1:]})
        elif b.get("type") == "text" and b.get("text", "")[:1] in CIRCLED:
            probs.append({"text": b["text"][1:]})
    ans = split_answers(slide.get("notes", {}).get("정답", []), len(probs))
    return [(render_item(r), a) for r, a in zip(probs, ans)]


def review_items(L):
    """이 차시를 알고 있는지 묻는 문항: 마지막 정리 장의 복습 문항. 없으면 마지막 연습 장."""
    legacy = [s for s in L["slides"] if "kind" not in s and s.get("role") == "review"]
    if legacy and legacy_items(legacy[-1]):
        return legacy[-1]["id"], legacy_items(legacy[-1])
    for kind in ("summary", "practice"):
        S = [s for s in L["slides"] if s.get("kind") == kind and (s.get("review") or s.get("problems"))]
        if S:
            return S[-1]["id"], items_from(S[-1])
    return None, []


def prior_items(L):
    S = [s for s in L["slides"] if s.get("role") == "prior"]
    for s in S:
        items = items_from(s) if s.get("problems") else legacy_items(s)
        if items:
            return s["id"], items
    return None, []


def walk(lessons, target, depth, passed):
    """대상에서 선수 학습을 거슬러 간다. 통과한 차시에서는 멈춘다. (단계별 차시, 경로)"""
    levels, seen, frontier = [], {target}, [target]
    for _ in range(depth):
        nxt = []
        for lid in frontier:
            for p in prereqs(lessons[lid]):
                if p not in seen and p in lessons:
                    seen.add(p)
                    nxt.append(p)
        if not nxt:
            break
        levels.append(nxt)
        frontier = [p for p in nxt if p not in passed]
    # 경로: 통과하지 않은 차시 중, 통과하지 않은 차시를 거쳐 대상에 닿는 것만
    need, stack = set(), [target]
    while stack:
        lid = stack.pop()
        if lid in need:
            continue
        need.add(lid)
        stack += [p for p in prereqs(lessons[lid]) if p in seen and p not in passed]
    order, done = [], set()

    def visit(lid):
        if lid in done:
            return
        done.add(lid)
        for p in prereqs(lessons[lid]):
            if p in need:
                visit(p)
        order.append(lid)

    visit(target)
    return levels, order


def label(L):
    return f"{L['grade_label']} {L['strand_label']} · {L['unit_folder']} {L['sequence']} 「{L['title']}」"


def file_hint(L):
    return f"dist/{L['grade_label']}/{L['strand_label']}/{L['unit_folder']}/{L['file_stem']}.pptx"


def build(lessons, target, depth, passed):
    T = lessons[target]
    levels, order = walk(lessons, target, depth, passed)
    md = [f"# 진단지 — {T['title']}", "",
          f"대상 수업: {label(T)} (`{target}`)", "",
          "## 하는 법", "",
          "1. 0단계부터 문항을 하나씩 소리 내어 읽어 주고 아이가 풀게 합니다. 정답은 맨 뒤에 있습니다(아이에게 보이지 않게).",
          "   0단계를 모두 맞히면 진단은 여기서 끝내고 대상 수업을 바로 시작합니다.",
          "2. 한 차시의 문항을 **모두 맞히면** 그 차시는 통과입니다. 그 아래 단계에서 그 차시의 선수 학습은 묻지 않습니다.",
          "3. **하나라도 틀리면** 그 차시를 표시하고, 다음 단계에서 그 차시의 선수 학습 문항을 풉니다.",
          "4. 끝나면 통과한 차시를 `--passed` 로 넣어 다시 실행하면 배울 순서가 나옵니다.",
          "",
          "한 번에 15분을 넘기지 않습니다. 지치면 멈추고 다음 날 이어 갑니다. "
          "틀린 것은 고쳐 주지 말고 표시만 합니다(진단이 목적입니다).", ""]
    key = []
    sid, items = prior_items(T)
    if items:
        md += [f"## 0단계 — 대상 수업의 ‘지난 시간 기억하기’ ({sid})", ""]
        md += [f"{CIRCLED[i]} {q}  " for i, (q, _) in enumerate(items)] + [""]
        key.append((f"0단계 {T['title']} {sid}", items))
    for n, lv in enumerate(levels, 1):
        md += [f"## {n}단계", ""]
        for lid in lv:
            L = lessons[lid]
            sid, items = review_items(L)
            mark = " — 통과" if lid in passed else ""
            md += [f"### {label(L)}{mark}", "", f"`{lid}` · 이 차시의 선수: "
                   + (", ".join(lessons[p]["title"] for p in prereqs(L) if p in lessons) or "없음"), ""]
            if not items:
                md += ["(가져올 복습 문항이 없습니다. 수업용 PPT의 정리 장을 보세요.)", ""]
                continue
            md += [f"{CIRCLED[i]} {q}  " for i, (q, _) in enumerate(items)] + [""]
            key.append((f"{n}단계 {L['title']} ({sid})", items))
    if not levels:
        md += ["이 차시에는 저장소 안에 연결된 선수 차시가 없습니다.", ""]
    md += ["## 배울 순서", ""]
    if passed:
        md += [f"통과한 차시 {len(passed)}개를 빼고, 선수 학습이 먼저 오게 늘어놓았습니다.", ""]
    else:
        md += ["아직 통과한 차시를 넣지 않아, 거슬러 간 차시를 모두 넣은 가장 긴 경로입니다.", ""]
    md += [f"{i}. {label(lessons[lid])} — `{file_hint(lessons[lid])}`" for i, lid in enumerate(order, 1)] + [""]
    md += ["## 정답 (부모용)", ""]
    for title, items in key:
        md += [f"**{title}**  "] + [f"{CIRCLED[i]} {a}  " for i, (_, a) in enumerate(items)] + [""]
    return "\n".join(md), order


def to_html(md):
    body = []
    for line in md.split("\n"):
        t = html.escape(line.rstrip())
        t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
        t = re.sub(r"`(.+?)`", r"<code>\1</code>", t)
        if t.startswith("### "):
            body.append(f"<h3>{t[4:]}</h3>")
        elif t.startswith("## "):
            cls = ' class="key"' if "정답" in t else ""
            body.append(f"<h2{cls}>{t[3:]}</h2>")
        elif t.startswith("# "):
            body.append(f"<h1>{t[2:]}</h1>")
        elif t:
            body.append(f"<p>{t}</p>")
    return ("<!doctype html><meta charset='utf-8'><title>진단지</title><style>"
            "body{font-family:'Noto Sans KR',sans-serif;max-width:46em;margin:2em auto;line-height:1.6;padding:0 1em}"
            "h2{border-bottom:2px solid #333;margin-top:1.6em}h3{margin-bottom:.2em}p{margin:.3em 0}"
            "code{font-size:.85em;color:#555}.key{page-break-before:always}</style>" + "\n".join(body))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target")
    ap.add_argument("--depth", type=int, default=3)
    ap.add_argument("--passed", nargs="*", default=[])
    ap.add_argument("--out")
    ap.add_argument("--html")
    a = ap.parse_args()
    lessons = load()
    for lid in [a.target] + a.passed:
        if lid not in lessons:
            sys.exit(f"없는 수업 ID: {lid}")
    md, _ = build(lessons, a.target, a.depth, set(a.passed))
    if a.out:
        Path(a.out).write_text(md, encoding="utf-8")
    if a.html:
        Path(a.html).write_text(to_html(md), encoding="utf-8")
    if not (a.out or a.html):
        print(md)


if __name__ == "__main__":
    main()
