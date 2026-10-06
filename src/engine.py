from mathematics import *

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
            node = CombinatoricNode(node, node, comb=False)  # 用 perm(n,n) 实现阶乘
        while self.current_token and self.current_token.type == 'OP' and self.current_token.value in ('perm', 'comb'):
            op = self.current_token.value
            self.eat('OP')
            right = self.factor()
            node = CombinatoricNode(node, right) if op == "comb" else CombinatoricNode(node, right, comb=False)

        return node

    def parse_function(self, token: Token) -> Node:
        func_type = token.type
        func_name = token.value

        if func_name in ['sin', 'cos', 'tan']:
            self.eat(func_type)
            if self.current_token and self.current_token.type == 'LPAREN':
                self.eat('LPAREN')
                arg = self.expr()
                self.eat('RPAREN')
                return TrigNode(func_name, arg)
            else:
                arg = self.factor()
                return TrigNode(func_name, arg)

        elif func_name in ['arcsin', 'arccos', 'arctan']:
            self.eat(func_type)
            if self.current_token and self.current_token.type == 'LPAREN':
                self.eat('LPAREN')
                arg = self.expr()
                self.eat('RPAREN')
                return ArcTrigNode(func_name, arg)
            else:
                arg = self.factor()
                return ArcTrigNode(func_name, arg)

        elif func_name == "ln":
            self.eat(func_type)
            self.eat(Token.TYPE_LPAREN)
            arg = self.expr()
            self.eat(Token.TYPE_RPAREN)
            return LogNode(arg)

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
                return LogNode(antilog_node, base_node)

        raise SyntaxError(f"Unknown function type: {func_type}")


""" Engine 计算引擎 """


class Engine:
    def __init__(self, calculator=None):
        from main import Calculator
        self.calculator: Calculator = calculator
        self.ans = None

    def parse(self, expression: str) -> Node:
        """解析表达式，返回 AST"""
        # 预处理
        expr = expression
        expr = expr.replace('×', '*').replace('÷', '/')
        expr = expr.replace('²', '^2').replace('³', '^3')

        # 词法分析
        lexer = Lexer(expr)
        parser = Parser(lexer)

        # 注入上下文
        # parser.variables = self.variables
        # parser.ans = self.variables.get('Ans', 0.0)
        # parser.context = {
        #     'variables': self.variables,
        #     'Ans': self.variables.get('Ans', 0.0),
        #     'angle_unit': self.angle_unit
        # }

        return parser.expr()  # 直接调用 expr() 解析

    def evaluate(self, expression: str) -> tuple:
        if not expression or expression.strip() == '':
            return IntegerNode(0), None

        try:

            # 1. Parser → AST
            ast = self.parse(expression)

            # 2. simplify the result AST
            result = ast.simplify(env=self.package_environment())
            print(result)    # temporary display, used for debugging

            # 3. update tha history
            formulas = result.to_str()

            return formulas, None

        except ZeroDivisionError:
            return 'Math Error', '除以零'
        except ValueError as e:
            return 'Value Error', str(e)
        except SyntaxError as e:
            return 'Syntax Error', str(e)
        except Exception as e:
            return 'Error', str(e)

    def package_environment(self) -> dict:
        env = {}
        for variable_name, formulas in self.calculator.settings.variables.items():
            # print(variable_name, formulas)
            env[variable_name] = self.parse(formulas)
        env["angle_unit"] = self.calculator.settings.settings["angle_unit"]
        return env

    def get_ast(self, expression: str) -> Node | None:
        """获取 AST（用于调试）"""
        try:
            return self.parse(expression)
        except:
            return None
