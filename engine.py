import math
from typing import Any

""" the class Node """


class Node:
    def evaluate(self) -> float | int:
        raise NotImplementedError

    def to_str(self) -> str:
        raise NotImplementedError

    def simplify(self):
        return self


class IntegerNode(Node):
    def __init__(self, value: int):
        self.value = value

    def evaluate(self) -> int:
        return self.value

    def to_str(self) -> str:
        return str(self.value)


class DecimalNode(Node):
    def __init__(self, value: float):
        self.value = value

    def evaluate(self) -> float:
        return float(self.value)

    def to_str(self) -> str:
        return str(self.value)


class VariableNode(Node):
    def __init__(self, name: str):
        self.name = name

    def evaluate(self) -> float:
        if self.name == "π":
            return math.pi
        elif self.name == "e":
            return math.e
        elif self.name == "i":
            pass
        return 0.0  # 暂时返回 0，后面会在 Engine 中处理

    def to_str(self) -> str:
        return self.name


# + - * /
class BinaryOpNode(Node):
    def __init__(self, left: Node, right: Node, op: str):
        self.left = left
        self.right = right
        self.op = op  # "+" "-" "*" "/"

    def evaluate(self) -> float:
        l = self.left.evaluate()
        r = self.right.evaluate()
        if self.op == "+":
            return l + r
        elif self.op == "-":
            return l - r
        elif self.op == "*":
            return l * r
        elif self.op == "/":
            if r == 0:
                raise ZeroDivisionError("Division by zero")
            return l / r

    def to_str(self) -> str:
        return f"{self.left.to_str()} {self.op} {self.right.to_str()}"


# (-)
class NegativeNode(Node):
    def __init__(self, child: Node):
        self.child = child

    def evaluate(self) -> float:
        return -self.child.evaluate()

    def to_str(self) -> str:
        return f"-({self.child.to_str()})"


# the triangle function
class TriangleFunctionNode(Node):
    def __init__(self, name: str, argument: Node, angle_unit: str):
        self.name = name
        self.argument = argument
        self.angle_unit = angle_unit

    def evaluate(self) -> float:
        arg = self.argument.evaluate()

        if self.angle_unit == "DEG":
            arg = math.radians(arg)
        elif self.angle_unit == "RAD":
            pass
        elif self.angle_unit == "GRA":
            arg = math.radians(0.9 * arg)

        if self.name == "sin":
            return math.sin(arg)
        elif self.name == "cos":
            return math.cos(arg)
        elif self.name == "tan":
            return math.tan(arg)

        elif self.name == "arcsin":
            return math.asin(arg)
        elif self.name == "arccos":
            return math.acos(arg)
        elif self.name == "arctan":
            return math.atan(arg)

    def to_str(self) -> str:
        return f"{self.name}({self.argument.to_str()})"


# the fraction struct
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


class PowerNode(Node):
    def __init__(self, base: Node, exponent: Node):
        self.base = base
        self.exponent = exponent

    def evaluate(self) -> float:
        base = self.base.evaluate()
        exp = self.exponent.evaluate()
        # 处理 0^0
        if base == 0 and exp == 0:
            raise ValueError("0^0 is undefined")
        # 处理负数开方（返回复数？暂时报错）
        if base < 0 and exp != int(exp):
            raise ValueError("Negative number to non-integer power")
        return pow(base, exp)

    def to_str(self) -> str:
        return f"power({self.base.to_str()}, {self.exponent.to_str()})"


class RootNode(Node):
    def __init__(self, degree: Node, expression: Node):
        self.degree = degree
        self.expression = expression

    def evaluate(self) -> float | int:
        degree = self.degree.evaluate()
        value = self.expression.evaluate()

        if degree == 0:
            raise SyntaxError("Math Error: 0th root is undefined")
        if value == 0:
            return 0

        # 处理负数开方
        if value < 0:
            if degree % 2 == 0:
                raise ValueError("Math Error: even root of negative number is not real")
            else:
                return - pow(abs(value), 1 / degree)

        return pow(value, 1 / degree)

    def to_str(self) -> str:
        return f"deg({self.degree.to_str()})root({self.expression.to_str()})"


class UnaryFunctionNode(Node):
    def __init__(self, name: str, argument: Node):
        self.name = name
        self.argument = argument

    def evaluate(self) -> float:
        arg = self.argument.evaluate()

        if self.name == "ln":
            return math.log(arg)

        elif self.name == "sqrt":
            return math.sqrt(arg)
        elif self.name == "sq":
            return arg ** 2
        elif self.name == "cbrt":
            return math.cbrt(arg)
        elif self.name == "cb":
            return arg ** 3

    def to_str(self) -> str:
        return f"{self.name}({self.argument.to_str()})"


class BinaryFunctionNode(Node):
    def __init__(self, name: str, argument1: Node, argument2: Node):
        self.name = name
        self.argument1 = argument1
        self.argument2 = argument2

    def evaluate(self) -> float:
        arg1 = self.argument1.evaluate()
        arg2 = self.argument2.evaluate()

        if self.name == "log":
            if arg1 <= 0:
                raise SyntaxError("Math Error: antilogarithm should be larger than 0")
            return math.log(arg2, arg1)

        elif self.name == "comb":
            if arg1 < arg2:
                raise SyntaxError("Math Error: r should not be larger than n in nCr")
            return math.comb(arg1, arg2)
        elif self.name == "perm":
            if arg1 < arg2:
                raise SyntaxError("Math Error: r should not be larger than n in nPr")
            return math.perm(arg1, arg2)

    def to_str(self) -> str:
        return f"{self.name}({self.argument1.to_str()}, {self.argument2.to_str()})"


"""the Lexer 词法分析"""


class Token:
    TYPE_NUM = 'NUM'
    TYPE_VAR = 'VAR'
    TYPE_OP = 'OP'
    TYPE_FUNC = 'FUNC'
    TYPE_LPAREN = 'LPAREN'
    TYPE_RPAREN = 'RPAREN'
    TYPE_COMMA = 'COMMA'
    TYPE_EOF = 'EOF'

    def __init__(self, category: str, value: Any):
        self.type = category
        self.value = value


class Lexer:
    def __init__(self, text: str):
        self.text = text
        self.pos = 0  # the position of the pointer
        self.current_char = self.text[0] if self.text else None

    def advance(self):
        self.pos += 1
        self.current_char = self.text[self.pos] if self.pos < len(self.text) else None

    def skip_space(self):
        while self.current_char and (self.current_char.isspace() or self.current_char == '|'):
            self.advance()

    def get_number(self) -> Token:
        num_str = ''
        while self.current_char and (self.current_char.isdigit() or self.current_char == '.'):
            num_str += self.current_char
            self.advance()
        return Token(Token.TYPE_NUM, float(num_str) if '.' in num_str else int(num_str))

    def get_identifier(self) -> Token:
        # 单字符变量与常量
        single_char_vars = {'A', 'B', 'C', 'D', 'E', 'F', 'x', 'y'}
        single_char_consts = {'π', 'e', 'i'}

        if self.current_char in single_char_vars:
            ch = self.current_char
            self.advance()
            return Token(Token.TYPE_VAR, ch)

        if self.current_char in single_char_consts:
            ch = self.current_char
            self.advance()
            return Token(Token.TYPE_VAR, ch)

        # 多字符标识符：函数名或 perm/comb
        id_str = ''
        while self.current_char and (self.current_char.isalpha() or self.current_char == '_'):
            id_str += self.current_char
            self.advance()

        funcs = ['sin', 'cos', 'tan', 'ln', 'arcsin', 'arccos', 'arctan',
                 'root', 'deg', 'log', 'base']
        if id_str in funcs:
            return Token(Token.TYPE_FUNC, id_str)
        elif id_str in ('perm', 'comb'):
            return Token(Token.TYPE_OP, id_str)
        else:
            raise SyntaxError(f'Unexpected id {id_str}')

    def get_tokens(self) -> Token | None:
        while self.current_char:
            if self.current_char.isspace() or self.current_char == '|':
                self.skip_space()
                continue
            if self.current_char.isdigit() or self.current_char == '.':
                return self.get_number()
            if self.current_char.isalpha():
                return self.get_identifier()
            if self.current_char == '(':
                self.advance()
                return Token(Token.TYPE_LPAREN, '(')
            if self.current_char == ')':
                self.advance()
                return Token(Token.TYPE_RPAREN, ')')
            if self.current_char == ',':
                self.advance()
                return Token(Token.TYPE_COMMA, ',')
            if self.current_char in ['+', '-', '*', '/', '^', '!']:
                op = self.current_char
                self.advance()
                return Token(Token.TYPE_OP, op)
            raise SyntaxError(f"Unexpected character: {self.current_char}")
        return None


"""the Parser 语法分析"""


class Parser:

    def __init__(self, lexer: Lexer, angle_unit: str = "DEG"):
        self.lexer = lexer
        self.angle_unit = angle_unit

        self.current_token = lexer.get_tokens()
        # 用于存储变量值（由外部注入）
        self.variables = {}
        self.ans = 0.0
        self.context = {}  # 存储变量上下文

    def eat(self, token_type: str):
        if self.current_token and self.current_token.type == token_type:
            self.current_token = self.lexer.get_tokens()
        else:
            token_repr = self.current_token.value if self.current_token else 'EOF'
            raise SyntaxError(f"Expected {token_type}, got {token_repr}")

    def expr(self) -> Node:
        node = self.term()

        while self.current_token and self.current_token.type == Token.TYPE_OP and self.current_token.value in ['+',
                                                                                                               '-']:
            op = self.current_token.value  # 记录运算符
            self.eat('OP')  # 消费运算符
            right = self.term()  # 解析右边的 term
            node = BinaryOpNode(node, right, op)  # 构建树节点

        return node

    def term(self) -> Node:
        node = self.factor()
        while self.current_token:
            # 1. 显式乘除
            if (self.current_token.type == Token.TYPE_OP and
                    self.current_token.value in ('*', '/')):
                op = self.current_token.value
                self.eat('OP')
                right = self.factor()
                if op == '/':
                    node = FractionNode(node, right) if (
                            isinstance(node, Node) and isinstance(right, Node)) else BinaryOpNode(node, right, '/')
                else:
                    node = BinaryOpNode(node, right, '*')
            # 2. 隐式乘法 (数字、变量、函数、左括号)
            elif self.current_token.type in (Token.TYPE_NUM, Token.TYPE_VAR, Token.TYPE_FUNC, Token.TYPE_LPAREN):
                right = self.factor()
                node = BinaryOpNode(node, right, '*')

            else:
                break
        return node

    def factor(self) -> Node:
        token = self.current_token

        # ====== 一级处理 ======

        # 一元负号
        if token and token.type == 'OP' and token.value == '-':
            self.eat('OP')
            node = self.factor()
            node = NegativeNode(node)

        # 数字
        elif token and token.type == 'NUM':
            self.eat('NUM')
            node = DecimalNode(token.value) if token.value % 1 > 0 else IntegerNode(token.value)

        # 变量
        elif token and token.type == 'VAR':
            self.eat('VAR')
            node = VariableNode(token.value)
            # 变量后紧跟函数或左括号的隐式乘法在 term 中处理，此处不重复

        # 括号
        elif token and token.type == 'LPAREN':
            self.eat('LPAREN')
            node = self.expr()
            self.eat('RPAREN')

        # 函数
        elif token and token.type == 'FUNC':
            node = self.parse_function(token)

        else:
            raise SyntaxError(...)

        # ====== 二级处理 ======

        # 幂运算符（右结合）
        if self.current_token and self.current_token.type == 'OP' and self.current_token.value == '^':
            self.eat('OP')
            right = self.factor()  # 递归处理右操作数
            node = PowerNode(node, right)

        # 处理后缀运算符（前瞻）
        while self.current_token and self.current_token.type == 'OP' and self.current_token.value == '!':
            self.eat('OP')
            node = BinaryFunctionNode('perm', node, node)  # 用 perm(n,n) 实现阶乘
        while self.current_token and self.current_token.type == 'OP' and self.current_token.value in ('perm', 'comb'):
            op = self.current_token.value
            self.eat('OP')
            right = self.factor()
            node = BinaryFunctionNode(op, node, right)

        return node

    def parse_function(self, token: Token) -> Node:
        func_type = token.type
        func_name = token.value

        if func_name in ['sin', 'cos', 'tan', 'arcsin', 'arccos', 'arctan', 'ln']:
            self.eat(func_type)
            if self.current_token and self.current_token.type == 'LPAREN':
                self.eat('LPAREN')
                arg = self.expr()
                self.eat('RPAREN')
                return TriangleFunctionNode(func_name, arg, self.angle_unit)
            else:
                arg = self.factor()
                return TriangleFunctionNode(func_name, arg, self.angle_unit)

        elif func_name == 'root':
            self.eat(func_type)
            self.eat(Token.TYPE_LPAREN)
            arg = self.expr()
            self.eat(Token.TYPE_RPAREN)
            return RootNode(IntegerNode(2), arg)
        elif func_name == 'deg':
            self.eat(func_type)

            self.eat(Token.TYPE_LPAREN)
            degree_node = self.expr()
            self.eat(Token.TYPE_RPAREN)

            if self.current_token and self.current_token.type == 'FUNC' and self.current_token.value == 'root':
                self.eat('FUNC')
                self.eat('LPAREN')
                arg = self.expr()
                self.eat('RPAREN')
                return RootNode(degree_node, arg)
            else:
                raise SyntaxError("Expected 'root' after degree expression")

        elif func_name == 'base':
            self.eat(func_type)

            self.eat(Token.TYPE_LPAREN)
            base_node = self.expr()
            self.eat(Token.TYPE_RPAREN)

            if self.current_token and self.current_token.type == 'FUNC' and self.current_token.value == 'log':
                self.eat('FUNC')
                self.eat(Token.TYPE_LPAREN)
                antilog_node = self.expr()
                self.eat(Token.TYPE_RPAREN)
                return BinaryFunctionNode('log', base_node, antilog_node)

        raise SyntaxError(f"Unknown function type: {func_type}")


""" Engine 计算引擎 """


class Engine:
    def __init__(self, calculator=None):
        self.calculator = calculator
        self.variables = {
            'ans': 0.0,
            'x': 0.0, 'y': 0.0,
            'a': 0.0, 'b': 0.0, 'c': 0.0, 'd': 0.0, 'e': 0.0, 'f': 0.0,
            'm': 0.0
        }
        self.settings = self.calculator.settings.settings  # DEG / RAD / GRA

        self.angle_unit = self.settings["angle_unit"]

    def set_variable(self, name: str, value: float):
        self.variables[name.lower()] = value

    def get_variable(self, name: str) -> float:
        return self.variables.get(name.lower(), 0.0)

    def set_angle_unit(self, unit: str):
        """设置角度单位"""
        if unit in ['DEG', 'RAD', 'GRA']:
            self.angle_unit = unit

    def parse(self, expression: str) -> Node:
        """解析表达式，返回 AST"""
        # 预处理
        expr = expression
        expr = expr.replace('×', '*').replace('÷', '/')
        expr = expr.replace('²', '^2').replace('³', '^3')

        # 词法分析
        lexer = Lexer(expr)
        parser = Parser(lexer, self.angle_unit)

        # 注入上下文
        parser.variables = self.variables
        parser.ans = self.variables.get('ans', 0.0)
        parser.context = {
            'variables': self.variables,
            'ans': self.variables.get('ans', 0.0),
            'angle_unit': self.angle_unit
        }

        return parser.expr()  # 直接调用 expr() 解析

    def evaluate(self, expression: str) -> tuple:
        """
        解析并计算表达式
        返回: (结果, 错误信息)
        """
        if not expression or expression.strip() == '':
            return 0.0, None

        try:
            # 1. 解析 → AST
            ast = self.parse(expression)

            # 2. 求值
            result = ast.evaluate()

            # 3. 格式化
            if isinstance(result, float):
                if result.is_integer():
                    result = int(result)
                else:
                    # 避免浮点精度问题
                    result = round(result, 12)
                    # 如果四舍五入后变成整数，转为 int
                    if result.is_integer():
                        result = int(result)

            # 4. 更新 ans
            self.variables['ans'] = float(result) if isinstance(result, (int, float)) else 0

            return result, None

        except ZeroDivisionError:
            return 'Math Error', '除以零'
        except ValueError as e:
            return 'Value Error', str(e)
        except SyntaxError as e:
            return 'Syntax Error', str(e)
        except Exception as e:
            return 'Error', str(e)

    def get_display_string(self, expression: str) -> str:
        """获取表达式的自然显示字符串"""
        try:
            ast = self.parse(expression)
            return ast.to_str()
        except:
            return expression

    def get_ast(self, expression: str) -> Node | None:
        """获取 AST（用于调试）"""
        try:
            return self.parse(expression)
        except:
            return None
