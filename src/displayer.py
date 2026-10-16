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
        self._result_text = None       # 右下角结果
        self._feedback_text = None     # 主区域覆盖

    def show_result(self, text):
        self._result_text = str(text) if text is not None else None

    def show_feedback(self, text):
        """把反馈文本作为主画布内容显示（覆盖公式区域）。"""
        self._feedback_text = str(text) if text is not None else None

    def clear_feedback(self):
        self._feedback_text = None

    def has_feedback(self) -> bool:
        return self._feedback_text is not None

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
        self.render()

    def render(self):
        self.screens[self.current_screen].render()
