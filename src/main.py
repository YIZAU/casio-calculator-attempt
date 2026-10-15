import tkinter as tk

from settings import Settings
from ui import UI
from controller import Controller, FormulaList
from engine import Engine
from displayer import ScreenManager


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
        self.screen_manager = ScreenManager(self, self.ui.canvas)
        self.controller = Controller(self, self.formulas)
        self.engine = Engine(self)

    def deal_input(self, key_name: str):
        # 关机状态：只响应 POWER
        if not self.settings.running:
            if key_name == "POWER":
                self._turn_off_shift_and_alpha()
                self.settings.running = True
                self.render()
            return

        # 开机状态：按屏幕分派
        screen = self.screen_manager.get_current_screen()

        if screen == "formula":
            self._deal_formula_input(key_name)
        elif screen == "variable":
            self._deal_variable_input(key_name)

    def _deal_formula_input(self, key_name: str):
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
            self.calculate()

        elif key_name == "STO" and self.settings.shift_mode:
            self.settings.turn_off_shift_mode()
            self.ui.update_flag('S', self.settings.turn_off_shift_mode())
            self.screen_manager.switch_current_screen("variable")
            self.ui.update_flag('X', True)

        else:
            if self.settings.shift_mode:
                self.ui.update_flag("S", self.settings.turn_off_shift_mode())
                self.controller.handle_formula_input(key_name, shift_mode=True)
            elif self.settings.alpha_mode:
                self.ui.update_flag("A", self.settings.turn_off_alpha_mode())
                self.controller.handle_formula_input(key_name, alpha_mode=True)
            else:
                self.controller.handle_formula_input(key_name)

    def _deal_variable_input(self, key_name: str):
        if key_name in ["NEG", "DMS", "INV", "SIN", "COS", "TAN", ")", "S2D", "M_PLUS"]:
            self.controller.handle_formula_input(key_name, alpha_mode=True)
            self.screen_manager.switch_current_screen("formula")
            self.ui.update_flag('X', False)
        elif key_name == "X":
            self.controller.handle_formula_input("X")
            self.screen_manager.switch_current_screen("formula")
            self.ui.update_flag('X', False)

        if key_name == "SHIFT":
            self.ui.update_flag("A", self.settings.turn_off_alpha_mode())
            self.ui.update_flag("S", self.settings.change_shift_mode())
        elif key_name == "ALPHA":
            self.ui.update_flag("S", self.settings.turn_off_shift_mode())
            self.ui.update_flag("A", self.settings.change_alpha_mode())

    def render(self):
        self.screen_manager.render()

    def calculate(self):
        expression = self.controller.get_expression()
        formulas, error = self.engine.calculate(expression)

        formula_screen = self.screen_manager.screens["formula"]

        if error:
            formula_screen.show_result(error)
        else:
            formula_screen.show_result(formulas)
            self.controller.save_history(expression)

        self.controller.clear()
        self.screen_manager.render()

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
