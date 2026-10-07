"""
数学引擎测试。
运行方式：
    cd Programs/Calculator
    pytest tests/test_mathmatics.py -v
"""
import pytest

from mathematics import *


# ============================================================
# 辅助函数
# ============================================================

def DEG_env():
    return {"angle_unit": "DEG"}

def RAD_env():
    return {"angle_unit": "RAD"}


def num(node):
    """把 simplify 结果转成 float，用于数值比较。"""
    return node.calculate()

def close(a, b, tol=1e-9):
    """浮点数近似比较。"""
    return abs(a - b) < tol

def sig(node):
    """把节点转成 to_str，用于结构比较。"""
    return node.to_str()


class TestPowerNode:

    def test_basic_integer_power(self):
        assert sig(PowerNode(IntegerNode(2), IntegerNode(10)).simplify()) == "1024"

    def test_zero_exponent(self):
        assert sig(PowerNode(IntegerNode(5), IntegerNode(0)).simplify()) == "1"

    def test_zero_to_zero(self):
        with pytest.raises(ValueError):
            PowerNode(IntegerNode(0), IntegerNode(0)).simplify()

    def test_zero_to_negative(self):
        with pytest.raises(ZeroDivisionError):
            PowerNode(IntegerNode(0), IntegerNode(-2)).simplify()

    def test_one_to_anything(self):
        assert sig(PowerNode(IntegerNode(1), IntegerNode(100)).simplify()) == "1"

    def test_minus_one_odd(self):
        assert sig(PowerNode(IntegerNode(-1), IntegerNode(5)).simplify()) == "-1"

    def test_minus_one_even(self):
        assert sig(PowerNode(IntegerNode(-1), IntegerNode(4)).simplify()) == "1"

    def test_negative_base_integer_exp(self):
        assert num(PowerNode(IntegerNode(-2), IntegerNode(3)).simplify()) == -8
        assert num(PowerNode(IntegerNode(-2), IntegerNode(4)).simplify()) == 16

    def test_negative_base_odd_fractional(self):
        # (-8)^(1/3) = -2
        result = PowerNode(
            NegativeNode(IntegerNode(8)),
            FractionNode(IntegerNode(1), IntegerNode(3)),
        ).simplify()
        assert num(result) == -2

    def test_negative_base_even_fractional(self):
        # (-4)^(1/2) 实数域无解
        with pytest.raises(ValueError):
            PowerNode(
                NegativeNode(IntegerNode(4)),
                FractionNode(IntegerNode(1), IntegerNode(2)),
            ).simplify()

    def test_negative_exponent(self):
        assert num(PowerNode(IntegerNode(2), IntegerNode(-3)).simplify()) == 1 / 8

    def test_perfect_nth_power(self):
        # 8^(1/3) = 2
        result = PowerNode(
            IntegerNode(8),
            FractionNode(IntegerNode(1), IntegerNode(3)),
        ).simplify()
        assert num(result) == 2

    def test_perfect_nth_power_higher_exp(self):
        # 8^(2/3) = 4
        result = PowerNode(
            IntegerNode(8),
            FractionNode(IntegerNode(2), IntegerNode(3)),
        ).simplify()
        assert num(result) == 4

    def test_transform_to_root(self):
        # 2^(1/2) 应该转成 RootNode，数值是 √2
        result = PowerNode(
            IntegerNode(2),
            FractionNode(IntegerNode(1), IntegerNode(2)),
        ).simplify()
        assert close(num(result), math.sqrt(2))

    def test_root_power_merging(self):
        # (√2)^4 = 4
        sqrt2 = RootNode(IntegerNode(2), IntegerNode(2))
        result = PowerNode(sqrt2, IntegerNode(4)).simplify()
        assert num(result) == 4

    def test_root_power_partial(self):
        # (√2)^3 = 2√2
        sqrt2 = RootNode(IntegerNode(2), IntegerNode(2))
        result = PowerNode(sqrt2, IntegerNode(3)).simplify()
        assert close(num(result), 2 * math.sqrt(2))

    def test_fraction_base(self):
        # (2/3)^2 = 4/9
        result = PowerNode(
            FractionNode(IntegerNode(2), IntegerNode(3)),
            IntegerNode(2),
        ).simplify()
        assert close(num(result), 4 / 9)


class TestRootNode:

    def test_sqrt_zero(self):
        assert num(RootNode(IntegerNode(2), IntegerNode(0)).simplify()) == 0

    def test_sqrt_one(self):
        assert num(RootNode(IntegerNode(2), IntegerNode(1)).simplify()) == 1

    def test_first_root(self):
        # ¹√5 = 5
        assert num(RootNode(IntegerNode(1), IntegerNode(5)).simplify()) == 5

    def test_perfect_square(self):
        assert num(RootNode(IntegerNode(2), IntegerNode(4)).simplify()) == 2
        assert num(RootNode(IntegerNode(2), IntegerNode(100)).simplify()) == 10

    def test_factor_extraction(self):
        assert close(num(RootNode(IntegerNode(2), IntegerNode(8)).simplify()), math.sqrt(8))
        assert close(num(RootNode(IntegerNode(2), IntegerNode(72)).simplify()), math.sqrt(72))

    def test_perfect_cube(self):
        assert num(RootNode(IntegerNode(3), IntegerNode(8)).simplify()) == 2

    def test_negative_odd_root(self):
        result = RootNode(
            IntegerNode(3),
            NegativeNode(IntegerNode(8)),
        ).simplify()
        assert num(result) == -2

    def test_negative_even_root(self):
        with pytest.raises(ValueError):
            RootNode(
                IntegerNode(2),
                NegativeNode(IntegerNode(4)),
            ).simplify()

    def test_fraction_radicand(self):
        # √(1/4) = 1/2
        result = RootNode(
            IntegerNode(2),
            FractionNode(IntegerNode(1), IntegerNode(4)),
        ).simplify()
        assert num(result) == 0.5

    def test_nested_root(self):
        # √(√16) = 2
        inner = RootNode(IntegerNode(2), IntegerNode(16))
        outer = RootNode(IntegerNode(2), inner)
        assert num(outer.simplify()) == 2

    def test_power_radicand(self):
        # √(x^2) = x（若支持变量）
        x = VariableNode("x")
        result = RootNode(IntegerNode(2), PowerNode(x, IntegerNode(2))).simplify()
        # 期望结果为 x 本身或保持原样，取决于实现
        assert "x" in sig(result)


class TestFractionNode:

    def test_gcd_reduction(self):
        result = FractionNode(IntegerNode(4), IntegerNode(6)).simplify()
        assert num(result) == 2 / 3

    def test_negative_numerator(self):
        result = FractionNode(IntegerNode(-4), IntegerNode(6)).simplify()
        assert num(result) == -2 / 3

    def test_negative_denominator(self):
        result = FractionNode(IntegerNode(4), IntegerNode(-6)).simplify()
        assert num(result) == -2 / 3

    def test_rationalize_single(self):
        # 1/√2 = √2/2
        result = FractionNode(
            IntegerNode(1),
            RootNode(IntegerNode(2), IntegerNode(2)),
        ).simplify()
        assert close(num(result), 1 / math.sqrt(2))

    def test_rationalize_pair(self):
        # 1/(√6 + √2) = (√6 - √2)/4
        den = BinaryOpNode(
            RootNode(IntegerNode(2), IntegerNode(6)),
            RootNode(IntegerNode(2), IntegerNode(2)),
            "+",
        )
        result = FractionNode(IntegerNode(1), den).simplify()
        assert close(num(result), 1 / (math.sqrt(6) + math.sqrt(2)))

    def test_rationalize_with_rational(self):
        # 1/(1 + √2) = √2 - 1
        den = BinaryOpNode(IntegerNode(1), RootNode(IntegerNode(2), IntegerNode(2)), "+")
        result = FractionNode(IntegerNode(1), den).simplify()
        assert close(num(result), 1 / (1 + math.sqrt(2)))


class TestDecimalNode:

    def test_whole_number(self):
        result = DecimalNode(1.0).simplify()
        assert isinstance(result, IntegerNode)
        assert result.value == 1

    def test_simple_fraction(self):
        result = DecimalNode(0.5).simplify()
        assert close(num(result), 0.5)

    def test_fraction_with_small_den(self):
        result = DecimalNode(1.234).simplify()
        assert close(num(result), 1.234)

    def test_long_decimal_kept(self):
        result = DecimalNode(3.14159265).simplify()
        # 分母会超过阈值，保留为 DecimalNode
        assert isinstance(result, DecimalNode)


class TestLogNode:

    def test_ln_one(self):
        result = LogNode(IntegerNode(1)).simplify()
        assert num(result) == 0

    def test_ln_e(self):
        result = LogNode(EulerNode()).simplify()
        assert num(result) == 1

    def test_ln_e_power(self):
        # ln(e^3) = 3
        arg = PowerNode(EulerNode(), IntegerNode(3))
        result = LogNode(arg).simplify()
        assert num(result) == 3

    def test_log2_1(self):
        result = LogNode(IntegerNode(1), IntegerNode(2)).simplify()
        assert num(result) == 0

    def test_log2_2(self):
        result = LogNode(IntegerNode(2), IntegerNode(2)).simplify()
        assert num(result) == 1

    def test_log2_8(self):
        result = LogNode(IntegerNode(8), IntegerNode(2)).simplify()
        assert num(result) == 3

    def test_log2_2_power5(self):
        # log_2(2^5) = 5
        arg = PowerNode(IntegerNode(2), IntegerNode(5))
        result = LogNode(arg, IntegerNode(2)).simplify()
        assert num(result) == 5

    def test_log_fraction_base(self):
        # log_{1/2}(1/8) = 3
        base = FractionNode(IntegerNode(1), IntegerNode(2))
        arg = FractionNode(IntegerNode(1), IntegerNode(8))
        result = LogNode(arg, base).simplify()
        assert num(result) == 3

    def test_log_decimal_base(self):
        # log_{1.1}(1.21) = 2
        base = DecimalNode(1.1)
        arg = DecimalNode(1.21)
        result = LogNode(arg, base).simplify()
        assert num(result) == 2

    def test_log_decimal_power_argument(self):
        # log_{1.1}(1.21^3) = 6
        base = DecimalNode(1.1)
        arg = PowerNode(DecimalNode(1.21), IntegerNode(3))
        result = LogNode(arg, base).simplify()
        assert num(result) == 6


class TestTrigNode:

    @pytest.mark.parametrize("name,angle,expected", [
        ("sin", 0,  0),
        ("sin", 30, 0.5),
        ("sin", 90, 1.0),
        ("cos", 0,  1.0),
        ("cos", 60, 0.5),
        ("cos", 90, 0.0),
        ("tan", 0,  0.0),
        ("tan", 45, 1.0),
    ])
    def test_special_deg(self, name, angle, expected):
        result = TrigNode(name, IntegerNode(angle)).simplify(DEG_env())
        assert close(num(result), expected)

    def test_sin_45(self):
        result = TrigNode("sin", IntegerNode(45)).simplify(DEG_env())
        assert close(num(result), math.sqrt(2) / 2)

    def test_sin_60(self):
        result = TrigNode("sin", IntegerNode(60)).simplify(DEG_env())
        assert close(num(result), math.sqrt(3) / 2)

    def test_sin_negative(self):
        # sin(-30°) = -1/2
        result = TrigNode("sin", NegativeNode(IntegerNode(30))).simplify(DEG_env())
        assert close(num(result), -0.5)

    def test_sin_second_quadrant(self):
        # sin(150°) = 1/2
        result = TrigNode("sin", IntegerNode(150)).simplify(DEG_env())
        assert close(num(result), 0.5)

    def test_sin_third_quadrant(self):
        # sin(210°) = -1/2
        result = TrigNode("sin", IntegerNode(210)).simplify(DEG_env())
        assert close(num(result), -0.5)

    @pytest.mark.parametrize("angle_expr,expected", [
        (FractionNode(PiNode(), IntegerNode(6)), 0.5),
        (FractionNode(PiNode(), IntegerNode(2)), 1.0),
    ])
    def test_special_rad(self, angle_expr, expected):
        result = TrigNode("sin", angle_expr).simplify(RAD_env())
        assert close(num(result), expected)

    def test_non_special_kept(self):
        result = TrigNode("sin", IntegerNode(1)).simplify(DEG_env())
        # 不是特殊角，保留
        assert "sin" in sig(result)


class TestArcTrigNode:

    @pytest.mark.parametrize("name,arg,expected", [
        ("arcsin", 0,   0),
        ("arcsin", 1,   math.pi / 2),
        ("arccos", 0,   math.pi / 2),
        ("arccos", 1,   0),
        ("arctan", 0,   0),
        ("arctan", 1,   math.pi / 4),
    ])
    def test_special_rad(self, name, arg, expected):
        result = ArcTrigNode(name, IntegerNode(arg)).simplify(RAD_env())
        assert close(num(result), expected)

    def test_arcsin_half(self):
        arg = FractionNode(IntegerNode(1), IntegerNode(2))
        result = ArcTrigNode("arcsin", arg).simplify(RAD_env())
        assert close(num(result), math.pi / 6)

    def test_arcsin_sqrt2_over_2(self):
        arg = FractionNode(
            RootNode(IntegerNode(2), IntegerNode(2)),
            IntegerNode(2),
        )
        result = ArcTrigNode("arcsin", arg).simplify(RAD_env())
        assert close(num(result), math.pi / 4)

    def test_arcsin_negative(self):
        # arcsin(-1/2) = -π/6
        arg = NegativeNode(FractionNode(IntegerNode(1), IntegerNode(2)))
        result = ArcTrigNode("arcsin", arg).simplify(RAD_env())
        assert close(num(result), -math.pi / 6)

    def test_arccos_negative(self):
        # arccos(-1/2) = 2π/3
        arg = NegativeNode(FractionNode(IntegerNode(1), IntegerNode(2)))
        result = ArcTrigNode("arccos", arg).simplify(RAD_env())
        assert close(num(result), 2 * math.pi / 3)

    def test_arctan_sqrt3(self):
        arg = RootNode(IntegerNode(2), IntegerNode(3))
        result = ArcTrigNode("arctan", arg).simplify(RAD_env())
        assert close(num(result), math.pi / 3)

    def test_arctan_2_minus_sqrt3(self):
        # arctan(2 - √3) = π/12
        arg = BinaryOpNode(
            IntegerNode(2),
            RootNode(IntegerNode(2), IntegerNode(3)),
            "-",
        )
        result = ArcTrigNode("arctan", arg).simplify(RAD_env())
        assert close(num(result), math.pi / 12)

    def test_arcsin_out_of_domain(self):
        with pytest.raises(ValueError):
            ArcTrigNode("arcsin", IntegerNode(2)).evaluate(RAD_env())

    def test_deg_mode(self):
        # arcsin(1/2) 在 DEG 模式下应输出 30
        arg = FractionNode(IntegerNode(1), IntegerNode(2))
        result = ArcTrigNode("arcsin", arg).simplify(DEG_env())
        assert close(num(result), 30)


class TestCombinatoricNode:

    def test_comb_basic(self):
        result = CombinatoricNode(IntegerNode(5), IntegerNode(3)).simplify()
        assert num(result) == 10

    def test_perm_basic(self):
        result = CombinatoricNode(IntegerNode(5), IntegerNode(3), False).simplify()
        assert num(result) == 60

    def test_comb_zero(self):
        result = CombinatoricNode(IntegerNode(5), IntegerNode(0)).simplify()
        assert num(result) == 1

    def test_perm_full(self):
        result = CombinatoricNode(IntegerNode(5), IntegerNode(5), False).simplify()
        assert num(result) == 120

    def test_comb_invalid(self):
        with pytest.raises(ValueError):
            CombinatoricNode(IntegerNode(5), IntegerNode(6)).simplify()


class TestBinaryOpNode:

    def test_fraction_addition(self):
        a = FractionNode(IntegerNode(1), IntegerNode(3))
        b = FractionNode(IntegerNode(1), IntegerNode(6))
        result = BinaryOpNode(a, b, "+").simplify()
        assert num(result) == 0.5

    def test_fraction_subtraction(self):
        a = FractionNode(IntegerNode(1), IntegerNode(2))
        b = FractionNode(IntegerNode(1), IntegerNode(3))
        result = BinaryOpNode(a, b, "-").simplify()
        assert close(num(result), 1 / 6)

    def test_integer_multiplication(self):
        assert num(BinaryOpNode(IntegerNode(2), IntegerNode(3), "*").simplify()) == 6


class TestVariableNode:

    def test_undefined_defaults_to_zero(self):
        env = {"angle_unit": "RAD"}
        result = VariableNode("x").simplify(env)
        assert num(result) == 0

    def test_defined(self):
        env = {"angle_unit": "RAD", "x": IntegerNode(5)}
        result = VariableNode("x").simplify(env)
        assert num(result) == 5

    def test_defined_fraction(self):
        env = {
            "angle_unit": "RAD",
            "x": FractionNode(IntegerNode(1), IntegerNode(3)),
        }
        result = VariableNode("x").simplify(env)
        assert close(num(result), 1 / 3)
