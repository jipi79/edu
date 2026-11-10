"""Shared geo helpers for the middle-school sample lessons (TEMP, LATLONG)."""
import math

INK = "1F2937"
GRIDC = "D5DBE3"


def r3(v):
    return round(v + 0.0, 3)


def P(x, y):
    return [r3(x), r3(y)]


def seg(a, b, color=INK, width=1.5, **kw):
    d = {"from": P(*a), "to": P(*b), "color": color, "width": width}
    d.update(kw)
    return d


def txt(at, text, size="small", bold=False, **kw):
    d = {"at": P(*at), "text": text, "size": size, "bold": bold}
    d.update(kw)
    return d


def arc_pts(cx, cy, r, a1, a2, n=48):
    return [P(cx + r * math.cos(math.radians(a1 + (a2 - a1) * i / n)), cy + r * math.sin(math.radians(a1 + (a2 - a1) * i / n))) for i in range(n + 1)]


def dist_point_seg(p, a, b):
    ax, ay = a
    bx, by = b
    px, py = p
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    t = 0 if L2 == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / L2))
    qx, qy = ax + t * dx, ay + t * dy
    return math.hypot(px - qx, py - qy)


def segs_cross(a, b, c, d):
    def orient(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    o1, o2, o3, o4 = orient(a, b, c), orient(a, b, d), orient(c, d, a), orient(c, d, b)
    return (o1 * o2 < 0) and (o3 * o4 < 0)
