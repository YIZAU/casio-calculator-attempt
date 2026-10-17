import tkinter as tk


class Screen:
    FONT_EXPR = ('Segoe UI', 18)
    FONT_RESULT = ('Segoe UI', 16)

    COLOR_BG = '#d5e3d4'
    COLOR_EXPR = 'black'
    COLOR_RESULT = '#333333'
    COLOR_CURSOR = '#0055aa'
    name = "undefined"

    def render(self):
        raise NotImplementedError


class InputFormulaScreen(Screen):
    name = "formula"

    def __init__(self, canvas, formulas):
        self.canvas = canvas
        self.formulas = formulas
        self._result_text = None  # 右下角结果
        self._feedback_text = None  # 主区域覆盖

    def show_result(self, text):
        self._result_text = str(text) if text is not None else None

    def show_feedback(self, text):
        """把反馈文本作为主画布内容显示（覆盖公式区域）。"""
        self._feedback_text = str(text) if text is not None else None

    def clear_feedback(self):
        self._feedback_text = None

    def has_feedback(self) -> bool:
        return self._feedback_text is not None

    def has_result(self) -> bool:
        return self._result_text is not None

    def render(self):
        self.canvas.delete('all')

        if self._feedback_text is not None:
            # 主区域：显示反馈文本
            self.canvas.create_text(
                8, 10, anchor='nw', text=self._feedback_text,
                font=self.FONT_EXPR, fill=self.COLOR_EXPR,
            )
        else:
            # 主区域：正常渲染公式 + 光标
            left, right = self._split_by_cursor()
            x, y = 8, 10

            left_id = self.canvas.create_text(
                x, y, anchor='nw', text=left,
                font=self.FONT_EXPR, fill=self.COLOR_EXPR,
            )
            bbox = self.canvas.bbox(left_id)
            cursor_x = bbox[2] if bbox else x

            self.canvas.create_text(
                cursor_x, y, anchor='nw', text='|',
                font=self.FONT_EXPR, fill=self.COLOR_CURSOR,
            )
            self.canvas.create_text(
                cursor_x + 1, y, anchor='nw', text=right,
                font=self.FONT_EXPR, fill=self.COLOR_EXPR,
            )

        # 右下角结果区域（独立于反馈）
        if self._result_text is not None:
            self.canvas.create_text(
                352, 122, anchor='se', text=self._result_text,
                font=self.FONT_RESULT, fill=self.COLOR_RESULT,
            )

    def _split_by_cursor(self):
        nodes = self.formulas.nodes
        idx = self.formulas.index
        return (
            ''.join(n.to_str() for n in nodes[:idx]),
            ''.join(n.to_str() for n in nodes[idx:]),
        )


class VariableScreen(Screen):
    name = "variable"

    LEFT_COL = ["A", "C", "E", "M", "y"]
    RIGHT_COL = ["B", "D", "F", "x"]
    ROW_COUNT = 5

    PADDING_X = 10
    PADDING_Y = 8
    COL_SPLIT = 0.5  # 两列的分割比例

    FONT_FAMILY = "Courier New"
    FONT_MIN = 8
    FONT_MAX = 20

    def __init__(self, canvas: tk.Canvas, variables: dict):
        self.variables = variables
        self.canvas = canvas

    def render(self):
        self.canvas.delete("all")

        w, h = self._get_canvas_size()
        font = self._compute_font(h)

        line_height = (h - 2 * self.PADDING_Y) / self.ROW_COUNT
        split_x = int(w * self.COL_SPLIT)

        # left column
        for i, var in enumerate(self.LEFT_COL):
            y = self.PADDING_Y + i * line_height
            self._draw_var(self.PADDING_X, y, var, font)

        # right column
        for i, var in enumerate(self.RIGHT_COL):
            y = self.PADDING_Y + i * line_height
            self._draw_var(split_x, y, var, font)

    def _draw_var(self, x, y, var, font):
        value = self._get_value(var)
        text = f"{var}={value}"
        self.canvas.create_text(
            x, y, anchor='nw', text=text,
            font=font, fill='black',
        )

    def _get_value(self, var):
        value = self.variables.get(var)
        if value is None:
            return "0"
        return str(value)

    def _get_canvas_size(self):
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w <= 1:
            w = int(self.canvas['width'])
        if h <= 1:
            h = int(self.canvas['height'])
        return w, h

    def _compute_font(self, h):
        row_height = (h - 2 * self.PADDING_Y) / self.ROW_COUNT
        size = int(row_height * 0.6)
        size = max(self.FONT_MIN, min(size, self.FONT_MAX))
        return self.FONT_FAMILY, size


class ErrorScreen(Screen):
    name = "error"

    FONT_ERROR = ('Segoe UI', 18, 'bold')
    FONT_HINT = ('Segoe UI', 14)

    COLOR_ERROR = '#333333'
    COLOR_HINT = '#333333'

    def __init__(self, canvas):
        self.canvas = canvas
        self.error_message = ""

    def set_error(self, message: str):
        self.error_message = message

    def render(self):
        self.canvas.delete('all')

        self.canvas.create_text(
            8, 10, anchor='nw', text=self.error_message,
            font=self.FONT_ERROR, fill=self.COLOR_ERROR
        )

        hint_ac = "[AC]      : Cancel"
        hint_goto = "[◀][▶] : Goto"

        self.canvas.create_text(
            8, 70, anchor='nw', text=hint_ac,
            font=self.FONT_HINT, fill=self.COLOR_HINT
        )
        self.canvas.create_text(
            8, 95, anchor='nw', text=hint_goto,
            font=self.FONT_HINT, fill=self.COLOR_HINT
        )


class ChoiceScreen(Screen):
    ITEMS_PER_PAGE = 4
    FONT_FAMILY = "Courier New"
    FONT_MIN = 8
    FONT_MAX = 20
    PADDING_X = 10
    PADDING_Y = 8
    TITLE_HEIGHT = 30
    COLORS = {
        'text': 'black',
        'highlight': '#0055aa',
        'scroll_bg': '#cccccc',
        'scroll_fg': '#0055aa',
    }

    def __init__(self, canvas: tk.Canvas, calculator):
        self.calculator = calculator
        self.canvas = canvas

        self.page = 0
        self.parent_screen = ""
        self.title = ""

        # 子类需要填充 self.items
        # 格式: [("显示文本", 目标字符串或可调用对象), ...]
        self.items = []

    # ---------- 供 Calculator 调用的接口 ----------

    def total_pages(self) -> int:
        return max(1, (len(self.items) + self.ITEMS_PER_PAGE - 1) // self.ITEMS_PER_PAGE)

    def page_up(self):
        self.page = (self.page - 1) % self.total_pages()

    def page_down(self):
        self.page = (self.page + 1) % self.total_pages()

    def select(self, num: int):
        idx_in_page = num - 1
        global_idx = self.page * self.ITEMS_PER_PAGE + idx_in_page

        if global_idx >= len(self.items):
            return

        _, target = self.items[global_idx]

        if callable(target):
            target()
        elif isinstance(target, str):
            self.calculator.screen_manager.switch_current_screen(target)

    # ---------- 渲染 ----------

    def render(self):
        self.canvas.delete('all')
        w, h = self._get_canvas_size()
        font = self._compute_font(h)

        if self.title:
            self.canvas.create_text(
                self.PADDING_X, self.PADDING_Y, anchor='nw',
                text=self.title,
                font=font,
                fill=self.COLORS['text']
            )

        start_idx = self.page * self.ITEMS_PER_PAGE
        end_idx = min(start_idx + self.ITEMS_PER_PAGE, len(self.items))
        current_items = self.items[start_idx:end_idx]

        # 计算剩余可用高度
        available_h = h - 2 * self.PADDING_Y - (self.TITLE_HEIGHT if self.title else 0)
        row_height = available_h / self.ITEMS_PER_PAGE
        item_start_y = self.PADDING_Y + (self.TITLE_HEIGHT if self.title else 0)

        for i, (text, _) in enumerate(current_items):
            y = item_start_y + i * row_height
            display_text = f"{i + 1}: {text}"
            self.canvas.create_text(
                self.PADDING_X, y, anchor='nw', text=display_text,
                font=font, fill=self.COLORS['text']
            )

        self._render_scrollbar(w, h)

    def _render_scrollbar(self, w, h):
        total = self.total_pages()
        if total <= 1:
            return  # 只有一页不需要滚动条

        bar_width = 6
        bar_x = w - bar_width - 5
        bar_top = self.PADDING_Y
        bar_height = h - 2 * self.PADDING_Y
        block_height = bar_height / total

        for i in range(total):
            y1 = bar_top + i * block_height
            y2 = y1 + block_height
            color = self.COLORS['scroll_fg'] if i == self.page else self.COLORS['scroll_bg']
            # 留点间隙
            self.canvas.create_rectangle(
                bar_x, y1 + 1, bar_x + bar_width, y2 - 1,
                fill=color, outline=""
            )

    def _get_canvas_size(self):
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w <= 1:
            w = int(self.canvas['width'])
        if h <= 1:
            h = int(self.canvas['height'])
        return w, h

    def _compute_font(self, h):
        row_height = (h - 2 * self.PADDING_Y) / 4
        size = int(row_height * 0.5)  # 0.5 稍小一点，留出行距
        size = max(self.FONT_MIN, min(size, self.FONT_MAX))
        return self.FONT_FAMILY, size


class SettingAngleScreen(ChoiceScreen):
    name = "setting_angle"

    def __init__(self, canvas: tk.Canvas, calculator):
        super().__init__(canvas, calculator)
        self.parent_screen = "setting"

        self.items = [
            ("Degree(D)", lambda: self.calculator.set_angle_unit("DEG")),
            ("Radian(R)", lambda: self.calculator.set_angle_unit("RAD")),
            ("Gradient(G)", lambda: self.calculator.set_angle_unit("GRA")),
        ]


class SettingIoScreen(ChoiceScreen):
    name = "setting_io"

    def __init__(self, canvas: tk.Canvas, calculator):
        super().__init__(canvas, calculator)
        self.parent_screen = "setting"

        self.items = [
            ("MathI/MathO", lambda: self.calculator.set_setting("io_mode", "MathI/MathO")),
            ("MathI/DecimalO", lambda: self.calculator.set_setting("io_mode", "MathI/DecimalO")),
            ("LineI/LineO", lambda: self.calculator.set_setting("io_mode", "LineI/LineO")),
            ("LineI/DecimalO", lambda: self.calculator.set_setting("io_mode", "LineI/DecimalO")),
        ]


class SettingNumberFormatScreen(ChoiceScreen):
    name = "setting_number_format"

    def __init__(self, canvas: tk.Canvas, calculator):
        super().__init__(canvas, calculator)
        self.parent_screen = "setting"

        self.items = [
            ("Fix", lambda: self.calculator.set_setting("number_format", "FIX")),
            ("Sci", lambda: self.calculator.set_setting("number_format", "SCI")),
            ("Norm", lambda: self.calculator.set_setting("number_format", "NORM"))
        ]


class SettingEngineerSymbolScreen(ChoiceScreen):
    name = "setting_engineer_symbol"

    def __init__(self, canvas: tk.Canvas, calculator):
        super().__init__(canvas, calculator)
        self.parent_screen = "setting"
        self.title = "Engineer Symbol?"

        self.items = [
            ("On", lambda: self.calculator.set_setting("engineer_symbol", True)),
            ("Off", lambda: self.calculator.set_setting("engineer_symbol", False))
        ]


class SettingFractionResultScreen(ChoiceScreen):
    name = "setting_fraction_result"

    def __init__(self, canvas: tk.Canvas, calculator):
        super().__init__(canvas, calculator)
        self.parent_screen = "setting"

        self.items = [
            ("ab/c", lambda: self.calculator.set_setting("fraction_result", "mixed")),
            ("d/c", lambda: self.calculator.set_setting("fraction_result", "improper"))
        ]


class SettingComplexScreen(ChoiceScreen):
    name = "setting_complex"

    def __init__(self, canvas: tk.Canvas, calculator):
        super().__init__(canvas, calculator)
        self.parent_screen = "setting"

        self.items = [
            ("a+bi", lambda: self.calculator.set_setting("complex_format", "rectangular")),
            ("r∠θ", lambda: self.calculator.set_setting("complex_format", "polar")),
        ]


class SettingStatisticsScreen(ChoiceScreen):
    name = "setting_statistics"

    def __init__(self, canvas: tk.Canvas, calculator):
        super().__init__(canvas, calculator)
        self.parent_screen = "setting"
        self.title = "Frequency?"

        self.items = [
            ("On", lambda: self.calculator.set_setting("frequency", True)),
            ("Off", lambda: self.calculator.set_setting("frequency", False)),
        ]


class SettingEquationScreen(ChoiceScreen):
    name = "setting_equation"

    def __init__(self, canvas: tk.Canvas, calculator):
        super().__init__(canvas, calculator)
        self.parent_screen = "setting"
        self.title = "Complex Result?"

        self.items = [
            ("On", lambda: self.calculator.set_setting("equation_complex_result", True)),
            ("Off", lambda: self.calculator.set_setting("equation_complex_result", False)),
        ]


class SettingTableScreen(ChoiceScreen):
    name = "setting_table"

    def __init__(self, canvas: tk.Canvas, calculator):
        super().__init__(canvas, calculator)
        self.parent_screen = "setting"

        self.items = [
            ("f(x)", lambda: self.calculator.set_setting("table_function_count", "single")),
            ("f(x), g(x)", lambda: self.calculator.set_setting("table_function_count", "dual")),
        ]


class SettingDecimalMarkScreen(ChoiceScreen):
    name = "setting_decimal_mark"

    def __init__(self, canvas: tk.Canvas, calculator):
        super().__init__(canvas, calculator)
        self.parent_screen = "setting"

        self.items = [
            ("Dot", lambda: self.calculator.set_setting("decimal_mark", "DOT")),
            ("Comma", lambda: self.calculator.set_setting("decimal_mark", "COMMA")),
        ]


class SettingDigitSeparatorScreen(ChoiceScreen):
    name = "setting_digit_separator"

    def __init__(self, canvas: tk.Canvas, calculator):
        super().__init__(canvas, calculator)
        self.parent_screen = "setting"
        self.title = "Digit Separator?"

        self.items = [
            ("On", lambda: self.calculator.set_setting("digit_separator", True)),
            ("Off", lambda: self.calculator.set_setting("digit_separator", False)),
        ]


class SettingLanguageScreen(ChoiceScreen):
    name = "setting_language"

    def __init__(self, canvas: tk.Canvas, calculator):
        super().__init__(canvas, calculator)
        self.parent_screen = "setting"

        self.items = [
            ("English", lambda: self.calculator.set_setting("language", "EN")),
            ("中文", lambda: self.calculator.set_setting("language", "CH")),
        ]


class SettingScreen(ChoiceScreen):
    name = "setting"

    def __init__(self, canvas: tk.Canvas, calculator):
        super().__init__(canvas, calculator)

        self.items = [
            ("Input/Output", "setting_io"),
            ("Angle Unit", "setting_angle"),
            ("Number Format", "setting_number_format"),
            ("Engineer Symbol", "setting_engineer_symbol"),
            ("Fraction Result", "setting_fraction_result"),
            ("Complex", "setting_complex"),
            ("Statistics", "setting_statistics"),
            ("Equation/Func", "setting_equation"),
            ("Table", "setting_table"),
            ("Decimal Mark", "setting_decimal_mark"),
            ("Digit Separator", "setting_digit_separator"),
            ("Language", "setting_language")
        ]


class ResetScreen(ChoiceScreen):
    name = "reset_menu"

    def __init__(self, canvas: tk.Canvas, calculator):
        super().__init__(canvas, calculator)
        self.title = "Reset?"

        self.items = [
            ("Setup Data", "reset_setup_confirm"),
            ("Memory", "reset_memory_confirm"),
            ("Initialize All", "reset_all_confirm"),
        ]


class ResetConfirmScreen(Screen):
    def __init__(self, canvas, target_name, reset_action, success_screen):
        self.canvas = canvas
        self.target_name = target_name
        self.reset_action = reset_action
        self.success_screen = success_screen

    def render(self):
        self.canvas.delete('all')
        w = int(self.canvas['width'])

        # 顶部居中标题
        self.canvas.create_text(
            w // 2, 15, text="Reset OK?", anchor='n',
            font=('Courier New', 14), fill='black'
        )
        # 左对齐的目标内容
        self.canvas.create_text(
            10, 45, text=self.target_name, anchor='nw',
            font=('Courier New', 14), fill='black'
        )
        # 底部提示
        self.canvas.create_text(
            10, 75, text="[=]     :Yes", anchor='nw',
            font=('Courier New', 14), fill='black'
        )
        self.canvas.create_text(
            10, 100, text="[AC]    :Cancel", anchor='nw',
            font=('Courier New', 14), fill='black'
        )


class ResetSuccessScreen(Screen):
    def __init__(self, canvas, target_name):
        self.canvas = canvas
        self.target_name = target_name

    def render(self):
        self.canvas.delete('all')
        w = int(self.canvas['width'])

        # 顶部居中标题
        self.canvas.create_text(
            w // 2, 15, text="Reset!", anchor='n',
            font=('Courier New', 14), fill='black'
        )
        # 左对齐的目标内容
        self.canvas.create_text(
            10, 45, text=self.target_name, anchor='nw',
            font=('Courier New', 14), fill='black'
        )
        # 底部提示
        self.canvas.create_text(
            10, 95, text="Press [AC] key", anchor='nw',
            font=('Courier New', 14), fill='black'
        )


class ScreenManager:
    def __init__(self, calculator, canvas):
        self.calculator = calculator
        self.canvas = canvas
        self.current_screen = "formula"
        self.screens = {
            "formula": InputFormulaScreen(canvas, calculator.formulas),
            "variable": VariableScreen(canvas, calculator.settings.variables),
            "error": ErrorScreen(canvas),

            "setting": SettingScreen(canvas, calculator),
            "setting_io": SettingIoScreen(canvas, calculator),
            "setting_angle": SettingAngleScreen(canvas, calculator),
            "setting_number_format": SettingNumberFormatScreen(canvas, calculator),
            "setting_engineer_symbol": SettingEngineerSymbolScreen(canvas, calculator),
            "setting_fraction_result": SettingFractionResultScreen(canvas, calculator),
            "setting_complex": SettingComplexScreen(canvas, calculator),
            "setting_statistics": SettingStatisticsScreen(canvas, calculator),
            "setting_equation": SettingEquationScreen(canvas, calculator),
            "setting_table": SettingTableScreen(canvas, calculator),
            "setting_decimal_mark": SettingDecimalMarkScreen(canvas, calculator),
            "setting_digit_separator": SettingDigitSeparatorScreen(canvas, calculator),
            "setting_language": SettingLanguageScreen(canvas, calculator),

            "reset_menu": ResetScreen(canvas, calculator),
            "reset_setup_confirm": ResetConfirmScreen(
                canvas, "Setup Data", calculator.settings.reset_setup_data, "reset_setup_success"
            ),
            "reset_setup_success": ResetSuccessScreen(canvas, "Setup Data"),
            "reset_memory_confirm": ResetConfirmScreen(
                canvas, "Memory", calculator.settings.reset_memory, "reset_memory_success"
            ),
            "reset_memory_success": ResetSuccessScreen(canvas, "Memory"),
            "reset_all_confirm": ResetConfirmScreen(
                canvas, "Initialize All", calculator.settings.reset_all, "reset_all_success"
            ),
            "reset_all_success": ResetSuccessScreen(canvas, "Initialize All"),
        }

    def get_current_screen(self) -> str:
        return self.current_screen

    def switch_current_screen(self, screen_name: str):
        self.current_screen = screen_name
        self.render()

    def is_choice_screen(self) -> bool:
        screen_instance = self.screens.get(self.current_screen)
        return isinstance(screen_instance, ChoiceScreen)

    def is_reset_confirm_screen(self) -> bool:
        screen_instance = self.screens.get(self.current_screen)
        return isinstance(screen_instance, ResetConfirmScreen)

    def is_reset_success_screen(self) -> bool:
        screen_instance = self.screens.get(self.current_screen)
        return isinstance(screen_instance, ResetSuccessScreen)

    def render(self):
        self.screens[self.current_screen].render()
