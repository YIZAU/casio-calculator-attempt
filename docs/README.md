# Casio Calculator Simulator - 项目文档

> **项目定位：**
>
>  基于 Python + Tkinter 从零构建的科学计算器模拟器。
>
> **当前版本：**
>
>  v0.4.4 (基础架构全面完成，进入功能爆发期)。

## 一、现有模块介绍

项目采用 **中央集权（Centralized Assembly)** 架构，所有核心组件由 `Calculator` 统一组装和调度。模块间单向依赖，逻辑解耦，形成了一条从“用户输入”到“屏幕渲染”的完整流水线。

| 文件            | 核心类 / 职责                  | 描述                                                                         |
|---------------|---------------------------|----------------------------------------------------------------------------|
| main.py       | Calculator                | 总控中心。 接收按键信号，处理关机/SHIFT/ALPHA 等全局逻辑，根据当前屏幕状态分发输入，统一调用渲染入口。                 |
| ui.py         | UI, Cell                  | 静态界面。 负责 Tkinter 窗口布局、状态栏指示灯（S/A/M/D/R/G 等）、按键矩阵的绑定。                       |
| settings.py   | Settings                  | 状态与数据持久化。 管理长期配置（角度制、输入输出模式、语言等）和用户变量，数据以 JSON 格式存于 data/ 目录。              |
| controller.py | Controller, FormulaList   | 公式编辑器。 维护扁平公式列表（带光标与结构标记），通过字典映射表处理按键动作，维护 History 历史记录。                   |
| engine.py     | Engine, Lexer, Parser     | 编译器前端。 负责将字符串解析为 Token，然后构建为 AST（抽象语法树），提供统一的符号计算环境上下文。                    |
| mathmatics.py | Node 家族                   | 数学引擎核心。 包含所有 AST 节点（整数、分数、幂、根号、三角函数、对数等），实现注册表驱动的 simplify(env) 符号化简与数值求值。 |
| displayer.py  | ScreenManager, Screen 家族  | 多屏幕渲染系统。 共享单一 Canvas，负责页面路由（switch_current_screen），实现了公式屏、变量屏、选项菜单屏、错误屏等。  |

## 二、现有接口调用方法

### 1. 按键输入分发

无论物理键盘还是 UI 按钮，最终都汇聚到 `Calculator` 的入口：

```
# 模拟按下计算器上的 "1" 键
calculator.deal_input("1")

# 模拟按下 SHIFT + STO
calculator.deal_input("SHIFT")
calculator.deal_input("STO")
```

### 2. 屏幕路由与渲染

所有屏幕都在 `ScreenManager` 中注册。切换屏幕并刷新显示：

```
# 切换到设置屏幕
calculator.screen_manager.switch_current_screen("setting")

# 强制触发当前屏幕重绘
calculator.render()
```

### 3. 数学引擎求值

引擎负责将字符串变为 AST，并在给定的上下文（`env`，包含变量与角度制）中完成化简：

```
# 获取化简后的节点（保留结构，如 1/3 仍为 FractionNode）
result_node, error = calculator.engine.calculate("sin(30)")

if not error:
    print(result_node.to_str()) # 输出: "1 / 2"

# 若要强制转小数：
value = result_node.evaluate(calculator.engine.context)
```

### 4. 翻译

UI 层渲染文本时，统一调用 `Settings` 的翻译接口：

```
# 根据当前用户设置的语言（EN/CH/JP）返回对应文本
text = calculator.settings.tr("reset_title")
```

---

## 三、项目未来版本展望

#### v0.5.x 2D 自然渲染引擎

**重构显示层：** 现有的渲染器是将字符串堆砌在屏幕上。未来的目标是引入 `DrawElement` 与排版引擎。针对 `MathI` 模式，将实现在 Canvas 上绘制真正的二维数学公式：分数的上下结构、根号的横线覆盖、幂指数的上标悬浮。该重构是后续一切高级 UI 功能的基础。

#### v0.6.x 设置联动

**完善设置功能：** 让 `Fix/Sci/Norm` 的小数位控制、复数输出格式真正影响引擎输出。

#### v0.6.x 深度按键扩充

**实现更多物理按键：** 借助现有的扁平列表与结构标记，轻松添加“绝对值 (Abs)”、“分数 (\(\frac{a}{b}\))”、“科学计数法 (\(\times10^x\))”等按键。新增按键将全部通过 `FormulaNode` 的结构标记实现，无需修改底层 Parser。

#### v0.8.x 数学引擎进阶

**从计算器走向计算机代数系统：** 扩展 `mathmatics.py`，引入更多复杂的 `Node` 与算法。
 计划支持：

- **微积分：** 数值求导、定积分计算。
- **方程求解：** 基于牛顿迭代法的一元方程求根。
- **数论功能：** 素因子分解。

#### v1.0.0+ 终极形态与移动端

**填补遗憾：** 全面支持复数运算（使用内置的 `ComplexNode`），修复边缘小问题。

 **跨平台：** 剥离 Tkinter 依赖，使用 Kivy / BeeWare 重写表现层，将这套纯粹的 Python 数学引擎和 ScreenManager 移植为 Android 移动端 App。