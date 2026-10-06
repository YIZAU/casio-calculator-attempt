import tkinter as tk
from PIL import Image, ImageTk

from pathlib import Path

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"


class Cell:
    def __init__(self, father, name: str, column: int, row: int, image_path: str,
                 command=None, size: tuple[int, int] = (65, 50),
                 fg: str = 'black', bg: str = '#4d4d4d', font: tuple[str, int] = ('Segoe UI', 12)):
        self.name = name
        self.column = column
        self.row = row
        self.font = font
        self.fg = fg
        self.bg = bg

        self.image = None
        if image_path:
            image = Image.open(image_path)
            image = image.resize(size, Image.Resampling.LANCZOS)
            self.image = ImageTk.PhotoImage(image)

        width, height = size
        self.frame = tk.Frame(father, width=width, height=height, bg="#4d4d4d")
        self.frame.grid_propagate(False)  # 固定大小
        self.frame.grid(row=self.row, column=self.column, padx=4, pady=3, sticky="nsew")

        if self.image:

            self.button = tk.Button(self.frame, image=self.image, font=self.font, relief=tk.FLAT, fg=self.fg,
                                    bg="#4d4d4d",
                                    command=command, borderwidth=0, highlightthickness=0)
            self.button.image = self.image
        else:
            self.button = tk.Button(self.frame, text=self.name, font=self.font, relief=tk.FLAT, fg=self.fg,
                                    bg=self.bg,
                                    command=command, borderwidth=0, highlightthickness=0)
        self.button.place(relwidth=1, relheight=1)


class UI:
    def __init__(self, calculator):
        from main import Calculator
        self.calculator: Calculator = calculator

        self.L1 = tk.Frame(self.calculator.root, bg='#d5e3d4', highlightthickness=10, highlightbackground='black',
                           pady=6)
        self.L2 = tk.Frame(self.calculator.root, bg='#4d4d4d')
        self.L3 = tk.Frame(self.calculator.root, bg='#4d4d4d')

        self.flag_images: dict[str, tk.PhotoImage] = {}
        self.flags: dict[str, tk.Label] = {}

    def initialize(self):
        self._initialize_L1()
        self._initialize_L2()
        self._initialize_L3()

        self.display_angle_unit()

    def _initialize_L1(self):
        self.L1.pack(pady=(10, 5), padx=10, fill='x')

        self.states_bar = tk.Frame(
            self.L1,
            width=360,
            height=10,
            bg='#d5e3d4',
            highlightthickness=0
        )
        self.states_bar.pack()

        index = 0
        for name in ['S', 'A', 'M', 'X', 'IO', 'D', 'R', 'G', 'FIX', 'SCI']:
            self.flag_images[name] = ImageTk.PhotoImage(Image.open(ASSETS_DIR / f"{name}_on.png").resize((16, 16)), Image.Resampling.LANCZOS)
            self.flags[name] = tk.Label(self.states_bar, image='', anchor='w', bg='#d5e3d4')
            self.flags[name].grid(row=0, column=index)
            index += 1

        self.canvas = tk.Canvas(
            self.L1,
            width=360,
            height=130,
            # bg = 'red',
            bg='#d5e3d4',
            highlightthickness=0
        )
        self.canvas.pack()

    def update_flag(self, name: str, active: bool):
        if active:
            self.flags[name].config(image=self.flag_images[name])
        else:
            self.flags[name].config(image='')

    def display_angle_unit(self):
        angle_unit = self.calculator.settings.settings.get("angle_unit")
        if angle_unit == "DEG":
            self.update_flag("D", True)
            self.update_flag("R", False)
            self.update_flag("G", False)
        elif angle_unit == "RAD":
            self.update_flag("D", False)
            self.update_flag("R", True)
            self.update_flag("G", False)
        else:
            self.update_flag("D", False)
            self.update_flag("R", False)
            self.update_flag("G", True)

    def _initialize_L2(self):
        for i in range(1, 6):
            self.L2.grid_rowconfigure(i, weight=1)
        for j in range(1, 7):
            self.L2.grid_columnconfigure(j, weight=2)
        self.L2.pack(anchor='center')

        L2_data = [
            ["SHIFT", None, (1, 1), "yellow", "#999999"],
            ["ALPHA", None, (2, 1), "yellow", "#999999"],
            ["UP", None, (3, 1), "yellow", "#999999"],
            ["DOWN", None, (4, 1), "yellow", "#999999"],
            ["MENU/SET", None, (5, 1), "yellow", "#999999"],
            ["POWER", None, (6, 1), "yellow", "#999999"],

            ["OPTN", ASSETS_DIR / "212.png", (1, 2), "white", "black"],
            ["CALC", ASSETS_DIR / "222.png", (2, 2), "white", "black"],
            ["LEFT", None, (3, 2), "yellow", "#999999"],
            ["RIGHT", None, (4, 2), "yellow", "#999999"],
            ["integrate", ASSETS_DIR / "252.png", (5, 2), "white", "black"],
            ["x", ASSETS_DIR / "262.png", (6, 2), "white", "black"],

            ["fraction", ASSETS_DIR / "213.png", (1, 3), "white", "black"],
            ["sqrt", ASSETS_DIR / "223.png", (2, 3), "white", "black"],
            ["square", ASSETS_DIR / "233.png", (3, 3), "white", "black"],
            ["power", ASSETS_DIR / "243.png", (4, 3), "white", "black"],
            ["log", ASSETS_DIR / "253.png", (5, 3), "white", "black"],
            ["ln", ASSETS_DIR / "263.png", (6, 3), "white", "black"],

            ["(-)", ASSETS_DIR / "214.png", (1, 4), "white", "black"],
            ["°'\"", ASSETS_DIR / "224.png", (2, 4), "white", "black"],
            ["f^-1", ASSETS_DIR / "234.png", (3, 4), "white", "black"],
            ["sin", ASSETS_DIR / "244.png", (4, 4), "white", "black"],
            ["cos", ASSETS_DIR / "254.png", (5, 4), "white", "black"],
            ["tan", ASSETS_DIR / "264.png", (6, 4), "white", "black"],

            ["STO", ASSETS_DIR / "215.png", (1, 5), "white", "black"],
            ["ENG", ASSETS_DIR / "225.png", (2, 5), "white", "black"],
            ["(", ASSETS_DIR / "235.png", (3, 5), "white", "black"],
            [")", ASSETS_DIR / "245.png", (4, 5), "white", "black"],
            ["S_D", ASSETS_DIR / "255.png", (5, 5), "white", "black"],
            ["M+", ASSETS_DIR / "265.png", (6, 5), "white", "black"]
        ]

        for name, image_path, (column, row), fg, bg in L2_data:
            Cell(self.L2, name, column, row, image_path,
                 fg=fg, bg=bg, font=('Segoe UI', 12),
                 command=lambda t=name: self.calculator.handle_input(t))

    def _initialize_L3(self):
        for i in range(1, 5):
            self.L3.grid_rowconfigure(i, weight=1)
        for j in range(1, 6):
            self.L3.grid_columnconfigure(j, weight=2)
        self.L3.pack(anchor='center')

        L3_data = [
            ["7", ASSETS_DIR / "311.png", (1, 1), "black", "white", (70, 55)],
            ["8", ASSETS_DIR / "321.png", (2, 1), "black", "white", (70, 55)],
            ["9", ASSETS_DIR / "331.png", (3, 1), "black", "white", (70, 55)],
            ["DEL", ASSETS_DIR / "341.png", (4, 1), "white", "blue", (70, 55)],
            ["AC", ASSETS_DIR / "351.png", (5, 1), "white", "blue", (70, 55)],
            ["4", ASSETS_DIR / "312.png", (1, 2), "black", "white", (70, 55)],
            ["5", ASSETS_DIR / "322.png", (2, 2), "black", "white", (70, 55)],
            ["6", ASSETS_DIR / "332.png", (3, 2), "black", "white", (70, 55)],
            ["*", ASSETS_DIR / "342.png", (4, 2), "black", "white", (70, 55)],
            ["/", ASSETS_DIR / "352.png", (5, 2), "black", "white", (70, 55)],
            ["1", ASSETS_DIR / "313.png", (1, 3), "black", "white", (70, 55)],
            ["2", ASSETS_DIR / "323.png", (2, 3), "black", "white", (70, 55)],
            ["3", ASSETS_DIR / "333.png", (3, 3), "black", "white", (70, 55)],
            ["+", ASSETS_DIR / "343.png", (4, 3), "black", "white", (70, 55)],
            ["-", ASSETS_DIR / "353.png", (5, 3), "black", "white", (70, 55)],
            ["0", ASSETS_DIR / "314.png", (1, 4), "black", "white", (70, 55)],
            [".", ASSETS_DIR / "324.png", (2, 4), "black", "white", (70, 55)],
            ["x10^", ASSETS_DIR / "334.png", (3, 4), "black", "white", (70, 55)],
            ["Ans", ASSETS_DIR / "344.png", (4, 4), "black", "white", (70, 55)],
            ["=", ASSETS_DIR / "354.png", (5, 4), "black", "white", (70, 55)],
        ]

        for name, image_path, (column, row), fg, bg, size in L3_data:
            Cell(self.L3, name, column, row, image_path,
                 size=size, fg=fg, bg=bg, font=('Segoe UI', 20),
                 command=lambda t=name: self.calculator.handle_input(t))
