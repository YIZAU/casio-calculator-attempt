import tkinter as tk

from controller import FormulaList


class Displayer:
    """把 FormulaList 画到 Canvas 上。

    目前只做最朴素的渲染：
      - 表达式：单行文本，光标位置用 '|' 表示
      - 结果：右下角一行文本
    """

    FONT_EXPR = ('Segoe UI', 18)
    FONT_RESULT = ('Segoe UI', 16)

    COLOR_BG = '#d5e3d4'
    COLOR_EXPR = 'black'
    COLOR_RESULT = '#333333'
    COLOR_CURSOR = '#0055aa'

    def __init__(self, calculator, canvas: tk.Canvas, formulas: FormulaList):
        self.calculator = calculator
        self.canvas = canvas
        self.formulas = formulas

        self._result_text: str | None = None

    def render(self, result=None):
        screen = self.calculator.current_screen

        if screen == "formula":
            self._render_formula(result)

    def _render_formula(self, result=None):
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

        # 结果
        self._result_text = None if result is None else str(result)
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
