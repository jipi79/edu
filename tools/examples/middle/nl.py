"""geo 수직선 도우미: 음수 눈금을 진짜 빼기 기호(−)로 쓰고, 이동 화살표(색·이름표)를 따로 그린다."""
MINUS = "−"


def sgn(v, plus=False):
    """수를 글자로: 음수는 −, plus=True면 양수에 +."""
    if v == 0:
        return "0"
    s = ("%g" % abs(v))
    if v < 0:
        return MINUS + s
    return ("+" + s) if plus else s


def numline(lo, hi, y=0.0, jumps=(), dots=(), labels="all", step=1, pad=0.6, label_dy=0.62, tick=0.18):
    """한 줄 수직선의 geo 조각(segments, texts, circles)을 돌려준다.
    jumps: [(from, to, height, color, label)] — height는 수직선 위 높이(단위)
    dots: [(x, color)] 꽉 찬 점
    """
    segs = [{"from": [lo - pad, y], "to": [hi + pad, y], "arrow": "both", "width": 2.25}]
    texts, circles = [], []
    n = int(round((hi - lo) / step))
    for i in range(n + 1):
        v = round(lo + i * step, 6)
        segs.append({"from": [v, y - tick], "to": [v, y + tick], "width": 1.75})
        show = labels == "all" or (isinstance(labels, (list, tuple)) and v in labels)
        if show:
            texts.append({"at": [v, y - label_dy], "text": sgn(v), "bold": False})
    for (a, b, h, color, lab) in jumps:
        segs.append({"from": [a, y + 0.05], "to": [a, y + h], "width": 1.5, "color": color})
        segs.append({"from": [a, y + h], "to": [b, y + h], "arrow": "end", "width": 2.5, "color": color})
        if lab:
            texts.append({"at": [(a + b) / 2, y + h + 0.38], "text": lab, "color": color})
    for (x, color) in dots:
        circles.append({"center": [x, y], "r": 0.13, "fill": color, "color": color, "width": 1})
    return segs, texts, circles


def geo(lines, alt, extra_texts=(), bounds=None):
    """여러 줄 수직선을 한 geo 그림으로."""
    segs, texts, circles = [], [], []
    for (s, t, c) in lines:
        segs += s; texts += t; circles += c
    texts += list(extra_texts)
    fig = {"type": "geo", "points": {}, "segments": segs, "texts": texts, "circles": circles, "names": False, "alt": alt}
    if bounds:
        fig["points"] = {"_lo": bounds[0], "_hi": bounds[1]}
    return fig
