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
            "module": {
                1: "CALCULATE",
                2: "COMPLEX",
                3: "BASE_N",
                4: "MARTIX",
                5: "MVECTOR",
                6: "MSTATISTICS",
                7: "TABLE",
                8: "EQUATION/FUNC",
                9: "INEQUALITY",
                10: "RATIO"
            },
            "io_mode": {
                1: "MathI/MathO",
                2: "MathI/DecimalO",
                3: "LineI/LineO",
                4: "LineI/DecimalO",
            },
            "angle_unit": [
                "DEG",
                "RAD",
                "GRA"
            ],
            "number_format": [
                "FIX",
                "SCI",
                "NORM"
            ],
            "fraction_result": [
                "mixed",
                "improper"
            ],
            "complex_format": [
                "rectangular",
                "polar"
            ],
            "table_function_count": [
                "single",
                "dual"
            ],
            "decimal_mark": [
                "dot",
                "comma"
            ],
            "language": [
                "EN",
                "CH"
            ]
        }

        with open(DATA_DIR / "settings.json", "r", encoding="utf-8") as f:
            self.settings: dict = json.load(f)

        with open(DATA_DIR / "variables.json", "r", encoding="utf-8") as v:
            self.variables: dict = json.load(v)

        with open(DATA_DIR / "locales.json", "r", encoding="utf-8") as l:
            self.locales: dict = json.load(l)

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

    def translate(self, key: str) -> str:
        language = self.settings.get("language", "EN")
        language_dict = self.locales[language]
        return language_dict.get(key, key)

    def reset_setup_data(self):
        defaults = {
            "module": "CALCULATE",
            "angle_unit": "DEG",
            "io_mode": "MathI/MathO",
            "number_format": "NORM",
            "engineer_symbol": False,
            "fraction_result": "improper",
            "complex_format": "rectangular",
            "frequency": True,
            "equation_complex_result": False,
            "table_function_count": "dual",
            "decimal_mark": "DOT",
            "digit_separator": False,
            "language": "EN"
        }
        self.settings = defaults
        with open(DATA_DIR / "settings.json", "w", encoding="utf-8") as f:
            json.dump(self.settings, f, ensure_ascii=False, indent=2)

    def reset_memory(self):
        """清空所有变量"""
        for k in self.variables.keys():
            self.variables[k] = "0"
        with open(DATA_DIR / "variables.json", "w", encoding="utf-8") as v:
            json.dump(self.variables, v, ensure_ascii=False, indent=2)

    def reset_all(self):
        """初始化全部"""
        self.reset_setup_data()
        self.reset_memory()
