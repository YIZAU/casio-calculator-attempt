import tkinter as tk


class DrawElement:
    KIND_TEXT = "text"
    KIND_LINE = "line"
    KIND_CURSOR = "cursor"

    def __init__(self, kind: str, content=None):
        self.kind = kind
        self.content = None


class FormulaMap:
    CanvasWidth = 480
    CanvasHeight = 130

    def __init__(self):
        self.map = None


class Displayer:
    def __init__(self, canvas: tk.Canvas, formula_list):
        self.canvas = canvas
        self.formulas = formula_list

