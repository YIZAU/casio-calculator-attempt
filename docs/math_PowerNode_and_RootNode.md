# PowerNode 与 RootNode 机制文档

本文档说明 `mathmatics.py` 中幂运算节点与根号运算节点的设计、化简流水线、辅助函数和相互转换规则。

---

## 一、职责与边界

### 1.1 两个节点的定位

| 节点 | 数学形式 | 输入字符串 |
| --- |------| --- |
| PowerNode | a^e  | a^(e) |
| RootNode | n√x  | deg(n)root(x) |

### 1.2 互不替代的原则

> **PowerNode 默认保持幂形式，RootNode 默认保持根号形式。**
>
>  两者只在数学化简必要时才互相转换，而不是无条件转换。

具体来说：

- `2^(1/2)` 会转成 `√2`，因为分数指数 `1/2` 的本质就是平方根。
- `(√2)^4` 会转成 `4`，因为 `(n√x)^m = x^(m/n)` 是结构化简。
- 但 `√2` **不会**被转成 `2^(1/2)`，因为那样会破坏 TrigNode 特殊值表里 `RootNode` 的结构依赖。

---

## 二、模块级辅助函数

PowerNode 和 RootNode 共用三个工具函数。它们放在模块级，不属于任何类。

### 2.1 `_integer_nth_root(x, n)`

求 `floor(x^(1/n))`，用二分法，**不依赖浮点**。

**为什么不用 `int(x ** (1/n))`？**

`27 ** (1/3)`

 在浮点下可能返回

`2.9999999999999996`

，

`int()`

 得到

`2`

， 但正确答案是

`3`

。大整数时浮点误差更严重。二分法永远精确。

```
def _integer_nth_root(x: int, n: int) -> int:
    if x < 0 or n <= 0:
        return 0
    if x < 2:
        return x
    lo, hi = 1, 1
    while hi ** n <= x:
        hi *= 2
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if mid ** n <= x:
            lo = mid
        else:
            hi = mid - 1
    return lo
```

**复杂度**：对 64 位整数在微秒级完成。

### 2.2 `_extract_nth_power(radicand, n)`

把整数 `radicand` 分解为 `outside^n · inside`，其中 `inside` 不含 `n` 次方因子。

```
def _extract_nth_power(radicand: int, n: int) -> tuple:
    if radicand <= 1:
        return radicand, 1
    outside, inside = 1, radicand
    i = 2
    while True:
        i_max = _integer_nth_root(inside, n)
        if i > i_max:
            break
        p = i ** n
        while inside % p == 0:
            outside *= i
            inside //= p
        i += 1
    return outside, inside
```

**关键点**：每次提取后重新计算 `i_max`，因为 `inside` 缩小了。这样避免循环到无意义的大 `i`。

#### 示例

| 输入 | n | 结果 (outside, inside) | 含义 |
| --- | --- | --- | --- |
| 8 | 2 | (2, 2) | √8 = 2√2 |
| 72 | 2 | (6, 2) | √72 = 6√2 |
| 24 | 3 | (2, 3) | ³√24 = 2·³√3 |
| 16 | 4 | (2, 1) | ⁴√16 = 2 |

### 2.3 `_int_pow(base, exp)`

整数底、整数指数的幂运算，含溢出保护。

```
def _int_pow(base: int, exp: int) -> Node | None:
    if exp == 0:
        return IntegerNode(1)
    if exp > 0:
        if exp > _MAX_INT_POWER:
            return None
        return IntegerNode(base ** exp)
    if base == 0:
        raise ZeroDivisionError("Math Error: division by zero")
    if -exp > _MAX_INT_POWER:
        return None
    return FractionNode(
        IntegerNode(1),
        IntegerNode(base ** (-exp)),
    ).simplify()
```

返回 `None` 表示"超出保护阈值，放弃折叠"。

### 2.4 `_extract_int_pair(frac)`

从 `FractionNode` 提取整数对 `(p, q)`，仅当分子分母都是 `IntegerNode` 且 `q > 0`。

**注意**

：这个函数

**只用于提取分数指数的 p 和 q**

，不是因子提取。因子提取用

`_extract_nth_power`

。

---

## 三、PowerNode 化简流水线

### 3.1 主流程

```
simplify(env)
  ├── b = base.simplify(env)
  ├── e = exp.simplify(env)
  │
  ├── for fold in (
  │       _fold_trivial,
  │       _fold_nested_power,
  │       _fold_root_power,
  │       _fold_negative_base,
  │       _fold_fraction_base,
  │       _fold_integer_base,
  │   ):
  │       result = fold(b, e, env)
  │       if result is not None:
  │           return result
  │
  └── return self 或 PowerNode(b, e)
```

### 3.2 折叠顺序的含义

L0

 _fold_trivial 平凡规则（0、1、-1 短路）

L1

 _fold_nested_power 嵌套幂 (a^m)^n

L2

 _fold_root_power 根号幂 (n√x)^m

L3

 _fold_negative_base 负数底 (-a)^e

L4

 _fold_fraction_base 分数底 (a/b)^e

L5

 _fold_integer_base 整数底 a^e

**顺序原则**：越早越简单。边界短路优先，结构改写次之，符号处理再次，数值折叠最后。

### 3.3 各折叠方法详解

#### 3.3.1 `_fold_trivial`

| 条件 | 结果 |
| --- | --- |
| e == 0 且 b!= 0 | IntegerNode(1) |
| e == 0 且 b == 0 | 抛 "0^0 is undefined" |
| e == 1 | 返回 b |
| b == 1 | IntegerNode(1) |
| b == -1，e 整数 | IntegerNode(±1) |
| b == 0，e > 0 | IntegerNode(0) |
| b == 0，e < 0 | 抛 "division by zero" |

#### 3.3.2 `_fold_nested_power`

处理 `(a^m)^n`，仅当 `m` 和 `n` 都是整数。

```
(a^m)^n = a^(m*n)   # 整数指数下恒成立
```

**为什么不处理分数指数？**

`((-8)^(1/3))^2`

 在复数主值下不等于

`((-8)^2)^(1/3)`

。涉及主值问题时保留原结构。

#### 3.3.3 `_fold_root_power`

处理 `(n√x)^m`，仅当 `n` 和 `m` 都是整数。

```
(n√x)^m = x^(m/n)
```

**示例**：

| 输入 | 中间结果 | 最终结果 |
| --- | --- | --- |
| (√2)^4 | 2^(4/2) → 2^2 | 4 |
| (³√2)^6 | 2^(6/3) → 2^2 | 4 |
| (√2)^3 | 2^(3/2) | 2√2（经 _fold_integer_base 转换） |

#### 3.3.4 `_fold_negative_base`

处理 `(-a)^e`，把负号从底数剥出来。

```
(-a)^e = (-1)^e · a^e
```

| e 类型 | 处理 |
| --- | --- |
| 整数 n | n 偶返回 inner，n 奇返回 -inner |
| 分数 p/q，q 偶 | 实数模式报错；复数模式返回 None（保留） |
| 分数 p/q，q 奇 | p 偶返回 inner，p 奇返回 -inner |

#### 3.3.5 `_fold_fraction_base`

处理 `(a/b)^e`，分子分母都是整数。

#### 整数指数

```
(a/b)^n = a^n / b^n     (n > 0)
(a/b)^n = b^|n| / a^|n| (n < 0)
```

#### 分数指数 p/q

分两条路径：

1. **完全 q 次方**：`a` 和 `b` 都是完全 q 次方时，直接算出精确结果。
2. **非完全 q 次方**：调 `_transform_to_root` 转成 `q√(...)` 形式。

#### 3.3.6 `_fold_integer_base`

处理正整数底 `a^e`。

#### 整数指数

调 `_int_pow`，带溢出保护。

#### 分数指数 p/q

1. **完全 q 次方**：`a` 是 `r^q` 时，返回 `r^p`。
2. **非完全 q 次方**：调 `_transform_to_root`。

### 3.4 `_transform_to_root`（核心新增）

把 `a^(p/q)` 转成 `q√(a^p)` 形式。这是 PowerNode 主动转换为 RootNode 的入口。

```
a^(p/q) → q√(a^p)          (p > 0)
a^(p/q) → 1 / q√(a^|p|)    (p < 0)
```

| 输入 | 转换路径 | 最终结果 |
| --- | --- | --- |
| 2^(1/2) | √(2^1) = √2 | √2 |
| 2^(3/2) | √(2^3) = √8 → 2√2 | 2√2 |
| 2^(-1/2) | 1 / √(2^1) | 1/√2 |
| 8^(1/3) | 完全 3 次方，不调此方法 | 2 |

**注意**

：只有整数底和分数底的两条分支会调用

`_transform_to_root`

。 其他底（如

`VariableNode`

、

`TrigNode`

）不参与此转换。

---

## 四、RootNode 化简流水线

### 4.1 主流程

```
simplify(env)
  ├── d = degree.simplify(env)
  ├── e = radicand.simplify(env)
  │
  ├── if d 不是正整数：return _rebuild(d, e)
  ├── n = d.value
  │
  ├── for fold in (
  │       _fold_trivial,
  │       _fold_nested_root,
  │       _fold_power_radicand,
  │       _fold_negative_radicand,
  │       _fold_fraction_radicand,
  │       _fold_integer_radicand,
  │   ):
  │       result = fold(n, e, env)
  │       if result is not None:
  │           return result
  │
  └── return _rebuild(d, e)
```

### 4.2 折叠顺序的含义

L0

 _fold_trivial n==1 或 e∈{0,1} 短路

L1

 _fold_nested_root 嵌套根号 (n·m)√x

L2

 _fold_power_radicand n√(x^m) 幂提取

L3

 _fold_negative_radicand 负 radicand

L4

 _fold_fraction_radicand 分数 radicand

L5

 _fold_integer_radicand 整数 radicand

### 4.3 各折叠方法详解

#### 4.3.1 `_fold_trivial`

| 条件 | 结果 |
| --- | --- |
| n == 1 | 返回 radicand（¹√x = x） |
| e == 0 | IntegerNode(0) |
| e == 1 | IntegerNode(1) |

#### 4.3.2 `_fold_nested_root`

```
n√(m√x) = (n·m)√x
```

展开后递归化简。

#### 4.3.3 `_fold_power_radicand`（支持部分提取）

处理 `n√(x^m)`，用 `divmod` 拆分。

```
m = q·n + r  (0 ≤ r < n)

n√(x^m) = x^q · n√(x^r)   (r > 0)
n√(x^m) = x^q              (r == 0)
```

| 输入 | q, r | 结果 |
| --- | --- | --- |
| √(x^2) | q=1, r=0 | x |
| √(x^3) | q=1, r=1 | x·√x |
| √(x^4) | q=2, r=0 | x^2 |
| √(x^5) | q=2, r=1 | x^2·√x |
| ³√(x^7) | q=2, r=1 | x^2·³√x |

#### 4.3.4 `_fold_negative_radicand`

```
n√(-x) = -n√x     (n 奇)
n√(-x) 抛错       (n 偶，实数模式)
n√(-x) 保留       (n 偶，复数模式)
```

#### 4.3.5 `_fold_fraction_radicand`

分母有理化：

```
n√(a/b) = n√(a·b) / b
```

步骤：

1. 确保 `b > 0`。
2. 记录 `a` 的符号，取绝对值。
3. `combined = |a| · b`，对它做因子提取。
4. 构造 `outside · n√inside / b`。
5. 若原来 `a` 是负数，按 n 奇偶处理符号。

#### 4.3.6 `_fold_integer_radicand`

整数 radicand 的因子提取。超过 `_MAX_RADICAND_FOR_FACTORING`（1010）时只做完全 n 次方判定。

```
outside, inside = _extract_nth_power(value, n)

inside == 1     → IntegerNode(outside)
outside == 1    → RootNode(n, inside)
否则            → outside · n√inside
```

---

## 五、PowerNode 与 RootNode 的转换约定

### 5.1 转换矩阵

| 输入形态 | 谁处理 | 输出 | 是否折叠 |
| --- | --- | --- | --- |
| (n√x)^m，m 被 n 整除 | PowerNode._fold_root_power | x^(m/n) | ✅ |
| (n√x)^m，m 不被 n 整除 | PowerNode._fold_root_power | x^(m/n)（分数指数） | ✅ |
| a^(p/q)，a 是完全 q 次方 | PowerNode._fold_integer_base | r^p | ✅ |
| a^(p/q)，a 不是完全 q 次方 | PowerNode._transform_to_root | q√(a^p) | ✅ |
| n√(x^m) | RootNode._fold_power_radicand | x^(m//n)·n√(x^(m%n)) | ✅ |

### 5.2 规范形式

> **规范形式是 RootNode**
>
> 。当幂运算的结果无法用整数或分数精确表示时，会转换成 RootNode 形式。

例如 `2^(1/2)` 不保留为幂，而是转成 `√2`。这样 TrigNode 特殊值表里构造的 `√2` 和用户输入的 `2^(1/2)` 会在化简后收敛到同一个结构。

### 5.3 死循环避免

唯一存在的风险路径：

```
PowerNode(a, p/q)
  → _transform_to_root
  → RootNode(q, a^p)
  → _fold_power_radicand
  → PowerNode(a, p/q)     ← 回到起点？
```

**不会发生**，因为：

1. `_transform_to_root` 只在 `a` 不是完全 q 次方时触发。
2. `RootNode._fold_power_radicand` 只在 `e` 是 `PowerNode(a, m)` 且 `a` 是整数时触发。
3. 进入 `_transform_to_root` 时，`a^p` 已经是整数，`RootNode` 内部会走 `_fold_integer_radicand`，不会再回到 PowerNode。

---

## 六、测试用例

### 6.1 PowerNode 侧

| 输入 | 预期输出 | 路径 |
| --- | --- | --- |
| 2^0 | 1 | _fold_trivial |
| 2^1 | 2 | _fold_trivial |
| 1^100 | 1 | _fold_trivial |
| (-1)^5 | -1 | _fold_trivial |
| 0^3 | 0 | _fold_trivial |
| 2^10 | 1024 | _fold_integer_base → _int_pow |
| 2^(-3) | 1/8 | _fold_integer_base → _int_pow |
| 2^(1/2) | √2 | _transform_to_root |
| 2^(3/2) | 2√2 | _transform_to_root → RootNode 因子提取 |
| 8^(1/3) | 2 | _fold_integer_base 完全 3 次方 |
| 8^(2/3) | 4 | _fold_integer_base 完全 3 次方 |
| (-2)^3 | -8 | _fold_negative_base |
| (-2)^4 | 16 | _fold_negative_base |
| (-8)^(1/3) | -2 | _fold_negative_base，q=3 奇 |
| (-4)^(1/2) | 抛 MathError | _fold_negative_base，q=2 偶 |
| (2/3)^2 | 4/9 | _fold_fraction_base |
| (√2)^4 | 4 | _fold_root_power → 2^(4/2) |
| (√2)^3 | 2√2 | _fold_root_power → 2^(3/2) → _transform_to_root |

### 6.2 RootNode 侧

| 输入 | 预期输出 | 路径 |
| --- | --- | --- |
| √0 | 0 | _fold_trivial |
| √1 | 1 | _fold_trivial |
| ¹√5 | 5 | _fold_trivial，n=1 |
| √4 | 2 | _fold_integer_radicand 完全平方 |
| √8 | 2√2 | _fold_integer_radicand 因子提取 |
| √72 | 6√2 | _fold_integer_radicand 因子提取 |
| ³√8 | 2 | _fold_integer_radicand 完全立方 |
| ³√24 | 2·³√3 | _fold_integer_radicand |
| ³√(-8) | -2 | _fold_negative_radicand |
| √(-4) | 抛 MathError | _fold_negative_radicand |
| √(1/4) | 1/2 | _fold_fraction_radicand |
| √(2/3) | √6/3 | _fold_fraction_radicand |
| √(√16) | 2 | _fold_nested_root → ⁴√16 |
| √(x^2) | x | _fold_power_radicand，r=0 |
| √(x^3) | x·√x | _fold_power_radicand，r=1 |
| √(x^4) | x^2 | _fold_power_radicand，r=0 |
| ³√(x^7) | x^2·³√x | _fold_power_radicand，q=2, r=1 |

---

## 七、边界与限制

### 7.1 数值上限

| 常量 | 值 | 用途 |
| --- | --- | --- |
| _MAX_INT_POWER | 105 | 整数指数上限，超过保留原节点 |
| _MAX_BASE_FOR_ROOT | 1012 | 分数指数的完全 q 次方判定上限 |
| _MAX_RADICAND_FOR_FACTORING | 1010 | RootNode 因子提取上限，超过只做完全 n 次方判定 |

### 7.2 已知的不完美之处

1. **`2^(-1/2)` 未有理化**
 当前返回 `1/√2`，标准形式应为 `√2/2`。 需要 FractionNode 识别 `1/√n` 形态再分子分母同乘 `√n`。
2. **`(2/3)^(3/2)` 无法完整约分**
 返回 `FractionNode(BinaryOpNode(...), IntegerNode(27))`， gcd 无法跨越 `BinaryOpNode` 约分。
3. **复数路径未实现**
 `env["complex_mode"]` 只是 hook，读到它不会走复数逻辑。 等 v2 上 `ImaginaryNode` / `ComplexNode` 时补。
4. **代数化简不在本层**
 `2^x · 2^y = 2^(x+y)` 属于 BinaryOpNode 的跨节点规则，不在 PowerNode 内处理。

### 7.3 复数 hook 的位置

| 位置 | 行为 |
| --- | --- |
| PowerNode._fold_negative_base，q 偶 | 复数模式返回 None（保留），实数模式抛 MathError |
| PowerNode.evaluate，base < 0 非整数指 | 复数模式返回 complex(base) ** exp，实数模式抛 MathError |
| RootNode._fold_negative_radicand，n 偶 | 复数模式返回 None（保留），实数模式抛 MathError |
| RootNode.evaluate，value < 0 且 degree 偶 | 复数模式返回 complex(value) ** (1/degree)，实数模式抛 MathError |

---

## 八、总结

> **PowerNode 和 RootNode 共享三个底层工具**
>
> （
>
> `_integer_nth_root`
>
> 、
>
> `_extract_nth_power`
>
> 、
>
> `_int_pow`
>
> ），
>
> **各自的化简流水线按"平凡 → 结构 → 负数 → 分数 → 整数"的顺序分发**
>
> ，
>
> **转换有方向：PowerNode → RootNode 是规范方向，反向只在数学化简必要时发生**
>
> ，
>
> **复数通过 `env["complex_mode"]` 预留 hook，当前不实现**
>
> 。

这套设计保证：

- 每个折叠方法职责单一，命名即职责。
- 转换路径可预测，不会死循环。
- 扩展新形态只需加一个 `_fold_*` 方法并插入列表。
- TrigNode 特殊值表构造的 `RootNode` 常量结构稳定，不会被误改。