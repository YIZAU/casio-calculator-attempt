class FormulaNode:
    TYPE_NUMBER = "number"
    TYPE_VARIABLE = "variable"
    TYPE_SIGN = "sign"
    TYPE_FUNCTION = "function"
    TYPE_FRACTION = "fraction"

    TYPE_POWER_START = "power_start"
    TYPE_POWER_END = "power_end"

    TYPE_ROOT_DEGREE = "root_degree"
    TYPE_ROOT_START = "root_start"
    TYPE_ROOT_END = "root_end"

    TYPE_LOG_BASE = "log_base"
    TYPE_LOG_START = "log_start"
    TYPE_LOG_END = "log_end"

    def __init__(self, text: str, node_type: str):
        self.text = text
        self.node_type = node_type

    def to_str(self) -> str:
        return self.text

    def is_number(self) -> bool:
        return self.node_type == self.TYPE_NUMBER

    def is_structure_marker(self) -> bool:
        return self.node_type in [self.TYPE_POWER_START, self.TYPE_POWER_END]


class FormulaList:
    def __init__(self, calculator):
        self.calculator = calculator
        self.nodes: list[FormulaNode] = []
        self.index: int = 0

    def insert_at_index(self, node: FormulaNode):
        self.nodes.insert(self.index, node)
        self.index += 1

    def clear(self):
        self.nodes = []
        self.index = 0

    def delete(self):
        if self.index > 0:

            if self._delete_power():
                return
            elif self._delete_root():
                return
            elif self._delete_logarithm():
                return

            # ====== 智能删除 func( 的形式 =====
            if self.nodes[self.index - 1].text == '(':
                if self.index > 1 and self.nodes[self.index - 2].node_type == FormulaNode.TYPE_FUNCTION:
                    self.index -= 2
                    del self.nodes[self.index:self.index + 2]
                    return

            #  ===== 普通删除的默认目标是 self.nodes[self.index - 1] ,也就是光标左侧最近的一项 =====
            self.index -= 1
            del self.nodes[self.index]

    def add_number(self, num: str):
        self.insert_at_index(FormulaNode(num, FormulaNode.TYPE_NUMBER))

    def add_variable(self, name: str):
        self.insert_at_index(FormulaNode(name, FormulaNode.TYPE_VARIABLE))

    def add_sign(self, op: str):
        self.insert_at_index(FormulaNode(op, FormulaNode.TYPE_SIGN))

    def add_power(self, base: str = None, exp: str = None):
        # 要保证配套的 PowerStart 和 PowerEnd 同时存在

        if base:
            if base == 'e':
                self.insert_at_index(FormulaNode('e', FormulaNode.TYPE_VARIABLE))
            elif base == "10":
                self.insert_at_index(FormulaNode("10", FormulaNode.TYPE_NUMBER))

        self.insert_at_index(FormulaNode("^(", FormulaNode.TYPE_POWER_START))

        if exp:
            self.insert_at_index(FormulaNode(exp, FormulaNode.TYPE_NUMBER))
            self.insert_at_index(FormulaNode(')', FormulaNode.TYPE_POWER_END))
            return  # 指定指数时，跳出幂

        self.insert_at_index(FormulaNode(')', FormulaNode.TYPE_POWER_END))
        self.index -= 1  # 未指定指数时，指针回到指数上

    def add_root(self, degree: int = None, sqrt: bool = True):
        if sqrt:
            self.insert_at_index(FormulaNode("root(", FormulaNode.TYPE_ROOT_START))
            self.insert_at_index(FormulaNode(')', FormulaNode.TYPE_ROOT_END))
            self.index -= 1
        else:
            if degree:
                self.insert_at_index(FormulaNode("deg(", FormulaNode.TYPE_ROOT_DEGREE))
                # degree 的值: 2 | 3 | None
                self.insert_at_index(FormulaNode(str(degree), FormulaNode.TYPE_NUMBER))
                self.insert_at_index(FormulaNode(")root(", FormulaNode.TYPE_ROOT_START))
                self.insert_at_index(FormulaNode(')', FormulaNode.TYPE_ROOT_END))
                self.index -= 1
            else:
                if self.index > 0 and self.nodes[self.index - 1].node_type in (FormulaNode.TYPE_NUMBER, FormulaNode.TYPE_VARIABLE):
                    deg_start = self._find_continuous_value_before_cursor()
                    now_index = self.index

                    self.index = deg_start
                    self.insert_at_index(FormulaNode("deg(", FormulaNode.TYPE_ROOT_DEGREE))
                    self.index = now_index + 1
                    self.insert_at_index(FormulaNode(")root(", FormulaNode.TYPE_ROOT_START))
                    self.insert_at_index(FormulaNode(')', FormulaNode.TYPE_ROOT_END))
                    self.index -= 1
                else:
                    self.insert_at_index(FormulaNode("deg(", FormulaNode.TYPE_ROOT_DEGREE))
                    self.insert_at_index(FormulaNode(")root(", FormulaNode.TYPE_ROOT_START))
                    self.insert_at_index(FormulaNode(')', FormulaNode.TYPE_ROOT_END))
                    self.index -= 2


    def add_logarithm(self):
        self.insert_at_index(FormulaNode("base(", FormulaNode.TYPE_LOG_BASE))
        self.insert_at_index(FormulaNode(")log(", FormulaNode.TYPE_LOG_START))
        self.insert_at_index(FormulaNode(')', FormulaNode.TYPE_LOG_END))
        self.index -= 2

    def add_function(self, func_name: str):
        self.insert_at_index(FormulaNode(func_name, FormulaNode.TYPE_FUNCTION))
        self.insert_at_index(FormulaNode('(', FormulaNode.TYPE_SIGN))

    def to_str(self) -> str:
        return "".join(node.to_str() for node in self.nodes)

    def move_right(self):
        if self.index < len(self.nodes):
            self.index += 1
        elif self.index == len(self.nodes):
            self.index = 0

    def move_left(self):
        if self.index > 0:
            self.index -= 1
        elif self.index == 0:
            self.index = len(self.nodes)

    def _delete_power(self) -> bool:
        # ===== 智能删除 幂 ======

        # 指针前是 PowerEnd
        if self.nodes[self.index - 1].node_type == FormulaNode.TYPE_POWER_END:
            self.index -= 1
            while self.nodes[self.index].node_type == FormulaNode.TYPE_POWER_END:
                self.index -= 1
            # 该级指数为空，删去该级幂结构
            if self.nodes[self.index].node_type == FormulaNode.TYPE_POWER_START:
                del self.nodes[self.index]  # 删除 PowerStart
                del self.nodes[self.index]  # 删除 PowerEnd
                return True
            # 该级指数非空，找到并删除第一个指数 Node
            else:
                del self.nodes[self.index]
                return True

        # 指针前是 PowerStart
        elif self.nodes[self.index - 1].node_type == FormulaNode.TYPE_POWER_START:
            # 该级指数为空，删去该级幂结构
            if self.nodes[self.index] and self.nodes[self.index].node_type == FormulaNode.TYPE_POWER_END:
                del self.nodes[self.index]
                self.index -= 1
                del self.nodes[self.index]
                return True
            # 该级指数非空，该级幂的指数合并到该级底数中
            else:
                # 先删除该级的 PowerStart
                self.index -= 1
                del self.nodes[self.index]

                # 找到并删除 PowerEnd
                del self.nodes[self._find_matching_power_end(self.index)]
                return True
        return False

    def _find_matching_power_end(self, start_index: int) -> int:
        depth = 1
        i = start_index + 1
        while i < len(self.nodes):
            if self.nodes[i].node_type == FormulaNode.TYPE_POWER_START:
                depth += 1
            elif self.nodes[i].node_type == FormulaNode.TYPE_POWER_END:
                depth -= 1
                if depth == 0:
                    return i
            i += 1

    def _delete_root(self) -> bool:
        # ===== 智能删除 根式 ======

        # 指针前是 RootDegree
        if self.nodes[self.index - 1].node_type == FormulaNode.TYPE_ROOT_DEGREE:
            # 根系数为空，取消根号，根式放出
            if self.nodes[self.index].node_type == FormulaNode.TYPE_ROOT_START:
                # 只需找到配套的 RootEnd
                rt_end = self._find_root_end_with_root_start(self.index)
                del self.nodes[rt_end]
                del self.nodes[self.index]  # 删除 RootStart
                self.index -= 1
                del self.nodes[self.index]  # 删除 RootDegree
            # 根系数非空，删除根系数最左侧 Node
            else:
                del self.nodes[self.index]
            return True

        # 指针前是 RootStart
        elif self.nodes[self.index - 1].node_type == FormulaNode.TYPE_ROOT_START:
            # 取消根号，根系数和根式放出
            rt_end = self._find_root_end_with_root_start(self.index - 1)
            rt_deg = self._find_root_degree_with_root_start(self.index - 1)
            del self.nodes[rt_end]
            self.index -= 1
            del self.nodes[self.index]  # 删除 RootStart
            if rt_deg != -1:
                del self.nodes[rt_deg]
                self.index -= 1  # 索引复位
            return True

        # 指针前是 RootEnd
        elif self.nodes[self.index - 1].node_type == FormulaNode.TYPE_ROOT_END:
            # 根式为空，取消根号，根系数放出
            if self.nodes[self.index - 2].node_type == FormulaNode.TYPE_ROOT_START:
                rt_deg = self._find_root_degree_with_root_start(self.index - 2)
                self.index -= 1
                del self.nodes[self.index]  # 删除 RootEnd
                self.index -= 1
                del self.nodes[self.index]  # 删除 RootStart
                if rt_deg != -1:
                    del self.nodes[rt_deg]
                    self.index -= 1  # 索引复位
            # 根式非空，删除根系数最右侧 Node
            else:
                self.index -= 2
                del self.nodes[self.index]
            return True
        return False

    def _find_root_end_with_root_start(self, rt_start) -> int:
        i = rt_start
        depth = 0
        while i < len(self.nodes):
            i += 1
            if self.nodes[i].node_type == FormulaNode.TYPE_ROOT_START:
                depth += 1
            elif self.nodes[i].node_type == FormulaNode.TYPE_ROOT_END:
                if depth > 0:
                    depth -= 1
                else:
                    return i

    def _find_root_degree_with_root_start(self, rt_start) -> int:
        i = rt_start - 1
        depth = 0
        while i >= 0:
            if self.nodes[i].node_type == FormulaNode.TYPE_ROOT_START:
                depth += 1
            elif self.nodes[i].node_type == FormulaNode.TYPE_ROOT_DEGREE:
                if depth > 0:
                    depth -= 1
                else:
                    return i
            i -= 1
        return -1  # 处理平方根

    def _find_continuous_value_before_cursor(self) -> int:
        i = self.index - 1
        while i >= 0 and self.nodes[i].node_type in (FormulaNode.TYPE_NUMBER, FormulaNode.TYPE_VARIABLE):
            i -= 1
        return i + 1

    def _delete_logarithm(self) -> bool:
        # ===== 智能删除 对数 ======

        # 指针前是 LogBase, 删除整个函数只保留真数
        if self.nodes[self.index - 1].node_type == FormulaNode.TYPE_LOG_BASE:
            log_start, log_end = self._find_log_pair_with_log_base(self.index - 1)
            del self.nodes[log_end]
            del self.nodes[self.index - 1: log_start + 1]
            return True

        # 指针前是 LogStart
        elif self.nodes[self.index - 1].node_type == FormulaNode.TYPE_LOG_START:
            # 底数与真数全为空，全部删除
            if self.nodes[self.index].node_type == FormulaNode.TYPE_LOG_END and self.nodes[self.index - 2].node_type == FormulaNode.TYPE_LOG_BASE:
                self.index -= 2
                del self.nodes[self.index: self.index + 3]
            # 底数与真数非全为空，底数为空，光标移至底数，不删除
            elif self.nodes[self.index - 2].node_type == FormulaNode.TYPE_LOG_BASE:
                self.index -= 1
            # 底数与真数非全为空，底数存在，删除底数最右侧 Node
            else:
                self.index -= 2
                del self.nodes[self.index]
            return True

        # 指针前是 LogEnd
        elif self.nodes[self.index - 1].node_type == FormulaNode.TYPE_LOG_END:
            # 底数与真数全为空，全部删除
            if self.nodes[self.index - 2].node_type == FormulaNode.TYPE_LOG_START and self.nodes[self.index - 3].node_type == FormulaNode.TYPE_LOG_BASE:
                self.index -= 3
                del self.nodes[self.index: self.index + 3]
            # 底数与真数非全为空，真数为空，光标移至真数，不删除
            elif self.nodes[self.index - 2].node_type == FormulaNode.TYPE_LOG_START:
                self.index -= 1
            # 底数与真数非全为空，真数存在，删除真数最右侧 Node
            else:
                self.index -= 2
                del self.nodes[self.index]
            return True
        return False

    def _find_log_pair_with_log_base(self, log_base) -> tuple[int, int]:
        i = j = log_base + 1
        depth = 0
        while i < len(self.nodes):
            if self.nodes[i].node_type == FormulaNode.TYPE_LOG_START:
                if depth == 0:
                    j = i
                else:
                    depth += 1
            elif self.nodes[i].node_type == FormulaNode.TYPE_LOG_END:
                if depth > 0:
                    depth -= 1
                else:
                    return j, i
            i += 1

    def refresh(self):
        displayer = getattr(self.calculator, "displayer", None)
        if displayer is not None:
            displayer.render()


class History:
    def __init__(self, controller):
        self.controller = controller

        self.index = -1
        self.log = []

    def save(self, formulas: str):
        self.log.append(formulas)
        self.index = -1

    def _forward(self):
        if self.index < -1:
            self.index += 1

    def _backward(self):
        if self.index > -1 * len(self.log):
            self.index -= 1

    def clear(self):
        self.index = -1
        self.log = []


class Controller:
    def __init__(self, calculator, formulas: FormulaList):
        from main import Calculator
        self.calculator: Calculator = calculator
        self.states = self.calculator.settings
        self.formulas = formulas

        self.history = History(self)

        self._INPUT_TABLE = {
            ("normal", "0"): (self.formulas.add_number, ("0",)),
            ("normal", "."): (self.formulas.add_number, (".",)),
            ("normal", "1"): (self.formulas.add_number, ("1",)),
            ("normal", "2"): (self.formulas.add_number, ("2",)),
            ("normal", "3"): (self.formulas.add_number, ("3",)),
            ("normal", "4"): (self.formulas.add_number, ("4",)),
            ("normal", "5"): (self.formulas.add_number, ("5",)),
            ("normal", "6"): (self.formulas.add_number, ("6",)),
            ("normal", "7"): (self.formulas.add_number, ("7",)),
            ("normal", "8"): (self.formulas.add_number, ("8",)),
            ("normal", "9"): (self.formulas.add_number, ("9",)),
            ("normal", "+"): (self.formulas.add_sign, ("+",)),
            ("normal", "-"): (self.formulas.add_sign, ("-",)),
            ("normal", "*"): (self.formulas.add_sign, ("*",)),
            ("normal", "/"): (self.formulas.add_sign, ("/",)),
            ("normal", "("): (self.formulas.add_sign, ("(",)),
            ("normal", ")"): (self.formulas.add_sign, (")",)),
            ("normal", "SIN"): (self.formulas.add_function, ("sin",)),
            ("normal", "COS"): (self.formulas.add_function, ("cos",)),
            ("normal", "TAN"): (self.formulas.add_function, ("tan",)),
            ("normal", "LN"): (self.formulas.add_function, ("ln",)),
            ("normal", "LOG"): (self.formulas.add_logarithm, ()),
            ("normal", "SQR"): (self._deal_power, ("square",)),
            ("normal", "POW"): (self._deal_power, ("power",)),
            ("normal", "EXP"): (self._deal_power, ("x10^",)),
            ("normal", "INV"): (self._deal_power, ("f^-1",)),
            ("normal", "SQRT"): (self.formulas.add_root, (None,)),
            ("normal", "X"): (self.formulas.add_variable, ("x",)),

            ("shift", "EXP"): (self.formulas.add_variable, ("π",)),
            ("shift", "SIN"): (self.formulas.add_function, ("arcsin",)),
            ("shift", "COS"): (self.formulas.add_function, ("arccos",)),
            ("shift", "TAN"): (self.formulas.add_function, ("arctan",)),
            ("shift", "SQR"): (self._deal_power, ("cube",)),
            ("shift", "LN"): (self._deal_power, ("e^",)),
            ("shift", "LOG"): (self._deal_power, ("10^",)),
            ("shift", "SQRT"): (self.formulas.add_root, (3, False)),
            ("shift", "POW"): (self.formulas.add_root, (None, False)),
            ("shift", "INV"): (self.formulas.add_sign, ("!",)),
            ("shift", "*"): (self.formulas.add_sign, ("perm",)),
            ("shift", "/"): (self.formulas.add_sign, ("comb",)),

            ("alpha", "EXP"): (self.formulas.add_variable, ("e",)),
            ("alpha", "NEG"): (self.formulas.add_variable, ("A",)),
            ("alpha", "DMS"): (self.formulas.add_variable, ("B",)),
            ("alpha", "INV"): (self.formulas.add_variable, ("C",)),
            ("alpha", "SIN"): (self.formulas.add_variable, ("D",)),
            ("alpha", "COS"): (self.formulas.add_variable, ("E",)),
            ("alpha", "TAN"): (self.formulas.add_variable, ("F",)),
            ("alpha", ")"): (self.formulas.add_variable, ("x",)),
            ("alpha", "S2D"): (self.formulas.add_variable, ("y",)),
            ("alpha", "M_PLUS"): (self.formulas.add_variable, ("M",)),
        }

    def handle_input(self, key_name: str, shift_mode=False, alpha_mode=False):
        current_mode = "normal"
        if shift_mode:
            current_mode = "shift"
        if alpha_mode:
            current_mode = "alpha"

        func, args = self._INPUT_TABLE.get((current_mode, key_name), None)
        if func is None:
            return
        func(*args)

        self.formulas.refresh()

    def _deal_power(self, msg: str):
        # 不允许连续幂
        if msg in ["square", "cube", "power", "f^-1", "x10^"]:
            if (self.formulas.index > 0 and
                    self.formulas.nodes[self.formulas.index - 1].node_type in (
                            FormulaNode.TYPE_POWER_END, FormulaNode.TYPE_POWER_START)):
                return
        if msg == "square":
            self.formulas.add_power(exp='2')
        elif msg == "cube":
            self.formulas.add_power(exp='3')
        elif msg == "e^":
            self.formulas.add_power(base='e')
        elif msg == "10^":
            self.formulas.add_power(base='10')
        elif msg == "power":
            self.formulas.add_power()
        elif msg == "x10^":
            self.formulas.add_sign('*')
            self.formulas.add_power(base='10')
        elif msg == "f^-1":
            self.formulas.add_power(exp='-1')

    def move_cursor(self, msg: str):
        if msg == "RIGHT":
            self.formulas.move_right()
        elif msg == "LEFT":
            self.formulas.move_left()
        elif msg == "UP":
            pass
        elif msg == "DOWN":
            pass

        self.formulas.refresh()

    def save_history(self, formulas: str):
        self.history.save(formulas)

    def clear(self):
        self.formulas.clear()
        self.formulas.refresh()

    def delete(self):
        self.formulas.delete()

        self.formulas.refresh()

    def get_expression(self) -> str:
        return self.formulas.to_str()
