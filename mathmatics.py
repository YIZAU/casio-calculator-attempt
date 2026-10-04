from __future__ import annotations

import math
from typing import Any, Callable

_TABLE: dict[tuple[str, type, type], Callable[[Any, Any], Any]] = {}


def register(op: str, lt: type, rt: type, commutative: bool = False):
    def register_rule(func):
        _TABLE[(op, lt, rt)] = func

        if commutative and lt is not rt:
            # Auto-generate the reversed entry (a, b) -> fn(b, a)
            _TABLE[(op, rt, lt)] = lambda a, b: func(b, a)

        return func

    return register_rule


def dispatch(op: str, a: Any, b: Any):
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

    def __init__(self, value: float):
        self.value = float(value)

    def evaluate(self, env=None) -> float:
        return self.value

    def to_str(self, parent_prec=0) -> str:
        return str(self.value)


class FractionNode(Node):
    is_numeric = True
    __slots__ = ("num", "den")

    def __init__(self, numerator: Node, denominator: Node):
        self.num = numerator
        self.den = denominator

    def simplify(self, env=None):
        num = self.num.simplify(env)
        den = self.den.simplify(env)
        if not isinstance(num, IntegerNode) or not isinstance(den, IntegerNode):
            return FractionNode(num, den)
        if den.value == 0:
            raise ZeroDivisionError("Division by zero")
        g = math.gcd(num.value, den.value)
        n, d = num.value // g, den.value // g
        if d < 0:
            n, d = -n, -d
        if d == 1:
            return IntegerNode(n)
        return FractionNode(IntegerNode(n), IntegerNode(d))

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
        l = self.left.simplify(env)
        r = self.right.simplify(env)

        if (isinstance(l, Node) and l.is_numeric
                and isinstance(r, Node) and r.is_numeric):
            res = dispatch(self.op, l, r)
            if res is not None:
                return res

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


class RootNode(Node):
    __slots__ = ("degree", "radicand")

    # 超过此值不再做因子提取（完全 n 次方判定仍然会做一次）
    _MAX_RADICAND_FOR_FACTORING = 10 ** 10

    def __init__(self, degree: Node, expression: Node):
        self.degree = degree
        self.radicand = expression

    def simplify(self, env=None):
        env = env or {}
        d = self.degree.simplify(env)
        r = self.radicand.simplify(env)

        # 1. degree 必须是非负整数，否则跳过折叠
        if isinstance(d, IntegerNode):
            if d.value == 0:
                raise ZeroDivisionError("The 0th root is illegal")
            if d.value == 1:
                return r

        if not isinstance(d, IntegerNode) or d.value < 1:
            if d is self.degree and r is self.radicand:
                return self
            return RootNode(d, r)
        n = d.value

        # 2. radicand 是整数
        if isinstance(r, IntegerNode):
            result = self._simplify_integer_radicand(n, r.value)
            if result is not None:
                return result.simplify(env)

        # 3. radicand 是分数
        if isinstance(r, FractionNode):
            result = self._simplify_fraction_radicand(n, r)
            if result is not None:
                return result.simplify(env)

        # 4. 其他情况保留（变量、嵌套根号、未折叠的函数等）
        if d is self.degree and r is self.radicand:
            return self
        return RootNode(d, r)

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
                raise ValueError("Math Error: even root of negative number is not real")
            return -pow(abs(value), 1 / degree)
        return pow(value, 1 / degree)

    def _simplify_integer_radicand(self, n: int, value: int) -> Node | None:
        # 负数：n 为奇数时剥离符号，n 为偶数时抛错
        if value < 0:
            if n % 2 == 0:
                raise ValueError("Math Error: even root of negative number is not real")
            inner = self._simplify_integer_radicand(n, -value)
            if inner is None:
                return None
            return NegativeNode(inner)

        # 短路
        if value == 0:
            return IntegerNode(0)
        if value == 1:
            return IntegerNode(1)

        # 超大数：只做一次完全 n 次方判定，不做因子分解
        if value > self._MAX_RADICAND_FOR_FACTORING:
            r = self._integer_nth_root(value, n)
            if r ** n == value:
                return IntegerNode(r)
            return None

        outside, inside = self._extract_nth_power(value, n)

        if inside == 1:
            return IntegerNode(outside)
        if outside == 1:
            return RootNode(IntegerNode(n), IntegerNode(inside))
        return BinaryOpNode(
            IntegerNode(outside),
            RootNode(IntegerNode(n), IntegerNode(inside)),
            "*",
        )

    def _simplify_fraction_radicand(self, n: int, frac: FractionNode) -> Node | None:
        num, den = frac.num, frac.den
        if not isinstance(num, IntegerNode) or not isinstance(den, IntegerNode):
            return None
        if den.value == 0:
            raise ZeroDivisionError("Division by zero")

        a, b = num.value, den.value
        if b < 0:
            a, b = -a, -b

        # 分母有理化：√(a/b) = √(a·b) / b
        combined = abs(a) * b
        if combined > self._MAX_RADICAND_FOR_FACTORING:
            return None

        outside, inside = self._extract_nth_power(combined, n)

        radical = IntegerNode(1) if inside == 1 else RootNode(IntegerNode(n), IntegerNode(inside))
        numerator = IntegerNode(outside) if inside == 1 else BinaryOpNode(IntegerNode(outside), radical, "*")

        result: Node = FractionNode(numerator, IntegerNode(b))

        if a < 0:
            if n % 2 == 0:
                raise ValueError("Math Error: even root of negative number is not real")
            result = NegativeNode(result)
            return result

    def _integer_nth_root(self, x: int, n: int) -> int:
            """返回 floor(x ** (1/n))，用二分。x >= 0，n >= 1。"""
            if x < 0:
                raise ValueError("integer_nth_root: x must be non-negative")
            if n <= 0:
                raise ValueError("integer_nth_root: n must be positive")
            if x < 2:
                return x

            lo, hi = 1, 1
            while hi ** n <= x:
                hi *= 2
            while lo < hi:
                mid = (lo + hi + 1) // 2
                if mid ** n <= x:
                    lo = mid
                else:
                    hi = mid - 1
            return lo

    def _extract_nth_power(self, radicand: int, n: int) -> tuple[int, int]:
            """
            把 radicand 分解为 outside^n * inside，inside 不再含 n 次方因子。
            返回 (outside, inside)。radicand >= 0，n >= 2。
            """
            if radicand <= 1:
                return radicand, 1

            outside = 1
            inside = radicand
            i = 2
            while True:
                i_max = self._integer_nth_root(inside, n)
                if i > i_max:
                    break
                p = i ** n
                while inside % p == 0:
                    outside *= i
                    inside //= p
                i += 1
            return outside, inside

    def to_str(self, parent_prec: int = 0) -> str:
        return f"deg({self.degree.to_str()})root({self.radicand.to_str()})"


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
            p, q, signs = self._reduce_to_first_quadrant(rational_c)

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
                c = self._rationalize(node.left)
                if c is not None:
                    return c
            if isinstance(node.left, PiNode):
                c = self._rationalize(node.right)
                if c is not None:
                    return c

        # π/n 或 (n·π)/m：分子递归提取，分母必须是 IntegerNode
        if isinstance(node, FractionNode):
            num_coef = self._extract_pi_coefficient(node.num)
            if num_coef is not None and isinstance(node.den, IntegerNode):
                return num_coef[0], num_coef[1] * node.den.value

        return None

    def _rationalize(self, node: Node) -> tuple[int, int] | None:
        """把 Node 归一为 (n, d)，仅支持 IntegerNode 和 FractionNode(int,int)。"""
        if isinstance(node, IntegerNode):
            return node.value, 1
        if isinstance(node, FractionNode):
            if isinstance(node.num, IntegerNode) and isinstance(node.den, IntegerNode):
                return node.num.value, node.den.value
        return None

    def _reduce_to_first_quadrant(self, rational_c: tuple[int, int]) -> tuple[int, int, tuple[int, int, int]]:
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

    def to_str(self, parent_prec=0) -> str:
        return f"{self.name}({self.argument.to_str()})"


class ArcTrigNode(Node):
    __slots__ = ("name", "argument")

    # 键: 值签名 ("rat", p, q) 或 ("root", n, d)  —— 都是正值
    # 值: {name: (p, q)}  表示输出 (p/q)·π，None 表示该函数在此值下无特殊角
    _SPECIAL_VALUES = {
        ("rat", 0, 1):      {"arcsin": (0, 1), "arccos": (1, 2), "arctan": (0, 1)},
        ("rat", 1, 1):      {"arcsin": (1, 2), "arccos": (0, 1), "arctan": (1, 4)},
        ("rat", 1, 2):      {"arcsin": (1, 6), "arccos": (1, 3), "arctan": None},

        ("root", 2, 2):     {"arcsin": (1, 4), "arccos": (1, 4), "arctan": None},
        ("root", 3, 2):     {"arcsin": (1, 3), "arccos": (1, 6), "arctan": None},
        ("root", 3, 3):     {"arcsin": None,   "arccos": None,   "arctan": (1, 6)},
        ("root", 3, 1):     {"arcsin": None,   "arccos": None,   "arctan": (1, 3)},
        ("root", 1, 1):     {"arcsin": None,   "arccos": None,   "arctan": (1, 4)},
    }

    def __init__(self, name: str, argument: Node):
        self.name = name
        self.argument = argument

    # ---------- simplify ----------

    def simplify(self, env: dict = None):
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
            if arg is self.argument and not negated:
                return self
            return ArcTrigNode(self.name, arg)

        # 3. 查表
        entry = self._SPECIAL_VALUES.get(sig)
        if entry is None or entry.get(self.name) is None:
            if arg is self.argument and not negated:
                return self
            return ArcTrigNode(self.name, arg)

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
        angle_unit = env.get("angle_unit", "RAD")
        if angle_unit == "RAD":
            return self._make_pi_node(p, q)
        elif angle_unit == "DEG":
            return FractionNode(IntegerNode(p * 180), IntegerNode(q)).simplify(env)
        elif angle_unit == "GRA":
            return FractionNode(IntegerNode(p * 200), IntegerNode(q)).simplify(env)

        return ArcTrigNode(self.name, arg)

    # ---------- evaluate ----------

    def evaluate(self, env: dict = None) -> float:
        env = env or {}
        arg = self.argument.evaluate(env)
        angle_unit = env.get("angle_unit", "RAD")

        if self.name == "arcsin":
            rad = math.asin(arg)
        elif self.name == "arccos":
            rad = math.acos(arg)
        elif self.name == "arctan":
            rad = math.atan(arg)
        else:
            raise ValueError(f"Unknown inverse triangle function: {self.name}")

        if angle_unit == "DEG":
            return math.degrees(rad)
        elif angle_unit == "GRA":
            return rad / math.pi * 200
        return rad

    # ---------- 辅助 ----------

    def _value_signature(self, node: Node) -> tuple | None:
        """返回 ("rat", p, q) 或 ("root", n, d)。正负已由外层剥离。"""
        # 有理数
        if isinstance(node, IntegerNode):
            return ("rat", node.value, 1)

        if isinstance(node, FractionNode):
            # p/q
            if isinstance(node.num, IntegerNode) and isinstance(node.den, IntegerNode):
                p, q = node.num.value, node.den.value
                g = math.gcd(abs(p), abs(q)) or 1
                return ("rat", p // g, q // g)
            # √n / d
            if isinstance(node.num, RootNode) and isinstance(node.den, IntegerNode):
                return self._root_signature(node.num, node.den.value)

        # 单个根号 √n
        if isinstance(node, RootNode):
            return self._root_signature(node, 1)

        return None

    def _root_signature(self, root: RootNode, den: int) -> tuple | None:
        if not isinstance(root.degree, IntegerNode) or root.degree.value != 2:
            return None
        if not isinstance(root.radicand, IntegerNode):
            return None
        # 提取平方因子：√8 → 2√2
        n = root.radicand.value
        outside = 1
        i = 2
        while i * i <= n:
            while n % (i * i) == 0:
                outside *= i
                n //= i * i
            i += 1
        return ("root", n, den // math.gcd(outside, den) if outside else den)

    def _make_pi_node(self, p: int, q: int) -> Node:
        if p == 0:
            return IntegerNode(0)
        g = math.gcd(abs(p), q) or 1
        p, q = p // g, q // g
        if q < 0:
            p, q = -p, -q

        numerator = PiNode() if abs(p) == 1 else BinaryOpNode(IntegerNode(abs(p)), PiNode(), "*")
        result = numerator if q == 1 else FractionNode(numerator, IntegerNode(q))
        return NegativeNode(result) if p < 0 else result

    def to_str(self, parent_prec: int = 0) -> str:
        return f"{self.name}({self.argument.to_str()})"


class PowerNode(Node):
    __slots__ = ("base", "exp")

    def __init__(self, base: Node, exponent: Node):
        self.base = base
        self.exp = exponent

    def simplify(self, env=None):
        b = self.base.simplify(env)
        e = self.exp.simplify(env)
        if b is self.base and e is self.exp:
            return self
        return PowerNode(b, e)

    def evaluate(self, env=None) -> float:
        base = self.base.evaluate()
        exp = self.exp.evaluate()
        if base == 0 and exp == 0:
            raise ValueError("Math Error: 0^0 is undefined")
        if isinstance(base, (int, float)) and base < 0 and exp != int(exp):
            raise ValueError("Negative number to non-integer power")
        return math.pow(base, exp)

    def to_str(self, parent_prec=0) -> str:
        return f"{self.base.to_str()}^({self.exp.to_str()})"


class UnaryFunctionNode(Node):
    __slots__ = ("name", "argument")

    def __init__(self, name: str, argument: Node):
        self.name = name
        self.argument = argument

    def simplify(self, env=None):
        a = self.argument.simplify(env)
        if a is self.argument:
            return self
        return UnaryFunctionNode(self.name, a)

    def evaluate(self, env=None) -> float:
        arg = self.argument.evaluate(env)

        if self.name == "ln":
            return math.log(arg)
        if self.name == "sqrt":
            return math.sqrt(arg)
        if self.name == "sq":
            return arg ** 2
        if self.name == "cbrt":
            return math.cbrt(arg)
        if self.name == "cb":
            return arg ** 3
        raise ValueError(f"Unknown unary function: {self.name}")

    def to_str(self, parent_prec=0) -> str:
        return f"{self.name}({self.argument.to_str()})"


class BinaryFunctionNode(Node):
    __slots__ = ("name", "argument1", "argument2")

    def __init__(self, name: str, argument1: Node, argument2: Node):
        self.name = name
        self.argument1 = argument1
        self.argument2 = argument2

    def simplify(self, env=None):
        a1 = self.argument1.simplify(env)
        a2 = self.argument2.simplify(env)
        if a1 is self.argument1 and a2 is self.argument2:
            return self
        return BinaryFunctionNode(self.name, a1, a2)

    def evaluate(self, env=None) -> float:
        a1 = self.argument1.evaluate(env)
        a2 = self.argument2.evaluate(env)

        if self.name == "log":
            if a1 <= 0:
                raise SyntaxError("Math Error: antilogarithm should be larger than 0")
            return math.log(a2, a1)
        if self.name == "comb":
            if a1 < a2:
                raise SyntaxError("Math Error: r should not be larger than n in nCr")
            return math.comb(int(a1), int(a2))
        if self.name == "perm":
            if a1 < a2:
                raise SyntaxError("Math Error: r should not be larger than n in nPr")
            return math.perm(int(a1), int(a2))
        raise ValueError(f"Unknown binary function: {self.name}")

    def to_str(self, parent_prec=0) -> str:
        if self.name == "log":
            return f"base({self.argument1.to_str()})log({self.argument2.to_str()})"
        return f"{self.name}({self.argument1.to_str()}, {self.argument2.to_str()})"


# =================================================================

@register("+", IntegerNode, IntegerNode, commutative=True)
def _(a, b): return IntegerNode(a.value + b.value)


@register("+", IntegerNode, DecimalNode, commutative=True)
def _(a, b): return DecimalNode(a.value + b.value)


@register("+", DecimalNode, DecimalNode, commutative=True)
def _(a, b): return DecimalNode(a.value + b.value)


@register("+", IntegerNode, FractionNode, commutative=True)
def _(a, b):
    return FractionNode(
        IntegerNode(a.value * b.den.value + b.num.value),
        b.den,
    ).simplify()


@register("+", FractionNode, FractionNode, commutative=True)
def _(a, b):
    return FractionNode(
        IntegerNode(a.num.value * b.den.value + b.num.value * a.den.value),
        IntegerNode(a.den.value * b.den.value),
    ).simplify()


@register("+", ComplexNode, ComplexNode, commutative=True)
def _(a, b):
    return ComplexNode(a.real + b.real, a.imag + b.imag)


@register("+", ComplexNode, IntegerNode, commutative=True)
def _(a, b):
    return ComplexNode(a.real + b, a.imag)


@register("+", ComplexNode, DecimalNode, commutative=True)
def _(a, b):
    return ComplexNode(a.real + b, a.imag)


# ---------- Subtraction ----------
@register("-", IntegerNode, IntegerNode)
def _(a, b): return IntegerNode(a.value - b.value)


@register("-", IntegerNode, DecimalNode)
def _(a, b): return DecimalNode(a.value - b.value)


@register("-", DecimalNode, IntegerNode)
def _(a, b): return DecimalNode(a.value - b.value)


@register("-", DecimalNode, DecimalNode)
def _(a, b): return DecimalNode(a.value - b.value)


@register("-", ComplexNode, ComplexNode)
def _(a, b):
    return ComplexNode(a.real - b.real, a.imag - b.imag)


@register("-", ComplexNode, IntegerNode)
def _(a, b):
    return ComplexNode(a.real - b, a.imag)


# ---------- Multiplication ----------
@register("*", IntegerNode, IntegerNode, commutative=True)
def _(a, b): return IntegerNode(a.value * b.value)


@register("*", IntegerNode, DecimalNode, commutative=True)
def _(a, b): return DecimalNode(a.value * b.value)


@register("*", DecimalNode, DecimalNode, commutative=True)
def _(a, b): return DecimalNode(a.value * b.value)


@register("*", IntegerNode, FractionNode, commutative=True)
def _(a, b):
    return FractionNode(
        IntegerNode(a.value * b.num.value),
        b.den,
    ).simplify()


@register("*", FractionNode, FractionNode, commutative=True)
def _(a, b):
    return FractionNode(
        IntegerNode(a.num.value * b.num.value),
        IntegerNode(a.den.value * b.den.value),
    ).simplify()


@register("*", ComplexNode, IntegerNode, commutative=True)
def _(a, b):
    return ComplexNode(a.real * b, a.imag * b)


# ---------- Division ----------
@register("/", IntegerNode, IntegerNode)
def _(a, b):
    if b.value == 0:
        raise ZeroDivisionError("Division by zero")
    return FractionNode(a, b).simplify()


@register("/", DecimalNode, DecimalNode)
def _(a, b):
    if b.value == 0:
        raise ZeroDivisionError("Division by zero")
    return DecimalNode(a.value / b.value)


@register("/", IntegerNode, DecimalNode)
def _(a, b):
    if b.value == 0:
        raise ZeroDivisionError("Division by zero")
    return DecimalNode(a.value / b.value)


@register("/", DecimalNode, IntegerNode)
def _(a, b):
    if b.value == 0:
        raise ZeroDivisionError("Division by zero")
    return DecimalNode(a.value / b.value)


@register("/", FractionNode, IntegerNode)
def _(a, b):
    if b.value == 0:
        raise ZeroDivisionError("Division by zero")
    return FractionNode(a.num, IntegerNode(a.den.value * b.value)).simplify()


@register("/", IntegerNode, FractionNode)
def _(a, b):
    if b.num.value == 0:
        raise ZeroDivisionError("Division by zero")
    return FractionNode(
        IntegerNode(a.value * b.den.value),
        b.num,
    ).simplify()


@register("/", FractionNode, FractionNode)
def _(a, b):
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
