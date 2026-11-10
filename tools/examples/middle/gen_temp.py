"""KR22-G07-SCI-TEMP-L01 온도와 열평형 — content JSON generator (figures computed + asserts)."""
import json
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from geo_common import INK, GRIDC, P, r3, seg, txt, dist_point_seg, segs_cross  # noqa: E402

OUT = Path(__file__).parent / "temp_content.json"

WARM_LINE, COLD_LINE = "C8434E", "3D5A80"
WARM_FILL, COLD_FILL, MID_FILL = "F6C9B8", "C9DDF0", "E3D7EC"
WARM_WATER, COLD_WATER, MID_WATER = "FDF1EA", "EDF4FB", "F6F1F8"

# ---------------------------------------------------------------- particle model
B = 2.2          # box side (units)
PR = 0.17        # particle radius
LEN = {"cold": 0.22, "mid": 0.42, "warm": 0.68}   # arrow length = how fast the particle moves
NPART = 7
POS = []
POS_ANG = []


def try_layout(rng):
    """Random (seeded) particle layout; returns positions + one arrow direction per particle so that the
    LONGEST arrow stays inside the box, misses other particles and does not cross other arrows. The same
    directions are reused for every speed, so the pictures differ only in arrow length (speed)."""
    centres = []
    while len(centres) < NPART:
        c = (rng.uniform(PR + 0.12, B - PR - 0.12), rng.uniform(PR + 0.12, B - PR - 0.12))
        if all(math.dist(c, o) >= 2 * PR + 0.32 for o in centres):
            centres.append(c)
    L = LEN["warm"]
    chosen, angs = [], []
    for i, c in enumerate(centres):
        base = rng.randrange(0, 360, 15)
        ok = None
        for k in range(24):
            ang = (base + 15 * ((k + 1) // 2) * (1 if k % 2 == 0 else -1)) % 360
            d = (math.cos(math.radians(ang)), math.sin(math.radians(ang)))
            s = (c[0] + PR * d[0], c[1] + PR * d[1])
            e = (c[0] + (PR + L) * d[0], c[1] + (PR + L) * d[1])
            if not (0.1 <= e[0] <= B - 0.1 and 0.1 <= e[1] <= B - 0.1):
                continue
            if any(dist_point_seg(o, s, e) < PR + 0.08 for j, o in enumerate(centres) if j != i):
                continue
            if any(segs_cross(s, e, s2, e2) or math.dist(e, e2) < 0.2 or dist_point_seg(e, s2, e2) < 0.1 for (s2, e2) in chosen):
                continue
            ok = (ang, s, e)
            break
        if not ok:
            return None
        chosen.append((ok[1], ok[2]))
        angs.append(ok[0])
    # arrows should not all point the same way (looks like flowing water, not random motion)
    if len({a // 90 for a in angs}) < 4:
        return None
    return centres, angs


def choose_layout():
    rng = random.Random(11)
    for _ in range(2000):
        got = try_layout(rng)
        if got:
            centres, angs = got
            POS[:] = [(x / B, y / B) for x, y in centres]
            POS_ANG[:] = angs
            return
    raise AssertionError("no particle layout found")


choose_layout()
for i, a in enumerate(POS):
    for j, b in enumerate(POS):
        if i < j:
            assert math.dist(a, b) * B >= 2 * PR + 0.32


def particle_box(ox, oy, speed, water=None, fill=None, line=None):
    """Return (polygons, circles, segments) for one container of water seen as particles."""
    water = water or {"warm": WARM_WATER, "cold": COLD_WATER, "mid": MID_WATER}[speed]
    fill = fill or {"warm": WARM_FILL, "cold": COLD_FILL, "mid": MID_FILL}[speed]
    line = line or {"warm": WARM_LINE, "cold": COLD_LINE, "mid": "7A4E8A"}[speed]
    polys = [{"pts": [P(ox, oy), P(ox + B, oy), P(ox + B, oy + B), P(ox, oy + B)], "fill": water, "width": 1.5, "color": "64748B"}]
    circles, segs = [], []
    L = LEN[speed]
    for (x, y), ang in zip(POS, POS_ANG):
        cx, cy = ox + x * B, oy + y * B
        d = (math.cos(math.radians(ang)), math.sin(math.radians(ang)))
        circles.append({"center": P(cx, cy), "r": PR, "fill": fill, "color": line, "width": 1.25})
        segs.append(seg((cx + PR * d[0], cy + PR * d[1]), (cx + (PR + L) * d[0], cy + (PR + L) * d[1]), INK, 1.75, arrow="end"))
    return polys, circles, segs


def particle_fig(speed, alt, caption=None, **extra):
    p, c, s = particle_box(0, 0, speed)
    f = {"type": "geo", "names": False, "polygons": p, "circles": c, "segments": s, "alt": alt}
    if caption:
        f["caption"] = caption
    f.update(extra)
    return f


def count_particles(fig):
    return sum(1 for c in fig.get("circles", []) if abs(c["r"] - PR) < 1e-9)


# ---------------------------------------------------------------- example data (예시)
T_MIN = list(range(0, 9))
WARM = [50, 40, 34, 30, 28, 27, 26, 26, 26]
COLD = [14, 19, 22, 24, 25, 25, 26, 26, 26]
MILK_T = [0, 2, 4, 6, 8, 10]
MILK = [4, 19, 25, 27, 28, 28]
BATH = [40, 32, 30, 29, 28, 28]
CHK_T = [0, 1, 2, 3, 4, 5]
CHK_A = [70, 57, 50, 47, 45, 45]
CHK_B = [20, 33, 40, 43, 45, 45]


def meet(ts, hot, cold):
    for t, h, c in zip(ts, hot, cold):
        if h == c:
            return t, h
    raise AssertionError("never meet")


def check_series(ts, hot, cold, ratio):
    """hot falls, cold rises, never cross, and (heat balance) drop ≈ ratio × rise within 1.5 °C."""
    assert all(a >= b for a, b in zip(hot, hot[1:])), hot
    assert all(a <= b for a, b in zip(cold, cold[1:])), cold
    assert all(h >= c for h, c in zip(hot, cold))
    t_eq, T_eq = meet(ts, hot, cold)
    assert all(h == c == T_eq for t, h, c in zip(ts, hot, cold) if t >= t_eq)
    assert cold[0] < T_eq < hot[0]
    for h, c in zip(hot, cold):
        assert abs((hot[0] - h) - ratio * (c - cold[0])) <= 1.5, (h, c)
    return t_eq, T_eq


EQ1 = check_series(T_MIN, WARM, COLD, 2)       # 바깥 찬물이 안쪽 물의 약 2배
EQ2 = check_series(MILK_T, BATH, MILK, 0.5)    # 물이 우유의 약 2배 → 물의 온도 변화가 절반
EQ3 = check_series(CHK_T, CHK_A, CHK_B, 1)     # 같은 양
assert EQ1 == (6, 26) and EQ2 == (8, 28) and EQ3 == (4, 45)
# mixing equal amounts of 50 °C and 14 °C water (worksheet 5) → at most the average
MIX = (50 + 14) / 2
assert MIX == 32


# ---------------------------------------------------------------- line graph drawn with geo
def graph(ts, series, T_lo, T_hi, T_step, lab_every, xs, ys, alt, caption=None, eq_mark=None, t_ticks=None):
    """series: list of dict(values, color, marker('circle'|'square'), label, label_at(t, T))."""
    X = lambda t: t * xs
    Y = lambda T: (T - T_lo) / T_step * ys
    tmax = max(ts)
    xmax, ymax = X(tmax), Y(T_hi)
    segs, polys, circles, texts = [], [], [], []
    for t in (t_ticks or ts):
        if t > 0:
            segs.append(seg((X(t), 0), (X(t), ymax), GRIDC, 0.75))
        texts.append(txt((X(t), -0.38), str(t)))
    T = T_lo + T_step
    while T <= T_hi + 1e-9:
        segs.append(seg((0, Y(T)), (xmax, Y(T)), GRIDC, 0.75))
        T += T_step
    T = T_lo
    while T <= T_hi + 1e-9:
        if (T - T_lo) % lab_every == 0:
            texts.append(txt((-0.55, Y(T)), str(T)))
        T += T_step
    segs.append(seg((0, 0), (xmax + 0.45, 0), INK, 1.5, arrow="end"))
    segs.append(seg((0, 0), (0, ymax + 0.45), INK, 1.5, arrow="end"))
    texts.append(txt((xmax / 2, -0.95), "시간(분)", bold=True))
    texts.append(txt((0.2, ymax + 0.85), "온도(°C)", bold=True))
    for s in series:
        v = s["values"]
        assert len(v) == len(ts)
        polys.append({"pts": [P(X(t), Y(T)) for t, T in zip(ts, v)], "open": True, "fill": "none", "color": s["color"], "width": 2.5})
        for t, T in zip(ts, v):
            assert T_lo <= T <= T_hi
            if s["marker"] == "circle":
                circles.append({"center": P(X(t), Y(T)), "r": 0.1, "fill": s["color"], "color": s["color"], "width": 1})
            else:
                h = 0.09
                polys.append({"pts": [P(X(t) - h, Y(T) - h), P(X(t) + h, Y(T) - h), P(X(t) + h, Y(T) + h), P(X(t) - h, Y(T) + h)], "fill": "FFFFFF", "color": s["color"], "width": 1.75})
        lt, lT = s["label_at"]
        texts.append(txt((X(lt), Y(lT)), s["label"], bold=True, color=s["color"], anchor="left"))
    if eq_mark:
        t, T, label = eq_mark
        segs.append(seg((X(t), Y(T)), (X(t), 0), "6B7280", 1.25, dash=True))
        texts.append(txt((X(t) + 0.2, Y(T) + 0.55), label, bold=True, anchor="left", bg=True))
    f = {"type": "geo", "names": False, "polygons": polys, "segments": segs, "circles": circles, "texts": texts, "alt": alt}
    if caption:
        f["caption"] = caption
    return f


# ---------------------------------------------------------------- thermometer drawn with geo
def thermometer(reading, alt, lo=0, hi=50):
    k = 0.1  # units per °C
    segs, texts = [], []
    tube = {"pts": [P(-0.17, -0.25), P(0.17, -0.25), P(0.17, (hi - lo) * k + 0.4), P(-0.17, (hi - lo) * k + 0.4)], "fill": "FFFFFF", "width": 1.5, "color": "64748B"}
    liquid = {"pts": [P(-0.07, -0.4), P(0.07, -0.4), P(0.07, (reading - lo) * k), P(-0.07, (reading - lo) * k)], "fill": WARM_LINE, "width": 0}
    for T in range(lo, hi + 1):
        y = (T - lo) * k
        L = 0.42 if T % 10 == 0 else 0.3 if T % 5 == 0 else 0.2
        segs.append(seg((0.17, y), (0.17 + L, y), INK, 1.25 if T % 10 == 0 else 0.75))
        if T % 10 == 0:
            texts.append(txt((0.95, y), str(T)))
    texts.append(txt((0.95, (hi - lo) * k + 0.75), "°C", bold=True))
    bulb = {"center": P(0, -0.6), "r": 0.32, "fill": WARM_LINE, "color": "64748B", "width": 1.5}
    # the top of the liquid column must sit exactly on the reading
    assert abs(liquid["pts"][2][1] - (reading - lo) * k) < 1e-9
    return {"type": "geo", "names": False, "polygons": [tube, liquid], "circles": [bulb], "segments": segs, "texts": texts, "alt": alt, "max_unit": 0.75}


# ---------------------------------------------------------------- apparatus (cup in a bowl), side view
def apparatus():
    polys = [
        # cold water in the bowl (drawn first, under the outlines); bowl side: (3,0)→(3.5,2.2)
        {"pts": [P(-3, 0), P(3, 0), P(3.386, 1.7), P(-3.386, 1.7)], "fill": "DCEBF7", "width": 0},
        {"pts": [P(-3.5, 2.2), P(-3, 0), P(3, 0), P(3.5, 2.2)], "open": True, "fill": "none", "color": "64748B", "width": 2.25},
        # warm water in the small cup; cup side: (1.25,0.12)→(1.4,2.75)
        {"pts": [P(-1.25, 0.12), P(1.25, 0.12), P(1.341, 1.7), P(-1.341, 1.7)], "fill": "F9D3C3", "width": 0},
        {"pts": [P(-1.4, 2.75), P(-1.25, 0.12), P(1.25, 0.12), P(1.4, 2.75)], "open": True, "fill": "none", "color": "374151", "width": 2.5},
        # thermometer bodies
        {"pts": [P(-0.95, 3.1), P(-0.25, 3.1), P(-0.25, 3.7), P(-0.95, 3.7)], "fill": "E5E7EB", "width": 1.25, "color": "4B5563"},
        {"pts": [P(1.95, 3.1), P(2.65, 3.1), P(2.65, 3.7), P(1.95, 3.7)], "fill": "E5E7EB", "width": 1.25, "color": "4B5563"},
    ]
    segs = [seg((-0.6, 0.45), (-0.6, 3.1), "4B5563", 2.5), seg((2.3, 0.4), (2.3, 3.1), "4B5563", 2.5)]
    texts = [
        txt((0.45, 0.9), "따뜻한\n물", bold=True),
        txt((-2.25, 0.85), "찬물", bold=True),
        txt((-2.05, 3.4), "온도계"),
        txt((3.7, 3.4), "온도계"),
        txt((0.65, 2.45), "작은 컵"),
        txt((-3.55, 2.65), "큰 그릇"),
    ]
    return {"type": "geo", "names": False, "polygons": polys, "segments": segs, "texts": texts,
            "alt": "옆에서 본 실험 장치: 찬물이 담긴 큰 그릇 가운데에 따뜻한 물이 담긴 작은 컵이 있고, 안쪽 물과 바깥 물에 온도계가 하나씩 꽂혀 있음"}


# ---------------------------------------------------------------- two-stage heat → equilibrium (particles)
def stages_fig():
    polys, circles, segs, texts = [], [], [], []
    for ox, sp in ((0, "warm"), (B, "cold"), (6.4, "mid"), (6.4 + B, "mid")):
        p, c, s = particle_box(ox, 0, sp)
        polys += p
        circles += c
        segs += s
    segs.append(seg((1.3, 2.75), (3.1, 2.75), "E9762B", 4, arrow="end"))
    texts.append(txt((2.2, 3.3), "열", size="label", bold=True, color="C2571A"))
    segs.append(seg((4.85, 1.1), (5.95, 1.1), "6B7280", 2.5, arrow="end"))
    texts += [
        txt((B / 2, -0.4), "50 °C", bold=True, color=WARM_LINE), txt((B * 1.5, -0.4), "14 °C", bold=True, color=COLD_LINE),
        txt((6.4 + B / 2, -0.4), "26 °C", bold=True), txt((6.4 + B * 1.5, -0.4), "26 °C", bold=True),
        txt((B, -1.05), "처음", size="label", bold=True), txt((6.4 + B, -1.05), "열평형", size="label", bold=True),
        txt((6.4 + B, 2.75), "온도가 같아요", bold=True, color="7A4E8A"),
    ]
    return {"type": "geo", "names": False, "polygons": polys, "circles": circles, "segments": segs, "texts": texts,
            "alt": "입자 모형: 처음에는 왼쪽 따뜻한 물(50 °C)의 입자 화살표가 길고 오른쪽 찬물(14 °C)의 화살표가 짧으며, 따뜻한 물에서 찬물 쪽으로 ‘열’ 화살표가 있음. 시간이 지나 열평형이 되면 두 물(26 °C) 모두 화살표 길이가 중간으로 같아짐"}


def cover_fig():
    polys, circles, segs, texts = [], [], [], []
    for ox, sp in ((0, "warm"), (B, "cold")):
        p, c, s = particle_box(ox, 0, sp)
        polys += p
        circles += c
        segs += s
    texts += [txt((B / 2, -0.45), "따뜻한 물", bold=True, color=WARM_LINE), txt((B * 1.5, -0.45), "찬물", bold=True, color=COLD_LINE),
              txt((B, 2.75), "?", size="label", bold=True)]
    return {"type": "geo", "names": False, "polygons": polys, "circles": circles, "segments": segs, "texts": texts,
            "alt": "맞닿은 따뜻한 물과 찬물의 입자 모형, 가운데 위에 물음표", "max_unit": 0.75}


# ---------------------------------------------------------------- figures
F_COLD = particle_fig("cold", "찬물의 입자 모형: 입자 7개, 운동을 나타내는 화살표가 짧음", caption="찬물", max_unit=1.25)
F_WARM = particle_fig("warm", "따뜻한 물의 입자 모형: 입자 7개, 운동을 나타내는 화살표가 김", caption="따뜻한 물", max_unit=1.25)
F_OPT = {
    "가": particle_fig("mid", "가: 입자 7개, 화살표 길이 중간", max_unit=1.3),
    "나": particle_fig("warm", "나: 입자 7개, 화살표가 가장 김", max_unit=1.3),
    "다": particle_fig("cold", "다: 입자 7개, 화살표가 가장 짧음", max_unit=1.3),
}
for f in [F_COLD, F_WARM, *F_OPT.values()]:
    assert count_particles(f) == NPART           # same amount of water → same number of particles
    assert len({c["r"] for c in f["circles"]}) == 1  # same particle size

F_GRAPH1 = graph(
    T_MIN, [
        {"values": WARM, "color": WARM_LINE, "marker": "circle", "label": "안쪽 따뜻한 물", "label_at": (0.25, 51.5)},
        {"values": COLD, "color": COLD_LINE, "marker": "square", "label": "바깥 찬물", "label_at": (0.25, 11.5)},
    ], 10, 50, 5, 10, 0.95, 0.62,
    "예시 자료로 그린 꺾은선그래프: 가로축 시간 0~8분, 세로축 온도 10~50 °C. 안쪽 따뜻한 물은 50, 40, 34, 30, 28, 27, 26, 26, 26 °C로 내려가고, 바깥 찬물은 14, 19, 22, 24, 25, 25, 26, 26, 26 °C로 올라가 6분부터 두 선이 26 °C에서 만남",
    caption="예시 자료로 그린 그래프", eq_mark=(6, 26, "열평형"))
F_GRAPH2 = graph(
    MILK_T, [
        {"values": BATH, "color": WARM_LINE, "marker": "circle", "label": "따뜻한 물", "label_at": (1.0, 40.5)},
        {"values": MILK, "color": COLD_LINE, "marker": "square", "label": "우유", "label_at": (1.3, 5.0)},
    ], 0, 40, 5, 10, 0.68, 0.5,
    "예시 그래프: 차가운 우유병을 따뜻한 물에 담갔을 때. 가로축 시간 0~10분(2분 간격), 세로축 온도 0~40 °C. 따뜻한 물은 40, 32, 30, 29, 28, 28 °C, 우유는 4, 19, 25, 27, 28, 28 °C",
    caption="우유병을 따뜻한 물에 담갔어요(예시)")
F_APP = apparatus()
F_STAGES = stages_fig()
F_THERMO = thermometer(23, "알코올 온도계: 0~50 °C 눈금(1 °C마다 작은 눈금), 빨간 액체 기둥 끝이 23 °C 눈금에 있음")
F_THERMO_SUP = thermometer(18, "알코올 온도계: 0~50 °C 눈금, 빨간 액체 기둥 끝이 18 °C 눈금에 있음")

T_TABLE = {"headers": ["시간(분)"] + [str(t) for t in CHK_T], "rows": [["가(°C)"] + [str(v) for v in CHK_A], ["나(°C)"] + [str(v) for v in CHK_B]],
           "widths": [0.22] + [0.13] * 6, "size": 20}
assert abs(sum(T_TABLE["widths"]) - 1) < 1e-9

PRE = "KR22-G05-SCI-HEAT-L01"

# ---------------------------------------------------------------- lesson content
C = {
    "status": "제작 완료",
    "objectives": [
        {"id": "A", "text": "같은 양의 물을 나타낸 입자 모형을 비교해 입자 운동이 활발할수록 온도가 높다는 것을 설명하고, 온도가 달라도 입자의 수와 크기는 그대로라고 말한다.",
         "evidence": "온도와 입자 운동(S03), 어느 물이 더 따뜻할까(S04), 누구 말이 맞을까(S05), 혼자 해 보기 ①(S13), 활동지 4",
         "success": "화살표가 긴(입자 운동이 활발한) 모형을 온도가 높은 물로 고르고, ‘물을 데우면 입자가 커지거나 많아진다’는 생각을 그림의 입자 수(7개)와 크기로 반박한다."},
        {"id": "B", "text": "따뜻한 물이 든 컵을 찬물에 넣는 실험 결과를 근거로, 열이 온도가 높은 물에서 낮은 물로 이동해 따뜻한 물은 식고 찬물은 데워지며 결국 두 물의 온도가 같아지는 것(열평형)을 입자 운동과 함께 설명한다.",
         "evidence": "예상(S06, 활동지 1), 컵 속 컵 실험과 결과(S07, S08, 활동지 1·2), 열평형(S10), 누구 말이 맞을까(S11), 혼자 해 보기 ②(S13), 체온계(S15), 활동지 5",
         "success": "‘따뜻한 물의 열이 찬물로 이동해 따뜻한 물은 온도가 내려가고 찬물은 올라가 같아진다’고 말하고, ‘찬 기운이 이동한다’는 생각을 바로잡으며, 체온계를 몇 분 기다리는 까닭을 열평형으로 말한다."},
        {"id": "C", "text": "시간–온도 기록을 꺾은선그래프로 나타내고, 그래프에서 두 물체가 열평형에 이른 때와 열평형 온도를 읽는다.",
         "evidence": "실험 기록(S07, 활동지 2), 그래프로 나타내요(S09, 활동지 3), 그래프를 읽어요(S12), 혼자 해 보기 ③(S13)",
         "success": "가로축 시간(분)·세로축 온도(°C)에 점을 찍어 두 선을 그리고, 두 선이 만나는 시각과 온도(예시: 6분, 26 °C)를 단위를 붙여 읽는다."},
    ],
    "materials": [
        "주방용 디지털 온도계 1~2개(없으면 100 °C까지 재는 알코올 온도계)",
        "작은 스테인리스 컵(또는 얇은 유리컵), 작은 컵이 들어가는 큰 그릇, 쟁반, 행주",
        "따뜻한 물(약 50 °C, 부모가 준비), 찬물(냉장고 물이나 수돗물)",
        "시계나 휴대 전화 타이머, 활동지, 연필, 빨간색·파란색 색연필",
    ],
    "boundary": "온도의 뜻과 입자 운동(화살표 길이로 나타낸 모형), 온도가 다른 두 물체 사이에서 열이 높은 쪽에서 낮은 쪽으로 이동하는 것, 열평형의 뜻, 시간–온도 기록을 꺾은선그래프로 나타내고 열평형에 이른 때와 온도를 읽는 것, 생활 속 열평형(체온계)을 다룬다. 전도·대류·복사(다음 차시 ‘열의 이동 방식’), 비열과 열량 계산, 절대 온도(K), 입자의 실제 크기와 빠르기, 상태 변화는 다루지 않는다. 화면의 그래프와 표의 수는 이해를 돕기 위한 예시이며, 실험 결과는 물의 양·컵의 재질·방의 온도에 따라 달라진다. 입자 그림은 눈에 보이지 않는 입자를 나타낸 모형이다.",
    "misconceptions": [
        {"id": "M1", "text": "물을 데우면 입자가 커지거나 입자의 수가 많아진다고 생각한다.",
         "response": "S03·S04에서 같은 양의 물은 입자 수(7개)와 크기가 같고 화살표(운동)만 다르다는 것을 짚고, S05에서 두 생각을 비교한다."},
        {"id": "M2", "text": "찬물의 ‘차가운 기운(냉기)’이 따뜻한 물로 이동해서 따뜻한 물이 식는다고 생각한다.",
         "response": "S08의 결과에서 찬물의 온도가 올라간 것을 증거로, 이동한 것은 따뜻한 물의 열이라는 것을 S10·S11에서 말하게 한다."},
        {"id": "M3", "text": "열평형이 되면 입자 운동이 멈추거나, 열평형 온도가 처음 높은 온도(또는 낮은 온도)와 같다고 생각한다.",
         "response": "S09 그래프에서 열평형 온도(26 °C)가 처음 두 온도(50 °C, 14 °C) 사이라는 것을 읽고, S10에서 열평형 뒤에도 입자는 계속 움직인다(두 물의 활발한 정도가 같아짐)고 알려 준다."},
    ],
    "safety": [
        "따뜻한 물은 부모님이 준비해 붓습니다. 끓는 물이나 정수기 온수를 그대로 쓰지 말고 찬물을 섞어 50 °C 안팎으로 맞춘 뒤 온도계로 확인합니다.",
        "컵과 그릇은 쟁반에 올려 식탁 가운데에 두고, 실험 중에는 옮기지 않습니다. 아이는 물과 컵을 만지지 않고 온도계의 숫자를 읽고 기록합니다.",
        "탐침 온도계는 끝이 뾰족하니 부모님이 옮기고, 쓰지 않을 때는 뚜껑을 씌웁니다. 전자 온도계는 탐침만 물에 넣고 본체가 젖지 않게 합니다.",
        "유리 온도계는 깨질 수 있습니다. 깨지면 아이는 손대지 않고 부모님이 치웁니다. 엎지른 물은 바로 닦습니다.",
    ],
    "checks": [
        {"type": "blank", "expr": "50 − 26 = □", "answer": 24, "where": "S09 예시: 안쪽 따뜻한 물의 온도 변화(°C)"},
        {"type": "blank", "expr": "26 − 14 = □", "answer": 12, "where": "S09 예시: 바깥 찬물의 온도 변화(°C)"},
        {"type": "compare", "values": ["50 − 26", "2 × (26 − 14)"], "rel": "=", "where": "S09 예시: 바깥 물이 안쪽 물의 2배라서 내려간 온도가 올라간 온도의 2배"},
        {"type": "compare", "values": ["14", "26"], "rel": "<", "where": "S09·S10: 열평형 온도는 처음 찬물보다 높음"},
        {"type": "compare", "values": ["26", "50"], "rel": "<", "where": "S09·S10: 열평형 온도는 처음 따뜻한 물보다 낮음"},
        {"type": "blank", "expr": "40 − 28 = □", "answer": 12, "where": "S12 예시: 따뜻한 물이 내려간 온도(°C)"},
        {"type": "blank", "expr": "28 − 4 = □", "answer": 24, "where": "S12 예시: 우유가 올라간 온도(°C)"},
        {"type": "blank", "expr": "70 − 45 = □", "answer": 25, "where": "S13 ③ 가가 내려간 온도(°C)"},
        {"type": "blank", "expr": "45 − 20 = □", "answer": 25, "where": "S13 ③ 나가 올라간 온도(°C) — 같은 양이라 변화가 같음"},
        {"type": "blank", "expr": "(50 + 14) ÷ 2 = □", "answer": 32, "where": "활동지 5: 같은 양을 섞을 때 열을 잃지 않으면 32 °C(실제로는 조금 낮음)"},
    ],
    "break_after": "S08",
}

S = []
S.append({
    "id": "S01", "kind": "cover", "section": "도입", "purpose": "오늘의 질문과 목표", "role": "intro", "objectives": ["A", "B", "C"],
    "title": "온도와 열평형",
    "question": "따뜻한 물과 찬물이 만나면\n온도는 어떻게 될까요?",
    "goals": ["① 온도를 입자의 운동으로 설명해요.", "② 두 물이 열평형에 이르는 과정을 그래프로 나타내요."],
    "figure": cover_fig(),
    "notes": {
        "목적": "오늘 할 일(입자 모형, 컵 속 컵 실험, 그래프)을 알리고 질문에 궁금증을 갖게 합니다.",
        "시간": "약 2분",
        "말하기": ["“뜨거운 국을 그릇에 두면 시간이 지나 어떻게 돼? 냉장고에서 꺼낸 우유는?”",
                 "“오늘은 따뜻한 물과 찬물을 맞닿게 해 두고 온도를 1분마다 재서 그래프로 그려 볼 거야. 그 전에 ‘온도’가 물속에서 무엇이 다른 건지 그림으로 먼저 보자.”"],
        "예상답": ["“국은 식고 우유는 미지근해져요.” “둘 다 중간 온도가 될 것 같아요.” 어떤 답이든 괜찮습니다. 맞고 틀림을 말하지 않고 넘어갑니다."],
        "막히면": ["목욕물이 시간이 지나면 식는 경험을 떠올리게 합니다."],
        "주의": ["준비물: 주방용 온도계(가능하면 2개), 작은 스테인리스 컵, 작은 컵이 들어가는 큰 그릇, 쟁반, 타이머, 빨강·파랑 색연필. 따뜻한 물(약 50 °C)은 S07 직전에 부모님이 준비합니다.",
               "표지의 그림은 오늘 S03에서 배울 ‘입자 모형’입니다. 지금은 설명하지 않아도 됩니다."],
    },
})
S.append({
    "id": "S02", "kind": "practice", "section": "도입", "purpose": "선수 학습 확인(온도계 읽기, 열의 이동 방향)", "role": "prior", "objectives": [],
    "title": "지난 학년 기억하기",
    "problems": [{"text": "오른쪽 온도계의 온도를\n단위를 붙여 읽어요."},
                 {"text": "차가운 컵을 손으로 감싸면\n열은 어디에서 어디로?"},
                 {"text": "열이 이동하면 두 물체의\n온도는 어떻게 되나요?"}],
    "figure": F_THERMO,
    "notes": {
        "목적": "5학년 ‘열의 이동’(KR22-G05-SCI-HEAT-L01)에서 배운 온도계 읽기와 열의 이동 방향을 확인합니다. 오늘 실험과 설명에 그대로 씁니다.",
        "시간": "약 2분",
        "말하기": ["“① 빨간 기둥 끝이 어느 눈금에 있어? 작은 눈금 한 칸은 1 °C야. 단위까지 붙여 읽어 볼래?”",
                 "“② 손이 따뜻하고 컵이 차가울 때 열은 어느 쪽으로 갈까?”",
                 "“③ 열이 계속 이동하면 손과 컵의 온도는 어떻게 될까?”"],
        "정답": ["① 23 °C(섭씨 이십삼 도)", "② 손에서 컵으로(온도가 높은 곳에서 낮은 곳으로)", "③ 손은 온도가 내려가고 컵은 올라가, 두 온도가 점점 같아진다(차이가 줄어든다)"],
        "막히면": ["두 문제 이상 흔들리면 S17(보충)을 먼저 합니다. 보충으로도 어려우면 5학년 ‘열의 이동’(KR22-G05-SCI-HEAT-L01)의 온도계 읽기와 손으로 감싸기 실험을 먼저 다시 합니다."],
        "주의": ["①에서 20과 30 사이의 작은 눈금을 세지 못하면 20에서 한 칸씩 손가락으로 세게 합니다.", "③의 ‘점점 같아진다’가 오늘 배울 ‘열평형’입니다. 이름은 아직 말하지 않습니다."],
    },
})
S.append({
    "id": "S03", "kind": "concept", "section": "개념", "purpose": "온도와 입자 운동(입자 모형)", "role": "teach", "objectives": ["A"],
    "title": "온도와 입자 운동",
    "text": "물질은 눈에 보이지 않는 아주 작은 알갱이(입자)로 되어 있어요.",
    "figures": [F_COLD, F_WARM],
    "points": [{"title": "온도", "text": "차갑고 따뜻한 정도를\n숫자로 나타낸 것"},
               {"title": "화살표", "text": "길수록 입자가\n빠르게 움직여요."},
               {"title": "온도가 높으면", "text": "입자 운동이 활발해요.\n수와 크기는 그대로!"}],
    "notes": {
        "목적": "온도를 입자 운동의 활발한 정도로 설명하는 입자 모형을 소개합니다(목표 A, 오해 M1).",
        "시간": "약 3분",
        "말하기": ["“물은 눈에 보이지 않을 만큼 작은 알갱이, 입자로 되어 있어. 동그라미 하나가 입자 하나라고 생각하자. 진짜 모습이 아니라 이해를 돕는 그림, ‘모형’이야.”",
                 "“입자는 가만히 있지 않고 늘 움직여. 화살표가 길수록 빠르게 움직인다는 뜻이야. 찬물과 따뜻한 물 중 화살표가 긴 쪽은?”",
                 "“입자 수를 세어 볼래? 두 그림 모두 몇 개야? 크기는?”",
                 "“그래서 온도가 높다는 건 입자 운동이 활발하다는 뜻이야.”"],
        "예상답": ["“따뜻한 물 화살표가 길어요.” “둘 다 7개고 크기도 같아요.”"],
        "막히면": ["‘활발하다’를 ‘빠르게, 힘차게 움직인다’로 바꾸어 말합니다. 몸으로 찬물 입자는 천천히, 따뜻한 물 입자는 빠르게 걷는 흉내를 내 봐도 좋습니다."],
        "주의": ["‘입자’는 중학교에서 처음 배우는 말입니다. 원자·분자라는 말은 아직 쓰지 않아도 됩니다.",
               "같은 양의 물이므로 입자의 수와 크기는 같습니다. 온도에 따라 달라지는 것은 운동의 빠르기(활발한 정도)입니다."],
    },
})
S.append({
    "id": "S04", "kind": "choice", "section": "연습", "purpose": "입자 모형으로 온도 비교하기", "role": "practice", "objectives": ["A"],
    "title": "어느 물이 더 따뜻할까요?",
    "text": "같은 양의 물을 입자 모형으로 나타냈어요.",
    "options": [{"figure": F_OPT["가"]}, {"figure": F_OPT["나"]}, {"figure": F_OPT["다"]}],
    "question": "가장 따뜻한 물과 가장 차가운 물을 고르고 까닭을 말해요.",
    "notes": {
        "목적": "입자 모형의 화살표 길이(운동의 활발한 정도)로 온도를 비교합니다(목표 A).",
        "시간": "약 2분",
        "말하기": ["“세 그림에서 같은 것은 뭐고 다른 것은 뭐야?”", "“가장 따뜻한 물은 어느 것일까? 어떻게 알았어?”"],
        "정답": ["가장 따뜻한 물: 나(화살표가 가장 김 = 입자 운동이 가장 활발함), 가장 차가운 물: 다(화살표가 가장 짧음). 가는 그 사이.", "같은 것: 입자 수(7개)와 크기. 다른 것: 화살표 길이(운동의 빠르기)."],
        "막히면": ["S03의 두 그림을 다시 보여 주고 ‘화살표가 길다 = 따뜻하다’를 짝지어 말하게 합니다."],
        "주의": ["까닭을 ‘입자가 빠르게 움직여서’처럼 운동으로 말하면 칭찬합니다. ‘색이 빨개서’라고 하면 색은 구별하기 쉽게 칠한 것일 뿐이라고 알려 줍니다(이 장의 그림은 모두 같은 색)."],
    },
})
S.append({
    "id": "S05", "kind": "compare", "section": "연습", "purpose": "오해 비교(데우면 입자가 커지거나 많아진다)", "role": "practice", "objectives": ["A"],
    "title": "누구 말이 맞을까요?",
    "claim": "물을 데우면 입자는 어떻게 될까요?",
    "left": {"title": "토끼", "text": "입자가 커지거나\n더 많아져요."},
    "right": {"title": "곰", "text": "입자의 수와 크기는 그대로고\n더 활발하게 움직여요."},
    "question": "누구 말이 맞을까요? 그림에서 무엇이 증거일까요?",
    "notes": {
        "목적": "‘데우면 입자가 커지거나 많아진다’는 오해를 입자 모형으로 바로잡습니다(목표 A, 오해 M1).",
        "시간": "약 1분",
        "말하기": ["“물을 데워도 물의 양은 그대로지? 그럼 입자 수가 늘어날 수 있을까?”", "“S03 그림에서 찬물과 따뜻한 물의 입자 수와 크기는 어땠어?”"],
        "정답": ["곰. 증거: 같은 양의 물이면 입자의 수(그림에서 7개)와 크기가 같고, 온도가 높은 물은 화살표가 길어 입자가 더 활발하게 움직입니다."],
        "막히면": ["S03으로 돌아가 두 그림의 입자를 함께 세어 봅니다."],
        "주의": ["데우면 부피가 조금 커지는 것(열팽창)은 입자 사이가 멀어지기 때문이며, 입자 자체가 커지는 것이 아닙니다. 열팽창은 뒤 차시에서 배웁니다. 아이가 물으면 이렇게만 알려 줍니다."],
    },
})
S.append({
    "id": "S06", "kind": "table", "section": "연습", "purpose": "실험 전 예상하기(따뜻한 물과 찬물)", "role": "practice", "objectives": ["B", "C"],
    "title": "예상해 봐요",
    "text": "따뜻한 물이 든 작은 컵을 찬물이 든 큰 그릇에 넣으면?",
    "table": {"headers": ["궁금한 것", "내 예상"], "rows": [["안쪽 따뜻한 물의 온도는?", ""], ["바깥 찬물의 온도는?", ""], ["오래 두면 두 물의 온도는?", ""]],
              "widths": [0.62, 0.38], "width": 11.5, "size": 26},
    "key": "예상은 활동지 1에 써요(올라간다·내려간다·그대로).",
    "notes": {
        "목적": "실험 전에 두 물의 온도 변화를 예상합니다(목표 B·C). 결과는 S07에서 재어 확인합니다.",
        "시간": "약 1분",
        "말하기": ["“안쪽 따뜻한 물의 온도는 올라갈까, 내려갈까, 그대로일까? 바깥 찬물은?”", "“아주 오래 두면 두 물의 온도는 어떻게 될까?”"],
        "예상답": ["어떤 예상이든 괜찮습니다. “따뜻한 물은 식고 찬물은 그대로일 것 같아요.” “둘 다 미지근해질 것 같아요.”"],
        "주의": ["결과를 알려 주지 않습니다. 예상은 활동지 1의 ‘내 예상’ 칸에 씁니다."],
    },
})
S.append({
    "id": "S07", "kind": "activity", "section": "연습", "purpose": "컵 속 컵 실험: 1분마다 두 물의 온도 재기", "role": "practice", "objectives": ["B", "C"],
    "title": "1분마다 온도를 재요",
    "steps": ["큰 그릇에 찬물을 반쯤 부어요.", "부모님이 작은 컵에 따뜻한 물을 붓고 그릇에 넣어요.",
              "바로 두 물의 온도를 재요(0분).", "1분마다 8분까지 재어 활동지 2에 써요."],
    "criteria": ["같은 순서로 1분마다", "숫자가 멈추면 읽어요"],
    "criteriaTitle": "기록할 때 확인해요",
    "figure": F_APP,
    "safety": "따뜻한 물과 컵은 부모님만 다뤄요.",
    "notes": {
        "목적": "따뜻한 물과 찬물을 컵 벽을 사이에 두고 맞닿게 한 뒤, 시간에 따른 두 물의 온도를 재어 기록합니다(목표 B·C).",
        "시간": "약 9분",
        "말하기": ["“0분에 두 물의 온도는 각각 몇 °C야? 숫자가 멈출 때까지 기다렸다가 읽고, 활동지 2의 0분 칸에 써 줘.”", "“1분이 지났어. 이번엔 어떻게 변했어? 올라간 쪽과 내려간 쪽은?”", "“두 물의 온도 차이가 어떻게 되어 가고 있어?”"],
        "예상답": ["“따뜻한 물은 점점 내려가고 찬물은 점점 올라가요. 차이가 줄어들어요.”",
                "예시 기록(안쪽 / 바깥): 0분 50 / 14, 1분 40 / 19, 2분 34 / 22, 3분 30 / 24, 4분 28 / 25, 5분 27 / 25, 6분 26 / 26, 7분 26 / 26, 8분 26 / 26 °C. 물의 양·컵·방의 온도에 따라 수는 달라집니다."],
        "막히면": ["온도계가 하나뿐이면 늘 ‘안쪽 → 바깥’ 순서로 재빨리 잽니다. 숫자가 멈출 때까지 3~5초 기다린 뒤 읽습니다.",
                "8분이 지나도 두 온도가 2 °C 넘게 다르면 2분 더 잽니다(유리·도자기 컵은 스테인리스 컵보다 느립니다)."],
        "주의": ["이 장의 9분 가운데 8분은 1분마다 재는 시간입니다. 타이머를 1분 간격으로 맞춰 두면 편합니다.", "준비: 큰 그릇의 찬물 높이가 작은 컵의 물 높이와 비슷하게 합니다. 바깥 물이 너무 많으면 컵이 뜨거나 넘칩니다. 바깥 물은 안쪽 물의 약 2배가 되게 합니다.",
               "따뜻한 물은 부모님이 50 °C 안팎으로 맞춰 붓습니다. 끓는 물은 쓰지 않습니다. 컵을 넣은 뒤에는 그릇과 컵을 옮기지 않습니다.",
               "부모님이 1분마다 바깥 물을 숟가락으로 한두 번 살살 저으면 온도가 고르게 됩니다.",
               "플라스틱·종이컵은 열이 천천히 전달되어 오래 걸립니다. 이 차이는 다음 차시 ‘열의 이동 방식’에서 다룹니다."],
    },
})
S.append({
    "id": "S08", "kind": "table", "section": "연습", "purpose": "결과 정리(처음과 나중의 온도)", "role": "practice", "objectives": ["B", "C"],
    "title": "결과를 정리해요",
    "text": "활동지 2를 보며 빈칸을 말로 채워요.",
    "table": {"headers": ["", "처음 온도(°C)", "8분 뒤 온도(°C)", "어떻게 변했나요?"],
              "rows": [["안쪽 따뜻한 물", "", "", ""], ["바깥 찬물", "", "", ""]],
              "widths": [0.28, 0.22, 0.22, 0.28], "width": 11.5, "size": 24, "firstColHead": True},
    "key": "두 물의 온도는 마지막에 어떻게 되었나요? 예상과 같았나요?",
    "notes": {
        "목적": "처음과 나중의 온도를 정리하고 예상과 비교합니다(목표 B·C, 오해 M2).",
        "시간": "약 2분",
        "말하기": ["“안쪽 물은 처음 몇 °C였고 8분 뒤에는 몇 °C야? 바깥 물은?”", "“올라간 물과 내려간 물은 각각 어느 쪽이야? 마지막에는?”", "“활동지 1의 예상과 같았어?”"],
        "예상답": ["안쪽 따뜻한 물: 온도가 내려감(예시 50 °C → 26 °C), 바깥 찬물: 온도가 올라감(예시 14 °C → 26 °C), 마지막에는 두 물의 온도가 같아짐(또는 거의 같아짐)."],
        "막히면": ["활동지 2의 0분과 8분 칸에만 손가락을 대고 큰 수, 작은 수를 비교합니다."],
        "주의": ["화면의 빈칸은 아이가 말로 채우는 자리입니다. 수는 집마다 다릅니다.", "찬물의 온도가 올라갔다는 것이 S11(찬 기운이 이동한다는 오해)의 증거가 됩니다. 꼭 짚어 둡니다.",
               "지치면 여기서 쉬고, 다음에 S09부터 이어도 됩니다."],
    },
})
S.append({
    "id": "S09", "kind": "concept", "section": "개념", "purpose": "시간–온도 기록을 꺾은선그래프로 나타내기(예시)", "role": "teach", "objectives": ["C"],
    "title": "그래프로 나타내요(예시)",
    "figure": F_GRAPH1,
    "figureRatio": 0.6,
    "points": [{"title": "가로축·세로축", "text": "가로는 시간(분),\n세로는 온도(°C)"},
               {"title": "그리기", "text": "1분마다 점을 찍고\n선으로 이어요."},
               {"title": "읽기", "text": "두 선이 만나는 때와\n온도를 찾아요."}],
    "notes": {
        "목적": "시간–온도 기록을 꺾은선그래프로 나타내는 방법을 예시 자료로 보여 주고, 두 선이 만나는 점에서 열평형에 이른 때와 온도를 읽습니다(목표 C, 오해 M3).",
        "시간": "약 3분",
        "말하기": ["“가로축은 시간, 세로축은 온도야. 0분에 따뜻한 물은 50 °C니까 여기에 점을 찍었어.”",
                 "“빨간 동그라미 선과 파란 네모 선은 각각 무엇일까? 시간이 지나면 두 선은 어떻게 돼?”",
                 "“두 선은 몇 분에 만나? 그때 온도는? 그 뒤로는?”",
                 "“이제 활동지 3에 우리가 잰 기록으로 그래프를 그려 보자. 처음 몇 점은 같이 찍고, 나머지는 수업 뒤에 해도 돼.”"],
        "정답": ["예시 그래프: 안쪽 따뜻한 물(빨강·동그라미)은 내려가고 바깥 찬물(파랑·네모)은 올라가며, 6분에 26 °C에서 만난 뒤 둘 다 26 °C로 그대로입니다.",
               "열평형 온도 26 °C는 처음 두 온도(50 °C와 14 °C) 사이에 있습니다."],
        "막히면": ["0분의 두 점만 같이 찍고, 1분의 점은 아이가 찍게 합니다. 세로 눈금 한 칸이 5 °C라는 것을 손가락으로 짚습니다."],
        "주의": ["이 그래프는 예시 자료입니다(바깥 물이 안쪽 물의 약 2배일 때). 우리 집 기록은 다를 수 있습니다.",
               "예시에서 따뜻한 물은 24 °C 내려가고 찬물은 12 °C 올라갔습니다. 바깥 찬물이 2배 많아서 온도가 덜 변한 것입니다. 물체마다 온도 변화가 다른 까닭(비열)은 뒤 차시에서 배웁니다. 아이가 물으면 ‘물이 많을수록 온도가 천천히 변한다’까지만 말합니다.",
               "꺾은선그래프는 초등학교 4학년 수학에서 배웠습니다. 세로축의 0~10 °C를 생략한 것(10부터 시작)을 알려 줍니다."],
    },
})
S.append({
    "id": "S10", "kind": "concept", "section": "개념", "purpose": "결과로 설명하기(열의 이동과 열평형, 입자 모형)", "role": "teach", "objectives": ["A", "B"],
    "title": "열은 높은 온도에서 낮은 온도로",
    "figure": F_STAGES,
    "points": [{"title": "열", "text": "온도가 높은 물체에서\n낮은 물체로 이동해요."},
               {"title": "입자로 보면", "text": "활발한 입자가 운동을\n옆 입자에 전해요."},
               {"title": "열평형", "text": "두 물체의 온도가\n같아진 상태"}],
    "notes": {
        "목적": "실험 결과를 증거로, 열이 온도가 높은 물에서 낮은 물로 이동해 두 물의 온도가 같아지는 것(열평형)을 입자 모형과 함께 설명합니다(목표 A·B, 오해 M2·M3).",
        "시간": "약 3분",
        "말하기": ["“따뜻한 물의 온도는 내려가고 찬물의 온도는 올라갔지? 따뜻한 물의 열이 찬물로 이동했기 때문이야. 열은 온도가 높은 곳에서 낮은 곳으로 이동해.”",
                 "“입자로 보면, 따뜻한 물의 활발한 입자가 컵 벽을 지나 찬물 쪽 입자에 운동을 조금씩 전해. 그래서 따뜻한 물 입자는 느려지고 찬물 입자는 빨라져.”",
                 "“두 물의 온도가 같아지면 열은 더 이상 한쪽으로 이동하지 않아. 이 상태를 ‘열평형’이라고 해.”",
                 "“열평형이 되면 입자는 멈출까?”"],
        "예상답": ["“따뜻한 물의 열이 찬물로 갔어요.” “열평형이 돼도 입자는 계속 움직여요. 두 물의 빠르기가 같아질 뿐이에요.”"],
        "막히면": ["S08의 표를 다시 보며 ‘내려간 쪽 = 열을 준 쪽, 올라간 쪽 = 열을 받은 쪽’으로 짝지어 말합니다."],
        "주의": ["열평형이 되어도 입자 운동은 멈추지 않습니다. 두 물체의 입자 운동의 활발한 정도(온도)가 같아질 뿐입니다(오해 M3).",
               "그림의 °C는 S09의 예시 자료입니다. 열평형 온도는 처음 두 온도 사이에 있습니다.",
               "열은 물질이 아니라 이동하는 에너지입니다. ‘열이 들어 있다’보다 ‘열이 이동한다’고 말하게 합니다."],
    },
})
S.append({
    "id": "S11", "kind": "compare", "section": "연습", "purpose": "오해 비교(찬 기운이 이동한다)", "role": "practice", "objectives": ["B"],
    "title": "누구 말이 맞을까요?",
    "claim": "찬물에 넣은 컵의 따뜻한 물이 식었어요. 왜 식었을까요?",
    "left": {"title": "토끼", "text": "찬물의 차가운 기운이\n따뜻한 물로 들어갔어요."},
    "right": {"title": "곰", "text": "따뜻한 물의 열이\n찬물로 빠져나갔어요."},
    "question": "누구 말이 맞을까요? 찬물의 온도가 올라간 것과 이어 말해요.",
    "notes": {
        "목적": "‘찬 기운(냉기)이 이동한다’는 오해를 실험 결과(찬물의 온도가 올라감)로 바로잡습니다(목표 B, 오해 M2).",
        "시간": "약 2분",
        "말하기": ["“토끼 말이 맞다면 찬물은 차가운 기운을 내주었으니 어떻게 됐어야 해? 실제로 찬물의 온도는?”"],
        "정답": ["곰. 증거: 찬물의 온도가 올라갔습니다(예시 14 °C → 26 °C). 열은 온도가 높은 따뜻한 물에서 낮은 찬물로 이동했고, 그래서 따뜻한 물은 식고 찬물은 데워졌습니다. ‘차가운 기운’이 이동하는 것이 아니라 열이 빠져나가서 차가워지는 것입니다."],
        "막히면": ["얼음을 손에 쥐면 손이 차가워지는 까닭을 묻고, ‘손의 열이 얼음으로 이동해서’라고 바꾸어 말해 봅니다(5학년에서 배운 예)."],
        "주의": ["일상에서 ‘냉기가 들어온다’고 말해도 괜찮지만, 과학에서는 열의 이동으로 설명한다는 것을 알려 줍니다."],
    },
})
S.append({
    "id": "S12", "kind": "practice", "section": "연습", "purpose": "처음 보는 그래프 읽기(예시)", "role": "practice", "objectives": ["B", "C"],
    "title": "그래프를 읽어요",
    "figure": F_GRAPH2,
    "problems": [{"text": "처음 온도가 더 높은 것은?"},
                 {"text": "열은 어느 쪽에서\n어느 쪽으로 이동했나요?"},
                 {"text": "열평형에 이른 때와\n그때의 온도는?"}],
    "hint": "두 선이 만나는 점을 찾아요.",
    "notes": {
        "목적": "처음 보는 예시 그래프에서 열의 이동 방향과 열평형에 이른 때·온도를 읽습니다(목표 B·C).",
        "시간": "약 2분",
        "말하기": ["“냉장고에서 꺼낸 우유병을 따뜻한 물에 담갔어. 0분에 어느 쪽이 더 높아?”", "“올라간 선은 무엇이고 내려간 선은 무엇이야? 그럼 열은 어디로 갔을까?”", "“두 선은 몇 분에 만나? 그때 몇 °C야?”"],
        "정답": ["① 따뜻한 물(40 °C, 우유는 4 °C)", "② 따뜻한 물에서 우유로", "③ 8분, 28 °C"],
        "막히면": ["가로 눈금이 2분 간격이라는 것을 먼저 짚습니다. 두 선이 처음 같은 높이가 되는 세로줄을 손가락으로 찾게 합니다."],
        "주의": ["예시 자료입니다. 우유병보다 물이 약 2배 많아서 물의 온도는 12 °C만 내려가고 우유는 24 °C 올라갔습니다.",
               "③에서 ‘10분’이라고 하면 두 선이 처음 만난 때를 묻는 것이라고 다시 알려 줍니다."],
    },
})
S.append({
    "id": "S13", "kind": "check", "section": "확인", "purpose": "혼자 해결", "role": "check", "objectives": ["A", "B", "C"],
    "title": "혼자 해 보기",
    "problems": [{"text": "물이 식으면 입자의\n운동과 수는?"},
                 {"text": "뜨거운 국에 찬 숟가락을\n넣으면 열은 어디로?"},
                 {"text": "표에서 열평형에 이른\n때와 온도는?"}],
    "figure": {"type": "table", **T_TABLE},
    "notes": {
        "목적": "도움 없이 입자 운동과 온도(①), 열의 이동 방향(②), 시간–온도 자료에서 열평형 읽기(③)를 하는지 확인합니다(목표 A·B·C).",
        "시간": "약 3분",
        "말하기": ["“이번에는 혼자 답해 볼래? 까닭도 함께 말해 줘.”", "“③의 표는 온도가 다른 두 물체 가와 나를 맞닿게 하고 1분마다 잰 거야.”"],
        "정답": ["① 입자 운동이 둔해진다(느려진다). 입자의 수(와 크기)는 그대로다.",
               "② 국에서 숟가락으로 이동한다. 숟가락은 온도가 올라가고 국은 (조금) 내려가 두 온도가 같아지려 한다.",
               "③ 4분, 45 °C(가는 70 °C → 45 °C, 나는 20 °C → 45 °C)"],
        "막히면": ["바로 알려 주지 말고 “S03에서 찬물의 화살표는?”, “열은 온도가 어느 쪽에서 어느 쪽으로?”, “가와 나의 수가 처음 같아지는 칸은?”이라고만 묻습니다.",
                "도움을 받아 해결했다면 기록표에 ‘도움’으로 표시합니다."],
        "주의": ["①에서 ‘입자가 작아진다’고 하면 오해 M1, ②에서 ‘숟가락의 차가운 기운이 국으로’라고 하면 오해 M2입니다. S05·S11을 다시 봅니다.",
               "③은 활동지 3과 같은 방법으로 그래프를 그려 확인해도 됩니다."],
    },
})
S.append({
    "id": "S14", "kind": "answers", "section": "확인", "purpose": "정답과 피드백", "role": "feedback", "teacher_only": True, "objectives": ["A", "B", "C"],
    "title": "혼자 해 보기 정답",
    "good": [{"text": "① 운동이 둔해짐", "note": "수·크기는\n그대로"}, {"text": "② 국 → 숟가락", "note": "높은 온도\n→ 낮은 온도"}, {"text": "③ 4분, 45 °C", "note": "처음\n같아진 때"}],
    "bad": [{"text": "① 입자가 작아짐", "note": "오해 M1"}, {"text": "② 찬 기운이 이동", "note": "오해 M2"}],
    "explain": "까닭을 입자 운동과 열의 이동으로 말하면 잘한 거예요.",
    "notes": {
        "목적": "아이의 답을 함께 확인하고 흔한 실수를 바로잡습니다. 수업용에만 있는 장입니다.",
        "시간": "약 2분",
        "말하기": ["“네 답과 같은지 볼까? 다르면 어디서 달라졌는지 찾아보자.”"],
        "정답": ["① 입자 운동이 둔해짐(수·크기는 그대로) ② 국에서 숟가락으로 열이 이동 ③ 4분, 45 °C"],
        "막히면": ["①이 틀리면 S03~S05로, ②가 틀리면 S10·S11로, ③이 틀리면 S09·S12로 돌아갑니다."],
        "주의": ["이 장은 학생용 파일에는 없습니다. 아이와 함께 볼 때는 슬라이드 쇼로 보여 줍니다."],
    },
})
S.append({
    "id": "S15", "kind": "choice", "section": "확인", "purpose": "마무리 확인(체온계와 열평형)", "role": "check", "objectives": ["B"],
    "title": "체온계는 왜 기다릴까요?",
    "text": "겨드랑이에 체온계를 넣고 몇 분 기다린 뒤에 읽어요.",
    "options": [{"text": "체온계의 열이\n몸으로 이동해야\n해서"}, {"text": "몸과 체온계가\n열평형이 되어야\n해서"}, {"text": "체온계 속\n입자 수가\n늘어나야 해서"}],
    "question": "고르고, 열의 이동으로 까닭을 말해요.",
    "notes": {
        "목적": "처음 보는 생활 상황에서 열평형을 이용해 설명하는지 확인합니다(목표 B).",
        "시간": "약 2분",
        "말하기": ["“체온계를 넣자마자 읽으면 어떻게 될까? 몸과 체온계 중 어느 쪽 온도가 높아? 열은 어디로 가?”"],
        "정답": ["나. 몸(약 36.5 °C)의 열이 온도가 낮은 체온계로 이동해 체온계의 온도가 올라가고, 몸과 체온계의 온도가 같아질 때(열평형) 읽어야 체온을 알 수 있습니다. 가는 열의 방향이 거꾸로이고, 다는 입자 수가 변하지 않으므로 틀립니다."],
        "막히면": ["S09 그래프에서 두 선이 만나기 전에 읽으면 어떻게 될지 묻습니다."],
        "주의": ["답만 맞히고 까닭을 말하지 못하면 기록표에 ‘답만’으로 적습니다.", "귀에 대는 적외선 체온계는 방식이 달라 금방 잽니다. 오늘은 겨드랑이 체온계만 다룹니다."],
    },
})
S.append({
    "id": "S16", "kind": "summary", "section": "정리", "purpose": "정리와 다음 수업 복습", "role": "review", "objectives": ["A", "B", "C"],
    "title": "오늘 배운 것",
    "key": "온도가 높을수록 입자 운동이 활발해요.\n열은 높은 온도에서 낮은 온도로 이동해 결국 열평형이 돼요.",
    "do": "그래프에서 두 선이 만나는 곳 찾기",
    "dont": "찬 기운이 이동한다고 생각하기",
    "review": [{"text": "온도가 높을수록\n입자 운동은?"}, {"text": "열은 어디에서\n어디로 이동하나요?"}, {"text": "열평형이란\n무엇인가요?"}],
    "next": "열의 이동 방식",
    "notes": {
        "목적": "핵심을 정리하고 다음 수업 첫 5분에 풀 복습 문제를 알려 줍니다.",
        "시간": "약 1분",
        "말하기": ["“따뜻한 물과 찬물이 만나면 어떻게 되는지 처음부터 끝까지 설명해 볼래?”"],
        "예상답": ["“따뜻한 물의 열이 찬물로 이동해서 따뜻한 물은 식고 찬물은 데워져요. 온도가 같아지면 열평형이에요.”"],
        "정답": ["① 활발하다(빠르다) ② 온도가 높은 곳에서 낮은 곳으로 ③ 온도가 다른 두 물체가 맞닿아 온도가 같아진 상태"],
        "막히면": ["S03과 S10을 다시 보여 줍니다."],
        "주의": ["복습 세 문제는 다음 수업을 시작할 때 활동지 마지막 쪽과 함께 풉니다.", "다음 차시 ‘열의 이동 방식’에서는 열이 어떤 방법(전도·대류·복사)으로 이동하는지 배웁니다."],
    },
})
S.append({
    "id": "S17", "kind": "concept", "layout": "support", "section": "보충", "purpose": "선수 학습 보충(온도계 읽기, 열의 이동 방향)", "role": "support", "objectives": [],
    "title": "보충: 온도계와 열의 이동",
    "figure": F_THERMO_SUP,
    "figureRatio": 0.36,
    "points": [{"title": "온도계 읽기", "text": "기둥 끝과 눈높이를 맞추고\n가까운 눈금을 읽어요."},
               {"title": "단위", "text": "°C를 붙여요.\n18 °C는 ‘섭씨 십팔 도’"},
               {"title": "열의 이동", "text": "온도가 높은 곳에서\n낮은 곳으로 이동해요."}],
    "notes": {
        "목적": "S02가 흔들리면 온도계 읽기와 열의 이동 방향을 다시 익힙니다.",
        "시간": "약 4분",
        "말하기": ["“빨간 기둥 끝은 10과 20 사이야. 10에서 작은 눈금을 하나씩 세어 볼까? 몇 °C야?”", "“따뜻한 손으로 차가운 숟가락을 쥐면 열은 어디로 갈까? 숟가락은 어떻게 돼?”"],
        "예상답": ["“18 °C요.” “손에서 숟가락으로 가서 숟가락이 따뜻해져요.”"],
        "막히면": ["실제 온도계로 방 안의 온도를 함께 읽고, 컵을 손으로 감싸 온도계가 올라가는 것을 다시 봅니다."],
        "주의": ["계획상 선수 차시는 5학년 ‘열의 이동’(KR22-G05-SCI-HEAT-L01)입니다. 보충으로도 어려우면 그 차시의 S03~S08을 먼저 다시 합니다.",
               "보충이 오래 걸리면 오늘은 여기까지 하고 다음 날 S02부터 다시 시작합니다."],
    },
})
C["slides"] = S

# ---------------------------------------------------------------- worksheet
WS_GRAPH = {
    "grid": "square", "grid_range": [0, 0, 10, 12], "ws_unit": 8, "ws_max_h": 118,
    "points": {"_left": [-1.7, 0], "_right": [11.2, 0]},
    "segments": [seg((0, 0), (10.6, 0), INK, 1.5, arrow="end"), seg((0, 0), (0, 12.6), INK, 1.5, arrow="end")],
    "texts": [txt((t, -0.6), str(t)) for t in range(0, 11)] + [txt((-0.8, k), str(5 * k)) for k in range(0, 13, 2)]
    + [txt((5, -1.4), "시간(분)", bold=True), txt((0.3, 13.4), "온도(°C)", bold=True)],
}
C["worksheet"] = {
    "title": "온도와 열평형 활동지",
    "items": [
        {"no": 1, "prompt": "컵 속 컵 실험: 실험 전에 ‘내 예상’을, 실험한 뒤 ‘결과’를 쓰세요(예: 올라간다·내려간다·그대로).",
         "table": {"headers": ["궁금한 것", "내 예상", "결과"], "rows": [["안쪽 따뜻한 물의 온도", "", ""], ["바깥 찬물의 온도", "", ""], ["오래 두면 두 물의 온도", "", ""]],
                   "widths": [0.36, 0.32, 0.32], "firstColHead": True},
         "answer": "예상은 어떤 답이든 괜찮음. 결과: 안쪽 따뜻한 물 – 내려간다, 바깥 찬물 – 올라간다, 오래 두면 – 같아진다(열평형). 결과 칸을 잰 기록에 맞게 썼는지 봅니다."},
        {"no": 2, "prompt": "1분마다 안쪽 따뜻한 물과 바깥 찬물의 온도(°C)를 재어 쓰세요.",
         "table": {"headers": ["시간(분)", "0", "1", "2", "3", "4", "5", "6", "7", "8"],
                   "rows": [["안쪽 물(°C)"] + [""] * 9, ["바깥 물(°C)"] + [""] * 9],
                   "widths": [0.235] + [0.085] * 9, "firstColHead": True, "size": 10.5},
         "answer": "잰 대로 쓰면 맞음. 예시(안쪽 / 바깥, °C): 0분 50/14, 1분 40/19, 2분 34/22, 3분 30/24, 4분 28/25, 5분 27/25, 6분 26/26, 7분 26/26, 8분 26/26. 실험을 하지 못했다면 이 예시 자료를 불러 주고 활동지 3을 그리게 합니다."},
        {"no": 3, "prompt": "활동지 2의 기록으로 꺾은선그래프를 그리세요. 안쪽 따뜻한 물은 빨간색, 바깥 찬물은 파란색으로 점을 찍고 이어요.",
         "geo": WS_GRAPH,
         "line_label": "두 선이 만난 때: ______분     그때의 온도: ______ °C", "lines": 0,
         "answer": "가로축 시간·세로축 온도에 점을 바르게 찍고 두 선을 그리면 맞음. 예시 자료라면 두 선이 6분, 26 °C에서 만나고 그 뒤로 같음. 우리 집 기록은 다를 수 있으며, 8분까지 같아지지 않았다면 ‘거의 같아짐(차이 ○ °C)’이라고 써도 됨."},
        {"no": 4, "prompt": "따뜻한 물이 식을 때 입자 모형은 어떻게 달라지나요? 알맞은 것을 모두 고르세요.",
         "choices": ["입자의 수가 줄어든다", "입자의 크기가 작아진다", "입자의 운동이 둔해진다", "입자의 수와 크기는 그대로다"],
         "answer": "‘입자의 운동이 둔해진다’와 ‘입자의 수와 크기는 그대로다’ 두 개. 수가 줄거나 크기가 작아진다고 고르면 오해 M1이므로 S03·S05를 다시 봅니다."},
        {"no": 5, "prompt": "[부모님과 함께, 할 수 있으면] 50 °C쯤의 따뜻한 물과 14 °C쯤의 찬물을 같은 양(예: 100 mL씩) 섞고 온도를 재세요. 섞은 물의 온도는 처음 두 온도와 비교해 어떤가요? 까닭을 ‘열’을 넣어 쓰세요.",
         "lines": 3,
         "answer": "섞은 물의 온도는 처음 두 온도 사이(같은 양이면 중간쯤, 열을 잃지 않으면 32 °C, 실제로는 컵과 공기로 열이 빠져나가 그보다 조금 낮음). 까닭: 따뜻한 물의 열이 찬물로 이동해 따뜻한 물은 식고 찬물은 데워져 온도가 같아지기(열평형) 때문. 실험을 못 했다면 예상과 까닭만 써도 됨."},
        {"no": 6, "new_page": True, "heading": "다음 수업을 시작할 때",
         "prompt": "① 온도가 높을수록 입자의 운동은 어떤가요?  ② 열은 어디에서 어디로 이동하나요?  ③ 열평형이란 무엇인가요?",
         "lines": 3,
         "answer": "① 활발하다(빠르다) ② 온도가 높은 곳(물체)에서 낮은 곳(물체)으로 ③ 온도가 다른 두 물체가 맞닿아 열이 이동한 끝에 두 물체의 온도가 같아진 상태"},
    ],
    "record": [
        "S02 선수 확인: 온도계 읽기·열의 이동 방향 모두 □  흔들림(보충 S17) □",
        "S07 실험 기록: 1분마다 기록함 □  숫자가 멈춘 뒤 읽음 □  도움을 받아 기록 □",
        "활동지 3 그래프: 혼자 그림 □  도움을 받아 그림 □  수업 뒤에 그리기로 함 □",
        "S13 혼자 해 보기: 모두 맞힘 □  한두 개 도움 □  도움을 받아 해결 □",
        "S15 마무리 확인: 답과 까닭 모두 □  답만 □  아직 □",
        "오해: 입자가 커지거나 많아짐(M1) □  찬 기운이 이동함(M2) □  열평형이면 입자가 멈춤(M3) □",
    ],
}

# ---------------------------------------------------------------- consistency asserts on text vs data
notes_txt = json.dumps(C, ensure_ascii=False)
assert "6분, 26 °C" in notes_txt and "8분, 28 °C" in notes_txt and "4분, 45 °C" in notes_txt
for t, w, c in zip(T_MIN, WARM, COLD):
    assert f"{t}분 {w}/{c}" in notes_txt or t == 0 and "0분 50/14" in notes_txt
OUT.write_text(json.dumps(C, ensure_ascii=False, indent=1), encoding="utf-8")
print("wrote", OUT, "slides", len(S), "angles", POS_ANG)
