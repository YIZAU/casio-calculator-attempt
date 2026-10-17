import json
from pathlib import Path

_SRC_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SRC_DIR.parent
DATA_DIR = _PROJECT_ROOT / "data"


class Settings:
    def __init__(self, calculator):
        self.calculator = calculator

        # 临时设置
        self.shift_mode = False
        self.alpha_mode = False

        # 长期设置
        self.running = True

        self._setting_map = {
            "input_mode": {
                1: "MODE_CALCULATE",
                2: "MODE_COMPLEX",
                3: "MODE_BASE_N",
                4: "MODE_MARTIX",
                5: "MODE_VECTOR",
                6: "MODE_STATISTICS",
                7: "MODE_TABLE",
                8: "MODE_EQUATION",
                9: "MODE_INEQUALITY",
                10: "MODE_RATIO"
            },
            "io_mode": {
                1: "IO_MATH_MATH",
                2: "IO_MATH_DECIMAL",
                3: "IO_LINEAR_LINEAR",
                4: "IO_LINEAR_DECIMAL",
            }
        }

        with open(DATA_DIR / "settings.json", "r", encoding="utf-8") as f:
            self.settings: dict = json.load(f)

        with open(DATA_DIR / "variables.json", "r", encoding="utf-8") as v:
            self.variables: dict = json.load(v)

    def set_variable(self, expression: str, var_name: str):
        self.variables[var_name] = expression

        path = DATA_DIR / "variables.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as v:
            json.dump(self.variables, v, ensure_ascii=False, indent=2)

    def save_settings(self, setting_name: str, value: str):
        self.settings[setting_name] = value

        path = DATA_DIR / "settings.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.settings, f, ensure_ascii=False, indent=2)

    def change_shift_mode(self) -> bool:
        self.shift_mode = not self.shift_mode
        return self.shift_mode

    def change_alpha_mode(self) -> bool:
        self.alpha_mode = not self.alpha_mode
        return self.alpha_mode

    def turn_off_shift_mode(self) -> False:
        self.shift_mode = False
        return False

    def turn_off_alpha_mode(self) -> False:
        self.alpha_mode = False
        return False
