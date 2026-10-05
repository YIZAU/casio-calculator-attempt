# LogNode 机制文档

本文档说明 `mathmatics.py` 中对数运算节点的设计、化简流水线、辅助工具，以及与 PowerNode / RootNode 的关系。

---

## 一、职责与定位

### 1.1 单一类承载 ln 与 log_b

| 函数 | base 字段 | to_str 输出 |
| --- | --- | --- |
| ln(x) | None（内部转成 EulerNode()） | ln(x) |
| log_b(x) | Node | base(b)log(x) |

**为什么合并**：`ln` 和 `log_b` 共享全部化简规则（`log(1)=0`、`log(底)=1`、`log(底^k)=k`），唯一的区别是底是不是常量 e。把底作为可选字段，一个类就足够。

### 1.2 与其他节点的一致性

| 节点 | 语义 |
| --- | --- |
| PowerNode | 幂运算 |
| RootNode | 根号 |
| TrigNode | 三角函数 |
| ArcTrigNode | 反三角函数 |
| LogNode | 对数 |
| CombinatoricNode | 排列组合 |

每个节点对应一类数学运算，各自拥有独立的化简流水线。

---

## 二、数据结构

```
class LogNode(Node):
    __slots__ = ("base", "argument")

    def __init__(self, argument: Node, base: Node = None):
        self.base = base if base is not None else EulerNode()
        self.argument = argument
```

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| base | Node | 底数。默认 EulerNode()，表示自然对数 |
| argument | Node | 真数（被取对数的值） |

**约定**

：

`isinstance(self.base, EulerNode)`

 是"是否为自然对数"的唯一判定。 不要在

`base`

 字段里存

`None`

，否则每次都要检查 None。

---

## 三、化简流水线

### 3.1 主流程

```
simplify(env)
  ├── b = base.simplify(env)
  ├── a = argument.simplify(env)
  │
  ├── for fold in (
  │       _fold_trivial,
  │       _fold_power_argument,
  │       _fold_numeric,
  │   ):
  │       result = fold(b, a, env)
  │       if result is not None:
  │           return result
  │
  └── return self 或 LogNode(a, b)
```

### 3.2 折叠顺序

L0

 _fold_trivial 平凡规则（log(1)=0, log(底)=1）

L1

 _fold_power_argument 指数提取（log(底^k)=k, log(x^k)=k·n）

L2

 _fold_numeric 数值匹配（整数、分数、小数）

**顺序原则**：结构识别优先，数值匹配兜底。指数提取依赖 `PowerNode` 结构，若先做数值匹配，`1.21^3` 会被算成 `1.771561`，丢失结构信息。

### 3.3 `_fold_trivial`

| 条件 | 结果 |
| --- | --- |
| a == 1（IntegerNode(1)） | IntegerNode(0) |
| _structurally_equal(a, b) | IntegerNode(1) |

**例**：

- `ln(1) = 0`
- `ln(e) = 1`（结构相等）
- `log_2(1) = 0`
- `log_2(2) = 1`

### 3.4 `_fold_power_argument`

处理 `log_b(x^k)`，仅当 `k` 是整数。这是本节点最核心的折叠。

```
log_b(b^k) = k                  (x 与 b 结构相等)
log_b(x^k) = k · n              (x 是 b 的 n 次幂)
```

| 输入 | x, b 关系 | 结果 |
| --- | --- | --- |
| ln(e^3) | x = e, b = e，结构相等 | 3 |
| log_2(2^5) | 结构相等 | 5 |
| log_{1.1}(1.21^3) | 1.21 = 1.1^2 | 3 * 2 = 6 |
| log_2(8^3) | 8 = 2^3 | 3 * 3 = 9 |

### 3.5 `_fold_numeric`

处理数值型 argument 与 base。跳过 `EulerNode`（ln 不做数值匹配）。

| 输入 | 匹配方式 | 结果 |
| --- | --- | --- |
| log_2(8) | 整数对整数：(8, 1) vs (2, 1) | 3 |
| log_{1/2}(1/8) | 分数对分数：(1, 8) vs (1, 2) | 3 |
| log_{1.1}(1.21) | 小数转有理数：(121, 100) vs (11, 10) | 2 |
| log_2(10) | 无法匹配 | 保留为 LogNode |

---

## 四、模块级工具函数

### 4.1 `_integer_power(a, b)`

判断 `a == b^n`，返回 `n` 或 `None`。

```
def _integer_power(a: int, b: int) -> int | None:
    if a < 1 or b < 2:
        return None
    if a == 1:
        return 0
    est = math.log(a) / math.log(b)
    n = round(est)
    for dn in (-1, 0, 1):
        cand = n + dn
        if 0 <= cand <= _MAX_LOG_EXP and b ** cand == a:
            return cand
    return None
```

**核心思想**：对数估值定位候选值，然后对 `n-1, n, n+1` 精确验证。浮点误差只影响初值，精确验证保证正确。

**与 `_integer_nth_root` 的对比**

：

`_integer_nth_root`

 用二分法求"x 的 n 次根"，用于 PowerNode/RootNode。

`_integer_power`

 用估值法求"a 是 b 的几次幂"，用于 LogNode。

 两者方向相反，不能互相复用。

### 4.2 `_rational_power_match(a, b)`

分数版本的幂匹配。判断有理数 `a` 是否等于有理数 `b` 的整数次幂。

```
def _rational_power_match(a: tuple, b: tuple) -> int | None:
    a_num, a_den = a
    b_num, b_den = b
    if a_num <= 0 or a_den <= 0 or b_num <= 0 or b_den <= 0:
        return None
    n1 = _integer_power(a_num, b_num)
    n2 = _integer_power(a_den, b_den)
    if n1 is None or n2 is None:
        return None
    return n1 if n1 == n2 else None
```

分子分母分别求幂次，两者相等才算匹配。

**例**：

- `(121, 100) vs (11, 10)`：`11² = 121`, `10² = 100`，返回 `2`
- `(8, 27) vs (2, 3)`：`2³ = 8`, `3³ = 27`，返回 `3`
- `(4, 9) vs (2, 3)`：`2² = 4`, `3² = 9`，返回 `2`

### 4.3 `_decimal_to_ratio(value)`

把浮点数转成精确有理数元组，不依赖 `decimal` 模块，纯字符串解析。

```
def _decimal_to_ratio(value: float) -> tuple | None:
    if not math.isfinite(value):
        return None
    s = str(value)
    # 处理科学计数法、普通小数、整数三种情况
    ...
    g = math.gcd(abs(num), den) or 1
    return (num // g, den // g)
```

**关键**

：用

`str(value)`

 而不是直接浮点运算。

`str(1.1)`

 返回

`"1.1"`

，Python 保证

`float(str(x)) == x`

， 所以字符串表示是精确的十进制形式。

 如果直接对

`1.1`

 做算术，会得到

`1.1000000000000001`

。

| 输入 | 输出 |
| --- | --- |
| 1.1 | (11, 10) |
| 0.25 | (1, 4) |
| -0.5 | (-1, 2) |
| 1e-3 | (1, 1000) |
| 5 | (5, 1) |

### 4.4 `_structurally_equal(a, b)`

结构比较，替代 `==` 运算符。Node 未实现 `__eq__`，默认比较对象身份，不能用 `==`。

```
def _structurally_equal(a: Node, b: Node) -> bool:
    if type(a) is not type(b):
        return False
    if isinstance(a, (IntegerNode, DecimalNode)):
        return a.value == b.value
    ...
```

递归比较各字段，覆盖所有节点类型。

---

## 五、完整路径示例

### 5.1 `log_{1.1}(1.21^3)` = 6

输入 AST：

```
LogNode(
    argument = PowerNode(DecimalNode(1.21), IntegerNode(3)),
    base     = DecimalNode(1.1)
)
```

化简步骤：

1. `b = DecimalNode(1.1)`（已是叶子）
2. `a = PowerNode(...).simplify()`：
 PowerNode 底数 `1.21` 是小数、指数 `3` 是整数， 走 `_fold_fraction_base` → `_transform_to_root` 路径。 **但这里有个陷阱**：如果 PowerNode 直接把 `1.21^3` 算成 `1.771561`， 那 LogNode 就看不到 PowerNode 结构了。
3. 为解决这个问题，**`_fold_power_argument` 需要在 `a = argument.simplify()` 之前检查原始结构**。

**当前实现的取舍**

：

`simplify`

 里先做了

`a = self.argument.simplify(env)`

。 如果 PowerNode 的

`_fold_fraction_base`

 遇到小数底时不折叠（保留为

`PowerNode(DecimalNode(1.21), 3)`

）， 那么

`_fold_power_argument`

 就能正确识别。

正确的折叠流程：

1. PowerNode 化简后仍保留为 `PowerNode(DecimalNode(1.21), IntegerNode(3))`
2. 进入 `_fold_power_argument`：

### 5.2 `log_2(8)` = 3

```
LogNode(
    argument = IntegerNode(8),
    base     = IntegerNode(2)
)
```

1. `_fold_trivial`：`a!= 1`，`_structurally_equal(8, 2)` → False
2. `_fold_power_argument`：`a` 不是 PowerNode，跳过
3. `_fold_numeric`：`(8, 1)` vs `(2, 1)` → `_integer_power(8, 2) = 3` → 返回 `IntegerNode(3)`

### 5.3 `ln(e^3)` = 3

```
LogNode(
    argument = PowerNode(EulerNode(), IntegerNode(3)),
    base     = EulerNode()  # 默认
)
```

1. `_fold_trivial`：`a` 不是 `IntegerNode(1)`，`_structurally_equal(PowerNode, EulerNode)` → False
2. `_fold_power_argument`：
    - `k = 3`, `x = EulerNode()`, `b = EulerNode()`
    - `_structurally_equal(x, b)` → True
    - 返回 `IntegerNode(3)`

---

## 六、测试用例

| 输入 | 预期输出 | 命中路径 |
| --- | --- | --- |
| ln(1) | 0 | _fold_trivial |
| ln(e) | 1 | _fold_trivial（结构相等） |
| ln(e^3) | 3 | _fold_power_argument |
| ln(2) | ln(2) | 保留 |
| log_2(1) | 0 | _fold_trivial |
| log_2(2) | 1 | _fold_trivial |
| log_2(2^5) | 5 | _fold_power_argument |
| log_2(8) | 3 | _fold_numeric |
| log_2(10) | log_2(10) | 保留 |
| log_{1.1}(1.21) | 2 | _fold_numeric |
| log_{1.1}(1.21^3) | 6 | _fold_power_argument |
| log_{1/2}(1/8) | 3 | _fold_numeric |
| log_{-2}(4) | 抛 MathError | evaluate 检查 base > 0 |
| log_1(5) | 抛 MathError | evaluate 检查 base!= 1 |

---

## 七、边界与限制

### 7.1 已处理

- 整数底、分数底、小数底
- PowerNode 结构识别（`x == b^k` 的两种路径）
- 负数、零底、底等于 1 的检测（`evaluate` 时）
- ln 与 log_b 的统一处理

### 7.2 未处理

| 情形 | 原因 |
| --- | --- |
| log_b(x·y) = log_b(x) + log_b(y) | 跨节点规则，属于 BinaryOpNode 的代数化简 |
| log_b(x^k) = k·log_b(x)（x ≠ b） | 会引入系数结构，让表达式更复杂，留给代数化简层 |
| 换底公式 log_b(x) = ln(x) / ln(b) | 不主动做，避免表达式膨胀 |
| 符号底 log_x(x^3) | 如果 x 是变量，_structurally_equal 能命中，返回 3 |
| 符号底 log_x(y^2) | 需要符号求根，超出范围 |

### 7.3 依赖 PowerNode 的化简策略

**关键依赖**

：LogNode 依赖 PowerNode 在遇到"小数底 + 整数指"时

**保留为 PowerNode**

，不要提前算成数值。 否则 LogNode 的

`_fold_power_argument`

 无法识别

`x^k`

 结构。

如果未来 PowerNode 的策略变更，LogNode 需要相应调整：在 `simplify` 开头先检查未化简的 `self.argument` 是否为 PowerNode。

---

## 八、与其他节点的关系

### 8.1 与 PowerNode 的对比

| 维度 | PowerNode | LogNode |
| --- | --- | --- |
| 已知 | 底数、指数 | 底数、真数 |
| 求 | 幂值 | 指数 |
| 核心工具 | _integer_nth_root | _integer_power |
| 折叠方向 | 求根、分解因子 | 求幂次、匹配结构 |
| 能否互相复用 | 不能。方向相反，只有"估值 + 精确验证"的思路相同 |

### 8.2 与 EulerNode 的关系

`EulerNode` 既作为 `ln` 的底，也作为其他表达式的常量。当 `LogNode.base` 是 `EulerNode` 时，走 `ln` 语义。

---

## 九、总结

> **LogNode 用一个类承载 ln 和 log_b**
>
> ，
>
> **通过三个折叠方法（trivial / power_argument / numeric）实现化简**
>
> ，
>
> **依赖四个模块级工具（_integer_power / _rational_power_match / _decimal_to_ratio / _structurally_equal）**
>
> ，
>
> **与 PowerNode 方向相反，只有设计思想同源**
>
> 。

关键点：

- **一个类一个语义**：ln 和 log_b 共享全部规则，无需分开。
- **结构识别优先**：`_fold_power_argument` 在数值匹配之前，保证 `1.21^3` 这样的结构不被提前数值化。
- **估值 + 精确验证**：`_integer_power` 不依赖浮点精度，只用浮点定初值。
- **字符串解析浮点**：`_decimal_to_ratio` 用 `str(value)` 保证 `1.1` 得到 `(11, 10)` 而非二进制近似。