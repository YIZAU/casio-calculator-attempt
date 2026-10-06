# ArcTrigNode 机制文档

本文档说明 `mathmatics.py` 中反三角函数节点的设计：签名提取、特殊值查表、负号变换与角度制输出。

---

## 一、职责与定位

### 1.1 三个函数的统一承载

| 函数 | 定义域 | 值域（RAD） |
| --- | --- | --- |
| arcsin(x) | [-1, 1] | [-π/2, π/2] |
| arccos(x) | [-1, 1] | [0, π] |
| arctan(x) | (-∞, +∞) | (-π/2, π/2) |

三个函数共享同一个类，因为它们的输入输出结构相同：**输入是数值，输出是角度**。

### 1.2 与 TrigNode 的对比

| 维度 | TrigNode | ArcTrigNode |
| --- | --- | --- |
| 输入 | 角度 | 数值（比值） |
| 输出 | 数值（比值） | 角度 |
| 转换方向 | 输入侧：度 → 弧度 | 输出侧：弧度 → 度 |
| 签名来源 | π 的有理倍数 | 根式的线性组合 |
| 查表键 | (p, q) | ("combo", frozenset) |

**镜像关系**

：TrigNode 的输入是 "角度"，ArcTrigNode 的输出是 "角度"。两者都需要

`angle_unit`

 参与，但转换方向相反。

---

## 二、数据结构

```
class ArcTrigNode(Node):
    __slots__ = ("name", "argument")

    def __init__(self, name: str, argument: Node):
        self.name = name
        self.argument = argument
```

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| name | str | "arcsin" / "arccos" / "arctan" |
| argument | Node | 输入的数值表达式 |

---

## 三、核心：值签名

### 3.1 为什么需要签名

表查找需要一个**可哈希、可比较、顺序无关**的键。Node 本身不满足这个条件（没有 `__hash__`，没有 `__eq__`）。所以把 Node 转换成规范化的签名。

### 3.2 统一格式：`("combo", frozenset)`

```
("combo", frozenset({(p, q, n), ...}))
```

每一项 `(p, q, n)` 表示 `(p/q)·√n`。整个值 = 各项之和。`n = 1` 时退化为有理数。

| 值 | 签名 |
| --- | --- |
| 0 | ("combo", frozenset({(0, 1, 1)})) |
| 1 | ("combo", frozenset({(1, 1, 1)})) |
| 1/2 | ("combo", frozenset({(1, 2, 1)})) |
| √2/2 | ("combo", frozenset({(1, 2, 2)})) |
| √3/2 | ("combo", frozenset({(1, 2, 3)})) |
| √3 | ("combo", frozenset({(1, 1, 3)})) |
| √3/3 | ("combo", frozenset({(1, 3, 3)})) |
| (√6 - √2)/4 | ("combo", frozenset({(1, 4, 6), (-1, 4, 2)})) |
| (√6 + √2)/4 | ("combo", frozenset({(1, 4, 6), (1, 4, 2)})) |
| 2 - √3 | ("combo", frozenset({(2, 1, 1), (-1, 1, 3)})) |

### 3.3 规范化流程

Node

 ↓ _expand_to_terms

[(p, q, n),...]

 原始终端项（可能有同类项） ↓ _merge_terms

[(p, q, n),...]

 已合并、已约分、已去零 ↓ frozenset

("combo", frozenset)

 最终签名

---

## 四、递归展开 `_expand_to_terms`

把任意 Node 展开成项列表。遇到不支持的结构返回 `None`。

### 4.1 支持的形态

| 输入 | 展开结果 | 说明 |
| --- | --- | --- |
| IntegerNode(3) | [(3, 1, 1)] | 3 = 3/1 |
| FractionNode(1, 2) | [(1, 2, 1)] | 1/2 |
| RootNode(2, 8) | [(2, 1, 2)] | √8 = 2√2，自动提取平方因子 |
| NegativeNode(√2) | [(-1, 1, 2)] | 每项取反 |
| √2 + √3 | [(1, 1, 2), (1, 1, 3)] | 拼接 |
| √2 - √3 | [(1, 1, 2), (-1, 1, 3)] | 右侧取反 |
| √2 · √3 | [(1, 1, 6)] | 根号合并为 √6 |
| 2√2 · 3√3 | [(6, 1, 6)] | 系数与根号分别合并 |
| (√6 - √2) / 4 | [(1, 4, 6), (-1, 4, 2)] | 分母缩放 |

### 4.2 不支持的形态

| 输入 | 结果 | 原因 |
| --- | --- | --- |
| ³√2 | None | 非平方根 |
| VariableNode("x") | None | 变量不在签名范围 |
| EulerNode() | None | 超越数 |
| PiNode() | None | 超越数 |
| LogNode(...) | None | 不是代数数 |
| PowerNode(2, 1/2) | 通常已转为 RootNode | 若能转成 RootNode 就能展开 |
| FractionNode(x, 2) | None | 分母是有理数但分子不是可展开的结构 |

### 4.3 分母的处理

```
if isinstance(node, FractionNode):
    if not isinstance(node.den, IntegerNode):
        return None
    d = node.den.value
    if d == 0:
        return None
    num_terms = self._expand_to_terms(node.num)
    if num_terms is None:
        return None
    return [(p, q * d, n) for p, q, n in num_terms]
```

分母必须是整数。分子递归展开后，每项的 `q` 乘以分母。

**为什么分母不能含根号**

：ArcTrigNode 的输入经过 FractionNode 有理化，分母不会含根号。若真遇到，说明上游有问题，返回

`None`

 保留原节点更安全。

---

## 五、合并同类项 `_merge_terms`

把相同根号 `n` 的项相加，分数通分，结果约分。

```
def _merge_terms(self, terms):
    acc = {}                       # n -> (p, q)
    for p, q, n in terms:
        if n not in acc:
            acc[n] = (0, 1)
        ap, aq = acc[n]
        new_p = ap * q + p * aq    # p/q + ap/aq
        new_q = aq * q
        g = math.gcd(abs(new_p), abs(new_q)) or 1
        acc[n] = (new_p // g, new_q // g)

    result = []
    for n, (p, q) in acc.items():
        if p == 0:
            continue               # 丢弃零项
        if q < 0:
            p, q = -p, -q          # 分母为正
        result.append((p, q, n))
    return result
```

### 5.1 合并示例

| 输入项 | 合并后 |
| --- | --- |
| [(1, 2, 2), (1, 2, 2)] | [(1, 1, 2)]（√2/2 + √2/2 = √2） |
| [(1, 1, 2), (-1, 1, 2)] | []（抵消为零，由上层补 (0,1,1)） |
| [(1, 4, 6), (-1, 4, 2)] | [(1, 4, 6), (-1, 4, 2)]（无同类项） |

---

## 六、平方因子提取 `_extract_square_factor`

把整数 `n` 分解为 `outside² · inside`，`inside` 无平方因子。

```
def _extract_square_factor(n: int) -> tuple:
    if n <= 0:
        return (1, 1)
    outside, inside = 1, n
    i = 2
    while i * i <= inside:
        while inside % (i * i) == 0:
            outside *= i
            inside //= i * i
        i += 1
    return outside, inside
```

| 输入 | 输出 | 含义 |
| --- | --- | --- |
| 8 | (2, 2) | √8 = 2√2 |
| 12 | (2, 3) | √12 = 2√3 |
| 18 | (3, 2) | √18 = 3√2 |
| 6 | (1, 6) | √6 已最简 |
| 1 | (1, 1) | √1 = 1 |
| 72 | (6, 2) | √72 = 6√2 |

---

## 七、特殊值表

键是签名，值是 `{name: (p, q)}`，表示输出 `(p/q)·π`。

| 值 | arcsin | arccos | arctan |
| --- | --- | --- | --- |
| 0 | 0 | π/2 | 0 |
| 1/2 | π/6 | π/3 | — |
| √2/2 | π/4 | π/4 | — |
| √3/2 | π/3 | π/6 | — |
| 1 | π/2 | 0 | π/4 |
| √3/3 | — | — | π/6 |
| √3 | — | — | π/3 |
| (√6 - √2)/4 | π/12 | 5π/12 | — |
| (√6 + √2)/4 | 5π/12 | π/12 | — |
| 2 - √3 | — | — | π/12 |
| 2 + √3 | — | — | 5π/12 |

**"—" 的含义**

：该函数在此值下不是特殊角。

`arctan(1/2)`

 不是 π 的有理倍数，所以不填。

**表的局限**

：只收录能用根式精确表示的值。像

`arcsin(0.3)`

 这样的输入会保留为原节点。

---

## 八、化简流程

### 8.1 主流程

```
simplify(env)
  ├── arg = argument.simplify(env)
  │
  ├── 剥离负号
  │     if isinstance(arg, NegativeNode):
  │         arg = arg.child
  │         negated = True
  │
  ├── sig = _value_signature(arg)
  │     if sig is None: return _rebuild(arg, negated)
  │
  ├── entry = _SPECIAL_VALUES.get(sig)
  │     if entry is None or entry[name] is None: return _rebuild(arg, negated)
  │
  ├── p, q = entry[name]
  │
  ├── 负输入变换
  │     if negated:
  │         if name == "arccos": p = q - p
  │         else: p = -p
  │
  └── 按 angle_unit 输出
        RAD: _make_pi_node(p, q)
        DEG: (p·180 / q)
        GRA: (p·200 / q)
```

### 8.2 负号变换表

| 函数 | 性质 | 变换 |
| --- | --- | --- |
| arcsin | 奇函数：arcsin(-x) = -arcsin(x) | p → -p |
| arctan | 奇函数：arctan(-x) = -arctan(x) | p → -p |
| arccos | 余函数：arccos(-x) = π - arccos(x) | p → q - p（即 (q-p)/q·π = π - (p/q)·π） |

### 8.3 角度制转换

| angle_unit | 输出 |
| --- | --- |
| RAD | (p/q)·π，通过 _make_pi_node 构造 |
| DEG | (p·180/q) 度，自动约分 |
| GRA | (p·200/q) 梯度，自动约分 |

---

## 九、完整示例

### 9.1 `arcsin(1/2)` = π/6

1.

`arg = FractionNode(1, 2).simplify()`

 →

`FractionNode(1, 2)`

 2. 不是 NegativeNode，negated = False

 3.

`_value_signature`

:

 _expand_to_terms →

`[(1, 2, 1)]`

 _merge_terms →

`[(1, 2, 1)]`

 →

`("combo", frozenset({(1, 2, 1)}))`

 4. 查表 →

`(1, 6)`

 5. angle_unit = RAD，_make_pi_node(1, 6) →

`FractionNode(PiNode(), IntegerNode(6))`

**输出**：`π/6`

### 9.2 `arccos(-1/2)` = 2π/3

1.

`arg = NegativeNode(FractionNode(1, 2))`

 2. 剥离负号：arg =

`FractionNode(1, 2)`

，negated = True

 3.

`_value_signature`

 →

`("combo", frozenset({(1, 2, 1)}))`

 4. 查表 name = "arccos" →

`(1, 3)`

 5. negated = True 且 name = "arccos"：

 p, q = 3 - 1, 3 →

`(2, 3)`

 6. _make_pi_node(2, 3) →

`FractionNode(2π, 3)`

**输出**：`2π/3`

### 9.3 `arctan(2 - √3)` = π/12

1.

`arg = BinaryOpNode(2, √3, "-").simplify()`

 → 保留

 2.

`_expand_to_terms`

:

 左：

`[(2, 1, 1)]`

 右：

`[(1, 1, 3)]`

，取反得

`[(-1, 1, 3)]`

 拼接 →

`[(2, 1, 1), (-1, 1, 3)]`

 3.

`_merge_terms`

 →

`[(2, 1, 1), (-1, 1, 3)]`

 4. 签名：

`("combo", frozenset({(2, 1, 1), (-1, 1, 3)}))`

 5. 查表 name = "arctan" →

`(1, 12)`

 6. RAD →

`FractionNode(PiNode(), IntegerNode(12))`

**输出**：`π/12`

### 9.4 `arcsin(√8/2)` = π/4

1.

`arg = FractionNode(√8, 2)`

，√8 已化简为 2√2

 实际结构是

`FractionNode(BinaryOpNode(2, √2, "*"), IntegerNode(2))`

 2.

`_expand_to_terms`

:

 分母 2，分子展开得

`[(2, 1, 2)]`

 缩放 →

`[(2, 2, 2)]`

 3.

`_merge_terms`

：约分 (2, 2) → (1, 1)，得

`[(1, 1, 2)]`

**陷阱**

：如果 (2, 2, 2) 不约分，签名会变成

`frozenset({(2, 2, 2)})`

， 而表里存的是

`frozenset({(1, 2, 2)})`

，匹配失败。

`_merge_terms`

 里的

`math.gcd(abs(p), q)`

 一步保证约分，这是关键。

### 9.5 `arcsin(0.3)`

1.

`arg = DecimalNode(0.3)`

 2.

`_expand_to_terms`

 不处理 DecimalNode，返回 None

 3. sig = None

 4. 返回

`_rebuild(arg, False)`

 =

`self`

**输出**：保留为 `arcsin(0.3)`，由上层决定是否转数值。

---

## 十、数值求值 `evaluate`

```
def evaluate(self, env=None) -> float:
    env = env or {}
    arg = self.argument.evaluate(env)
    au = env.get("angle_unit", "RAD")

    if self.name == "arcsin":
        if arg < -1 or arg > 1:
            raise ValueError("Math Error: arcsin domain is [-1, 1]")
        rad = math.asin(arg)
    elif self.name == "arccos":
        if arg < -1 or arg > 1:
            raise ValueError("Math Error: arccos domain is [-1, 1]")
        rad = math.acos(arg)
    elif self.name == "arctan":
        rad = math.atan(arg)
    else:
        raise ValueError(f"Unknown inverse trig function: {self.name}")

    if au == "DEG":
        return math.degrees(rad)
    if au == "GRA":
        return rad / math.pi * 200
    return rad
```

### 10.1 与 simplify 的关系

**两条路径完全独立**

：

`simplify`

 走符号路径，返回 Node，命中特殊值时返回精确形式。

`evaluate`

 走数值路径，返回 float。

 两者之间没有调用关系。

### 10.2 定义域检查

| 函数 | 检查 | 违反时 |
| --- | --- | --- |
| arcsin / arccos | -1 ≤ arg ≤ 1 | 抛 ValueError |
| arctan | 无限制 | — |

### 10.3 输出侧转换

| angle_unit | 转换 |
| --- | --- |
| RAD | 直接返回弧度 |
| DEG | math.degrees(rad) |
| GRA | rad / π * 200 |

---

## 十一、测试用例

| 输入 | angle_unit | 预期输出 | 命中路径 |
| --- | --- | --- | --- |
| arcsin(0) | RAD | 0 | 签名 (0,1,1)，查表 |
| arcsin(1/2) | RAD | π/6 | 签名 (1,2,1)，查表 |
| arcsin(√2/2) | RAD | π/4 | 签名 (1,2,2)，查表 |
| arcsin(√3/2) | RAD | π/3 | 签名 (1,2,3)，查表 |
| arcsin(1) | RAD | π/2 | 签名 (1,1,1)，查表 |
| arccos(0) | RAD | π/2 | 签名 (0,1,1)，查表 |
| arctan(1) | RAD | π/4 | 签名 (1,1,1)，查表 |
| arctan(√3) | RAD | π/3 | 签名 (1,1,3)，查表 |
| arctan(√3/3) | RAD | π/6 | 签名 (1,3,3)，查表 |
| arcsin(-1/2) | RAD | -π/6 | 剥离负号 + p 取反 |
| arccos(-1/2) | RAD | 2π/3 | 剥离负号 + p → q - p |
| arctan(2 - √3) | RAD | π/12 | 签名 (2,1,1),(-1,1,3) |
| arcsin(√8/2) | RAD | π/4 | 约分 (2,2) → (1,2,2) |
| arcsin(1/2) | DEG | 30 | RAD 结果 × 180/π |
| arcsin(1/2) | GRA | 100/3 | RAD 结果 × 200/π |
| arcsin(0.3) | RAD | arcsin(0.3) | 签名失败，保留 |
| arcsin(2) | — | 抛定义域错误 | evaluate 检查 |

---

## 十二、局限与限制

| 情形 | 状态 | 原因 |
| --- | --- | --- |
| arcsin(0.3) | 保留 | 无法用根式表示，签名失败 |
| arcsin(³√2) | 保留 | 非平方根，_expand_to_terms 返回 None |
| arcsin(1/(√6+√2)) | 部分处理 | FractionNode 有理化后变成 (√6-√2)/4，签名能识别 |
| arcsin(π/6) | 保留 | π 不是代数数，不在签名范围 |
| RAD 下 arctan(1/2) | 保留 | 1/2 不是特殊值 |
| DEG 下 arcsin(1/2) | 30 | 先算 RAD 结果再乘以 180 |
| arcsin(√6/4 + √2/4) | 5π/12 | 签名合并后得到 (√6+√2)/4 |

**与卡西欧的对比**

：

 卡西欧的 DEG 模式下

`arcsin(0.5)`

 直接显示

`30`

，而不是先算 π/6 再乘。

 本设计通过先算 RAD 结果再转角度，得到同样的输出，且只维护一套特殊值表。

---

## 十三、辅助方法

### 13.1 `_make_pi_node(p, q)`

```
def _make_pi_node(self, p: int, q: int) -> Node:
    if p == 0:
        return IntegerNode(0)
    g = math.gcd(abs(p), q) or 1
    p, q = p // g, q // g
    if q < 0:
        p, q = -p, -q

    numerator = PiNode() if abs(p) == 1 else BinaryOpNode(IntegerNode(abs(p)), PiNode(), "*")
    result: Node = numerator if q == 1 else FractionNode(numerator, IntegerNode(q))
    return NegativeNode(result) if p < 0 else result
```

构造 `(p/q)·π`：

 +

`p = 0`

 →

`0`

 +

`p = ±1, q = 1`

 →

`±π`

 +

`p = 1, q = 6`

 →

`π/6`

 +

`p = 5, q = 12`

 →

`5π/12`

 +

`p = -1, q = 6`

 →

`-π/6`

### 13.2 `_rebuild(arg, negated)`

```
def _rebuild(self, arg: Node, negated: bool) -> Node:
    if negated:
        arg = NegativeNode(arg)
    if arg is self.argument:
        return self
    return ArcTrigNode(self.name, arg)
```

未命中时构造返回值。若 `arg` 未被修改（原样返回），则返回 `self`，避免无谓构造。

---

## 十四、设计总结

> **ArcTrigNode 是 TrigNode 的镜像**
>
> ：
>
>  输入是数值，输出是角度，
>
>  签名格式统一为
>
> `("combo", frozenset({(p, q, n), ...}))`
>
> ，
>
>  通过
>
> `_expand_to_terms → _merge_terms → frozenset`
>
>  三步规范化，
>
>  负号在查表前后处理，
>
>  RAD 下输出 π 形式，DEG / GRA 下转换成度数 / 梯度。

### 14.1 设计亮点

 + **统一签名格式**：`("combo", frozenset)` 覆盖了有理数、单项根式、根式线性组合三类形态。 + **自动规范化**：`√8/2` 和 `√2` 得到同一签名，`√2/2 + √2/2` 合并为 `√2`。 + **路径独立**：`simplify` 走符号，`evaluate` 走数值，两者不互相调用。 + **负号处理清晰**：先剥离，再查表，最后按函数奇偶性变换。 + **角度制转换统一**：所有输出先按 RAD 得到 `(p, q)`，再由 `angle_unit` 决定最终形式。

### 14.2 局限

 + 无法处理不能用根式精确表示的值（如 `arcsin(0.3)`）。 + 无法处理超越数输入（如 `arcsin(π/6)`）。 + 无法处理非平方根的根式（如 `arcsin(³√2)`）。 + 特殊值表只收录第一象限的基础角。

### 14.3 与 TrigNode 的对称性

| 环节 | TrigNode | ArcTrigNode |
| --- | --- | --- |
| 签名来源 | π 的有理倍数 (p, q) | 根式线性组合 (p, q, n) |
| 归约 | p % (2q) 归到第一象限 | 无（值本身不分象限） |
| 符号处理 | 象限 signs 元组 | 剥离 NegativeNode + 按函数奇偶 |
| 输出 | 数值 Node（如 √2/2） | 角度 Node（如 π/6） |
| 角度制参与 | 输入侧（度 → 弧度） | 输出侧（弧度 → 度） |