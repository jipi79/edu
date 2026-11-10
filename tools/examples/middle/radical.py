"""중3 수학(실수와 그 계산, 곱셈 공식) 차시 생성기 공용 도우미.

- 식 읽기: 화면에 쓰는 식(2√3 × √5, √12 + √27, 6 ÷ √3, (2x − 5y)², (x + 3)(x − 1))을 읽는다.
  붙여 쓴 곱(2√3, 3a², √2(√6 + 3))은 ×·÷보다 먼저 묶는다(6 ÷ 2√3 = 6 ÷ (2√3)).
  √ 는 바로 뒤의 수 또는 괄호 하나에만 걸린다(√12, √(2² × 3)). √3² 처럼 쓰지 않는다((√3)², √(3²)).
- Rad: 근호가 있는 수를 정확히(근호 안은 제곱인수가 없는 자연수, 계수는 분수) 나타내 계산한다.
- Poly: 다항식을 계수 사전({단항식: 계수})으로 전개한다.
- Checks: checks 항목을 만든다. 이 파일을 쓸 때는 검산기가 근호를 읽지 못해 제곱한 값끼리 비교했지만,
  이제 check_lesson.py가 √·²를 읽으므로 화면에 보이는 답을 그대로 blank/compare/equiv에 넣어도 된다.
"""
import json
import math
from fractions import Fraction as F
from pathlib import Path

M = "−"
DIG = "0123456789"
SUP = {"⁰": 0, "¹": 1, "²": 2, "³": 3, "⁴": 4, "⁵": 5, "⁶": 6, "⁷": 7, "⁸": 8, "⁹": 9}
L6 = "①②③④⑤⑥"


def notes(목적, 시간, 말하기, 정답=None, 예상답=None, 막히면=None, 주의=None):
    n = {"목적": 목적, "시간": 시간, "말하기": 말하기}
    if 예상답: n["예상답"] = 예상답
    if 정답: n["정답"] = 정답
    if 막히면: n["막히면"] = 막히면
    if 주의: n["주의"] = 주의
    return n


def dump(out, content):
    Path(out).write_text(json.dumps(content, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("wrote", out)


# ---------------- 제곱인수 ----------------

def squarefree(n):
    """n = k² × m (m은 제곱인수가 없는 수)인 (k, m)."""
    assert n >= 0 and int(n) == n
    n = int(n)
    if n == 0:
        return 0, 1
    k, m, p = 1, n, 2
    while p * p <= m:
        while m % (p * p) == 0:
            m //= p * p
            k *= p
        p += 1
    return k, m


def is_square(n):
    n = F(n)
    if n < 0:
        return False
    a, b = n.numerator, n.denominator
    return math.isqrt(a) ** 2 == a and math.isqrt(b) ** 2 == b


# ---------------- 근호가 있는 수 ----------------

class Rad:
    """Σ c·√m (m: 제곱인수가 없는 자연수, c: 분수). m = 1 은 유리수 부분."""

    def __init__(self, terms=None):
        self.t = {m: F(c) for m, c in (terms or {}).items() if F(c) != 0}

    @staticmethod
    def of(x):
        return x if isinstance(x, Rad) else Rad({1: F(x)})

    @staticmethod
    def sqrt(x):
        x = Rad.of(x)
        assert x.is_rational(), f"근호 안이 유리수가 아니다: {x}"
        q = x.rational()
        assert q >= 0, f"음수의 제곱근: {q}"
        # √(a/b) = √(ab)/b
        a, b = q.numerator, q.denominator
        k, m = squarefree(a * b)
        return Rad({m: F(k, b)})

    def is_rational(self):
        return all(m == 1 for m in self.t)

    def rational(self):
        assert self.is_rational()
        return self.t.get(1, F(0))

    def single(self):
        """한 항(c√m)이면 (c, m)."""
        if not self.t:
            return F(0), 1
        assert len(self.t) == 1, f"항이 여러 개: {self}"
        (m, c), = self.t.items()
        return c, m

    def __add__(self, o):
        o = Rad.of(o)
        d = dict(self.t)
        for m, c in o.t.items():
            d[m] = d.get(m, F(0)) + c
        return Rad(d)

    __radd__ = __add__

    def __neg__(self):
        return Rad({m: -c for m, c in self.t.items()})

    def __sub__(self, o):
        return self + (-Rad.of(o))

    def __rsub__(self, o):
        return Rad.of(o) - self

    def __mul__(self, o):
        o = Rad.of(o)
        d = {}
        for m1, c1 in self.t.items():
            for m2, c2 in o.t.items():
                k, m = squarefree(m1 * m2)
                d[m] = d.get(m, F(0)) + c1 * c2 * k
        return Rad(d)

    __rmul__ = __mul__

    def __truediv__(self, o):
        c, m = Rad.of(o).single()
        assert c != 0
        # 1/(c√m) = √m/(c·m)
        return self * Rad({m: F(1) / (c * m)})

    def __rtruediv__(self, o):
        return Rad.of(o) / self

    def __pow__(self, n):
        r = Rad.of(1)
        for _ in range(n):
            r = r * self
        return r

    def __eq__(self, o):
        return self.t == Rad.of(o).t

    def __hash__(self):
        return hash(tuple(sorted(self.t.items())))

    def __float__(self):
        return float(sum(float(c) * math.sqrt(m) for m, c in self.t.items()))

    def sign(self):
        v = float(self)
        return (v > 0) - (v < 0)

    def __repr__(self):
        return " + ".join(f"{c}√{m}" if m != 1 else f"{c}" for m, c in sorted(self.t.items())) or "0"


# ---------------- 다항식 ----------------

class Poly:
    """{((문자, 지수), …): 계수} 사전으로 나타낸 다항식."""

    def __init__(self, terms=None):
        self.t = {k: F(c) for k, c in (terms or {}).items() if F(c) != 0}

    @staticmethod
    def of(x):
        return x if isinstance(x, Poly) else Poly({(): F(x)})

    @staticmethod
    def var(v):
        return Poly({((v, 1),): F(1)})

    def __add__(self, o):
        o = Poly.of(o)
        d = dict(self.t)
        for k, c in o.t.items():
            d[k] = d.get(k, F(0)) + c
        return Poly(d)

    __radd__ = __add__

    def __neg__(self):
        return Poly({k: -c for k, c in self.t.items()})

    def __sub__(self, o):
        return self + (-Poly.of(o))

    def __mul__(self, o):
        o = Poly.of(o)
        d = {}
        for k1, c1 in self.t.items():
            for k2, c2 in o.t.items():
                e = dict(k1)
                for v, n in k2:
                    e[v] = e.get(v, 0) + n
                k = tuple(sorted(e.items()))
                d[k] = d.get(k, F(0)) + c1 * c2
        return Poly(d)

    __rmul__ = __mul__

    def __truediv__(self, o):
        o = Poly.of(o)
        assert len(o.t) == 1
        (k2, c2), = o.t.items()
        d = {}
        for k1, c1 in self.t.items():
            e = dict(k1)
            for v, n in k2:
                e[v] = e.get(v, 0) - n
                assert e[v] >= 0, "나누어떨어지지 않는다"
            k = tuple(sorted((v, n) for v, n in e.items() if n))
            d[k] = d.get(k, F(0)) + c1 / c2
        return Poly(d)

    def __pow__(self, n):
        r = Poly.of(1)
        for _ in range(n):
            r = r * self
        return r

    def __eq__(self, o):
        return self.t == Poly.of(o).t

    def __repr__(self):
        return str(self.t)


# ---------------- 식 읽기 ----------------

def tokens(s):
    out, i = [], 0
    while i < len(s):
        c = s[i]
        if c.isspace():
            i += 1
        elif c in DIG:
            j = i
            while j < len(s) and (s[j] in DIG or (s[j] == "." and j + 1 < len(s) and s[j + 1] in DIG)):
                j += 1
            out.append(("num", s[i:j])); i = j
        elif c in SUP:
            j = i
            while j < len(s) and s[j] in SUP:
                j += 1
            out.append(("sup", int("".join(str(SUP[ch]) for ch in s[i:j])))); i = j
        elif "a" <= c <= "z":
            out.append(("var", c)); i += 1
        elif c == "√":
            out.append(("sqrt", c)); i += 1
        elif c in "+−-×÷/":
            out.append(("op", {"-": "−", "/": "÷"}.get(c, c))); i += 1
        elif c in "({[":
            out.append(("(", c)); i += 1
        elif c in ")}]":
            out.append((")", c)); i += 1
        else:
            raise ValueError(f"읽을 수 없는 글자 {c!r} in {s!r}")
    return out


class Parser:
    def __init__(self, s):
        self.t = tokens(s); self.i = 0; self.s = s

    def peek(self):
        return self.t[self.i] if self.i < len(self.t) else (None, None)

    def take(self):
        tok = self.t[self.i]; self.i += 1; return tok

    def parse(self):
        e = self.expr()
        if self.i != len(self.t):
            raise ValueError(f"남은 글자 in {self.s!r}: {self.t[self.i:]}")
        return e

    def expr(self):
        node = self.term()
        while self.peek() in (("op", "+"), ("op", "−")):
            op = self.take()[1]
            node = ("bin", op, node, self.term())
        return node

    def term(self):
        node = self.unary()
        while self.peek() in (("op", "×"), ("op", "÷")):
            op = self.take()[1]
            node = ("bin", op, node, self.unary())
        return node

    def unary(self):
        if self.peek() == ("op", "−"):
            self.take(); return ("neg", self.unary())
        if self.peek() == ("op", "+"):
            self.take(); return self.unary()
        return self.juxt()

    def juxt(self):
        fs = [self.power()]
        while self.peek()[0] in ("num", "var", "(", "sqrt"):
            fs.append(self.power())
        return fs[0] if len(fs) == 1 else ("mul", fs)

    def atom(self):
        k, v = self.take()
        if k == "num":
            return ("num", v)
        if k == "var":
            return ("var", v)
        if k == "(":
            node = ("par", self.expr())
            if self.take()[0] != ")":
                raise ValueError("괄호 짝")
            return node
        if k == "sqrt":
            return ("sqrt", self.atom())
        raise ValueError(f"뜻밖의 {k} {v} in {self.s!r}")

    def power(self):
        node = self.atom()
        if self.peek()[0] == "sup":
            node = ("pow", node, self.take()[1])
        return node


def parse(s):
    return Parser(s).parse()


def ev(node, kind, env=None):
    """kind: 'rad'(근호가 있는 수), 'poly'(다항식), 'num'(문자에 env의 수를 넣은 분수)."""
    k = node[0]
    if k == "num":
        x = F(node[1])
        return Rad.of(x) if kind == "rad" else Poly.of(x) if kind == "poly" else x
    if k == "var":
        if kind == "poly":
            return Poly.var(node[1])
        if kind == "num":
            return F(env[node[1]])
        raise ValueError("근호 계산에 문자가 있다")
    if k == "par":
        return ev(node[1], kind, env)
    if k == "neg":
        return -ev(node[1], kind, env)
    if k == "pow":
        return ev(node[1], kind, env) ** node[2]
    if k == "sqrt":
        if kind != "rad":
            raise ValueError("다항식 계산에 근호가 있다")
        return Rad.sqrt(ev(node[1], kind, env))
    if k == "mul":
        r = ev(node[1][0], kind, env)
        for f in node[1][1:]:
            r = r * ev(f, kind, env)
        return r
    a, b = ev(node[2], kind, env), ev(node[3], kind, env)
    return {"+": lambda: a + b, "−": lambda: a - b, "×": lambda: a * b, "÷": lambda: a / b}[node[1]]()


def rad(s):
    return ev(parse(s), "rad")


def poly(s):
    return ev(parse(s), "poly")


def num(s, env=None):
    return ev(parse(s), "num", env or {})


# ---------------- 검산기용 식 만들기 ----------------

def fmt_val(v):
    v = F(v)
    s = str(abs(v.numerator)) if v.denominator == 1 else f"{abs(v.numerator)}/{v.denominator}"
    return f"({M}{s})" if v < 0 else f"({s})"


def emit(node, env=None):
    """수 식(문자는 env의 수로)을 검산기가 읽는 글자로. 근호는 쓸 수 없다."""
    k = node[0]
    if k == "num": return node[1]
    if k == "var": return fmt_val(env[node[1]])
    if k == "par": return "(" + emit(node[1], env) + ")"
    if k == "neg": return M + emit(node[1], env)
    if k == "pow":
        b = emit(node[1], env)
        return "(" + " × ".join([b] * node[2]) + ")" if node[2] > 1 else b
    if k == "mul": return "(" + " × ".join(emit(f, env) for f in node[1]) + ")"
    if k == "sqrt": raise ValueError("근호는 검산 식에 쓸 수 없다")
    return f"{emit(node[2], env)} {node[1]} {emit(node[3], env)}"


def emit_sq(node):
    """곱·몫으로만 된 근호 식의 제곱을 근호 없는 식으로: 2√3 × √5 → (2 × 2) × 3 × 5."""
    k = node[0]
    if k == "num": return f"({node[1]} × {node[1]})"
    if k == "par": return emit_sq(node[1])
    if k == "neg": return emit_sq(node[1])
    if k == "sqrt": return "(" + emit(node[1]) + ")"
    if k == "pow":
        b = emit_sq(node[1])
        return "(" + " × ".join([b] * node[2]) + ")"
    if k == "mul": return "(" + " × ".join(emit_sq(f) for f in node[1]) + ")"
    if k == "bin" and node[1] in ("×", "÷"):
        return f"({emit_sq(node[2])} {node[1]} {emit_sq(node[3])})"
    raise ValueError("덧셈·뺄셈이 있는 식은 제곱 비교를 만들 수 없다")


ENVS = [{"a": 2, "b": 3, "x": 2, "y": 3}, {"a": -3, "b": 5, "x": 5, "y": -2}, {"a": 7, "b": -4, "x": -3, "y": 4},
        {"a": F(1, 2), "b": 2, "x": 3, "y": F(-1, 3)}]


class Checks(list):
    def blank(self, expr, answer, where):
        """검산기와 같은 방식으로 미리 확인한다(□에 답을 넣어 양쪽이 같은지)."""
        left, right = expr.replace("□", str(answer)).split("=")
        assert num(left) == num(right), (expr, answer, where, num(left), num(right))
        self.append({"type": "blank", "expr": expr, "answer": answer, "where": where})

    def cmp(self, a, b, rel, where):
        x, y = num(a), num(b)
        assert {"<": x < y, ">": x > y, "=": x == y}[rel], (a, b, rel, where)
        self.append({"type": "compare", "values": [a, b], "rel": rel, "where": where})

    def simp(self, n, k, m, where):
        """√n = k√m: k × k × m = n (m은 제곱인수가 없다)."""
        assert squarefree(n) == (k, m), (n, k, m)
        self.blank(f"□ × □ × {m} = {n}", k, where)

    def rad_eq(self, lhs, rhs, where, sq=True):
        """근호 식 lhs = rhs를 정확히 확인. 곱·몫만 있으면 제곱끼리 같다는 compare를 더한다."""
        a, b = rad(lhs), rad(rhs)
        assert a == b, (lhs, rhs, a, b, where)
        if sq:
            assert a.sign() == b.sign()
            self.append({"type": "compare", "values": [emit_sq(parse(lhs)), emit_sq(parse(rhs))], "rel": "=", "where": f"{where} (제곱해서 비교)"})
            # 검산기로도 성립하는지 미리 확인
            assert num(self[-1]["values"][0]) == num(self[-1]["values"][1])

    def rad_only(self, lhs, rhs, where):
        """검산 식 없이 생성기 안에서만 확인(덧셈·뺄셈이 있는 근호 식). where는 기록용."""
        a, b = rad(lhs), rad(rhs)
        assert a == b, (lhs, rhs, a, b, where)

    def poly_eq(self, lhs, rhs, where, env=None):
        a, b = poly(lhs), poly(rhs)
        assert a == b, (lhs, rhs, a, b, where)
        env = env or ENVS[0]
        for e in ENVS:
            assert num(lhs, e) == num(rhs, e)
        self.append({"type": "compare", "values": [emit(parse(lhs), env), emit(parse(rhs), env)], "rel": "=", "where": where})

    def poly_ne(self, lhs, rhs, where, env=None):
        assert poly(lhs) != poly(rhs), (lhs, rhs, where)
        env = env or ENVS[0]
        a, b = num(lhs, env), num(rhs, env)
        assert a != b
        self.append({"type": "compare", "values": [emit(parse(lhs), env), emit(parse(rhs), env)], "rel": "<" if a < b else ">", "where": where})

    def val(self, expr, env, answer, where):
        v = num(expr, env)
        assert v == F(answer), (expr, env, v, answer)
        self.append({"type": "blank", "expr": f"{emit(parse(expr), env)} = □", "answer": answer, "where": where})


def approx_ok(n, approx, digits):
    """approx(소수 digits자리, 버림)가 √n의 버림값인지 math.isqrt로 확인."""
    scale = 10 ** digits
    return math.isqrt(n * scale * scale) == round(F(str(approx)) * scale)


# ---------------- 그림 도우미 ----------------

def r3(v):
    return round(float(v) + 0.0, 3)


def seg(a, b, **kw):
    d = {"from": [r3(a[0]), r3(a[1])], "to": [r3(b[0]), r3(b[1])]}
    d.update(kw)
    return d


def txt(at, text, **kw):
    d = {"at": [r3(at[0]), r3(at[1])], "text": text}
    d.update(kw)
    return d


def numline(lo, hi, y=0.0, labels="all", step=1, pad=0.6, label_dy=0.62, tick=0.18, width=2.25):
    """한 줄 수직선의 geo 조각(segments, texts). 음수 눈금은 진짜 빼기 기호."""
    segs = [{"from": [lo - pad, y], "to": [hi + pad, y], "arrow": "both", "width": width}]
    texts = []
    n = int(round((hi - lo) / step))
    for i in range(n + 1):
        v = round(lo + i * step, 6)
        segs.append({"from": [v, y - tick], "to": [v, y + tick], "width": 1.75})
        if labels == "all" or (isinstance(labels, (list, tuple)) and v in labels):
            s = ("%g" % abs(v))
            texts.append({"at": [v, y - label_dy], "text": (M + s) if v < 0 else s, "bold": False})
    return segs, texts
