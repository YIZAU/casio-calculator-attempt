# Calculator / ScreenManager / FormulaList 协作关系

本文档说明三个模块级文件（`main.py`、`displayer.py`、`controller.py`）中，`Calculator`、`ScreenManager`、`FormulaList` 三类之间的依赖方向、调用路径和扩展性评估。

---

## 一、三方职责

| 类 | 所在文件 | 职责 |
| --- | --- | --- |
| Calculator | main.py | 顶层装配。创建所有对象、持有全局引用、接收按键、转发渲染请求 |
| ScreenManager | displayer.py | 屏幕路由。管理 Screen 集合，转发 render() 到当前 Screen |
| FormulaList | controller.py | 公式数据。持有节点列表和光标，提供插入/删除/移动操作，变更后触发渲染 |

---

## 二、依赖方向

Calculator

 ├─ owns ─→

FormulaList

 （数据源） ├─ owns ─→

ScreenManager

 （渲染路由） ├─ owns ─→ Settings / UI / Controller / Engine │ └─ method ─→ render() ─→ ScreenManager.render() ─→ Screen.render()

FormulaList

 └─ method ─→ refresh() ─→ Calculator.render() ─→ ...

ScreenManager

 └─ no back-reference to Calculator（单向依赖）

**关键设计**：

- `Calculator` 是唯一的"根"，其他所有对象都从它挂载。
- `FormulaList` 通过 `self.calculator` 反向持有对 `Calculator` 的引用，用于触发渲染。
- `ScreenManager` 不知道 `Calculator` 的其他部分，只持有被注册的 Screen 对象。
- **渲染入口唯一**：所有渲染请求最终都汇聚到 `Calculator.render()`。

---

## 三、核心调用链

### 3.1 按键 → 数据变更 → 渲染

[用户按键]

 │ ▼

Calculator.deal_input(key)

 │ ▼

Calculator._deal_formula_input(key)

 │ ▼

Controller.handle_formula_input(key)

 或 move_cursor / delete / clear │ ▼ (通过 _INPUT_TABLE 查表)

FormulaList.add_number(...)

 或 其他插入操作 │ ▼

FormulaList.refresh()

 │ ▼

Calculator.render()

 │ ▼

ScreenManager.render()

 │ ▼

InputFormulaScreen.render()

 │ ▼

[Canvas 重绘]

### 3.2 计算 → 显示结果

[用户按 =]

 │ ▼

Calculator._deal_formula_input("=")

 │ ▼

Calculator.calculate()

 │ ├─→ Controller.get_expression() 获取表达式字符串 ├─→ Engine.calculate(...) 计算结果 Node │ ▼

screen_manager.screens["formula"]

 │ ▼

.show_result(text)

 写入内部状态 │ ▼

Controller.clear()

 清空 FormulaList │ ▼

Calculator.render()

 触发渲染

### 3.3 三条路径的共同终点

| 起点 | 中间经过 | 终点 |
| --- | --- | --- |
| 普通按键插入 | FormulaList.refresh | Calculator.render |
| 光标移动 | FormulaList.refresh | Calculator.render |
| 计算完成 | Calculator.calculate | Calculator.render |
| 删除/清空 | FormulaList.refresh | Calculator.render |

**所有渲染最终都经过 `Calculator.render()`。**

这保证了渲染时机的一致性。

---

## 四、数据流与依赖的边界

### 4.1 谁持有谁

Calculator

 ├── settings: Settings ├── ui: UI ├── formulas: FormulaList ← 数据 ├── screen_manager: ScreenManager ← 渲染 ├── controller: Controller ← 输入逻辑 └── engine: Engine ← 计算

FormulaList

 └── calculator: Calculator ← 反向引用（只用于 render）

ScreenManager

 ├── calculator: Calculator ← 用于转发（可选） └── screens: dict[str, Screen]

### 4.2 依赖方向

| 从 | 到 | 用途 |
| --- | --- | --- |
| Calculator | FormulaList / ScreenManager / Controller / Engine | 装配 |
| FormulaList | Calculator | 触发渲染 |
| Controller | FormulaList / Settings | 修改数据 |
| ScreenManager | Screen | 转发渲染 |
| Screen | Canvas / FormulaList | 绘制 |

### 4.3 不存在的依赖

- `ScreenManager` 不知道 `FormulaList` 的存在——它只持有 Screen 对象
- `Screen` 不知道 `Controller` 的存在——它只绘制 Canvas
- `FormulaList` 不知道 `Engine` 的存在——它只管理节点列表
- `Calculator` 不知道 `Screen` 的绘制细节——它只调 `render()`

---

## 五、扩展性评估：加新 Screen 的成本

### 5.1 需要改的文件

| 文件 | 改动量 | 说明 |
| --- | --- | --- |
| displayer.py | +1 个类 | 继承 Screen，实现 render(self) |
| main.py | +1 行注册 | screen_manager.screens["xxx"] = XxxScreen(...) |
| main.py | +1 个 if 分支 | _deal_input 里加 elif screen == "xxx":... |
| controller.py | 通常不动 | 除非新 Screen 需要新的数据操作 |

### 5.2 举例：加一个菜单 Screen

```
# displayer.py

class MenuScreen(Screen):
    name = "menu"

    def __init__(self, canvas):
        self.canvas = canvas
        self.items = []
        self.selected = 0

    def render(self):
        self.canvas.delete('all')
        for i, item in enumerate(self.items):
            y = 20 + i * 24
            color = "blue" if i == self.selected else "black"
            self.canvas.create_text(20, y, anchor='w',
                                    text=item, fill=color)
```

```
# main.py

# __init__ 中
self.screen_manager.screens["menu"] = MenuScreen(self.ui.canvas)

# _deal_input 中
elif screen == "menu":
    self._deal_menu_input(key_name)
```

新 Screen 的类不需要知道 `Calculator`、`Controller`、`Engine`。它只需要 `canvas` 和自己的内部状态。

### 5.3 不会发生的事

- **不需要改 `Screen` 基类**——只要子类实现 `render(self)` 就够
- **不需要改 `ScreenManager`**——它用字典，天然支持多 Screen
- **不需要改 `FormulaList`**——它只负责数据
- **不需要改 `Controller`**——除非新 Screen 需要新的输入动作
- **不需要改 `Engine`**——计算逻辑独立

### 5.4 唯一会变大的地方

**`Calculator._deal_input` 会随 Screen 数量增长。**

 每加一个 Screen，就多一个

`elif`

 分支和一个

`_deal_xxx_input`

 方法。

 这是当前设计里唯一没有完全解耦的地方。

缓解方式（未来）：把每个 Screen 的输入逻辑封装到 Screen 内部，`ScreenManager.handle_input` 转发给当前 Screen。你之前明确说过"Screen 不处理输入"，所以这个方案被搁置。如果将来 `Calculator` 太大，可以重新考虑。

---

## 六、渲染链的健壮性

### 6.1 单一入口

所有渲染请求都汇聚到 `Calculator.render()`：

```
def render(self):
    self.screen_manager.render()
```

这意味着未来要加"节流渲染"、"渲染前后钩子"、"渲染日志"，只需改这一个方法。

### 6.2 数据变更触发渲染

`FormulaList` 的每个修改方法末尾调 `refresh()`，`refresh()` 调 `calculator.render()`。这形成了一条链：

数据变更

→

 触发渲染

→

 屏幕更新

**不需要手动在按键处理里写 `render()`**（除了 `calculate()` 这类不经过 FormulaList 的操作）。

### 6.3 潜在的重复渲染

看 `calculate()`：

```
self.controller.clear()          # 内部会 refresh → render
self.screen_manager.render()     # 又一次 render
```

渲染了两次。功能上没问题，但效率上有浪费。

**修法**：在 `calculate()` 里直接操作 `self.formulas.nodes`，绕过 `clear()` 的 `refresh()`，最后统一 `render()` 一次。

---

## 七、当前架构的评估

### 7.1 已经做对的部分

- **渲染入口唯一**：`Calculator.render()` 是所有渲染的汇聚点
- **Screen 无状态副作用**：Screen 只管画，不修改数据
- **数据变更自动触发渲染**：`refresh()` 链路保证数据与显示同步
- **ScreenManager 用字典**：加 Screen 只需注册一个 key
- **依赖方向清晰**：数据向下、渲染向上

### 7.2 需要警惕的部分

| 问题 | 影响 | 何时处理 |
| --- | --- | --- |
| Calculator._deal_input 随屏幕数增长 | 文件变大 | 3 个以上 Screen 时考虑重构 |
| calculate() 重复渲染 | 性能小损 | 发现即可修 |
| FormulaList 反向依赖 Calculator | 耦合 | 可接受，因为 refresh 是通用需求 |
| ScreenManager 持有 canvas | 略冗余 | 等 Screen 数量多了可以清理 |

---

## 八、回答你的问题

> **现在是否可以较为自由地添加 Screen 且不会在将来大改？**

### 答案：是，有前提。

**可以自由添加的部分：**

- **渲染**：新 Screen 只需继承 `Screen` 并实现 `render(self)`。这一个方法。
- **注册**：在 `Calculator.__init__` 里加一行 `screens["xxx"] = XxxScreen(...)`。
- **切换**：`screen_manager.current_screen = "xxx"` 一行。

**不能自由扩展的部分：**

- **输入处理**：每个新 Screen 都需要在 `Calculator._deal_input` 里加一个分支。这是当前架构的必然代价，因为输入逻辑集中在 `Calculator`。

**这个"不能"是不是问题？**

- 如果 Screen 数量控制在 **3~5 个**，`_deal_input` 的分支不超过 5 个，可以接受。
- 如果未来要支持解方程、矩阵、向量、统计等十几种模式，`_deal_input` 会膨胀。
- 那时可以引入"输入分发表"或"让 Screen 自己处理输入"，但需要改动较多代码。

### 8.1 一个折中方案

不需要现在做。如果未来 `_deal_input` 超过 5 个分支，可以改成：

```
self._input_handlers = {
    "formula": self._deal_formula_input,
    "menu":    self._deal_menu_input,
    "settings": self._deal_settings_input,
}

def deal_input(self, key_name):
    screen = self.screen_manager.get_current_screen()
    handler = self._input_handlers.get(screen)
    if handler:
        handler(key_name)
```

这只是把 `if-elif` 换成字典查表。它不会消除"每个 Screen 需要一个处理函数"的事实，只是让添加更干净。

### 8.2 最终建议

**当前架构已经足够好，可以放心添加 Screen。**

 只要遵守以下两条规则：

 1. 新 Screen 只做渲染，不碰数据，不碰输入

 2. 所有渲染请求通过

`Calculator.render()`

 走

 那么新 Screen 的引入不会引发连锁改动。

`Calculator._deal_input`

 会线性增长，这是当前设计的可接受代价。等到分支太多（比如超过 5 个），再引入输入分发表。

---

## 九、一句话总结

> **数据在 `FormulaList`，渲染在 `ScreenManager` 与 `Screen`，装配和输入在 `Calculator`。**
>
>  三者职责清晰、依赖方向单向、渲染入口唯一。
>
> **加 Screen 是自由的**
>
> ：只需新增一个 Screen 子类、注册一行、在
>
> `_deal_input`
>
>  加一个分支。不会引发大改。
>
>  唯一会线性增长的是
>
> `_deal_input`
>
>  的分支数。这是可接受的，也是当前约束（"Screen 不处理输入"）的必然结果。等真的碍事时再重构。