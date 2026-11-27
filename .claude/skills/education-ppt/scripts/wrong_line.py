"""노트 ‘틀리면’ 한 줄을 읽는다(check_lesson.py, tools/app/export.py 가 함께 쓴다).

꼴 (references/authoring.md ‘틀리면’):
  ①을 3이라고 하면: 중간 수만 더했습니다(M1). “아직 더하지 않은 수가 있니?” 하고 묻습니다.
  ③을 ‘육십십’이나 80이라고 하면: 십의 자리를 그대로 읽었습니다(M1·M2). “6묶음이면 몇십이지?” 하고 묻습니다. S05로 돌아갑니다.
  다를 고르면: 받은 이야기의 식입니다(M2). “구슬을 주면 늘어날까, 줄어들까?” 하고 묻습니다.
  곰을 고르면: 뒤의 두 수를 먼저 뺐습니다(M2). “돌 9개에서 먼저 몇 개를 덜어 냈지?” 하고 묻습니다.
  ‘받침이 없어요’를 고르면: …   (이름에 빈칸이 있으면 따옴표)
  ‘맞아요’라고 하면: 친구의 말을 그대로 믿었습니다(M1). “아래에 무엇이 있지?” 하고 묻습니다.   (친구 말이 맞는지 묻는 장)
"""
import re

CIRCLED = "①②③④⑤⑥⑦⑧⑨⑩"
HEAD = re.compile(
    rf"^(?:(?P<n>[{CIRCLED}])(?:을|를|에서|에)?\s+(?P<val>.+?)(?:이)?라고\s+(?:하면|답하면|쓰면|말하면|읽으면)"
    rf"|(?P<pick>‘[^’]+’|[^\s:‘]+?)(?:을|를)\s+고르면"
    rf"|(?P<say>‘[^’]+’)(?:이)?라고\s+(?:하면|답하면|말하면))\s*:\s*(?P<rest>.+)$")
TAIL = re.compile(
    r"^(?P<reason>.+?)(?:\((?P<m>M\d+(?:·M\d+)*)\))?\.\s*(?P<fb>“[^”]+”)\s*(?:하고|라고)\s*(?:묻습니다|말합니다)\."
    r"(?:\s*(?P<goto>S\d\d)(?:으)?로\s*돌아갑니다\.)?\s*$")


def split_values(val):
    """‘20이나 39’, ‘‘육십십’이나 80’ → ['20', '39'] / ['육십십', '80']"""
    parts = re.split(r"(?:(?<=[\d’”\]])나|이나|,|\s또는)\s+(?=[‘“\d−A-Za-z가-힣\[])", val)
    out = []
    for p in parts:
        p = p.strip().strip("‘’“”").strip()
        if p:
            out.append(p)
    return out or [val.strip()]


def parse(line):
    """한 줄 → dict 또는 None(꼴이 맞지 않음)."""
    m = HEAD.match(line.strip())
    if not m:
        return None
    t = TAIL.match(m.group("rest"))
    if not t:
        return None
    out = {"reason": t.group("reason").strip(), "feedback": t.group("fb").strip("“”"),
           "misconceptions": t.group("m").split("·") if t.group("m") else []}
    if t.group("goto"):
        out["goto"] = t.group("goto")
    if m.group("n"):
        out["n"] = CIRCLED.index(m.group("n")) + 1
        out["values"] = split_values(m.group("val"))
    elif m.group("pick"):
        out["pick"] = m.group("pick").strip("‘’")
    else:
        out["say"] = m.group("say").strip("‘’")  # 견주기·고르기 장에서 한 장 전체에 대한 답(‘맞아요’)
    return out
