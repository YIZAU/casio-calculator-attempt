from __future__ import annotations

import math
from typing import Any, Callable

_MAX_INT_POWER = 10 ** 5              # 整数幂上限
_MAX_BASE_FOR_ROOT = 10 ** 12         # 分数指数时完全 q 次方判定的底数上限

_MAX_LOG_EXP = 10 ** 5   # 指数上限，避免异常输入导致死循环

_TABLE: dict[tuple[str, type, type], Callable[[Any, Any], Any]] = {}


def register(op: str, lt: type, rt: type, commutative: bool = False):
    def register_rule(func):
        _TABLE[(op, lt, rt)] = func
        if commutative and lt is not rt:
            # Auto-generate the reversed entry (a, b) -> fn(b, a)
            _TABLE[(op, rt, lt)] = lambda a, b: func(b, a)
        return func
    return register_rule


def dispatch(op: str, a: Node, b: Node) -> Node | None:
    """Look up a folding rule; return None if no rule exists."""
    fn = _TABLE.get((op, type(a), type(b)))
    return fn(a, b) if fn else None


class Node:
    """Base of every expression node."""

    is_numeric: bool = False
    __slots__ = ()

    # ---- Operator overloading ----

    def __add__(self, other):
        return self._binary_op(other, "+")

    def __radd__(self, other):
        return BinaryOpNode(other, self, "+")

    def __sub__(self, other):
        return self._binary_op(other, "-")

    def __rsub__(self, other):
        return BinaryOpNode(other, self, "-")

    def __mul__(self, other):
        return self._binary_op(other, "*")

    def __rmul__(self, other):
        return BinaryOpNode(other, self, "*")

    def __truediv__(self, other):
        return self._binary_op(other, "/")

    def __rtruediv__(self, other):
        return BinaryOpNode(other, self, "/")

    def __str__(self) -> str:
        return self.to_str()

    # def __pow__(self, other):
    #     return PowerNode()
    #
    # def __rpow__(self, other):
    #     return BinaryOpNode(other, self, "^")

    # def __neg__(self):
    #     return NegativeNode(self)

    def _binary_op(self, other, op):
        if (self.is_numeric
                and isinstance(other, Node)
                and other.is_numeric):
            r = dispatch(op, self, other)
            if r is not None:
                return r
        return BinaryOpNode(self, other, op)

    def evaluate(self, env: dict | None = None):
        raise NotImplementedError

    def to_str(self, parent_prec: int = 0) -> str:
        raise NotImplementedError

    def simplify(self, env: dict | None = None):
        return self


class IntegerNode(Node):
    is_numeric = True
    __slots__ = ("value",)

    def __init__(self, value: int):
        self.value = int(value)

    def evaluate(self, env=None) -> int:
        return self.value

    def to_str(self, parent_prec=0) -> str:
        return str(self.value)


class DecimalNode(Node):
    is_numeric = True
    __slots__ = ("value",)

    _MAX_FRACTION_DEN = 10 ** 4

    def __init__(self, value: float):
        self.value = float(value)

    def simplify(self, env: dict | None = None):
        if self.value == int(self.value):
            return IntegerNode(int(self.value))

        ratio = _decimal_to_ratio(self.value)
        if ratio is not None:
            num, den = ratio
            if den <= self._MAX_FRACTION_DEN:
                return FractionNode(IntegerNode(num), IntegerNode(den))

        return self

    def evaluate(self, env=None) -> float:
        return self.value

    def to_str(self, parent_prec=0) -> str:
        return str(self.value)


def _is_sqrt_node(node: Node) -> bool:
    """node 是 √n（n > 1 的整数）"""
    return (isinstance(node, RootNode)
            and isinstance(node.degree, IntegerNode)
            and node.degree.value == 2
            and isinstance(node.radicand, IntegerNode)
            and node.radicand.value > 1)


def _is_rational_value(node: Node) -> bool:
    """node 是有理数：整数或分数"""
    if isinstance(node, IntegerNode):
        return True
    if isinstance(node, FractionNode):
        return (isinstance(node.num, IntegerNode)
                and isinstance(node.den, IntegerNode)
                and node.den.value > 0)
    return False


def _split_signed(node: Node):
    """
    把 node 拆成 (t1, op, t2)：
    - node 是 a + b → (a, '+', b)
    - node 是 a - b → (a, '-', b)
    - node 是单项 → (node, None, None)
    只处理顶层的加减，不递归。
    """
    if isinstance(node, BinaryOpNode) and node.op in ('+', '-'):
        return node.left, node.op, node.right
    return node, None, None


def _analyze_denominator(den: Node):
    """
    分析分母是否可有理化。
    返回 dict 或 None：
      {'kind': 'single', 'k': int, 'n': int}       # den = k·√n
      {'kind': 'pair', 't1': Node, 't2': Node, 'op': str}  # den = t1 ± t2
    """
    # 情形 1：单个 √n 或 k·√n
    if _is_sqrt_node(den):
        return {'kind': 'single', 'k': 1, 'n': den.radicand.value}

    if isinstance(den, BinaryOpNode) and den.op == "*":
        for sqrt_side, other_side in ((den.left, den.right), (den.right, den.left)):
            if _is_sqrt_node(sqrt_side) and isinstance(other_side, IntegerNode):
                return {'kind': 'single', 'k': other_side.value, 'n': sqrt_side.radicand.value}

    # 情形 2：t1 ± t2
    t1, op, t2 = _split_signed(den)
    if op is None or t2 is None:
        return None

    # 每一项必须是有理数或含至多一个平方根
    if not (_is_rational_value(t1) or _is_sqrt_node(t1) or _has_single_sqrt(t1)):
        return None
    if not (_is_rational_value(t2) or _is_sqrt_node(t2) or _has_single_sqrt(t2)):
        return None

    # 至少一项必须含平方根，否则分母已经有理
    if _is_rational_value(t1) and _is_rational_value(t2):
        return None

    return {'kind': 'pair', 't1': t1, 't2': t2, 'op': op}


def _has_single_sqrt(node: Node) -> bool:
    """node 是 k·√n 形式（k 是整数）"""
    if isinstance(node, BinaryOpNode) and node.op == "*":
        for sqrt_side, other_side in ((node.left, node.right), (node.right, node.left)):
            if _is_sqrt_node(sqrt_side) and isinstance(other_side, IntegerNode):
                return True
    return False


class FractionNode(Node):
    is_numeric = True
    __slots__ = ("num", "den")

    def __init__(self, numerator: Node, denominator: Node):
        self.num = numerator
        self.den = denominator

    def simplify(self, env=None):
        env = env or {}
        num = self.num.simplify(env)
        den = self.den.simplify(env)

        # 分母是有理数：走 gcd 路径
        if _is_rational_value(den):
            return self._reduce_to_lowest(num, den)

        # 分母含平方根：尝试有理化
        rationalized = self._try_rationalize(num, den, env)
        if rationalized is not None:
            return rationalized

        # 无法处理：保留
        if num is self.num and den is self.den:
            return self
        return FractionNode(num, den)

    def _reduce_to_lowest(self, num: Node, den: Node) -> Node:
        if den.value == 0:
            raise ZeroDivisionError("Math Error: division by zero")

        # 分子分母都是整数：直接 gcd
        if isinstance(num, IntegerNode) and isinstance(den, IntegerNode):
            g = math.gcd(num.value, den.value) or 1
            n, d = num.value // g, den.value // g
            if d < 0:
                n, d = -n, -d
            if d == 1:
                return IntegerNode(n)
            return FractionNode(IntegerNode(n), IntegerNode(d))

        # 分母是分数：翻转为乘法
        if isinstance(den, FractionNode):
            if (isinstance(den.num, IntegerNode) and isinstance(den.den, IntegerNode)
                    and den.num.value != 0):
                new_num = FractionNode(num, den.num).simplify()
                return FractionNode(
                    new_num.num if isinstance(new_num, FractionNode) else new_num,
                    IntegerNode(den.den.value) if not isinstance(new_num, FractionNode)
                    else IntegerNode(new_num.den.value * den.den.value),
                ).simplify()

        return FractionNode(num, den)

    def _try_rationalize(self, num: Node, den: Node, env) -> Node | None:
        info = _analyze_denominator(den)
        if info is None:
            return None

        if info['kind'] == 'single':
            return self._rationalize_single(num, info['k'], info['n'], env)

        if info['kind'] == 'pair':
            return self._rationalize_pair(num, info['t1'], info['t2'], info['op'], env)

        return None

    def _rationalize_single(self, num: Node, k: int, n: int, env) -> Node:
        """num / (k·√n) → num·√n / (k·n)"""
        conj = RootNode(IntegerNode(2), IntegerNode(n))
        new_num = BinaryOpNode(num, conj, "*").simplify(env)

        new_den_value = k * n
        if new_den_value == 1:
            return new_num
        return FractionNode(new_num, IntegerNode(new_den_value)).simplify(env)

    def _rationalize_pair(self, num: Node, t1: Node, t2: Node, op: str, env) -> Node | None:
        """num / (t1 ± t2) → num·(t1 ∓ t2) / (t1² - t2²)"""
        conj_op = "-" if op == "+" else "+"
        conj = BinaryOpNode(t1, t2, conj_op)

        # 新分母：t1² - t2²
        t1_sq = BinaryOpNode(t1, t1, "*").simplify(env)
        t2_sq = BinaryOpNode(t2, t2, "*").simplify(env)
        new_den = BinaryOpNode(t1_sq, t2_sq, "-").simplify(env)

        # 若共轭技巧未能消去平方根，放弃
        if not _is_rational_value(new_den):
            return None

        # 新分子
        new_num = BinaryOpNode(num, conj, "*").simplify(env)

        return FractionNode(new_num, new_den).simplify(env)

    def evaluate(self, env=None) -> float:
        d = self.den.evaluate(env)
        if d == 0:
            raise ZeroDivisionError("Division by zero")
        return self.num.evaluate(env) / d

    def to_str(self, parent_prec=0) -> str:
        return f"({self.num.to_str()} / {self.den.to_str()})"


class ComplexNode(Node):
    is_numeric = True
    __slots__ = ("real", "imag")

    def __init__(self, real: Node, imaginary: Node):
        self.real = real
        self.imag = imaginary

    def simplify(self, env=None):
        r = self.real.simplify(env) if isinstance(self.real, Node) else self.real
        i = self.imag.simplify(env) if isinstance(self.imag, Node) else self.imag
        if r is self.real and i is self.imag:
            return self
        return ComplexNode(r, i)

    def evaluate(self, env=None):
        return complex(self.real.evaluate(env), self.imag.evaluate(env))

    def to_str(self, parent_prec=0) -> str:
        r = self.real.to_str()
        i = self.imag.to_str()
        if i.startswith("-"):
            return f"{r}{i}i"
        return f"{r}+{i}i"


class ConstantNode(Node):
    __slots__ = ()


class PiNode(ConstantNode):
    __slots__ = ()

    def evaluate(self, env: dict | None = None):
        return math.pi

    def to_str(self, parent_prec: int = 0) -> str:
        return "π"


class EulerNode(ConstantNode):
    __slots__ = ()

    def evaluate(self, env: dict | None = None):
        return math.e

    def to_str(self, parent_prec: int = 0) -> str:
        return "e"


class ImaginaryNode(ConstantNode):
    __slots__ = ()

    def evaluate(self, env: dict | None = None):
        return 1j

    def to_str(self, parent_prec: int = 0) -> str:
        return "i"


class VariableNode(Node):
    __slots__ = ("name",)

    def __init__(self, name: str):
        self.name = name

    def simplify(self, env: dict | None = None) -> Node:
        if self.name == "π":
            return PiNode()
        if self.name == "e":
            return EulerNode()
        if self.name == "i":
            return ImaginaryNode()

        if env and self.name in env.keys():
            unknown_variable = env.get("unknown", None)
            if unknown_variable is None:
                return env[self.name]
            else:
                return self if unknown_variable == self.name else env[self.name]

        raise NameError(f"Undefined variable: {self.name}")

    def evaluate(self, env=None):
        env = env or {}
        if self.name == "π":
            return math.pi
        if self.name == "e":
            return math.e
        if self.name == "i":
            return 1j
        if self.name in env.keys():
            v = env[self.name]
            return v.evaluate(env) if isinstance(v, Node) else v
        raise NameError(f"Undefined variable: {self.name}")

    def to_str(self, parent_prec=0) -> str:
        return self.name


class NegativeNode(Node):
    __slots__ = ("child",)

    def __init__(self, child: Node):
        self.child = child

    def simplify(self, env=None):
        env = env or {}
        c = self.child.simplify(env)
        if isinstance(c, Node) and c.is_numeric:
            r = dispatch("neg", c, c)
            if r is not None:
                return r
        return NegativeNode(c)

    def evaluate(self, env=None) -> float:
        return -self.child.evaluate(env)

    def to_str(self, parent_prec=0) -> str:
        return f"-({self.child.to_str()})"


class BinaryOpNode(Node):
    __slots__ = ("left", "right", "op")

    def __init__(self, left: Node, right: Node, op: str):
        self.left = left
        self.right = right
        self.op = op  # "+", "-", "*", "/"

    def simplify(self, env=None):
        env = env or {}
        l = self.left.simplify(env)
        r = self.right.simplify(env)

        res = dispatch(self.op, l, r)
        if res is not None:
            return res.simplify(env)

        if l is self.left and r is self.right:
            return self
        return BinaryOpNode(l, r, self.op)

    def evaluate(self, env=None):
        l = self.left.evaluate(env)
        r = self.right.evaluate(env)

        if self.op == "+":
            return l + r
        if self.op == "-":
            return l - r
        if self.op == "*":
            return l * r
        if self.op == "/":
            if r == 0:
                raise ZeroDivisionError("Division by zero")
            return l / r
        raise ValueError(f"Unknown operator: {self.op}")

    def to_str(self, parent_prec=0) -> str:
        return f"{self.left.to_str()}{self.op}{self.right.to_str()}"


def _integer_nth_root(x: int, n: int) -> int:
    """floor(x ** (1/n))，二分法，避免浮点误差。"""
    if x < 0 or n <= 0:
        return 0
    if x < 2:
        return x
    low, high = 1, 1
    while high ** n <= x:
        high *= 2
    while low < high:
        mid = (low + high + 1) // 2
        if mid ** n <= x:
            low = mid
        else:
            high = mid - 1
    return low


def _extract_int_pair(frac: FractionNode) -> tuple:
    """从 FractionNode 提取 (p, q)，q > 0。失败返回 (None, None)。"""
    if not isinstance(frac.num, IntegerNode) or not isinstance(frac.den, IntegerNode):
        return None, None
    p, q = frac.num.value, frac.den.value
    if q <= 0:
        return None, None
    return p, q


def _extract_nth_power(radicand: int, n: int) -> tuple:
    """把 radicand 分解为 outside^n * inside，inside 不含 n 次方因子。"""
    if radicand <= 1:
        return radicand, 1
    outside, inside = 1, radicand
    i = 2
    while True:
        # if i^n <= inside, i <= inside^(1/n), this line is used to find the upper bound of i
        # recalculate i_max every loop, this dynamically shrinking upper limit lets the loop exit early
        i_max = _integer_nth_root(inside, n)
        if i > i_max:
            break
        p = i ** n
        # to find outside, we list all possible i, and see if i^n can divide the radicand
        while inside % p == 0:
            outside *= i
            inside //= p
        i += 1
    return outside, inside


def _int_pow(base: int, exp: int) -> Node | None:
    """整数 ^ 整数，含溢出保护。"""
    if exp == 0:
        if base == 0:
            raise ValueError("Math Error: 0^0 is not defined")
        return IntegerNode(1)
    if exp > 0:
        if exp > _MAX_INT_POWER:
            return None
        return IntegerNode(base ** exp)
    if base == 0:
        raise ZeroDivisionError("Math Error: division by zero")
    if -exp > _MAX_INT_POWER:
        return None
    return FractionNode(
        IntegerNode(1),
        IntegerNode(base ** (-exp)),
    ).simplify()


class PowerNode(Node):
    __slots__ = ("base", "exp")

    def __init__(self, base: Node, exp: Node):
        self.base = base
        self.exp = exp

    def simplify(self, env=None):
        env = env or {}
        b = self.base.simplify(env)
        e = self.exp.simplify(env)

        result = self._fold_trivial(b, e, env)
        if result is not None:
            return result

        result = self._fold_nested_power(b, e, env)
        if result is not None:
            return result

        result = self._fold_root_power(b, e, env)
        if result is not None:
            return result

        result = self._fold_negative_base(b, e, env)
        if result is not None:
            return result

        result = self._fold_fraction_base(b, e, env)
        if result is not None:
            return result

        result = self._fold_integer_base(b, e, env)
        if result is not None:
            return result

        if b is self.base and e is self.exp:
            return self
        return PowerNode(b, e)

    def _fold_trivial(self, b: Node, e: Node, env):
        # e == 0
        if isinstance(e, IntegerNode) and e.value == 0:
            if isinstance(b, IntegerNode) and b.value == 0:
                raise ValueError("Math Error: 0^0 is undefined")
            return IntegerNode(1)

        # e == 1
        if isinstance(e, IntegerNode) and e.value == 1:
            return b

        # b == 1
        if isinstance(b, IntegerNode) and b.value == 1:
            return IntegerNode(1)

        # b == -1
        if isinstance(b, IntegerNode) and b.value == -1:
            if isinstance(e, IntegerNode):
                return IntegerNode(1 if e.value % 2 == 0 else -1)

        # b == 0
        if isinstance(b, IntegerNode) and b.value == 0:
            if isinstance(e, IntegerNode):
                if e.value < 0:
                    raise ZeroDivisionError("Math Error: division by zero")
                return IntegerNode(0)
            if isinstance(e, DecimalNode):
                if e.value < 0:
                    raise ZeroDivisionError("Math Error: division by zero")
                return IntegerNode(0)
            if isinstance(e, FractionNode):
                if isinstance(e.num, IntegerNode) and e.num.value < 0:
                    raise ZeroDivisionError("Math Error: division by zero")
                return IntegerNode(0)

        return None

    def _fold_nested_power(self, b: Node, e: Node, env):
        """(a^m)^n = a^(m*n)，m、n 都是整数时成立。"""
        if not isinstance(b, PowerNode):
            return None
        m = b.exp
        if not isinstance(m, IntegerNode) or not isinstance(e, IntegerNode):
            return None
        new_exp = IntegerNode(m.value * e.value)
        return PowerNode(b.base, new_exp).simplify(env)

    def _fold_root_power(self, b: Node, e: Node, env):
        """(n√x)^m = x^(m/n)，m、n 都是整数时成立。"""
        if not isinstance(b, RootNode):
            return None
        d = b.degree
        if not isinstance(d, IntegerNode) or not isinstance(e, IntegerNode):
            return None
        # 显式构造后先简化 FractionNode，避免 e=4, d=2 时残留 4/2
        new_exp = FractionNode(e, d).simplify(env)
        return PowerNode(b.radicand, new_exp).simplify(env)

    def _fold_negative_base(self, b: Node, e: Node, env):
        """(-a)^e = (-1)^e · a^e"""
        if not isinstance(b, NegativeNode):
            return None
        pos_base = b.child

        if isinstance(e, IntegerNode):
            inner = PowerNode(pos_base, e).simplify(env)
            if inner is None:
                return None
            return inner if e.value % 2 == 0 else NegativeNode(inner)

        if isinstance(e, FractionNode):
            p, q = _extract_int_pair(e)
            if p is None:
                return None
            if q % 2 == 0:
                if env.get("complex_mode"):
                    return None
                raise ValueError("Math Error: even root of negative number")
            inner = PowerNode(pos_base, e).simplify(env)
            if inner is None:
                return None
            return inner if p % 2 == 0 else NegativeNode(inner)

        return None

    def _fold_fraction_base(self, b: Node, e: Node, env):
        """(a/b)^e"""
        if not isinstance(b, FractionNode):
            return None
        if not isinstance(b.num, IntegerNode) or not isinstance(b.den, IntegerNode):
            return None
        if b.den.value == 0:
            raise ZeroDivisionError("Math Error: division by zero")

        # 整数指数
        if isinstance(e, IntegerNode):
            n = e.value
            if n >= 0:
                if n > _MAX_INT_POWER:
                    return None
                return FractionNode(
                    IntegerNode(b.num.value ** n),
                    IntegerNode(b.den.value ** n),
                ).simplify(env)
            n = -n
            if n > _MAX_INT_POWER:
                return None
            if b.num.value == 0:
                raise ZeroDivisionError("Math Error: division by zero")
            return FractionNode(
                IntegerNode(b.den.value ** n),
                IntegerNode(b.num.value ** n),
            ).simplify(env)

        # 分数指数 p/q
        if isinstance(e, FractionNode):
            p, q = _extract_int_pair(e)
            if p is None:
                return None
            if b.num.value < 0:
                return None
            if abs(p) > _MAX_INT_POWER:
                return None

            # 完全 q 次方判定（分子分母都要）
            if (b.num.value <= _MAX_BASE_FOR_ROOT
                    and b.den.value <= _MAX_BASE_FOR_ROOT):
                num_r = _integer_nth_root(b.num.value, q)
                den_r = _integer_nth_root(b.den.value, q)
                if num_r ** q == b.num.value and den_r ** q == b.den.value:
                    if p >= 0:
                        return FractionNode(
                            IntegerNode(num_r ** p),
                            IntegerNode(den_r ** p),
                        ).simplify(env)
                    n = -p
                    return FractionNode(
                        IntegerNode(den_r ** n),
                        IntegerNode(num_r ** n),
                    ).simplify(env)

            # 非完全 q 次方：转为 RootNode 形式
            return self._transform_to_root(b, p, q, env)

        return None

    def _fold_integer_base(self, b: Node, e: Node, env):
        """a^e，a 是正整数"""
        if not isinstance(b, IntegerNode):
            return None
        if b.value < 0:
            return None

        # 整数指数
        if isinstance(e, IntegerNode):
            return _int_pow(b.value, e.value)

        # 分数指数 p/q
        if isinstance(e, FractionNode):
            p, q = _extract_int_pair(e)
            if p is None:
                return None
            if b.value == 0:
                return None
            if abs(p) > _MAX_INT_POWER:
                return None

            # 完全 q 次方 → 直接算
            if b.value <= _MAX_BASE_FOR_ROOT:
                r = _integer_nth_root(b.value, q)
                if r ** q == b.value:
                    return _int_pow(r, p)

            # 非完全 q 次方 → 转为 RootNode 形式
            return self._transform_to_root(b, p, q, env)

        return None

    def _transform_to_root(self, b: Node, p: int, q: int, env):
        """
        a^(p/q) → q√(a^p)，p < 0 时返回 1 / q√(a^|p|)
        用于整数底和分数底的非完全 q 次方情形。
        """
        if q <= 1:
            return None

        # 先算 b^p
        powered = PowerNode(b, IntegerNode(abs(p))).simplify(env)
        if powered is None:
            return None

        # 检查是否能开 q 次方
        ratio = _node_to_ratio(powered)
        if ratio is None:
            return None
        num, den = ratio

        # 分子分母都要有 q 次方因子
        out_num, in_num = _extract_nth_power(abs(num), q)
        out_den, in_den = _extract_nth_power(den, q)

        if in_num == abs(num) and in_den == den:
            # 提取不出任何因子，转换无意义
            return None

        # 有因子可提取，走根号化简
        if p > 0:
            inner = PowerNode(b, IntegerNode(p)).simplify(env)
            if inner is None:
                return None
            return RootNode(IntegerNode(q), inner).simplify(env)
        elif p < 0:
            inner = PowerNode(b, IntegerNode(-p)).simplify(env)
            if inner is None:
                return None
            radical = RootNode(IntegerNode(q), inner).simplify(env)
            return FractionNode(IntegerNode(1), radical).simplify(env)
        # p == 0 已在平凡规则处理
        return None

    def evaluate(self, env=None):
        env = env or {}
        base = self.base.evaluate(env)
        exp = self.exp.evaluate(env)

        if base == 0 and exp == 0:
            raise ValueError("Math Error: 0^0 is undefined")

        # 复数参与
        if isinstance(base, complex) or isinstance(exp, complex):
            return base ** exp

        # 负数底、非整数指
        if isinstance(base, (int, float)) and base < 0:
            if isinstance(exp, (int, float)) and exp == int(exp):
                pass   # 整数指数，合法
            else:
                if env.get("complex_mode"):
                    return complex(base) ** exp
                raise ValueError("Math Error: negative number to non-integer power")

        return pow(base, exp)

    def to_str(self, parent_prec: int = 0) -> str:
        base_str = self.base.to_str(4)
        exp_str = self.exp.to_str()
        return f"{base_str}^({exp_str})"


class RootNode(Node):
    __slots__ = ("degree", "radicand")

    _MAX_RADICAND_FOR_FACTORING = 10 ** 10

    def __init__(self, degree: Node, radicand: Node):
        self.degree = degree
        self.radicand = radicand

    def simplify(self, env=None):
        env = env or {}
        d = self.degree.simplify(env)
        e = self.radicand.simplify(env)

        if not isinstance(d, IntegerNode) or d.value < 1:
            return self._rebuild(d, e)

        n = d.value

        result = self._fold_trivial(n, e)
        if result is not None:
            return result

        result = self._fold_nested_root(n, e, env)
        if result is not None:
            return result

        result = self._fold_power_radicand(n, e, env)
        if result is not None:
            return result

        result = self._fold_negative_radicand(n, e, env)
        if result is not None:
            return result

        result = self._fold_fraction_radicand(n, e, env)
        if result is not None:
            return result

        result = self._fold_integer_radicand(n, e, env)
        if result is not None:
            return result

        return self._rebuild(d, e)

    def _fold_trivial(self, n, e: Node):
        if n == 1:
            return e
        if isinstance(e, IntegerNode):
            if e.value == 0:
                return IntegerNode(0)
            if e.value == 1:
                return IntegerNode(1)
        return None

    def _fold_nested_root(self, n, e: Node, env):
        """n√(m√x) = (n·m)√x"""
        if not isinstance(e, RootNode):
            return None
        inner_d = e.degree
        if not isinstance(inner_d, IntegerNode) or inner_d.value < 1:
            return None
        new_d = IntegerNode(n * inner_d.value)
        return RootNode(new_d, e.radicand).simplify(env)

    def _fold_power_radicand(self, n, e: Node, env):
        """n√(x^m) = x^(m//n) · n√(x^(m%n))"""
        if not isinstance(e, PowerNode):
            return None
        exp = e.exp
        if not isinstance(exp, IntegerNode):
            return None

        m = exp.value
        quotient, remainder = divmod(m, n)

        if remainder == 0:
            return PowerNode(e.base, IntegerNode(quotient)).simplify(env)

        if quotient == 0:
            return None   # 无法提取

        outer = PowerNode(e.base, IntegerNode(quotient)).simplify(env)
        inner = RootNode(
            IntegerNode(n),
            PowerNode(e.base, IntegerNode(remainder)).simplify(env),
        ).simplify(env)
        return BinaryOpNode(outer, inner, "*").simplify(env)

    def _fold_negative_radicand(self, n, e: Node, env):
        """n√(-x) = -n√x（n 奇）；n 偶时实数模式报错"""
        if not isinstance(e, NegativeNode):
            return None
        if n % 2 == 0:
            if env.get("complex_mode"):
                return None
            raise ValueError("Math Error: even root of negative number")
        inner = RootNode(IntegerNode(n), e.child).simplify(env)
        return NegativeNode(inner).simplify(env)

    def _fold_fraction_radicand(self, n, e: Node, env):
        """n√(a/b) = n√(a·b) / b"""
        if not isinstance(e, FractionNode):
            return None
        if not isinstance(e.num, IntegerNode) or not isinstance(e.den, IntegerNode):
            return None

        a, b = e.num.value, e.den.value
        if b == 0:
            raise ZeroDivisionError("Math Error: division by zero")
        if b < 0:
            a, b = -a, -b

        negative = a < 0
        a = abs(a)

        combined = a * b
        if combined > self._MAX_RADICAND_FOR_FACTORING:
            return None

        outside, inside = _extract_nth_power(combined, n)

        if inside == 1:
            numerator: Node = IntegerNode(outside)
        elif outside == 1:
            numerator = RootNode(IntegerNode(n), IntegerNode(inside))
        else:
            numerator = BinaryOpNode(
                IntegerNode(outside),
                RootNode(IntegerNode(n), IntegerNode(inside)),
                "*",
            )

        result: Node = FractionNode(numerator, IntegerNode(b))

        if negative:
            if n % 2 == 0:
                if env.get("complex_mode"):
                    return None
                raise ValueError("Math Error: even root of negative number")
            result = NegativeNode(result)

        return result.simplify(env)

    def _fold_integer_radicand(self, n, e: Node, env):
        if not isinstance(e, IntegerNode):
            return None
        value = e.value

        if value < 0:
            return None
        if value == 0:
            return IntegerNode(0)
        if value == 1:
            return IntegerNode(1)

        if value > self._MAX_RADICAND_FOR_FACTORING:
            r = _integer_nth_root(value, n)
            if r ** n == value:
                return IntegerNode(r)
            return None

        outside, inside = _extract_nth_power(value, n)

        if inside == 1:
            return IntegerNode(outside)
        if outside == 1:
            return RootNode(IntegerNode(n), IntegerNode(inside))
        return BinaryOpNode(
            IntegerNode(outside),
            RootNode(IntegerNode(n), IntegerNode(inside)),
            "*",
        )

    def _rebuild(self, d: Node, e: Node) -> Node:
        if d is self.degree and e is self.radicand:
            return self
        return RootNode(d, e)

    def evaluate(self, env=None):
        env = env or {}
        degree = self.degree.evaluate(env)
        value = self.radicand.evaluate(env)

        if degree == 0:
            raise ValueError("Math Error: 0th root is undefined")
        if value == 0:
            return 0
        if value < 0:
            if degree % 2 == 0:
                if env.get("complex_mode"):
                    return complex(value) ** (1 / degree)
                raise ValueError("Math Error: even root of negative number is not real")
            return -pow(abs(value), 1 / degree)
        return pow(value, 1 / degree)

    def to_str(self, parent_prec: int = 0) -> str:
        return f"deg({self.degree.to_str()})root({self.radicand.to_str()})"


def _integer_power(a: int, b: int) -> int | None:
    """若 a == b^n（n 为非负整数），返回 n；否则 None。要求 a >= 1, b >= 2。"""
    if a < 1 or b < 2:
        return None
    if a == 1:
        return 0

    try:
        est = math.log(a) / math.log(b)
    except (ValueError, ZeroDivisionError):
        return None

    n = round(est)
    if n < 0 or n > _MAX_LOG_EXP:
        return None

    for dn in (-1, 0, 1):
        cand = n + dn
        if 0 <= cand <= _MAX_LOG_EXP and b ** cand == a:
            return cand
    return None


def _rational_power_match(a: tuple, b: tuple) -> int | None:
    a_num, a_den = a
    b_num, b_den = b

    if a_num <= 0 or a_den <= 0 or b_num <= 0 or b_den <= 0:
        return None

    # 退化：b = 1
    if b_num == 1 and b_den == 1:
        return 0 if (a_num == 1 and a_den == 1) else None

    # b 是整数：a 的分母必须是 1
    if b_den == 1:
        if a_den != 1:
            return None
        return _integer_power(a_num, b_num)

    # b 是分数：分子分母分别匹配，指数必须一致
    n1 = _integer_power(a_num, b_num)
    n2 = _integer_power(a_den, b_den)
    if n1 is None or n2 is None:
        return None
    return n1 if n1 == n2 else None


def _decimal_to_ratio(value: float) -> tuple | None:
    """
    把浮点数转成精确有理数元组 (num, den)，用字符串解析，不依赖 decimal 模块。
    例：1.1 → (11, 10)；0.25 → (1, 4)；1e-3 → (1, 1000)。
    """
    if not math.isfinite(value):
        return None

    s = str(value)

    # 科学计数法："1e+20" / "1.5e-3"
    if 'e' in s or 'E' in s:
        mant, _, exp_str = s.replace('E', 'e').partition('e')
        exp = int(exp_str)
        if '.' in mant:
            int_p, frac_p = mant.split('.')
            digits = int_p + frac_p
            num = int(digits) if digits else 0
            den = 10 ** len(frac_p) if frac_p else 1
        else:
            num = int(mant)
            den = 1
        if exp >= 0:
            num *= 10 ** exp
        else:
            den *= 10 ** (-exp)
    # 普通小数："1.21" / "-0.5"
    elif '.' in s:
        int_p, frac_p = s.split('.')
        negative = int_p.startswith('-')
        if negative:
            int_p = int_p[1:]
        int_val = int(int_p) if int_p else 0
        frac_val = int(frac_p) if frac_p else 0
        den = 10 ** len(frac_p) if frac_p else 1
        num = int_val * den + frac_val
        if negative:
            num = -num
    # 整数
    else:
        return int(s), 1

    g = math.gcd(abs(num), den) or 1
    return num // g, den // g


def _node_to_ratio(node: Node) -> tuple | None:
    """把数值类 Node 转成 (num, den)；其他类型返回 None。"""
    if isinstance(node, IntegerNode):
        return (node.value, 1)
    if isinstance(node, FractionNode):
        if isinstance(node.num, IntegerNode) and isinstance(node.den, IntegerNode):
            return (node.num.value, node.den.value)
        return None
    if isinstance(node, DecimalNode):
        return _decimal_to_ratio(node.value)
    return None


def _structurally_equal(a: Node, b: Node) -> bool:
    """判断两个 Node 结构是否完全一致。"""
    if type(a) is not type(b):
        return False
    if isinstance(a, (IntegerNode, DecimalNode)):
        return a.value == b.value
    if isinstance(a, VariableNode):
        return a.name == b.name
    if isinstance(a, (EulerNode, PiNode)):
        return True
    if isinstance(a, NegativeNode):
        return _structurally_equal(a.child, b.child)
    if isinstance(a, BinaryOpNode):
        return (a.op == b.op
                and _structurally_equal(a.left, b.left)
                and _structurally_equal(a.right, b.right))
    if isinstance(a, PowerNode):
        return (_structurally_equal(a.base, b.base)
                and _structurally_equal(a.exp, b.exp))
    if isinstance(a, RootNode):
        return (_structurally_equal(a.degree, b.degree)
                and _structurally_equal(a.radicand, b.radicand))
    if isinstance(a, FractionNode):
        return (_structurally_equal(a.num, b.num)
                and _structurally_equal(a.den, b.den))
    return False


class LogNode(Node):
    __slots__ = ("base", "argument")

    def __init__(self, argument: Node, base: Node = None):
        # base=None 表示自然对数 ln
        self.base = base if base is not None else EulerNode()
        self.argument = argument

    def simplify(self, env=None):
        env = env or {}
        b = self.base.simplify(env)

        # 提前识别 log_b(b^k)，趁 argument 还是 PowerNode
        raw = self.argument
        if isinstance(raw, PowerNode):
            raw_base = raw.base.simplify(env)
            if _structurally_equal(raw_base, b):
                return raw.exp

        a = self.argument.simplify(env)

        result = self._fold_trivial(b, a)
        if result is not None:
            return result
        result = self._fold_power_argument(b, a, env)
        if result is not None:
            return result
        result = self._fold_numeric(b, a)
        if result is not None:
            return result

        if b is self.base and a is self.argument:
            return self
        return LogNode(a, b)

    def _fold_trivial(self, b: Node, a: Node):
        if isinstance(a, IntegerNode) and a.value == 1:
            return IntegerNode(0)
        if _structurally_equal(a, b):
            return IntegerNode(1)
        return None

    def _fold_power_argument(self, b: Node, a: Node, env):
        """log_b(x^k)：若 x == b 返回 k；若 x == b^n 返回 k·n。"""
        if not isinstance(a, PowerNode):
            return None
        if not isinstance(a.exp, IntegerNode):
            return None

        k = a.exp.value
        x = a.base

        if _structurally_equal(x, b):
            return IntegerNode(k)

        n = self._match_power(x, b)
        if n is not None:
            return IntegerNode(k * n)
        return None

    def _fold_numeric(self, b: Node, a: Node):
        if isinstance(b, EulerNode):
            return None

        b_ratio = _node_to_ratio(b)
        a_ratio = _node_to_ratio(a)
        if b_ratio is None or a_ratio is None:
            return None

        n = _rational_power_match(a_ratio, b_ratio)
        if n is not None:
            return IntegerNode(n)
        return None

    def _match_power(self, x, b) -> int | None:
        x_ratio = _node_to_ratio(x)
        b_ratio = _node_to_ratio(b)
        if x_ratio is None or b_ratio is None:
            return None
        return _rational_power_match(x_ratio, b_ratio)

    def evaluate(self, env=None):
        env = env or {}
        arg = self.argument.evaluate(env)
        if arg <= 0:
            raise ValueError("Math Error: Antilogarithm should be positive")

        if isinstance(self.base, EulerNode):
            return math.log(arg)

        base = self.base.evaluate(env)
        if base <= 0:
            raise ValueError("Math Error: Base should be positive")
        if base == 1:
            raise ValueError("Math Error: Base should not be 1")
        return math.log(arg, base)

    def to_str(self, parent_prec: int = 0) -> str:
        if isinstance(self.base, EulerNode):
            return f"ln({self.argument.to_str()})"
        return f"base({self.base.to_str()})log({self.argument.to_str()})"


def _reduce_angle_to_first_quadrant(rational_c: tuple[int, int]) -> tuple[int, int, tuple[int, int, int]]:
    """
    返回 (p, q, sign)：
      - (p/q)·π 是第一象限内的角
      - sign = (sin_sign, cos_sign, tan_sign) 的元组
    """
    p, q = rational_c

    g = math.gcd(p, q)
    p, q = p // g, q // g

    if q < 0:
        p, q = -p, -q

    # 归一化到 [0, 2)：用模运算，负数自动变正
    p = p % (2 * q)

    if p == 0:
        return 0, 1, (+1, +1, +1)

    # 判断落在 哪个象限
    if 2 * p <= q:
        # [0, π/2]
        return p, q, (+1, +1, +1)
    elif p <= q:
        # (π/2, π]
        return q - p, q, (+1, -1, -1)
    elif 2 * p <= 3 * q:
        # (π, 3π/2]
        return p - q, q, (-1, -1, +1)
    else:
        # (3π/2, 2π)
        return 2 * q - p, q, (-1, +1, -1)


def _rationalize(node: Node) -> tuple[int, int] | None:
    """把 Node 归一为 (n, d)，仅支持 IntegerNode 和 FractionNode(int,int)。"""
    if isinstance(node, IntegerNode):
        return node.value, 1
    if isinstance(node, FractionNode):
        if isinstance(node.num, IntegerNode) and isinstance(node.den, IntegerNode):
            return node.num.value, node.den.value
    return None


class TrigNode(Node):
    __slots__ = ("name", "argument")
    _SPECIAL_ANGLES = {
        (0, 1):
            {
                'sin': IntegerNode(0),
                'cos': IntegerNode(1),
                'tan': IntegerNode(0)
            },
        (1, 12):
            {
                'sin': FractionNode(
                    BinaryOpNode(RootNode(IntegerNode(2), IntegerNode(6)), RootNode(IntegerNode(2), IntegerNode(2)),
                                 "-"), IntegerNode(4)),
                'cos': FractionNode(
                    BinaryOpNode(RootNode(IntegerNode(2), IntegerNode(6)), RootNode(IntegerNode(2), IntegerNode(2)),
                                 "+"), IntegerNode(4)),
                'tan': BinaryOpNode(IntegerNode(2), RootNode(IntegerNode(2), IntegerNode(3)), "-")
            },
        (1, 6):
            {
                'sin': FractionNode(IntegerNode(1), IntegerNode(2)),
                'cos': FractionNode(RootNode(IntegerNode(2), IntegerNode(3)), IntegerNode(2)),
                'tan': FractionNode(RootNode(IntegerNode(2), IntegerNode(3)), IntegerNode(3))
            },
        (1, 4):
            {
                'sin': FractionNode(RootNode(IntegerNode(2), IntegerNode(2)), IntegerNode(2)),
                'cos': FractionNode(RootNode(IntegerNode(2), IntegerNode(2)), IntegerNode(2)),
                'tan': IntegerNode(1)
            },
        (1, 3):
            {
                'sin': FractionNode(RootNode(IntegerNode(2), IntegerNode(3)), IntegerNode(2)),
                'cos': FractionNode(IntegerNode(1), IntegerNode(2)),
                'tan': RootNode(IntegerNode(2), IntegerNode(3))
            },
        (5, 12):
            {
                'sin': FractionNode(
                    BinaryOpNode(RootNode(IntegerNode(2), IntegerNode(6)), RootNode(IntegerNode(2), IntegerNode(2)),
                                 "+"), IntegerNode(4)),
                'cos': FractionNode(
                    BinaryOpNode(RootNode(IntegerNode(2), IntegerNode(6)), RootNode(IntegerNode(2), IntegerNode(2)),
                                 "-"), IntegerNode(4)),
                'tan': BinaryOpNode(IntegerNode(2), RootNode(IntegerNode(2), IntegerNode(3)), "+")
            },
        (1, 2):
            {
                'sin': IntegerNode(1),
                'cos': IntegerNode(0),
                "tan": None
            }
    }

    def __init__(self, name: str, argument: Node):
        self.name = name
        self.argument = argument

    def simplify(self, env: dict = None):
        env = env or {}

        arg = self.argument.simplify(env)
        angle_unit = env.get("angle_unit", "RAD")

        if angle_unit == "DEG":
            arg = BinaryOpNode(arg / IntegerNode(180), PiNode(), "*").simplify(env)
        elif angle_unit == "GRA":
            arg = BinaryOpNode(arg / IntegerNode(200), PiNode(), "*").simplify(env)

        rational_c = self._extract_pi_coefficient(arg)
        if rational_c is not None:
            p, q, signs = _reduce_angle_to_first_quadrant(rational_c)

            value_nodes = self._SPECIAL_ANGLES.get((p, q), None)

            # 表中存在相应的特殊角
            if value_nodes is not None:

                # 处理数学上未定义的输入
                if value_nodes[self.name] is None:
                    raise ValueError(f"MathError: {self.name}({p}/{q} * π) is not defined")

                if self.name == "sin":
                    i = 0
                elif self.name == "cos":
                    i = 1
                else:
                    i = 2
                sign = signs[i]
                if sign == -1:
                    return NegativeNode(value_nodes[self.name]).simplify(env)
                return value_nodes[self.name]

        # if self.name == "sin":
        #     return DecimalNode(math.sin(arg.evaluate(env)))
        # elif self.name == "cos":
        #     return DecimalNode(math.cos(arg.evaluate(env)))
        # else:
        #     return DecimalNode(math.tan(arg.evaluate(env)))

        return TrigNode(self.name, arg)

    def evaluate(self, env: dict = None) -> float:
        env = env or {}
        arg = self.argument.evaluate(env)

        angle_unit = env.get("angle_unit", "RAD")
        if angle_unit == "DEG":
            arg = math.radians(arg)
        elif angle_unit == "GRA":
            arg = math.radians(0.9 * arg)

        if self.name == "sin":
            return math.sin(arg)
        elif self.name == "cos":
            return math.cos(arg)
        elif self.name == "tan":
            return math.tan(arg)

        raise ValueError(f"Unknown triangle function: {self.name}")

    def _extract_pi_coefficient(self, node: Node) -> tuple[int, int] | None:
        # attempt to return (num, den) from num/den * pi

        # 0 → (0, 1)
        if isinstance(node, IntegerNode) and node.value == 0:
            return 0, 1

        # π → (1, 1)
        if isinstance(node, PiNode):
            return 1, 1

        # n·π 或 π·n
        if isinstance(node, BinaryOpNode) and node.op == "*":
            if isinstance(node.right, PiNode):
                c = _rationalize(node.left)
                if c is not None:
                    return c
            if isinstance(node.left, PiNode):
                c = _rationalize(node.right)
                if c is not None:
                    return c

        # π/n 或 (n·π)/m：分子递归提取，分母必须是 IntegerNode
        if isinstance(node, FractionNode):
            num_coef = self._extract_pi_coefficient(node.num)
            if num_coef is not None and isinstance(node.den, IntegerNode):
                return num_coef[0], num_coef[1] * node.den.value

        return None

    def to_str(self, parent_prec=0) -> str:
        return f"{self.name}({self.argument.to_str()})"


def _extract_square_factor(n: int) -> tuple:
    """n = outside² · inside，inside 无平方因子。返回 (outside, inside)。"""
    if n <= 0:
        return 1, 1
    outside, inside = 1, n
    i = 2
    while i * i <= inside:
        while inside % (i * i) == 0:
            outside *= i
            inside //= i * i
        i += 1
    return outside, inside


class ArcTrigNode(Node):
    __slots__ = ("name", "argument")

    # 键: ("combo", frozenset({(p, q, n), ...}))
    #     表示值 = Σ (p/q)·√n
    # 值: {name: (p, q)}  表示输出 (p/q)·π
    #     None 表示该函数在此值下无特殊角
    _SPECIAL_VALUES = {
        ("combo", frozenset({(0, 1, 1)})):
            {
            "arcsin": (0, 1), "arccos": (1, 2), "arctan": (0, 1),
            },
        ("combo", frozenset({(1, 1, 1)})):
            {
            "arcsin": (1, 2), "arccos": (0, 1), "arctan": (1, 4),
            },
        ("combo", frozenset({(1, 2, 1)})):
            {
            "arcsin": (1, 6), "arccos": (1, 3), "arctan": None,
            },
        ("combo", frozenset({(1, 2, 2)})):
            {
            "arcsin": (1, 4), "arccos": (1, 4), "arctan": None,
            },
        ("combo", frozenset({(1, 2, 3)})):
            {
            "arcsin": (1, 3), "arccos": (1, 6), "arctan": None,
            },
        ("combo", frozenset({(1, 3, 3)})):
            {
            "arcsin": None, "arccos": None, "arctan": (1, 6),
            },
        ("combo", frozenset({(1, 1, 3)})):
            {
            "arcsin": None, "arccos": None, "arctan": (1, 3),
            },
        ("combo", frozenset({(1, 4, 6), (-1, 4, 2)})):
            {
            "arcsin": (1, 12), "arccos": (5, 12), "arctan": None,
            },
        ("combo", frozenset({(1, 4, 6), (1, 4, 2)})):
            {
            "arcsin": (5, 12), "arccos": (1, 12), "arctan": None,
            },
        ("combo", frozenset({(2, 1, 1), (-1, 1, 3)})):
            {
            "arcsin": None, "arccos": None, "arctan": (1, 12),
            },
        ("combo", frozenset({(2, 1, 1), (1, 1, 3)})):
            {
            "arcsin": None, "arccos": None, "arctan": (5, 12),
            },
    }

    def __init__(self, name: str, argument: Node):
        self.name = name
        self.argument = argument

    def simplify(self, env=None):
        env = env or {}
        arg = self.argument.simplify(env)

        # 1. 剥离负号
        negated = False
        if isinstance(arg, NegativeNode):
            arg = arg.child
            negated = True

        # 2. 提取值签名
        sig = self._value_signature(arg)
        if sig is None:
            return self._rebuild(arg, negated)

        # 3. 查表
        entry = self._SPECIAL_VALUES.get(sig)
        if entry is None or entry.get(self.name) is None:
            return self._rebuild(arg, negated)

        p, q = entry[self.name]

        # 4. 负输入变换
        if negated:
            if self.name == "arccos":
                # arccos(-v) = π - arccos(v)
                p, q = q - p, q
            else:
                # arcsin / arctan 是奇函数
                p = -p

        # 5. 按 angle_unit 输出
        au = env.get("angle_unit", "RAD")
        if au == "RAD":
            return self._make_pi_node(p, q)
        if au == "DEG":
            return FractionNode(IntegerNode(p * 180), IntegerNode(q)).simplify(env)
        if au == "GRA":
            return FractionNode(IntegerNode(p * 200), IntegerNode(q)).simplify(env)

        return self._rebuild(arg, negated)

    def _value_signature(self, node: Node) -> tuple | None:
        """
        返回 ("combo", frozenset({(p, q, n), ...}))
        表示值 = Σ (p/q) · √n。无法规范化时返回 None。
        """
        terms = self._expand_to_terms(node)
        if terms is None:
            return None

        merged = self._merge_terms(terms)
        if not merged:
            merged = [(0, 1, 1)]      # 零的规范签名

        return ("combo", frozenset(merged))

    def _expand_to_terms(self, node: Node) -> list | None:
        """把 Node 展开为项列表 [(p, q, n), ...]。"""
        # 整数
        if isinstance(node, IntegerNode):
            return [(node.value, 1, 1)]

        # 分数：分母是有理数
        if isinstance(node, FractionNode):
            if not isinstance(node.den, IntegerNode):
                return None
            d = node.den.value
            if d == 0:
                return None
            num_terms = self._expand_to_terms(node.num)
            if num_terms is None:
                return None
            return [(p, q * d, n) for p, q, n in num_terms]

        # 平方根 √n
        if isinstance(node, RootNode):
            if not (isinstance(node.degree, IntegerNode) and node.degree.value == 2):
                return None
            if not isinstance(node.radicand, IntegerNode):
                return None
            n = node.radicand.value
            if n < 0:
                return None
            outside, inside = _extract_square_factor(n)
            return [(outside, 1, inside)]

        # 负号
        if isinstance(node, NegativeNode):
            inner = self._expand_to_terms(node.child)
            if inner is None:
                return None
            return [(-p, q, n) for p, q, n in inner]

        # 二元运算
        if isinstance(node, BinaryOpNode):
            if node.op in ('+', '-'):
                l = self._expand_to_terms(node.left)
                r = self._expand_to_terms(node.right)
                if l is None or r is None:
                    return None
                if node.op == '-':
                    r = [(-p, q, n) for p, q, n in r]
                return l + r

            if node.op == '*':
                l = self._expand_to_terms(node.left)
                r = self._expand_to_terms(node.right)
                if l is None or r is None:
                    return None
                result = []
                for ap, aq, an in l:
                    for bp, bq, bn in r:
                        outside, inside = _extract_square_factor(an * bn)
                        result.append((ap * bp * outside, aq * bq, inside))
                return result

        return None

    def _merge_terms(self, terms: list) -> list:
        """合并同类项（相同根号 n），约分，丢弃零项。"""
        acc: dict[int, tuple[int, int]] = {}   # n -> (p, q)

        for p, q, n in terms:
            if n not in acc:
                acc[n] = (0, 1)
            ap, aq = acc[n]
            new_p = ap * q + p * aq
            new_q = aq * q
            g = math.gcd(abs(new_p), abs(new_q)) or 1
            acc[n] = (new_p // g, new_q // g)

        result = []
        for n, (p, q) in acc.items():
            if p == 0:
                continue
            if q < 0:
                p, q = -p, -q
            result.append((p, q, n))
        return result

    def _make_pi_node(self, p: int, q: int) -> Node:
        """构造 (p/q)·π 的节点。"""
        if p == 0:
            return IntegerNode(0)
        g = math.gcd(abs(p), q) or 1
        p, q = p // g, q // g
        if q < 0:
            p, q = -p, -q

        numerator = PiNode() if abs(p) == 1 else BinaryOpNode(IntegerNode(abs(p)), PiNode(), "*")
        result: Node = numerator if q == 1 else FractionNode(numerator, IntegerNode(q))
        return NegativeNode(result) if p < 0 else result

    def _rebuild(self, arg: Node, negated: bool) -> Node:
        """未命中表时构造返回值。"""
        if negated:
            arg = NegativeNode(arg)
        if arg is self.argument:
            return self
        return ArcTrigNode(self.name, arg)

    def evaluate(self, env=None) -> float:
        env = env or {}
        arg = self.argument.evaluate(env)
        au = env.get("angle_unit", "RAD")

        if self.name == "arcsin":
            if arg < -1 or arg > 1:
                raise ValueError("Math Error: arcsin domain is [-1, 1]")
            rad = math.asin(arg)
        elif self.name == "arccos":
            if arg < -1 or arg > 1:
                raise ValueError("Math Error: arccos domain is [-1, 1]")
            rad = math.acos(arg)
        elif self.name == "arctan":
            rad = math.atan(arg)
        else:
            raise ValueError(f"Unknown inverse trig function: {self.name}")

        if au == "DEG":
            return math.degrees(rad)
        if au == "GRA":
            return rad / math.pi * 200
        return rad

    def to_str(self, parent_prec: int = 0) -> str:
        return f"{self.name}({self.argument.to_str()})"


class CombinatoricNode(Node):
    __slots__ = ("n", "r", "comb")

    def __init__(self, n: Node, r: Node, comb: bool = True):
        self.n = n
        self.r = r
        self.comb = comb

    def simplify(self, env: dict | None = None) -> Node:
        n = self.n.simplify(env)
        r = self.r.simplify(env)

        if not isinstance(n, IntegerNode) or not isinstance(r, IntegerNode):
            raise ValueError("Math Error: The attribute must be a integer")
        if n.value < 0 or r.value < 0:
            raise ValueError("Math Error: arguments must be non-negative")
        if n.value < r.value:
            raise ValueError("Math Error: r should not be larger than n in nCr")

        return IntegerNode(math.comb(n.value, r.value)) if self.comb else IntegerNode(math.perm(n.value, r.value))

    def evaluate(self, env: dict | None = None):
        return self.simplify(env).evaluate(env)

    def to_str(self, parent_prec: int = 0) -> str:
        return f"{self.n.to_str()} comb {self.r.to_str()}" if self.comb else f"{self.n.to_str()} perm {self.r.to_str()}"


# =================================================================

@register("+", IntegerNode, IntegerNode, commutative=True)
def _(a: IntegerNode, b: IntegerNode): return IntegerNode(a.value + b.value)


@register("+", IntegerNode, DecimalNode, commutative=True)
def _(a: IntegerNode, b: DecimalNode): return DecimalNode(a.value + b.value)


@register("+", DecimalNode, DecimalNode, commutative=True)
def _(a: DecimalNode, b: DecimalNode): return DecimalNode(a.value + b.value)


@register("+", IntegerNode, FractionNode, commutative=True)
def _(a: IntegerNode, b: FractionNode):
    return FractionNode(
        IntegerNode(a.value * b.den.value + b.num.value),
        b.den,
    ).simplify()


@register("+", DecimalNode, FractionNode, commutative=True)
def _(a: DecimalNode, b: FractionNode):
    return DecimalNode(a.value + b.evaluate())


@register("+", FractionNode, FractionNode, commutative=True)
def _(a: FractionNode, b: FractionNode):
    return FractionNode(
        IntegerNode(a.num.value * b.den.value + b.num.value * a.den.value),
        IntegerNode(a.den.value * b.den.value),
    ).simplify()


@register("+", ComplexNode, ComplexNode, commutative=True)
def _(a: ComplexNode, b: ComplexNode):
    return ComplexNode(a.real + b.real, a.imag + b.imag)


@register("+", ComplexNode, IntegerNode, commutative=True)
def _(a:ComplexNode, b: IntegerNode):
    return ComplexNode(a.real + b, a.imag)


@register("+", ComplexNode, DecimalNode, commutative=True)
def _(a: ComplexNode, b: DecimalNode):
    return ComplexNode(a.real + b, a.imag)


@register("+", LogNode, LogNode)
def _(a: LogNode, b: LogNode):
    base_a = a.base.simplify()
    base_b = b.base.simplify()
    if _structurally_equal(base_a, base_b):
        return LogNode(a.argument * b.argument, base_a)
    return None


# ---------- Subtraction ----------
@register("-", IntegerNode, IntegerNode)
def _(a: IntegerNode, b: IntegerNode): return IntegerNode(a.value - b.value)


@register("-", IntegerNode, DecimalNode)
def _(a: IntegerNode, b: DecimalNode): return DecimalNode(a.value - b.value)


@register("-", DecimalNode, IntegerNode)
def _(a: DecimalNode, b: IntegerNode): return DecimalNode(a.value - b.value)


@register("-", DecimalNode, DecimalNode)
def _(a: DecimalNode, b: DecimalNode): return DecimalNode(a.value - b.value)


@register("-", ComplexNode, ComplexNode)
def _(a: ComplexNode, b: ComplexNode):
    return ComplexNode(a.real - b.real, a.imag - b.imag)


@register("-", ComplexNode, IntegerNode)
def _(a: ComplexNode, b: IntegerNode):
    return ComplexNode(a.real - b, a.imag)


@register("-", LogNode, LogNode)
def _(a: LogNode, b: LogNode):
    base_a = a.base.simplify()
    base_b = b.base.simplify()
    if _structurally_equal(base_a, base_b):
        return LogNode((a.argument / b.argument), base_a)
    return None


# ---------- Multiplication ----------
@register("*", IntegerNode, IntegerNode, commutative=True)
def _(a: IntegerNode, b: IntegerNode): return IntegerNode(a.value * b.value)


@register("*", IntegerNode, DecimalNode, commutative=True)
def _(a: IntegerNode, b: DecimalNode): return DecimalNode(a.value * b.value)


@register("*", DecimalNode, DecimalNode, commutative=True)
def _(a: DecimalNode, b: DecimalNode): return DecimalNode(a.value * b.value)


@register("*", IntegerNode, FractionNode, commutative=True)
def _(a: IntegerNode, b: FractionNode):
    return FractionNode(
        IntegerNode(a.value * b.num.value),
        b.den,
    ).simplify()


@register("*", FractionNode, FractionNode, commutative=True)
def _(a: FractionNode, b: FractionNode):
    return FractionNode(
        IntegerNode(a.num.value * b.num.value),
        IntegerNode(a.den.value * b.den.value),
    ).simplify()


@register("*", ComplexNode, IntegerNode, commutative=True)
def _(a: ComplexNode, b: IntegerNode):
    return ComplexNode(a.real * b, a.imag * b)


@register("*", RootNode, RootNode, commutative=True)
def _(a: RootNode, b: RootNode):
    if not isinstance(a.degree, IntegerNode) or not isinstance(b.degree, IntegerNode):
        return None
    if a.degree.value != b.degree.value:
        return None
    new_radicand = a.radicand * b.radicand
    return RootNode(a.degree, new_radicand)

@register("*", PowerNode, PowerNode, commutative=True)
def _(a: PowerNode, b: PowerNode):
    base_a = a.base.simplify()
    base_b = b.base.simplify()
    if _structurally_equal(base_a, base_b):
        return PowerNode(base_a, BinaryOpNode(a.exp, b.exp, "+"))
    return None


# ---------- Division ----------
@register("/", IntegerNode, IntegerNode)
def _(a: IntegerNode, b: IntegerNode):
    if b.value == 0:
        raise ZeroDivisionError("Division by zero")
    return FractionNode(a, b).simplify()


@register("/", DecimalNode, DecimalNode)
def _(a: DecimalNode, b: DecimalNode):
    if b.value == 0:
        raise ZeroDivisionError("Division by zero")
    return DecimalNode(a.value / b.value)


@register("/", IntegerNode, DecimalNode)
def _(a: IntegerNode, b: DecimalNode):
    if b.value == 0:
        raise ZeroDivisionError("Division by zero")
    return DecimalNode(a.value / b.value)


@register("/", DecimalNode, IntegerNode)
def _(a: DecimalNode, b: IntegerNode):
    if b.value == 0:
        raise ZeroDivisionError("Division by zero")
    return DecimalNode(a.value / b.value)


@register("/", FractionNode, IntegerNode)
def _(a: FractionNode, b: IntegerNode):
    if b.value == 0:
        raise ZeroDivisionError("Division by zero")
    return FractionNode(a.num, IntegerNode(a.den.value * b.value)).simplify()


@register("/", IntegerNode, FractionNode)
def _(a: IntegerNode, b: FractionNode):
    if b.num.value == 0:
        raise ZeroDivisionError("Division by zero")
    return FractionNode(
        IntegerNode(a.value * b.den.value),
        b.num,
    ).simplify()


@register("/", FractionNode, FractionNode)
def _(a: FractionNode, b: FractionNode):
    if b.num.value == 0:
        raise ZeroDivisionError("Division by zero")
    return FractionNode(
        IntegerNode(a.num.value * b.den.value),
        IntegerNode(a.den.value * b.num.value),
    ).simplify()


#
# # ---------- Unary neg (dispatch channel "neg") ----------
# @register("neg", IntegerNode, IntegerNode)
# def _(a, _b): return IntegerNode(-a.value)
#
#
# @register("neg", DecimalNode, DecimalNode)
# def _(a, _b): return DecimalNode(-a.value)


if __name__ == "__main__":
    print(IntegerNode(1) + IntegerNode(2))
    print(IntegerNode(1) / IntegerNode(3) + IntegerNode(2))
