"""KR22-G07-SOC-LATLONG-L01 위도와 경도 — content JSON generator (figures computed + coordinate asserts)."""
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from geo_common import INK, P, r3, seg, txt, arc_pts  # noqa: E402

OUT = Path(__file__).parent / "latlong_content.json"

OCEAN, EQC, PMC, GRAYL, RED = "DCEBF7", "E9762B", "3D5A80", "AAB4BF", "C8434E"
R = 2.0


# ---------------------------------------------------------------- wording helpers (single source for every answer)
def lat_ko(lat, nd=0):
    v = f"{abs(lat):.{nd}f}"
    return "0°" if lat == 0 else f"{'북위' if lat > 0 else '남위'} {v}°"


def lon_ko(lon, nd=0):
    v = f"{abs(lon):.{nd}f}"
    return "0°" if lon == 0 else f"{'동경' if lon > 0 else '서경'} {v}°"


def ko(lat, lon, nd=0):
    return f"{lat_ko(lat, nd)}, {lon_ko(lon, nd)}"


def sym(lat, lon, nd=0):
    return f"{abs(lat):.{nd}f}°{'N' if lat >= 0 else 'S'}, {abs(lon):.{nd}f}°{'E' if lon >= 0 else 'W'}"


# ---------------------------------------------------------------- real places (decimal degrees as a map app shows them)
CITY = {
    "서울": (37.5665, 126.9780),       # 서울시청 부근
    "시드니": (-33.8688, 151.2093),
    "뉴욕": (40.7128, -74.0060),
    "런던": (51.5074, -0.1278),
    "모스크바": (55.7558, 37.6173),
}
ROUND = {k: (round(a, 1), round(b, 1)) for k, (a, b) in CITY.items()}
assert ROUND["서울"] == (37.6, 127.0) and ROUND["시드니"] == (-33.9, 151.2)
assert ROUND["뉴욕"] == (40.7, -74.0) and ROUND["런던"] == (51.5, -0.1) and ROUND["모스크바"] == (55.8, 37.6)
TABLE_CITIES = ["서울", "시드니", "뉴욕", "런던"]
south = [c for c in TABLE_CITIES if CITY[c][0] < 0]
assert south == ["시드니"]
assert max(TABLE_CITIES, key=lambda c: CITY[c][0]) == "런던"
# S16: in January (northern winter) the only southern-hemisphere option has summer
S16_OPTIONS = ["모스크바", "시드니", "뉴욕"]
assert [c for c in S16_OPTIONS if CITY[c][0] < 0] == ["시드니"]

# standard meridians (time zones without daylight saving except London) — 15° = 1 hour
STD = {"서울": 135, "런던": 0, "방콕": 105, "두바이": 60, "모스크바": 45}
UTC = {"서울": 9, "런던": 0, "방콕": 7, "두바이": 4, "모스크바": 3}
for c, m in STD.items():
    assert m % 15 == 0 and m // 15 == UTC[c]
assert 360 / 24 == 15


def diff_hours(a, b):
    return (STD[a] - STD[b]) // 15


def clock(h):
    h %= 24
    return f"오전 {h}시" if h < 12 else ("낮 12시" if h == 12 else f"오후 {h - 12}시")


assert diff_hours("서울", "런던") == 9 and clock(18 - 9) == "오전 9시" and clock(18) == "오후 6시"
assert diff_hours("서울", "방콕") == 2 and clock(10 - 2) == "오전 8시"
assert diff_hours("서울", "두바이") == 5 and clock(15 - 5) == "오전 10시"
assert diff_hours("서울", "모스크바") == 6 and clock(15 - 6) == "오전 9시"


# ---------------------------------------------------------------- 15° practice grid
G_LAT = (-45, 45)
G_LON = (-60, 75)
STEP = 15


def grid_fig(points, alt, mark_label=True, ws=False):
    """points: list of (name, lat, lon). 1 unit = 15°. Lines every 15°, equator and prime meridian coloured."""
    x0, x1 = G_LON[0] / STEP, G_LON[1] / STEP
    y0, y1 = G_LAT[0] / STEP, G_LAT[1] / STEP
    segs, texts, circles = [], [], []
    for lon in range(G_LON[0], G_LON[1] + 1, STEP):
        x = lon / STEP
        if lon != 0:
            segs.append(seg((x, y0 - 0.3), (x, y1 + 0.3), GRAYL, 1))
    for lat in range(G_LAT[0], G_LAT[1] + 1, STEP):
        y = lat / STEP
        if lat != 0:
            segs.append(seg((x0 - 0.3, y), (x1 + 0.3, y), GRAYL, 1))
        texts.append(txt((x0 - 1.35, y), lat_ko(lat), bold=(lat == 0)))
    segs.append(seg((x0 - 0.3, 0), (x1 + 0.3, 0), EQC, 3))
    segs.append(seg((0, y0 - 0.3), (0, y1 + 0.3), PMC, 3))
    for lon in range(G_LON[0], G_LON[1] + 1, 2 * STEP):
        x = lon / STEP
        texts.append(txt((x, y0 - 0.95), "0°" if lon == 0 else lon_ko(lon).replace(" ", "\n"), bold=(lon == 0)))
    texts.append(txt((x1 + 1.05, 0.0), "적도", bold=True, color="C2571A"))
    texts.append(txt((0, y1 + 0.75), "본초 자오선", bold=True, color=PMC))
    for name, lat, lon in points:
        assert lat % STEP == 0 and lon % STEP == 0
        assert G_LAT[0] <= lat <= G_LAT[1] and G_LON[0] <= lon <= G_LON[1]
        x, y = lon / STEP, lat / STEP
        circles.append({"center": P(x, y), "r": 0.14, "fill": RED, "color": INK, "width": 1})
        if mark_label:
            texts.append(txt((x + 0.42, y + 0.42), name, size="label", bold=True, bg=True))
    names = [p[0] for p in points]
    assert len(set(names)) == len(names)
    assert len({(p[1], p[2]) for p in points}) == len(points)
    f = {"type": "geo", "names": False, "segments": segs, "texts": texts, "circles": circles, "alt": alt,
         "points": {"_a": [x0 - 2.2, y0 - 1.4], "_b": [x1 + 1.7, y1 + 1.0]}}
    if ws:
        f.pop("alt")
        f["ws_unit"] = 11
        f["ws_max_h"] = 110
    return f


def grid_alt(points, extra=""):
    parts = [f"{n}는 {ko(a, b)}" for n, a, b in points]
    return "위도·경도 연습 격자(간단히 나타낸 그림, 한 칸 15°): 가로선은 남위 45°~북위 45°, 세로선은 서경 60°~동경 75°. 가운데 주황 가로선은 적도, 파랑 세로선은 본초 자오선. " + ", ".join(parts) + extra


S05_PTS = [("가", 45, 30), ("나", -15, -30), ("다", -30, -60), ("라", -30, 60), ("마", 30, 60)]
S05_TARGET = (-30, 60)
assert [n for n, a, b in S05_PTS if (a, b) == S05_TARGET] == ["라"]
assert ("마", -S05_TARGET[0], S05_TARGET[1]) in S05_PTS and ("다", S05_TARGET[0], -S05_TARGET[1]) in S05_PTS  # N/S and E/W traps
S14_PTS = [("가", -45, -15), ("나", 15, 60)]
WS_PTS = [("바", 45, 60), ("사", -30, -45)]
WS_TARGET = (15, -15)
assert all((a, b) != WS_TARGET for _, a, b in WS_PTS)
PT = {n: (a, b) for n, a, b in S05_PTS}


# ---------------------------------------------------------------- globes
def ocean_circle(r=R):
    return {"center": [0, 0], "r": r, "fill": OCEAN, "color": INK, "width": 2, "order": "below"}


def front_globe(lats=(-60, -30, 30, 60), lons=(-60, -30, 30, 60), equator=True, prime=True):
    segs, ells = [], []
    for la in lats:
        y, half = R * math.sin(math.radians(la)), R * math.cos(math.radians(la))
        segs.append(seg((-half, y), (half, y), GRAYL, 1))
    for lo in lons:
        rx = R * abs(math.sin(math.radians(lo)))
        ells.append({"center": [0, 0], "rx": r3(rx), "ry": R, "from": -90 if lo > 0 else 90, "to": 90 if lo > 0 else 270, "color": GRAYL, "width": 1})
    if equator:
        segs.append(seg((-R, 0), (R, 0), EQC, 3))
    if prime:
        segs.append(seg((0, -R), (0, R), PMC, 3))
    return segs, ells


def cover_fig():
    segs, ells = front_globe()
    return {"type": "geo", "names": False, "circles": [ocean_circle(), {"center": P(R * math.cos(math.radians(30)) * math.sin(math.radians(45)), R * math.sin(math.radians(30))), "r": 0.13, "fill": RED, "color": INK, "width": 1}],
            "segments": segs, "ellipses": ells, "alt": "간단히 나타낸 지구: 가로로 그은 위선과 세로로 휘어진 경선, 주황색 적도와 파랑 본초 자오선, 북반구의 한 곳에 빨간 점", "max_unit": 0.75}


def lat_side_fig():
    """Side view: latitude = angle at the centre measured from the equator plane."""
    segs, texts = [], []
    for la in (-60, -30, 30, 60):
        y, half = R * math.sin(math.radians(la)), R * math.cos(math.radians(la))
        segs.append(seg((-half, y), (half, y), GRAYL, 1.25))
        texts.append(txt((-half - 1.05, y), lat_ko(la)))
    segs.append(seg((-R, 0), (R, 0), EQC, 3))
    texts.append(txt((-R - 1.0, 0), "적도 0°", bold=True, color="C2571A"))
    p30 = (R * math.cos(math.radians(30)), R * math.sin(math.radians(30)))
    segs.append(seg((0, 0), p30, RED, 2.25))
    texts += [txt((0, R + 0.4), "북극(북위 90°)", bold=True), txt((0, -R - 0.4), "남극(남위 90°)", bold=True)]
    return {"type": "geo", "names": False,
            "points": {"_O": [0, 0], "_E": [R, 0], "_P": P(*p30)},
            "circles": [ocean_circle(), {"center": [0, 0], "r": 0.07, "fill": INK, "color": INK, "width": 1},
                        {"center": P(*p30), "r": 0.12, "fill": RED, "color": INK, "width": 1}],
            "segments": segs, "texts": texts,
            "angles": [{"at": "_O", "from": "_E", "to": "_P", "label": "30°", "r": 0.55, "label_dist": 0.95}],
            "caption": "옆에서 본 지구(간단히 나타낸 그림)",
            "alt": "옆에서 본 지구: 가운데 적도(0°)와 북위 30°·60°, 남위 30°·60°의 위선. 지구 중심에서 적도 쪽과 북위 30°인 곳 쪽으로 그은 두 선 사이의 각이 30°로 표시됨. 위쪽 북극은 북위 90°, 아래쪽 남극은 남위 90°"}


def lon_polar_fig():
    """View from above the North Pole, prime meridian pointing down; east = counter-clockwise."""
    th = lambda lon: -90 + lon
    segs, texts = [], []
    for lon in range(-150, 181, 30):
        if lon in (0, 60):
            continue
        a = math.radians(th(lon))
        segs.append(seg((0, 0), (R * math.cos(a), R * math.sin(a)), GRAYL, 1.25))
    p0 = (0, -R)
    a60 = math.radians(th(60))
    p60 = (R * math.cos(a60), R * math.sin(a60))
    segs.append(seg((0, 0), p0, PMC, 3))
    segs.append(seg((0, 0), p60, RED, 2.25))
    texts += [txt((0, -R - 0.42), "본초 자오선(0°)", bold=True, color=PMC),
              txt((R + 0.95, 0), "동경 90°"), txt((-R - 0.95, 0), "서경 90°"), txt((0, R + 0.4), "180°"),
              txt((p60[0] + 0.75, p60[1] - 0.45), "동경 60°", bold=True, color=RED),
              txt((-0.55, 0.3), "북극", bold=True, bg=True)]
    # 동경 90° is counter-clockwise from 0° (to the right when 0° points down)
    assert abs(math.cos(math.radians(th(90))) - 1) < 1e-9
    return {"type": "geo", "names": False,
            "points": {"_C": [0, 0], "_Z": P(*p0), "_Q": P(*p60)},
            "circles": [ocean_circle(), {"center": [0, 0], "r": 0.07, "fill": INK, "color": INK, "width": 1}],
            "segments": segs, "texts": texts,
            "angles": [{"at": "_C", "from": "_Z", "to": "_Q", "label": "60°", "r": 0.5, "label_dist": 1.0}],
            "caption": "북극 위에서 본 지구(간단히 나타낸 그림)",
            "alt": "북극 위에서 내려다본 지구: 가운데 북극에서 바깥으로 경선이 30°마다 뻗어 있고, 아래쪽 파랑 선이 본초 자오선(0°), 그 오른쪽(동쪽) 빨간 선이 동경 60°. 두 선 사이의 각이 60°. 오른쪽은 동경 90°, 왼쪽은 서경 90°, 위쪽은 180°"}


def sun_angle_fig():
    """Side view at the equinox: equal-width beams hit the equator and a high latitude."""
    polys, segs, texts = [], [], []
    xs = lambda y: -math.sqrt(R * R - y * y)
    beams = [(-0.3, 0.3), (1.3, 1.9)]
    arcs = []
    for y1, y2 in beams:
        polys.append({"pts": [P(-4.4, y1), P(xs(y1), y1), P(xs(y2), y2), P(-4.4, y2)], "fill": "FCE7A6", "width": 0})
        ym = (y1 + y2) / 2
        segs.append(seg((-4.4, ym), (xs(ym) - 0.08, ym), "D68A00", 2, arrow="end"))
        a1, a2 = 180 - math.degrees(math.asin(y1 / R)), 180 - math.degrees(math.asin(y2 / R))
        polys.append({"pts": arc_pts(0, 0, R, a1, a2, 16), "open": True, "fill": "none", "color": EQC, "width": 6})
        arcs.append(R * abs(math.radians(a2 - a1)))
    # same beam width, but the surface it lights is much wider at high latitude
    assert abs((beams[0][1] - beams[0][0]) - (beams[1][1] - beams[1][0])) < 1e-9
    assert arcs[1] / arcs[0] > 1.7, arcs
    segs.append(seg((-R, 0), (R, 0), EQC, 1.5, dash=True))
    texts += [txt((R + 0.6, 0), "적도", bold=True, color="C2571A"), txt((0, R + 0.38), "북극", bold=True), txt((0, -R - 0.38), "남극", bold=True),
              txt((-3.4, 0.8), "햇빛", bold=True, color="B07000"),
              txt((-0.75, -0.6), "저위도", bold=True), txt((0.0, 1.05), "고위도", bold=True)]
    return {"type": "geo", "names": False, "polygons": polys, "segments": segs, "texts": texts,
            "circles": [ocean_circle()],
            "caption": "춘분·추분 무렵(간단히 나타낸 그림)",
            "alt": "옆에서 본 지구에 왼쪽에서 같은 폭의 햇빛 두 줄기가 들어옴: 적도 부근(저위도)에는 거의 수직으로 닿아 좁은 곳을 비추고, 북극에 가까운 곳(고위도)에는 비스듬히 닿아 약 2배 넓은 곳을 비춤"}, arcs


def season_fig():
    """June: axis tilted 23.5° toward the sun (left). Day side left, night side right."""
    t = math.radians(23.5)
    a = (-math.sin(t), math.cos(t))          # axis (north)
    e = (math.cos(t), math.sin(t))           # equator direction
    # subsolar latitude = latitude of the point facing the sun (-1, 0)
    assert abs(math.degrees(math.asin(-1 * a[0])) - 23.5) < 1e-9

    def p(lat):
        c, s = math.cos(math.radians(lat)), math.sin(math.radians(lat))
        return (R * (c * -e[0] + s * a[0]), R * (c * -e[1] + s * a[1]))

    seoul, sydney = p(ROUND["서울"][0]), p(ROUND["시드니"][0])
    polys = [{"pts": arc_pts(0, 0, R, -90, 90, 36), "fill": "B9C3D1", "width": 0}]
    segs = [seg((-1.3 * R * a[0], -1.3 * R * a[1]), (1.3 * R * a[0], 1.3 * R * a[1]), INK, 1.5, dash=True),
            seg((-R * e[0], -R * e[1]), (R * e[0], R * e[1]), EQC, 3)]
    for y in (1.2, 0.0, -1.2):
        segs.append(seg((-4.6, y), (-math.sqrt(R * R - y * y) - 0.15, y), "D68A00", 2, arrow="end"))
    texts = [txt((-3.6, 1.65), "햇빛", bold=True, color="B07000"),
             txt((1.3 * R * a[0] - 0.05, 1.3 * R * a[1] + 0.35), "자전축", bold=True),
             txt((-1.15, -0.08), "적도", bold=True, color="C2571A", bg=True),
             txt((seoul[0] + 0.75, seoul[1] + 0.05), "서울", bold=True, bg=True),
             txt((sydney[0] + 0.85, sydney[1] + 0.1), "시드니", bold=True, bg=True),
             txt((1.0, 1.05), "북반구\n여름", size="label", bold=True, color=RED, bg=True),
             txt((0.95, -1.15), "남반구\n겨울", size="label", bold=True, color=PMC, bg=True)]
    circles = [ocean_circle(), {"center": [0, 0], "r": R, "fill": "none", "color": INK, "width": 2},
               {"center": P(*seoul), "r": 0.12, "fill": RED, "color": INK, "width": 1},
               {"center": P(*sydney), "r": 0.12, "fill": RED, "color": INK, "width": 1}]
    return {"type": "geo", "names": False, "polygons": polys, "segments": segs, "texts": texts, "circles": circles,
            "caption": "6~8월의 지구(간단히 나타낸 그림)",
            "alt": "옆에서 본 6~8월의 지구: 자전축의 북쪽이 왼쪽의 태양 쪽으로 기울어 북반구(서울)는 햇빛을 높이 받아 여름, 남반구(시드니)는 비스듬히 받아 겨울. 오른쪽 절반은 밤"}


def time_fig():
    """View from above the North Pole; sun on the left. θ = 45° + 경도 (east = counter-clockwise),
    so 동경 135° faces the sun (noon) and 경도 0° is on the night side."""
    th = lambda lon: 45 + lon
    assert th(135) == 180
    polys = [{"pts": [[0, 0]] + arc_pts(0, 0, R, -90, 90, 36), "fill": "B9C3D1", "width": 0}]
    segs = []
    for lon in range(-165, 181, 15):
        if lon in (0, 135):
            continue
        q = math.radians(th(lon))
        segs.append(seg((0, 0), (R * math.cos(q), R * math.sin(q)), "9AA5B1", 0.75))
    q0, q135 = math.radians(th(0)), math.radians(th(135))
    segs.append(seg((0, 0), (R * math.cos(q0), R * math.sin(q0)), PMC, 3))
    segs.append(seg((0, 0), (R * math.cos(q135), R * math.sin(q135)), RED, 3))
    for y in (1.45, -1.45):
        segs.append(seg((-4.7, y), (-math.sqrt(R * R - y * y) - 0.15, y), "D68A00", 2, arrow="end"))
    # rotation arrow (counter-clockwise) outside the globe, bottom-left
    arc = arc_pts(0, 0, R + 0.35, 200, 245, 12)
    polys.append({"pts": arc, "open": True, "fill": "none", "color": INK, "width": 2})
    end = (math.cos(math.radians(250)) * (R + 0.35), math.sin(math.radians(250)) * (R + 0.35))
    segs.append(seg(arc[-1], end, INK, 2, arrow="end"))
    # local times: noon at 동경 135°, 경도 0° is 135° = 9 h behind → 3 a.m.
    hours_behind = (135 - 0) // 15
    assert hours_behind == 9 and clock(12 - hours_behind) == "오전 3시"
    texts = [txt((-3.3, 0.0), "동경 135°\n낮 12시", bold=True, color=RED),
             txt((R * math.cos(q0) + 0.65, R * math.sin(q0) + 0.6), "경도 0°\n새벽 3시", bold=True, color=PMC),
             txt((-3.7, 1.95), "햇빛", bold=True, color="B07000"),
             txt((-2.75, -2.15), "자전\n방향", bold=False),
             txt((0.0, -0.45), "북극", bold=True, bg=True),
             txt((1.0, -0.6), "밤", size="label", bold=True)]
    return {"type": "geo", "names": False, "polygons": polys, "segments": segs, "texts": texts,
            "circles": [ocean_circle(), {"center": [0, 0], "r": R, "fill": "none", "color": INK, "width": 2}],
            "caption": "북극 위에서 본 지구(간단히 나타낸 그림)",
            "alt": "북극 위에서 내려다본 지구: 왼쪽에서 햇빛이 들어와 왼쪽 절반은 낮, 오른쪽 절반은 밤. 경선이 15°마다 그어져 있고, 태양을 향한 동경 135°(빨강)는 낮 12시, 오른쪽 위 밤 쪽의 경도 0°(파랑)는 새벽 3시. 지구는 시계 반대 방향(서→동)으로 자전"}


def support_fig():
    segs, ells = front_globe(lats=(), lons=())
    texts = [txt((R + 0.95, 0), "적도(0°)", bold=True, color="C2571A"), txt((0, R + 0.4), "본초 자오선(0°)", bold=True, color=PMC),
             txt((-0.95, 0.95), "북위\n서경", size="label", bold=True), txt((0.95, 0.95), "북위\n동경", size="label", bold=True),
             txt((-0.95, -0.95), "남위\n서경", size="label", bold=True), txt((0.95, -0.95), "남위\n동경", size="label", bold=True)]
    return {"type": "geo", "names": False, "circles": [ocean_circle()], "segments": segs, "ellipses": ells, "texts": texts,
            "caption": "간단히 나타낸 그림",
            "alt": "간단히 나타낸 지구: 가로 주황 선은 적도, 세로 파랑 선은 본초 자오선. 네 부분에 북위·서경(왼쪽 위), 북위·동경(오른쪽 위), 남위·서경(왼쪽 아래), 남위·동경(오른쪽 아래)"}


F_SUN, ARCS = sun_angle_fig()

# ---------------------------------------------------------------- lesson
seoul_ko, seoul_sym = ko(*ROUND["서울"], nd=1), sym(*ROUND["서울"], nd=1)
assert seoul_ko == "북위 37.6°, 동경 127.0°" and seoul_sym == "37.6°N, 127.0°E"

C = {
    "status": "제작 완료",
    "objectives": [
        {"id": "A", "text": "적도와 본초 자오선을 기준으로 위도(0°~90°, 북위·남위)와 경도(0°~180°, 동경·서경)의 뜻을 설명하고, 15° 간격 격자와 지도 앱에서 장소의 위치를 ‘북위 ○°, 동경 ○°’(○°N, ○°E)로 나타내거나 위도·경도로 장소를 찾는다.",
         "evidence": "위도와 경도(S03), 쓰는 법(S04), 격자에서 말하기(S05), 실제 도시(S06), 지도 앱(S07), 혼자 해 보기 ①(S14), 활동지 1·2·3",
         "success": "처음 보는 격자의 점 두 개를 위도 먼저, 북·남과 동·서를 붙여 바르게 말하고, 지도 앱에 나온 음수(−)를 남위·서경으로 바꾸어 읽는다."},
        {"id": "B", "text": "위도에 따라 햇빛을 받는 각도가 달라 저위도는 덥고 고위도는 춥다는 것과, 북반구와 남반구의 계절이 반대라는 것을 지구 그림으로 설명한다.",
         "evidence": "위도와 기온(S08), 계절이 반대예요(S09), 누구 말이 맞을까(S10), 혼자 해 보기 ②(S14), 1월에 수영하기 좋은 곳(S16), 활동지 4",
         "success": "‘적도 부근은 햇빛을 거의 수직으로 받아 좁은 곳에 빛이 모여 덥다’고 말하고, 1월에 서울은 겨울·시드니는 여름인 까닭을 북반구·남반구와 자전축의 기울기로 말한다."},
        {"id": "C", "text": "지구가 24시간에 360° 자전해 경도 15°마다 1시간의 시차가 생긴다는 것을 알고, 표준 경선으로 두 곳의 시차와 시각을 구한다(동쪽에 있는 곳의 시각이 빠름).",
         "evidence": "시각이 다른 까닭(S11), 서울과 런던(S12), 서울과 방콕(S13), 혼자 해 보기 ③(S14), 활동지 5",
         "success": "서울(동경 135°)과 처음 보는 도시의 시차를 ‘경도 차이 ÷ 15’로 구하고, 동쪽인 서울의 시각이 빠르다는 것을 이용해 그 도시의 시각을 바르게 말한다."},
    ],
    "materials": [
        "활동지, 연필, 색연필",
        "지도 앱이 있는 휴대 전화나 컴퓨터(부모와 함께, 위도·경도를 보여 주는 앱)",
        "지구본이나 사회과 부도(있으면)",
        "손전등과 공(선택: S08 시범)",
    ],
    "boundary": "위도·경도의 뜻과 표시(북위·남위·동경·서경, °N·°S·°E·°W), 15° 간격 격자에서 위치 읽기, 지도 앱으로 실제 장소의 위도·경도 찾기(소수로 나온 값과 음수의 뜻), 위도에 따라 햇빛을 받는 각도가 달라 기온이 다른 까닭(저위도·중위도·고위도의 기초), 북반구와 남반구의 계절이 반대인 까닭, 경도 15°마다 1시간의 시차와 표준 경선을 이용한 간단한 시차 계산을 다룬다. 날짜 변경선, 서머타임 계산, 분(′)·초(″) 단위, 도법, 기후 지역의 구분(다음 차시 ‘세계의 기후 지역’)은 다루지 않는다(서머타임은 부모용 노트에만 적음). 화면의 지구 그림과 격자는 간단히 나타낸 그림이며 실제 지도가 아니다. 도시의 위도·경도는 소수 첫째 자리까지 반올림한 어림값이다.",
    "misconceptions": [
        {"id": "M1", "text": "위도와 경도를 바꾸어 말하거나(경도를 먼저 말함), 북위·남위 또는 동경·서경을 바꾸어 읽는다.",
         "response": "S04에서 ‘위도 먼저, 북·남과 동·서를 붙여’ 쓰는 약속을 정하고, S05 ③에서 북·남(마)과 동·서(다)를 바꾼 점을 함정으로 두어 확인한다."},
        {"id": "M2", "text": "우리나라 안의 경험(제주도가 따뜻함)을 넓혀 ‘남쪽으로 갈수록 늘 덥다’고 생각한다.",
         "response": "S08에서 적도에서 멀어질수록 햇빛을 비스듬히 받는다는 것을 그림으로 보고, S10에서 두 생각을 비교한다(남반구에서는 남쪽으로 갈수록 추움)."},
        {"id": "M3", "text": "세계 어디나 계절이 같다(1월은 어디나 겨울)고 생각한다.",
         "response": "S09에서 자전축이 기운 지구 그림으로 북반구와 남반구의 계절이 반대임을 보고, S16에서 1월에 여름인 곳을 고르게 한다."},
        {"id": "M4", "text": "시차를 거꾸로 계산한다(서쪽에 있는 곳의 시각이 빠르다고 생각함).",
         "response": "S11 그림에서 동쪽에 있는 곳이 해를 먼저 맞는다는 것을 보고, S12·S13에서 ‘동쪽이 빠르다’를 매번 말하게 한다."},
    ],
    "checks": [
        {"type": "blank", "expr": "3 × 15 = □", "answer": 45, "where": "S05 ① 가: 적도에서 북쪽으로 3칸 = 북위 45°"},
        {"type": "blank", "expr": "2 × 15 = □", "answer": 30, "where": "S05 ① 가: 본초 자오선에서 동쪽으로 2칸 = 동경 30°"},
        {"type": "blank", "expr": "1 × 15 = □", "answer": 15, "where": "S05 ② 나: 남쪽 1칸 = 남위 15°"},
        {"type": "blank", "expr": "2 × 15 = □", "answer": 30, "where": "S05 ② 나: 서쪽 2칸 = 서경 30°"},
        {"type": "blank", "expr": "4 × 15 = □", "answer": 60, "where": "S05 ③ 라: 동쪽 4칸 = 동경 60°(남쪽 2칸 = 남위 30°)"},
        {"type": "compare", "values": ["40.7", "51.5"], "rel": "<", "where": "S06 ②: 뉴욕(북위 40.7°)보다 런던(북위 51.5°)이 북쪽"},
        {"type": "compare", "values": ["37.6", "51.5"], "rel": "<", "where": "S06 ②: 서울(북위 37.6°)보다 런던이 북쪽"},
        {"type": "blank", "expr": "360 ÷ 24 = □", "answer": 15, "where": "S11: 1시간에 자전하는 각도(°)"},
        {"type": "blank", "expr": "(135 − 0) ÷ 15 = □", "answer": 9, "where": "S11·S12: 서울과 런던의 시차(시간)"},
        {"type": "blank", "expr": "18 − 9 = □", "answer": 9, "where": "S12: 서울 오후 6시(18시)일 때 런던 오전 9시"},
        {"type": "blank", "expr": "135 − 105 = □", "answer": 30, "where": "S13 ①: 서울과 방콕의 경도 차이(°)"},
        {"type": "blank", "expr": "30 ÷ 15 = □", "answer": 2, "where": "S13 ②: 서울과 방콕의 시차(시간)"},
        {"type": "blank", "expr": "10 − 2 = □", "answer": 8, "where": "S13 ③: 서울 오전 10시일 때 방콕 오전 8시"},
        {"type": "blank", "expr": "3 × 15 = □", "answer": 45, "where": "S14 ① 가: 남쪽 3칸 = 남위 45°(서쪽 1칸 = 서경 15°)"},
        {"type": "blank", "expr": "4 × 15 = □", "answer": 60, "where": "S14 ① 나: 동쪽 4칸 = 동경 60°(북쪽 1칸 = 북위 15°)"},
        {"type": "blank", "expr": "(135 − 60) ÷ 15 = □", "answer": 5, "where": "S14 ③: 서울과 두바이의 시차(시간)"},
        {"type": "blank", "expr": "(135 − 45) ÷ 15 = □", "answer": 6, "where": "활동지 5: 서울과 모스크바의 시차(시간)"},
        {"type": "blank", "expr": "15 − 6 = □", "answer": 9, "where": "활동지 5: 서울 오후 3시(15시)일 때 모스크바 오전 9시"},
    ],
    "break_after": "S07",
}

S = []
S.append({
    "id": "S01", "kind": "cover", "section": "도입", "purpose": "오늘의 질문과 목표", "role": "intro", "objectives": ["A", "B", "C"],
    "title": "위도와 경도",
    "question": "지구 위의 한 곳을\n숫자로 어떻게 나타낼까요?",
    "goals": ["① 위도와 경도로 세계 여러 곳의 위치를 나타내요.", "② 위치에 따라 계절과 시각이 다른 까닭을 설명해요."],
    "figure": cover_fig(),
    "notes": {
        "목적": "오늘 할 일(위도·경도로 위치 나타내기, 위도와 계절, 경도와 시각)을 알리고 궁금증을 갖게 합니다.",
        "시간": "약 2분",
        "말하기": ["“친구에게 우리 집 위치를 알려 줄 때는 주소를 쓰지? 그럼 바다 한가운데 있는 배의 위치는 어떻게 알려 줄까?”",
                 "“지구 위 어느 곳이든 숫자 두 개로 나타내는 방법이 있어. 6학년 때 배운 위도와 경도야. 오늘은 그걸로 실제 도시를 찾고, 왜 나라마다 계절과 시각이 다른지도 알아볼 거야.”"],
        "예상답": ["“배는 주소가 없어서 모르겠어요.” “위도랑 경도요!” 어떤 답이든 괜찮습니다."],
        "막히면": ["해외에 사는 친척이나 해외 운동 경기 중계 시각(새벽 경기)을 떠올리게 하면 ‘시각이 다르다’는 것과 이어집니다."],
        "주의": ["오늘 화면의 지구와 격자는 간단히 나타낸 그림입니다. 실제 위치는 S07에서 지도 앱(또는 사회과 부도·지구본)으로 함께 확인합니다.",
               "S07에서 쓸 지도 앱(위도·경도를 보여 주는 앱)이 열리는지 미리 확인해 둡니다."],
    },
})
S.append({
    "id": "S02", "kind": "practice", "section": "도입", "purpose": "선수 학습 확인(적도·본초 자오선, 우리나라의 위치)", "role": "prior", "objectives": [],
    "title": "지난 학년 기억하기",
    "problems": [{"text": "적도의 위도는 몇 도인가요?"}, {"text": "경도 0°인 세로선의 이름은?"}, {"text": "우리나라는 북위·남위, 동경·서경 중\n어디에 있나요?"}],
    "notes": {
        "목적": "6학년 ‘세계 여러 나라’(KR22-G06-SOC-WORLDMAP-L01)에서 배운 적도·본초 자오선과 우리나라의 위치를 확인합니다. 오늘 위치를 읽을 때 그대로 씁니다.",
        "시간": "약 2분",
        "말하기": ["“6학년 때 30°마다 선이 있는 그림에서 위도와 경도를 읽었지? 기억나는 대로 말해 볼래?”", "“③은 우리나라가 적도의 북쪽인지 남쪽인지, 본초 자오선의 동쪽인지 서쪽인지 생각해 봐.”"],
        "정답": ["① 0°", "② 본초 자오선", "③ 북위, 동경(대략 북위 33°~43°, 동경 124°~132°)"],
        "막히면": ["두 문제 이상 어려우면 S18(보충)을 먼저 하고 돌아옵니다. 방위(동서남북) 자체가 흔들리면 4학년 ‘지도 읽기’(KR22-G04-SOC-MAP-L01)의 방위표 부분을 먼저 다시 봅니다."],
        "주의": ["②에서 ‘적도’라고 하면 위도와 경도를 바꾼 것입니다(오해 M1). ‘가로선은 적도, 세로선은 본초 자오선’을 다시 짚습니다."],
    },
})
S.append({
    "id": "S03", "kind": "concept", "section": "개념", "purpose": "위도와 경도의 뜻(지구 중심과 북극에서 잰 각)", "role": "teach", "objectives": ["A"],
    "title": "위도와 경도는 각도예요",
    "figures": [lat_side_fig(), lon_polar_fig()],
    "key": "위도: 적도에서 남북으로 잰 각(0°~90°, 북위·남위)\n경도: 본초 자오선에서 동서로 잰 각(0°~180°, 동경·서경)",
    "notes": {
        "목적": "위도는 적도를 기준으로 남북으로, 경도는 본초 자오선을 기준으로 동서로 잰 각이라는 것과 그 범위를 알려 줍니다(목표 A).",
        "시간": "약 3분",
        "말하기": ["“왼쪽은 지구를 옆에서 본 그림이야. 지구 중심에서 적도 쪽으로 한 줄, 빨간 점 쪽으로 한 줄을 그었더니 사이 각이 30°야. 그래서 빨간 점은 북위 30°야.”",
                 "“위도는 북극까지 가면 몇 도일까? 그래서 위도는 0°부터 90°까지 있어.”",
                 "“오른쪽은 북극 위에서 내려다본 그림이야. 아래쪽 파랑 선이 본초 자오선(0°)이고, 동쪽으로 60° 돌아간 빨간 선이 동경 60°야. 동쪽과 서쪽으로 각각 180°까지 있어서 경도는 0°부터 180°까지야.”",
                 "“같은 위도를 이은 가로선은 ‘위선’, 같은 경도를 이은 세로선은 ‘경선’이라고 해.”"],
        "예상답": ["“북극은 90°예요.” “경도는 반 바퀴씩이라 180°예요.”"],
        "막히면": ["각이 어렵다면 ‘위도는 적도에서 위아래(남북)로 얼마나 갔나, 경도는 본초 자오선에서 옆(동서)으로 얼마나 갔나’로 말해 줍니다. 손가락으로 지구본이나 공 위를 따라가며 보여 줘도 좋습니다."],
        "주의": ["두 그림은 간단히 나타낸 것입니다. 본초 자오선은 영국 런던의 그리니치 천문대를 지나는 경선입니다.",
               "동경 180°와 서경 180°는 같은 선입니다(지구 뒤쪽). 날짜 변경선은 오늘 다루지 않습니다.",
               "1°보다 작은 단위(분 ′, 초 ″)는 다루지 않습니다. 지도 앱은 소수(37.6°)로 보여 줍니다."],
    },
})
S.append({
    "id": "S04", "kind": "table", "section": "개념", "purpose": "위도·경도를 쓰는 약속(N·S·E·W)", "role": "teach", "objectives": ["A"],
    "title": "위도·경도를 쓰는 법",
    "table": {"headers": ["", "위도", "경도"],
              "rows": [["기준선", "적도(0°)", "본초 자오선(0°)"], ["이은 선", "위선(가로선)", "경선(세로선)"], ["범위", "0°~90°", "0°~180°"], ["나누어 부르기", "북위(N)·남위(S)", "동경(E)·서경(W)"]],
              "widths": [0.26, 0.37, 0.37], "width": 11.5, "size": 24, "firstColHead": True},
    "key": f"서울: {seoul_ko} → {seoul_sym}\n위도를 먼저, 경도를 나중에 써요.",
    "notes": {
        "목적": "위도·경도를 쓰는 약속(위도 먼저, 북·남과 동·서를 붙임, 영어 머리글자 N·S·E·W)을 정리합니다(목표 A, 오해 M1).",
        "시간": "약 2분",
        "말하기": ["“표를 같이 읽어 보자. 위도의 기준선은? 경도의 기준선은?”",
                 "“N은 North(북), S는 South(남), E는 East(동), W는 West(서)의 첫 글자야. 지도나 지도 앱에서 자주 봐.”",
                 f"“서울은 {seoul_ko}야. 기호로 쓰면 {seoul_sym}. 위도를 먼저 쓰는 게 약속이야.”"],
        "예상답": ["“위도는 적도, 경도는 본초 자오선이에요.” “37.6°N은 북위 37.6°예요.”"],
        "막히면": ["N·S·E·W가 어렵다면 방위표에 영어 머리글자를 함께 써 봅니다(위 N, 아래 S, 오른쪽 E, 왼쪽 W)."],
        "주의": ["서울의 값은 서울시청 부근을 소수 첫째 자리까지 반올림한 어림값입니다(37.5665, 126.9780). 교과서에 따라 ‘북위 37°, 동경 127°’처럼 정수로 쓰기도 합니다.",
               "적도 위는 그냥 ‘위도 0°’, 본초 자오선 위는 ‘경도 0°’라고 하고 북·남, 동·서를 붙이지 않습니다."],
    },
})
S05_ANS = {n: ko(*PT[n]) for n in ("가", "나")}
assert S05_ANS == {"가": "북위 45°, 동경 30°", "나": "남위 15°, 서경 30°"}
S.append({
    "id": "S05", "kind": "practice", "section": "연습", "purpose": "15° 격자에서 위도·경도로 위치 말하기", "role": "practice", "objectives": ["A"],
    "title": "격자에서 위치를 말해요",
    "problems": [{"text": "가의 위도와 경도는?"}, {"text": "나의 위도와 경도는?"}, {"text": f"{ko(*S05_TARGET)}인\n곳의 기호는?"}],
    "figure": {**grid_fig(S05_PTS, grid_alt(S05_PTS)), "caption": "한 칸은 15°예요"},
    "notes": {
        "목적": "15° 간격 격자에서 점의 위치를 위도·경도로 말하고, 위도·경도를 보고 점을 찾습니다(목표 A, 오해 M1).",
        "시간": "약 3분",
        "말하기": ["“6학년 때는 한 칸이 30°였지? 이번에는 한 칸이 15°야. 이름이 붙은 선은 30°마다만 있어.”",
                 "“가는 적도에서 북쪽으로 몇 칸이야? 3칸이면 3 × 15 = ?”",
                 "“③은 거꾸로 찾는 거야. 남위 30°는 적도의 어느 쪽 가로선이지? 동경 60°는?”"],
        "정답": [f"① {S05_ANS['가']}", f"② {S05_ANS['나']}", "③ 라"],
        "막히면": ["적도·본초 자오선에서 손가락으로 한 칸씩 짚으며 15, 30, 45를 셉니다.", "세로 경선의 이름은 30°마다만 적혀 있습니다. 이름 사이의 선은 15°를 더하거나 빼서 읽습니다."],
        "주의": ["③에서 ‘마’를 고르면 북위·남위를, ‘다’를 고르면 동경·서경을 바꾼 것입니다(오해 M1).", "그림은 연습용 격자이며 실제 지도가 아닙니다."],
    },
})
CITY_ROWS = [[c, ko(*ROUND[c], nd=1), sym(*ROUND[c], nd=1) if c == "서울" else ""] for c in TABLE_CITIES]
S.append({
    "id": "S06", "kind": "table", "section": "연습", "purpose": "실제 도시의 위도·경도 읽기와 기호로 쓰기", "role": "practice", "objectives": ["A", "B"],
    "title": "실제 도시의 위치",
    "table": {"headers": ["도시", "위도·경도(어림값)", "기호로 쓰면"], "rows": CITY_ROWS, "widths": [0.18, 0.46, 0.36], "width": 11.5, "size": 24, "firstColHead": True},
    "key": "① 빈칸을 말로 채워요.  ② 남반구에 있는 도시는?\n③ 가장 북쪽에 있는 도시는?",
    "notes": {
        "목적": "실제 도시의 위도·경도를 읽고 기호(N·S·E·W)로 바꾸며, 위도로 남반구·북반구와 남북 위치를 비교합니다(목표 A, B의 준비).",
        "시간": "약 2분",
        "말하기": ["“시드니는 기호로 어떻게 쓸까? 뉴욕은? 런던은?”", "“적도보다 남쪽, 곧 남반구에 있는 도시는 어디야? 어떻게 알았어?”", "“가장 북쪽에 있는 도시는? 숫자를 어떻게 비교했어?”"],
        "정답": [f"① 시드니 {sym(*ROUND['시드니'], nd=1)}, 뉴욕 {sym(*ROUND['뉴욕'], nd=1)}, 런던 {sym(*ROUND['런던'], nd=1)}",
               "② 시드니(남위)", f"③ 런던(북위 {ROUND['런던'][0]}°: 북위끼리는 숫자가 클수록 북쪽)"],
        "막히면": ["‘북위·남위’ 칸에서 ‘남’이 들어간 도시만 먼저 찾게 합니다. ③은 북위인 도시의 숫자만 크기 비교합니다."],
        "주의": ["‘반구’는 지구의 절반입니다. 적도의 북쪽은 북반구, 남쪽은 남반구입니다. S09에서 계절과 이어집니다.",
               "값은 각 도시 중심부를 소수 첫째 자리까지 반올림한 어림값입니다(서울 37.5665, 126.9780 / 시드니 −33.8688, 151.2093 / 뉴욕 40.7128, −74.0060 / 런던 51.5074, −0.1278).",
               "런던은 본초 자오선 바로 서쪽이라 경도가 0°에 아주 가깝습니다."],
    },
})
S.append({
    "id": "S07", "kind": "activity", "section": "연습", "purpose": "지도 앱으로 실제 장소의 위도·경도 찾기(부모와 함께)", "role": "practice", "objectives": ["A"],
    "title": "지도 앱으로 찾아요",
    "text": "부모님과 함께 해요.",
    "steps": ["지도 앱에서 우리 동네 시청(구청)을 찾아요.", "그 자리를 길게 눌러 위도·경도 숫자를 봐요.", "시드니와 뉴욕도 찾아 활동지 3에 써요.", "−(음수)가 붙으면 남위나 서경이에요."],
    "criteria": ["위도를 먼저, 경도를 나중에", "북·남과 동·서를 붙여 써요"],
    "criteriaTitle": "기록할 때 확인해요",
    "safety": "우리 집 주소와 위치는 다른 사람에게 알리지 않아요.",
    "notes": {
        "목적": "지도 앱으로 실제 장소의 위도·경도를 찾고, 앱이 보여 주는 소수와 음수를 북위·남위·동경·서경으로 바꾸어 읽습니다(목표 A).",
        "시간": "약 3분",
        "말하기": ["“지도 앱에서 우리 시청(구청)을 찾아서 빈 곳을 길게 눌러 볼래? 숫자 두 개가 나오지? 앞이 위도, 뒤가 경도야.”",
                 "“시드니는 앞 숫자에 −가 붙어 있네. −는 남위라는 뜻이야. 뉴욕은 뒤 숫자에 −가 있지? 그건 서경이야.”",
                 "“우리 동네는 서울보다 북쪽이야, 남쪽이야? 숫자로 비교해 볼까?”"],
        "예상답": ["“우리 시청은 37.4, 127.1이에요. 북위 37.4°, 동경 127.1°예요.” “시드니는 −33.9니까 남위 33.9°예요.”"],
        "정답": ["기준: 위도를 먼저, 북위·남위와 동경·서경을 붙여 쓰고, 음수(−)를 남위·서경으로 바르게 바꾸면 잘한 것입니다. 우리나라 안의 장소는 대략 북위 33°~39°(휴전선 남쪽), 동경 124°~132°입니다.",
               f"시드니 약 {ko(*ROUND['시드니'], nd=1)}(앱: −33.87, 151.21), 뉴욕 약 {ko(*ROUND['뉴욕'], nd=1)}(앱: 40.71, −74.01)"],
        "막히면": ["예: 구글 지도 앱에서는 빈 곳을 길게 누르면 핀이 꽂히고 위쪽 검색 창이나 아래 정보 창에 ‘37.5665, 126.9780’ 같은 숫자가 나옵니다. 컴퓨터에서는 그 자리를 마우스 오른쪽 단추로 누릅니다.",
                "앱에서 숫자를 찾기 어렵거나 기기가 없으면 사회과 부도의 세계 지도에서 위선·경선을 따라 읽습니다(5° 또는 10° 간격으로 읽고 어림합니다)."],
        "주의": ["우리 집이 아니라 시청·구청처럼 모두가 아는 장소를 찾게 합니다. 집 위치는 다른 사람에게 알리지 않는다는 것도 함께 이야기합니다.",
               "수업 시간에는 한 곳만 찾고, 나머지는 수업 뒤에 활동지 3으로 해도 됩니다.",
               "지도 앱은 부모님이 함께 보며 쓰고, 광고나 다른 화면으로 넘어가지 않게 합니다.",
               "지치면 여기서 쉬고, 다음에 S08부터 이어도 됩니다."],
    },
})
S.append({
    "id": "S08", "kind": "concept", "section": "개념", "purpose": "위도에 따라 기온이 다른 까닭(햇빛을 받는 각도)", "role": "teach", "objectives": ["B"],
    "title": "위도에 따라 기온이 달라요",
    "figure": F_SUN,
    "figureRatio": 0.52,
    "points": [{"title": "저위도(적도 부근)", "text": "햇빛을 거의 수직으로 받아\n좁은 곳에 모여 더워요."},
               {"title": "고위도(극 부근)", "text": "햇빛을 비스듬히 받아\n넓게 퍼져서 추워요."},
               {"title": "중위도", "text": "그 사이(약 30°~60°)예요.\n우리나라도 중위도!"}],
    "notes": {
        "목적": "위도에 따라 햇빛이 땅에 닿는 각도가 달라 같은 양의 햇빛이 비추는 넓이가 다르고, 그래서 저위도는 덥고 고위도는 춥다는 것을 설명합니다(목표 B, 오해 M2).",
        "시간": "약 3분",
        "말하기": ["“노란 햇빛 두 줄기는 폭이 같아. 그런데 지구에 닿은 주황색 부분의 길이는 어때?”",
                 "“같은 양의 햇빛이 좁은 곳에 모이면 더 뜨거울까, 넓게 퍼지면 더 뜨거울까? 6학년 때 손전등 실험 기억나?”",
                 "“그래서 적도 부근(저위도)은 1년 내내 덥고, 극 부근(고위도)은 추워. 우리나라는 그 사이 중위도에 있어.”"],
        "예상답": ["“위쪽은 빛이 넓게 퍼져서 덜 따뜻해요.” “적도는 햇빛이 똑바로 와서 더워요.”"],
        "막히면": ["손전등으로 공의 가운데와 위쪽을 같은 거리에서 비추어, 위쪽에서는 밝은 부분이 길쭉하게 넓어지고 어두워지는 것을 보여 줍니다(6학년 ‘공전과 계절’의 손전등 실험과 같은 원리)."],
        "주의": ["그림은 춘분·추분 무렵을 간단히 나타낸 것입니다. 실제로는 자전축이 기울어 있어 계절에 따라 햇빛이 가장 높이 비추는 위도가 바뀝니다(S09).",
               f"그림에서 같은 폭의 햇빛이 고위도에서는 저위도보다 약 {ARCS[1] / ARCS[0]:.1f}배 넓은 곳을 비춥니다.",
               "저위도·중위도·고위도의 경계(약 30°, 60°)는 대략의 구분입니다. 기후 지역의 구분(열대·온대·냉대 등)은 다음 차시 ‘세계의 기후 지역’에서 배웁니다."],
    },
})
S.append({
    "id": "S09", "kind": "concept", "section": "개념", "purpose": "북반구와 남반구의 계절이 반대인 까닭", "role": "teach", "objectives": ["B"],
    "title": "북반구와 남반구는 계절이 반대",
    "figure": season_fig(),
    "figureRatio": 0.55,
    "points": [{"title": "6~8월", "text": "북반구가 해 쪽으로 기울어\n서울은 여름, 시드니는 겨울"},
               {"title": "12~2월", "text": "반대로 남반구가 기울어\n서울은 겨울, 시드니는 여름"}],
    "notes": {
        "목적": "자전축이 기울어진 채 공전하기 때문에 북반구와 남반구의 계절이 반대라는 것을 설명합니다(목표 B, 오해 M3).",
        "시간": "약 3분",
        "말하기": ["“6학년 때 지구는 자전축이 기울어진 채 태양 둘레를 돈다고 배웠지? 이 그림은 6~8월의 지구야. 북쪽이 해 쪽으로 기울었어.”",
                 "“서울과 시드니 중 햇빛을 더 높이(똑바로) 받는 곳은? 그럼 7월에 서울은 무슨 계절이고 시드니는?”",
                 "“12월에는 지구가 태양 반대편으로 가서 남쪽이 해 쪽으로 기울어. 그때는?”"],
        "예상답": ["“서울은 여름이고 시드니는 겨울이에요.” “12월엔 시드니가 여름이에요. 그래서 크리스마스에 바닷가에 가요.”"],
        "막히면": ["S06 표에서 서울은 북위, 시드니는 남위였다는 것을 다시 보고 ‘북반구·남반구’와 짝짓습니다.", "지구본이 있으면 축을 한쪽으로 기울인 채 전등 양쪽에 놓아 보며 6학년 모형 실험을 떠올립니다."],
        "주의": ["그림은 크기와 거리를 실제 비율로 그리지 않은, 간단히 나타낸 것입니다. 자전축은 약 23.5° 기울어져 있습니다.",
               "적도 부근은 1년 내내 덥고 계절 변화가 작습니다. 북반구·남반구의 계절이 반대인 것은 주로 중위도·고위도의 이야기입니다."],
    },
})
S.append({
    "id": "S10", "kind": "compare", "section": "연습", "purpose": "오해 비교(남쪽으로 갈수록 늘 덥다)", "role": "practice", "objectives": ["B"],
    "title": "누구 말이 맞을까요?",
    "claim": "제주도는 서울보다 남쪽이라 더 따뜻해요.\n그럼 남쪽으로 계속 가면 계속 더 따뜻할까요?",
    "left": {"title": "토끼", "text": "남쪽으로 갈수록\n늘 더 더워져요."},
    "right": {"title": "곰", "text": "적도에서 멀어질수록 추워요.\n적도를 지나 더 남쪽으로 가면\n다시 추워져요."},
    "question": "누구 말이 맞을까요? 위도로 까닭을 말해요.",
    "notes": {
        "목적": "우리나라 안의 경험을 넓혀 ‘남쪽 = 더움’으로 생각하는 오해를 위도로 바로잡습니다(목표 B, 오해 M2).",
        "시간": "약 2분",
        "말하기": ["“토끼 말이 맞다면 지구에서 가장 남쪽인 남극은 어때야 해? 실제로는?”", "“기온을 정하는 것은 ‘남쪽이냐’가 아니라 무엇에서 얼마나 떨어졌느냐일까?”"],
        "정답": ["곰. 기온은 적도에서 얼마나 떨어졌는지(위도)에 따라 달라집니다. 북반구에서는 남쪽으로 가면 적도에 가까워져 따뜻해지지만, 적도를 지나 남반구로 가면 남쪽으로 갈수록 적도에서 멀어져 추워집니다(남극이 가장 추움)."],
        "막히면": ["S08 그림의 남극 쪽에도 햇빛이 비스듬히 닿는다는 것을 손가락으로 짚어 줍니다."],
        "주의": ["기온은 위도 말고도 높이(산), 바다와의 거리 등에 따라서도 달라집니다. 오늘은 위도만 다룹니다."],
    },
})
S.append({
    "id": "S11", "kind": "concept", "section": "개념", "purpose": "경도에 따라 시각이 다른 까닭(15° = 1시간)", "role": "teach", "objectives": ["C"],
    "title": "경도에 따라 시각이 달라요",
    "figure": time_fig(),
    "figureRatio": 0.56,
    "points": [{"title": "시차", "text": "두 곳의 시각 차이"},
               {"title": "1시간에 15°", "text": "24시간에 360° 자전\n360° ÷ 24 = 15°"},
               {"title": "동쪽이 빨라요", "text": "동쪽에 있는 곳이 해를\n먼저 맞아 시각이 빨라요."}],
    "notes": {
        "목적": "지구가 서쪽에서 동쪽으로 하루(24시간)에 한 바퀴(360°) 자전하므로 경도 15°마다 1시간의 시차가 생기고, 동쪽에 있는 곳의 시각이 빠르다는 것을 설명합니다(목표 C, 오해 M4).",
        "시간": "약 3분",
        "말하기": ["“북극 위에서 내려다보면 지구는 화살표처럼 시계 반대 방향, 곧 서쪽에서 동쪽으로 돌아. 왼쪽에서 햇빛이 오니까 왼쪽이 낮이야.”",
                 "“지구는 24시간에 360°를 돌아. 그럼 1시간에 몇 도를 돌까?”",
                 "“빨간 선(동경 135°)이 해를 정면으로 볼 때가 낮 12시야. 파란 선(경도 0°)은 아직 밤이지? 135°는 15°의 몇 배야? 그러니까 몇 시간 늦을까?”"],
        "예상답": ["“1시간에 15°요.” “135 ÷ 15 = 9니까 9시간 늦어서 새벽 3시예요.”"],
        "막히면": ["공에 스티커 두 개를 붙이고 손전등을 비춘 채 천천히 돌리며, 어느 스티커가 먼저 빛을 받는지 봅니다(동쪽 스티커가 먼저)."],
        "주의": ["그림은 간단히 나타낸 것입니다. 경선은 15°마다 그렸습니다.",
               "나라마다 시각의 기준으로 삼는 경선을 ‘표준 경선’이라고 합니다. 우리나라는 동경 135°를 씁니다(서울의 실제 경도는 약 동경 127°). S12에서 다룹니다."],
    },
})
S.append({
    "id": "S12", "kind": "steps", "section": "개념", "purpose": "시차 구하기 시범(서울과 런던)", "role": "teach", "objectives": ["C"],
    "title": "서울과 런던의 시차",
    "problem": {"text": "표준 경선(나라의 시각을 정하는 기준 경선)은\n서울 동경 135°, 런던 경도 0°예요."},
    "steps": [f"경도 차이: 135° − 0° = 135°", f"시차: 135 ÷ 15 = {diff_hours('서울', '런던')}, 곧 {diff_hours('서울', '런던')}시간",
              "서울이 동쪽이라 서울 시각이 9시간 빨라요.", f"서울이 {clock(18)}면 런던은 {clock(18 - 9)}예요."],
    "notes": {
        "목적": "표준 경선의 경도 차이를 15로 나누어 시차를 구하고, 동쪽이 빠르다는 것으로 다른 도시의 시각을 구하는 방법을 보여 줍니다(목표 C, 오해 M4).",
        "시간": "약 2분",
        "말하기": ["“나라마다 시각을 정할 때 기준으로 쓰는 경선이 있어. 그걸 ‘표준 경선’이라고 해. 우리나라는 동경 135°, 영국은 경도 0°야.”",
                 "“경도 차이는? 15°마다 1시간이니까 시차는?”",
                 "“서울과 런던 중 동쪽은? 그럼 어느 쪽 시각이 빨라? 서울이 저녁 6시면 런던은?”"],
        "정답": ["① 135° ② 9시간 ③ 서울이 9시간 빠름 ④ 런던 오전 9시"],
        "막히면": ["18시에서 9를 빼는 것이 어려우면 시계 그림을 그려 9칸 거꾸로 돌려 봅니다."],
        "주의": ["영국은 3월 마지막 일요일부터 10월 마지막 일요일까지 서머타임(시계를 1시간 앞당김)을 써서 그동안 서울과의 시차가 8시간입니다. 지도 앱의 세계 시계가 8시간으로 나오면 이 때문이라고 알려 줍니다. 계산은 오늘 다루지 않습니다.",
               "우리나라는 서머타임을 쓰지 않습니다."],
    },
})
S.append({
    "id": "S13", "kind": "practice", "section": "연습", "purpose": "시차 구하기 연습(서울과 방콕)", "role": "practice", "objectives": ["C"],
    "title": "서울과 방콕의 시차",
    "text": "방콕(태국)은 동경 105°의 시각을 써요.",
    "problems": [{"text": "서울(동경 135°)과 방콕의 경도 차이는?"}, {"text": "두 곳의 시차는?"}, {"text": "서울이 오전 10시이면 방콕은 몇 시?"}],
    "hint": "15°마다 1시간, 동쪽에 있는 곳이 시각이 빨라요.",
    "notes": {
        "목적": "S12의 방법으로 서울과 방콕의 시차와 시각을 구합니다(목표 C, 오해 M4).",
        "시간": "약 2분",
        "말하기": ["“경도 차이부터 구해 볼까? 그다음 15로 나눠.”", "“서울과 방콕 중 어느 쪽이 동쪽이야? 그럼 방콕의 시각은 더 빠를까, 늦을까?”"],
        "정답": [f"① 135° − 105° = 30°", f"② 30 ÷ 15 = {diff_hours('서울', '방콕')}, 2시간", f"③ {clock(10 - 2)}(서울이 동쪽이라 2시간 빠름)"],
        "막히면": ["S12의 네 단계를 다시 보고 같은 순서로 말하게 합니다."],
        "주의": ["③에서 ‘낮 12시’라고 하면 시차를 거꾸로 더한 것입니다(오해 M4). 서울이 동쪽이라 해를 먼저 맞는다는 것을 S11 그림으로 다시 봅니다.", "태국은 서머타임을 쓰지 않습니다."],
    },
})
S14_ANS = {n: ko(a, b) for n, a, b in S14_PTS}
assert S14_ANS == {"가": "남위 45°, 서경 15°", "나": "북위 15°, 동경 60°"}
S.append({
    "id": "S14", "kind": "check", "section": "확인", "purpose": "혼자 해결", "role": "check", "objectives": ["A", "B", "C"],
    "title": "혼자 해 보기",
    "problems": [{"text": "가와 나의 위도와 경도는?"}, {"text": "적도 부근이 극 부근보다\n더운 까닭은?"}, {"text": "서울(동경 135°)과 두바이\n(동경 60°)의 시차는?"}],
    "figure": {**grid_fig(S14_PTS, grid_alt(S14_PTS)), "caption": "한 칸은 15°예요"},
    "notes": {
        "목적": "도움 없이 격자에서 위치 읽기(①), 위도와 기온(②), 시차 구하기(③)를 하는지 확인합니다(목표 A·B·C).",
        "시간": "약 3분",
        "말하기": ["“이번에는 혼자 해 볼래? ①은 위도를 먼저 말해 줘. ②와 ③은 까닭이나 식도 말해 줘.”"],
        "정답": [f"① 가 {S14_ANS['가']} / 나 {S14_ANS['나']}",
               "② 적도 부근은 햇빛을 거의 수직으로 받아 같은 양의 햇빛이 좁은 곳에 모이기 때문(극 부근은 비스듬히 받아 넓게 퍼짐)",
               f"③ (135 − 60) ÷ 15 = {diff_hours('서울', '두바이')}, 5시간(서울이 5시간 빠름)"],
        "막히면": ["바로 알려 주지 말고 “한 칸은 몇 도였지?”, “S08 그림에서 햇빛이 닿은 넓이는?”, “15°마다 몇 시간?”이라고만 묻습니다.", "도움을 받아 해결했다면 기록표에 ‘도움’으로 표시합니다."],
        "주의": ["①에서 북·남이나 동·서를 빠뜨리면 다시 말하게 합니다. 위도와 경도를 모두 바르게 말해야 맞습니다.", "정답 확인은 다음 장(S15)에서 함께 합니다."],
    },
})
S.append({
    "id": "S15", "kind": "answers", "section": "확인", "purpose": "정답과 피드백", "role": "feedback", "teacher_only": True, "objectives": ["A", "B", "C"],
    "title": "혼자 해 보기 정답",
    "good": [{"text": "① 가 남위 45°, 서경 15°\n나 북위 15°, 동경 60°"}, {"text": "② 햇빛을 거의 수직으로\n받아 좁은 곳에 모여요."}, {"text": "③ 75 ÷ 15 = 5, 5시간"}],
    "bad": [{"text": "“가는 서경 15°,\n남위 45°”", "note": "경도를\n먼저 말함"}, {"text": "“적도가 해와\n가까워서”", "note": "거리가 아니라\n각도"}],
    "explain": "위도 먼저, 북·남과 동·서를 붙여 말하면 잘한 거예요.",
    "notes": {
        "목적": "아이의 답을 확인하고 흔한 실수와 비교합니다. 수업용에만 있는 장입니다.",
        "시간": "약 2분",
        "말하기": ["“네 답과 왼쪽이 같아? 오른쪽 답은 무엇이 아쉬울까?”"],
        "정답": [f"① 가 {S14_ANS['가']}, 나 {S14_ANS['나']} ② 햇빛을 거의 수직으로 받아 좁은 곳에 모임 ③ 5시간(서울이 빠름)"],
        "막히면": ["①이 틀리면 S04·S05로, ②가 틀리면 S08로, ③이 틀리면 S11~S13으로 돌아갑니다."],
        "주의": ["‘적도가 해와 가까워서 덥다’는 흔한 오해입니다. 지구 크기에 비해 태양은 아주 멀어서 적도와 극의 거리 차이는 거의 영향이 없고, 햇빛을 받는 각도가 중요합니다.", "이 장은 학생용 파일에서 빠집니다."],
    },
})
S.append({
    "id": "S16", "kind": "choice", "section": "확인", "purpose": "마무리 확인(남반구의 계절)", "role": "check", "objectives": ["B"],
    "title": "1월에 바다 수영을 한다면?",
    "text": "1월 겨울방학에 바닷가에서 수영하기 좋은 도시는?",
    "options": [{"text": f"모스크바\n({lat_ko(ROUND['모스크바'][0], 1)})"}, {"text": f"시드니\n({lat_ko(ROUND['시드니'][0], 1)})"}, {"text": f"뉴욕\n({lat_ko(ROUND['뉴욕'][0], 1)})"}],
    "question": "고르고, 위도와 계절로 까닭을 말해요.",
    "notes": {
        "목적": "처음 보는 상황에서 북반구와 남반구의 계절이 반대라는 것을 위도로 판단하는지 확인합니다(목표 B, 오해 M3).",
        "시간": "약 2분",
        "말하기": ["“세 도시 중 남반구에 있는 곳은? 1월에 우리나라는 겨울이지? 그럼 그곳은?”"],
        "정답": ["나(시드니). 남위에 있는 남반구 도시라서 1월이 여름입니다. 모스크바와 뉴욕은 북위(북반구)라 1월이 우리나라처럼 겨울입니다."],
        "막히면": ["S09 그림을 다시 보여 주고 ‘12~2월에는 남반구가 해 쪽으로 기운다’를 읽게 합니다."],
        "주의": ["답만 맞히고 까닭(남반구라 계절이 반대)을 말하지 못하면 기록표에 ‘답만’으로 적습니다."],
    },
})
S.append({
    "id": "S17", "kind": "summary", "section": "정리", "purpose": "정리와 다음 수업 복습", "role": "review", "objectives": ["A", "B", "C"],
    "title": "오늘 배운 것",
    "key": "위도·경도로 위치를 ‘북위 ○°, 동경 ○°’처럼 나타내요.\n위도에 따라 기온·계절이, 경도에 따라 시각이 달라요.",
    "do": "위도 먼저, 북·남과 동·서 붙이기",
    "dont": "남쪽으로 가면 늘 덥다고 생각하기",
    "review": [{"text": "위도와 경도의\n기준선은?"}, {"text": "적도 부근이\n더운 까닭은?"}, {"text": "경도 몇 °마다\n1시간 차이가 날까요?"}],
    "next": "세계의 기후 지역",
    "notes": {
        "목적": "핵심을 정리하고 다음 수업 첫 5분에 풀 복습 문제를 알려 줍니다.",
        "시간": "약 1분",
        "말하기": ["“서울의 위치를 위도·경도로 말해 볼래? 7월에 시드니는 무슨 계절이고, 서울이 저녁 6시일 때 런던은 몇 시야?”"],
        "예상답": [f"“{seoul_ko}예요. 시드니는 겨울이고, 런던은 오전 9시예요.”"],
        "정답": ["① 위도는 적도, 경도는 본초 자오선 ② 햇빛을 거의 수직으로 받아 좁은 곳에 모이기 때문 ③ 15°"],
        "막히면": ["S03, S08, S11을 다시 보여 줍니다."],
        "주의": ["복습 세 문제는 다음 수업을 시작할 때 활동지 마지막 쪽과 함께 풉니다.", "활동지 3의 지도 앱 찾기는 다음 수업 전까지 함께 해 오면 좋습니다.", "다음 차시 ‘세계의 기후 지역’에서는 위도와 이어지는 기후 지역(열대·온대·건조·냉대·한대)을 기온·강수량 그래프로 구별합니다."],
    },
})
S.append({
    "id": "S18", "kind": "concept", "layout": "support", "section": "보충", "purpose": "선수 학습 보충(적도와 본초 자오선, 북위·남위·동경·서경)", "role": "support", "objectives": [],
    "title": "보충: 적도와 본초 자오선",
    "figure": support_fig(),
    "figureRatio": 0.5,
    "points": [{"title": "적도", "text": "지구 가운데를 두른 가로선\n위도 0°"},
               {"title": "본초 자오선", "text": "영국 런던을 지나는 세로선\n경도 0°"},
               {"title": "나누어 부르기", "text": "적도 위·아래는 북위·남위\n오른쪽·왼쪽은 동경·서경"}],
    "notes": {
        "목적": "S02가 흔들리면 6학년에서 배운 적도·본초 자오선과 북위·남위·동경·서경을 다시 확인합니다.",
        "시간": "약 4분",
        "말하기": ["“주황 가로선이 적도야. 적도보다 위쪽(북쪽)은 북위, 아래쪽(남쪽)은 남위야.”", "“파랑 세로선이 본초 자오선이야. 오른쪽(동쪽)은 동경, 왼쪽(서쪽)은 서경이야.”", "“우리나라는 네 칸 중 어디에 있을까?”"],
        "예상답": ["“북위·동경 칸이에요.”"],
        "막히면": ["종이에 큰 십자를 그리고 위 ‘북’, 오른쪽 ‘동’만 써 준 뒤 아이가 나머지 방위를 채우게 합니다."],
        "주의": ["계획상 이 차시의 선수 차시는 6학년 ‘세계 여러 나라’(KR22-G06-SOC-WORLDMAP-L01)와 4학년 ‘지도 읽기’(KR22-G04-SOC-MAP-L01)입니다. 보충으로도 어려우면 ‘세계 여러 나라’의 S08~S09(위도와 경도)를 먼저 하고, 방위가 흔들리면 ‘지도 읽기’의 방위표 부분을 먼저 합니다.",
               "‘오른쪽 = 동쪽’은 북쪽이 위인 지도에서만 맞습니다.", "보충이 오래 걸리면 오늘은 여기까지 하고 다음 날 S02부터 다시 시작합니다."],
    },
})
C["slides"] = S

WS_GRID = grid_fig(WS_PTS, "", ws=True)
C["worksheet"] = {
    "title": "위도와 경도 활동지",
    "items": [
        {"no": 1, "prompt": "빈칸에 알맞은 말이나 수를 쓰세요.\n위도의 기준선은 (　　　　), 경도의 기준선은 (　　　　　　)이에요. 위도는 0°부터 (　　)°까지, 경도는 0°부터 (　　　)°까지 있어요.\n북위 37.6°, 동경 127.0°를 N·S·E·W를 써서 나타내면 (　　　　　　　　　　　　　)예요.",
         "answer": f"적도 / 본초 자오선 / 90 / 180 / {seoul_sym}"},
        {"no": 2, "prompt": f"한 칸은 15°예요. ① 바와 사의 위도와 경도를 쓰세요. ② {ko(*WS_TARGET)}인 곳에 ● 표시를 하세요.",
         "geo": WS_GRID, "line_label": "①", "lines": 2,
         "answer": f"① 바 {ko(*[p for p in WS_PTS if p[0] == '바'][0][1:])} / 사 {ko(*[p for p in WS_PTS if p[0] == '사'][0][1:])} ② 적도에서 북쪽으로 1칸, 본초 자오선에서 서쪽으로 1칸인 곳"},
        {"no": 3, "prompt": "[부모님과 함께] 지도 앱에서 찾아 위도와 경도를 쓰세요(소수 첫째 자리까지, 북위·남위와 동경·서경을 붙여서).",
         "table": {"headers": ["장소", "위도", "경도", "북반구/남반구"], "rows": [["우리 동네 시청(구청)", "", "", ""], ["시드니", "", "", ""], ["뉴욕", "", "", ""], ["내가 고른 곳: ", "", "", ""]],
                   "widths": [0.34, 0.22, 0.22, 0.22], "firstColHead": True},
         "answer": f"기준: 위도를 먼저, 북위·남위와 동경·서경을 붙여 쓰고 음수(−)를 바르게 바꾸면 맞음. 우리 동네는 대략 북위 33°~39°, 동경 124°~132°(북반구). 시드니 약 {ko(*ROUND['시드니'], nd=1)}(남반구), 뉴욕 약 {ko(*ROUND['뉴욕'], nd=1)}(북반구). 찾는 자리에 따라 소수점 아래가 조금 달라도 맞음."},
        {"no": 4, "prompt": "1월에 서울과 시드니는 각각 어떤 계절인가요? 까닭을 ‘북반구’, ‘남반구’를 넣어 쓰세요.",
         "lines": 3,
         "answer": "서울 겨울, 시드니 여름. 서울은 북반구, 시드니는 남반구에 있는데, 12~2월에는 자전축의 남쪽이 해 쪽으로 기울어 남반구가 햇빛을 높이(수직에 가깝게) 받기 때문에 두 곳의 계절이 반대이다. 북반구·남반구와 계절이 반대라는 것을 쓰면 맞음."},
        {"no": 5, "prompt": "모스크바(러시아)는 동경 45°의 시각을 써요. 서울(동경 135°)과 모스크바의 시차를 식으로 구하고, 서울이 오후 3시일 때 모스크바의 시각을 쓰세요.",
         "lines": 2,
         "answer": f"(135 − 45) ÷ 15 = {diff_hours('서울', '모스크바')}, 6시간. 서울이 동쪽이라 6시간 빠르므로 모스크바는 {clock(15 - 6)}."},
        {"no": 6, "new_page": True, "heading": "다음 수업을 시작할 때",
         "prompt": "① 위도와 경도의 기준이 되는 선은 각각 무엇인가요?  ② 적도 부근이 극 부근보다 더운 까닭은 무엇인가요?  ③ 경도 몇 °마다 1시간의 시차가 생기나요?",
         "lines": 3,
         "answer": "① 위도는 적도, 경도는 본초 자오선 ② 햇빛을 거의 수직으로 받아 같은 양의 햇빛이 좁은 곳에 모이기 때문 ③ 15°"},
    ],
    "record": [
        "S02 선수 확인: 세 문제 모두 □  흔들림(보충 S18) □",
        "S05·S06 위치 나타내기: 위도 먼저, 북·남과 동·서를 붙여 말함 □  도움 □",
        "S07·활동지 3 지도 앱: 함께 했음 □  다음에 하기로 함 □",
        "S14 혼자 해 보기: 모두 맞힘 □  한두 개 도움 □  도움을 받아 해결 □",
        "S16 마무리 확인: 답과 까닭 모두 □  답만 □  아직 □",
        "오해: 위도·경도를 바꿔 읽음(M1) □  남쪽은 늘 더움(M2) □  계절이 어디나 같음(M3) □  시차를 거꾸로(M4) □",
    ],
}

# ---------------------------------------------------------------- cross-checks between text and data
dump = json.dumps(C, ensure_ascii=False)
for n, a, b in S05_PTS[:2] + S14_PTS + WS_PTS:
    assert ko(a, b) in dump, (n, ko(a, b))
assert "북위 15°, 서경 15°" in dump
OUT.write_text(json.dumps(C, ensure_ascii=False, indent=1), encoding="utf-8")
print("wrote", OUT, "slides", len(S), "arc ratio", round(ARCS[1] / ARCS[0], 2))
