import tkinter as tk

from settings import Settings
from ui import UI
from controller import Controller, FormulaList
from engine import Engine
from displayer import ScreenManager


class Calculator:
    VARIABLE_MAP = {
        "NEG": "A", "DMS": "B", "INV": "C",
        "SIN": "D", "COS": "E", "TAN": "F",
        ")": "x", "S2D": "y", "M_PLUS": "M",
        "X": "x",
    }

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

        self._pending_sto = False
        self.root_screen = "formula"

    def deal_input(self, key_name: str):
        # 关机状态：只响应 POWER
        if not self.settings.running:
            if key_name == "POWER":
                self._turn_off_shift_and_alpha()
                self.settings.running = True
                self.render()
            return

        # 全局：模式切换
        if key_name == "SHIFT":
            self.ui.update_flag("A", self.settings.turn_off_alpha_mode())
            self.ui.update_flag("S", self.settings.change_shift_mode())
            return
        if key_name == "ALPHA":
            self.ui.update_flag("S", self.settings.turn_off_shift_mode())
            self.ui.update_flag("A", self.settings.change_alpha_mode())
            return

        # 开机状态：按屏幕分派
        screen = self.screen_manager.get_current_screen()

        if self.screen_manager.is_choice_screen():
            self._deal_choice_input(key_name)
        elif screen == "formula":
            self._deal_formula_input(key_name)
        elif screen == "variable":
            self._deal_variable_input(key_name)
        elif screen == "error":
            self._deal_error_input(key_name)

    def _deal_formula_input(self, key_name: str):
        if self._pending_sto:
            self._handle_pending_sto(key_name)
            return

        formula_screen = self.screen_manager.screens["formula"]
        need_render = False

        if formula_screen.has_feedback():
            self.controller.clear()
            formula_screen.clear_feedback()
            need_render = True

        if formula_screen.has_result():
            formula_screen.show_result(None)
            need_render = True

        if need_render:
            self.render()

        # 特殊按键在主程序中处理
        if key_name == "POWER":
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

        elif key_name == "STO":
            if self.settings.shift_mode:
                self.settings.turn_off_shift_mode()
                self.ui.update_flag('S', self.settings.turn_off_shift_mode())
                self.screen_manager.switch_current_screen("variable")
                self.ui.update_flag('X', True)
            else:
                self._pending_sto = True
                self.ui.update_flag('X', True)

        elif key_name == "MENU":
            if self.settings.shift_mode:
                self.settings.turn_off_shift_mode()
                self.ui.update_flag('S', self.settings.turn_off_shift_mode())
                self.screen_manager.switch_current_screen("setting")

        else:
            self.controller.handle_formula_input(key_name, shift_mode=self.settings.shift_mode, alpha_mode=self.settings.alpha_mode)
            self.ui.update_flag("S", self.settings.turn_off_shift_mode())
            self.ui.update_flag("A", self.settings.turn_off_alpha_mode())

    def _deal_variable_input(self, key_name: str):
        if key_name in ["NEG", "DMS", "INV", "SIN", "COS", "TAN", ")", "S2D", "M_PLUS"]:
            self.screen_manager.switch_current_screen("formula")
            self.ui.update_flag('X', False)
            self.controller.handle_formula_input(key_name, alpha_mode=True)
        elif key_name == "X":
            self.screen_manager.switch_current_screen("formula")
            self.ui.update_flag('X', False)
            self.controller.handle_formula_input("X")

    def _deal_error_input(self, key_name: str):
        if key_name == "AC":
            self.controller.clear()
            self.screen_manager.switch_current_screen("formula")

        elif key_name in ("LEFT", "RIGHT"):
            self.screen_manager.switch_current_screen("formula")

    def _deal_choice_input(self, key_name: str):
        # 获取当前的 ChoiceScreen 实例
        screen_name = self.screen_manager.get_current_screen()
        screen = self.screen_manager.screens[screen_name]

        if key_name == "UP":
            screen.page_up()
            self.render()

        elif key_name == "DOWN":
            screen.page_down()
            self.render()

        elif key_name == "LEFT":
            if screen.parent_screen:
                self.screen_manager.switch_current_screen(screen.parent_screen)

        elif key_name in ("1", "2", "3", "4"):
            # 将字符转为数字，传给 select 处理
            # select 内部如果触发了切屏，内部的 switch_current_screen 会自动 render
            screen.select(int(key_name))

        elif key_name == "AC":
            # 通用的退出逻辑：在设置菜单中按 AC，默认退回公式屏
            self.screen_manager.switch_current_screen("formula")

    def _handle_pending_sto(self, key_name):
        self._pending_sto = False
        self.ui.update_flag('X', False)

        if key_name == "=":
            self.calculate()
            return

        if key_name not in ["NEG", "DMS", "INV", "SIN", "COS", "TAN", ")", "S2D", "M_PLUS", "X"]:
            return

        if not self.formulas.nodes:
            return

        # Engine 唯一被调用的一处
        expression = self.controller.get_expression()
        result, error = self.engine.calculate(expression)

        if error:
            self.screen_manager.screens["formula"].show_feedback(error)
            self.render()
            return

        var_name = self.VARIABLE_MAP[key_name]
        self.settings.variables[var_name] = str(result)

        self.screen_manager.screens["formula"].show_feedback(
            f"{expression}→{var_name}"
        )
        self.settings.set_variable(result, var_name)
        self.render()

        self._result_shown = True

    def render(self):
        self.screen_manager.render()

    def calculate(self):
        expression = self.controller.get_expression()
        formulas, error = self.engine.calculate(expression)

        if error:
            error_screen = self.screen_manager.screens["error"]
            error_screen.set_error(error)
            self.screen_manager.switch_current_screen("error")
        else:
            formula_screen = self.screen_manager.screens["formula"]
            formula_screen.show_result(formulas)
            self.controller.save_history()
            self.controller.clear()
            self.screen_manager.render()

    def set_angle_unit(self, value):
        self.settings.save_settings("angle_unit", value)
        self.ui.display_angle_unit()
        self.screen_manager.switch_current_screen(self.root_screen)

    def set_setting(self, key, value):
        self.settings.save_settings(key, value)
        self.screen_manager.switch_current_screen(self.root_screen)

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
