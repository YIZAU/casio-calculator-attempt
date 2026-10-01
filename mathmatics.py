import math


class Node:
    def evaluate(self) -> float | int:
        raise NotImplementedError

    def to_str(self) -> str:
        raise NotImplementedError

    def simplify(self):
        return self


class Number(Node):
    def evaluate(self) -> float | int:
        raise NotImplementedError

    def to_str(self) -> str:
        raise NotImplementedError

    def simplify(self):
        return self


class IntegerNode(Number):
    def __init__(self, value: int):
        self.value = value

    def evaluate(self) -> int:
        return self.value

    def to_str(self) -> str:
        return str(self.value)


class DecimalNode(Number):
    def __init__(self, value: float):
        self.value = value

    def evaluate(self) -> float:
        return float(self.value)

    def to_str(self) -> str:
        return str(self.value)


class FractionNode(Node):
    def __init__(self, numerator: Node, denominator: Node):
        self.numerator = numerator
        self.denominator = denominator

    def simplify(self):
        num = self.numerator.simplify()
        den = self.denominator.simplify()
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

    def evaluate(self) -> float:
        return self.numerator.evaluate() / self.denominator.evaluate()

    def to_str(self) -> str:
        return f"frac({self.numerator.to_str()}, {self.denominator.to_str()})"
