import tkinter as tk

from settings import Settings
from ui import UI
from controller import Controller, FormulaList
from engine import Engine
from displayer import Displayer


class Calculator:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Casio Calculator")
        self.root.geometry("400x710+300+25")
        self.root.configure(bg='#4d4d4d')
        self.root.resizable(False, False)

        self.settings = Settings(self)

        self.ui = UI(self)
        self.ui.initialize()

        self.formulas = FormulaList(self)
        self.displayer = Displayer(self.ui.canvas, self.formulas)  # ← 提前
        self.controller = Controller(self, self.formulas)
        self.engine = Engine(self)

    def handle_input(self, key_name: str):
        if self.settings.running:
            # 特殊按键在主程序中处理
            if key_name == "SHIFT":
                self.ui.update_flag("A", self.settings.turn_off_alpha_mode())
                self.ui.update_flag("S", self.settings.change_shift_mode())
            elif key_name == "ALPHA":
                self.ui.update_flag("S", self.settings.turn_off_shift_mode())
                self.ui.update_flag("A", self.settings.change_alpha_mode())

            elif key_name == "POWER":
                self.restart()
            elif key_name == "AC":
                if self.settings.shift_mode:
                    self.settings.running = False
                    self._turn_off_shift_and_alpha()
                else:
                    self.controller.clear()
            elif key_name == "DEL":
                if self.settings.shift_mode:
                    self._turn_off_shift_and_alpha()
                    pass
                elif self.settings.alpha_mode:
                    self._turn_off_shift_and_alpha()
                    pass
                else:
                    self.controller.delete()
            elif key_name == "=":
                self.calculate(self.settings.shift_mode)
            elif key_name in ["UP", "DOWN", "LEFT", "RIGHT"]:
                self.controller.move_cursor(key_name)

            else:
                if self.settings.shift_mode:
                    self.ui.update_flag("S", self.settings.turn_off_shift_mode())
                    self.controller.handle_input(key_name, shift_mode=True)
                elif self.settings.alpha_mode:
                    self.ui.update_flag("A", self.settings.turn_off_alpha_mode())
                    self.controller.handle_input(key_name, alpha_mode=True)
                else:
                    self.controller.handle_input(key_name)

        elif key_name == "POWER":
            self._turn_off_shift_and_alpha()
            self.settings.running = True

    def calculate(self, shift_mode: bool):
        expression = self.controller.get_expression()
        formulas, error = self.engine.evaluate(expression)

        if error:
            print(error)
        else:
            self.controller.save_history(expression)

        self.controller.clear()
        # ------------------------------------------------------------------------------------
        self.displayer.render(result=(error if error else formulas))
        # ------------------------------------------------------------------------------------

    def restart(self):
        self._turn_off_shift_and_alpha()
        print("restart")

    def _turn_off_shift_and_alpha(self):
        self.ui.update_flag("S", self.settings.turn_off_shift_mode())
        self.ui.update_flag("A", self.settings.turn_off_alpha_mode())

    def run(self):
        self.root.mainloop()


if __name__ == '__main__':
    calculator = Calculator()
    calculator.run()
