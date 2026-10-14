import tkinter as tk

from controller import FormulaList


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

    def __init__(self, canvas: tk.Canvas, formulas: FormulaList):
        self.canvas = canvas
        self.formulas = formulas

        self._result_text: str | None = None

    def show_result(self, text):
        self._result_text = str(text) if text is not None else None

    def render(self):
        """重绘整块 canvas。

        result=None   -> 只画表达式，不显示结果
        result=xxx    -> 表达式下方额外显示 xxx（一般是本次计算的结果或错误）
        """
        self.canvas.delete('all')

        left, right = self._split_by_cursor()

        # 表达式（左半 + 光标 + 右半）
        # 光标用单独一个 text item，方便以后上色
        x = 8
        y = 10

        left_id = self.canvas.create_text(
            x, y, anchor='nw', text=left,
            font=self.FONT_EXPR, fill=self.COLOR_EXPR,
        )
        # 光标接在左半段右侧
        bbox = self.canvas.bbox(left_id)
        cursor_x = (bbox[2] if bbox else x)

        self.canvas.create_text(
            cursor_x, y, anchor='nw', text='|',
            font=self.FONT_EXPR, fill=self.COLOR_CURSOR,
        )
        self.canvas.create_text(
            cursor_x + 1, y, anchor='nw', text=right,
            font=self.FONT_EXPR, fill=self.COLOR_EXPR,
        )

        if self._result_text is not None:
            self.canvas.create_text(
                352, 122, anchor='se', text=self._result_text,
                font=self.FONT_RESULT, fill=self.COLOR_RESULT,
            )

    def clear(self):
        self.canvas.delete('all')
        self._result_text = None

    def _split_by_cursor(self) -> tuple[str, str]:
        nodes = self.formulas.nodes
        idx = self.formulas.index

        left = ''.join(n.to_str() for n in nodes[:idx])
        right = ''.join(n.to_str() for n in nodes[idx:])
        return left, right


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


class ScreenManager:
    def __init__(self, calculator, canvas):
        self.calculator = calculator
        self.canvas = canvas
        self.current_screen = "formula"
        self.screens = {
            "formula": InputFormulaScreen(canvas, calculator.formulas),
            "variable": VariableScreen(canvas, calculator.settings.variables),
        }

    def get_current_screen(self) -> str:
        return self.current_screen

    def switch_current_screen(self, screen_name: str):
        self.current_screen = screen_name

    def render(self):
        self.screens[self.current_screen].render()
