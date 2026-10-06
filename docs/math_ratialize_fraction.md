# FractionNode 分母有理化机制

本文档说明 `FractionNode.simplify` 中的分母有理化逻辑：为什么只处理平方根，如何识别可有理化的分母，以及如何执行共轭相乘。

---

## 一、什么是分母有理化

> **分母有理化**
>
> ：把分母中的根号消去，转为有理数，使表达式呈"标准形式"。

| 原始形式 | 有理化后 | 关键等式 |
| --- | --- | --- |
| 1/√2 | √2/2 | 分子分母同乘 √2，分母得 2 |
| 1/√8 | √2/4 | √8 = 2√2，消去后分子分母再约分 |
| 1/(√6 + √2) | (√6 - √2)/4 | 乘以共轭 √6 - √2，分母得 6 - 2 = 4 |

### 1.1 为什么只对平方根做

有理化的本质是找到一个"共轭"表达式，使得它和分母相乘后根号消失。

 +

`√a · √a = a`

：平方根自乘即消 +

`(√a + √b)(√a - √b) = a - b`

：共轭相乘消根号 +

`³√a · ³√a = ³√(a²)`

：**没有消去**，需要三项

`³√a · ³√a · ³√a`

 才得

`a`

 更高次根号的有理化需要更多项，且结果形式不唯一。卡西欧也不做这个。

**结论**

：有理化只处理

`√n`

 形式，不处理

`ⁿ√x`

（n ≥ 3）。

---

## 二、可识别的情形

| 种类 | 分母形态 | 共轭 | 乘积 |
| --- | --- | --- | --- |
| single | √n | √n | n |
| single | k·√n（k 是整数） | √n | k·n |
| pair | t1 + t2 | t1 - t2 | t1² - t2² |
| pair | t1 - t2 | t1 + t2 | t1² - t2² |

其中 `t1`、`t2` 各自是"有理数"或"含至多一个平方根的数"。

### 2.1 覆盖与不覆盖的例子

| 分母 | 是否识别 | 原因 |
| --- | --- | --- |
| √2 | ✅ single | 单个平方根 |
| 3√2 | ✅ single | 系数 × 平方根 |
| √6 + √2 | ✅ pair | 两个平方根之和 |
| 1 + √2 | ✅ pair | 有理数 + 平方根 |
| 3 - 2√5 | ✅ pair | 有理数 - 系数 × 平方根 |
| ³√2 | ❌ | 非平方根 |
| 1 + √2 + √3 | ❌ | 三项，需要两次有理化 |
| √2 + √3 + √5 | ❌ | 三项，共轭复杂 |
| √2 · √3 | ❌（但会先折叠成 √6） | 乘积会被 RootNode 化简 |
| (√2)/2 作为分母 | ❌ | 分母本身已经是有理数倍数，不属于可识别类型 |

---

## 三、识别辅助函数

### 3.1 `_is_sqrt_node(node)`

判断节点是否是 `√n`（n > 1 的整数）。

```
def _is_sqrt_node(node: Node) -> bool:
    return (isinstance(node, RootNode)
            and isinstance(node.degree, IntegerNode)
            and node.degree.value == 2
            and isinstance(node.radicand, IntegerNode)
            and node.radicand.value > 1)
```

**为什么要求 `n > 1`**：`√1 = 1` 是有理数，会被 RootNode 提前折叠。出现 `√1` 说明上游有问题，这里直接判为不是。

### 3.2 `_is_rational_value(node)`

判断节点是否是有理数（整数或分数，分母 > 0）。

```
def _is_rational_value(node: Node) -> bool:
    if isinstance(node, IntegerNode):
        return True
    if isinstance(node, FractionNode):
        return (isinstance(node.num, IntegerNode)
                and isinstance(node.den, IntegerNode)
                and node.den.value > 0)
    return False
```

### 3.3 `_split_signed(node)`

把顶层的 `a + b` 或 `a - b` 拆成 `(a, op, b)`。非加减节点返回 `(node, None, None)`。

```
def _split_signed(node: Node):
    if isinstance(node, BinaryOpNode) and node.op in ('+', '-'):
        return node.left, node.op, node.right
    return node, None, None
```

**只拆顶层**，不递归。这样 `1 + √2 + √3` 被拆成 `(1 + √2, '+', √3)`，右侧 `√3` 合法，但左侧 `1 + √2` 含加减不是简单项，判定失败。

### 3.4 `_has_single_sqrt(node)`

判断节点是否是 `k·√n` 形式（k 是整数）。

```
def _has_single_sqrt(node: Node) -> bool:
    if isinstance(node, BinaryOpNode) and node.op == "*":
        for sqrt_side, other_side in ((node.left, node.right), (node.right, node.left)):
            if _is_sqrt_node(sqrt_side) and isinstance(other_side, IntegerNode):
                return True
    return False
```

---

## 四、分析函数 `_analyze_denominator`

核心判定函数。返回描述分母结构的信息，或返回 `None` 表示不可识别。

```
def _analyze_denominator(den: Node):
    # 情形 1：单个 √n
    if _is_sqrt_node(den):
        return {'kind': 'single', 'k': 1, 'n': den.radicand.value}

    # 情形 1b：k·√n
    if isinstance(den, BinaryOpNode) and den.op == "*":
        for sqrt_side, other_side in ((den.left, den.right), (den.right, den.left)):
            if _is_sqrt_node(sqrt_side) and isinstance(other_side, IntegerNode):
                return {'kind': 'single', 'k': other_side.value, 'n': sqrt_side.radicand.value}

    # 情形 2：t1 ± t2
    t1, op, t2 = _split_signed(den)
    if op is None or t2 is None:
        return None

    # 每一项必须是有理数或含至多一个平方根
    if not _valid_pair_term(t1):
        return None
    if not _valid_pair_term(t2):
        return None

    # 至少一项含平方根，否则分母已经有理
    if _is_rational_value(t1) and _is_rational_value(t2):
        return None

    return {'kind': 'pair', 't1': t1, 't2': t2, 'op': op}
```

其中 `_valid_pair_term` 判断单个项是否合法（有理数，或单项平方根，或 k√n）：

```
def _valid_pair_term(node: Node) -> bool:
    return (_is_rational_value(node)
            or _is_sqrt_node(node)
            or _has_single_sqrt(node))
```

---

## 五、有理化执行

### 5.1 single 情形

```
num / (k·√n) → num·√n / (k·n)
```

```
def _rationalize_single(self, num, k, n, env):
    conj = RootNode(IntegerNode(2), IntegerNode(n))
    new_num = BinaryOpNode(num, conj, "*").simplify(env)
    new_den_value = k * n
    if new_den_value == 1:
        return new_num
    return FractionNode(new_num, IntegerNode(new_den_value)).simplify(env)
```

### 5.2 pair 情形

```
num / (t1 + t2) → num·(t1 - t2) / (t1² - t2²)
num / (t1 - t2) → num·(t1 + t2) / (t1² - t2²)
```

```
def _rationalize_pair(self, num, t1, t2, op, env):
    conj_op = "-" if op == "+" else "+"
    conj = BinaryOpNode(t1, t2, conj_op)

    t1_sq = BinaryOpNode(t1, t1, "*").simplify(env)
    t2_sq = BinaryOpNode(t2, t2, "*").simplify(env)
    new_den = BinaryOpNode(t1_sq, t2_sq, "-").simplify(env)

    if not _is_rational_value(new_den):
        return None   # 共轭技巧未消根号，放弃

    new_num = BinaryOpNode(num, conj, "*").simplify(env)
    return FractionNode(new_num, new_den).simplify(env)
```

**为什么要检查 `_is_rational_value(new_den)`**

：

 形如

`√2 + ³√2`

 的分母，共轭相乘后得到

`2 - ³√4`

，仍然含根号。

`_analyze_denominator`

 判定时会拒绝这种输入，但这是兜底的二次检查，防止边界漏网。

---

## 六、完整示例

### 6.1 `1/√2`

1. 分析：

`_analyze_denominator(√2)`

 → {'kind': 'single', 'k': 1, 'n': 2}

 2. 执行：

`_rationalize_single(1, 1, 2, env)`

 3. conj = √2

 4. new_num = 1 · √2 = √2

 5. new_den_value = 1 · 2 = 2

 6. 结果：

`FractionNode(√2, 2)`

 → 分母有理数，走约分路径 → 保留

**输出**：`√2 / 2`

### 6.2 `1/(√6 + √2)`

1. 分析：

`_split_signed(√6 + √2)`

 → (√6, '+', √2)

 2. √6、√2 都是 _is_sqrt_node，至少一项含根号

 3. 返回 {'kind': 'pair', 't1': √6, 't2': √2, 'op': '+'}

 4. 执行：

`_rationalize_pair(1, √6, √2, '+', env)`

 5. conj = √6 - √2

 6. t1_sq = √6 · √6 = 6

 7. t2_sq = √2 · √2 = 2

 8. new_den = 6 - 2 = 4

 9. new_num = 1 · (√6 - √2) = √6 - √2

 10. 结果：

`FractionNode(√6 - √2, 4)`

**输出**：`(√6 - √2) / 4`

### 6.3 `2/√8`

1. 分母

`√8`

 先被 RootNode 化简为

`2√2`

 2. 分析：

`_analyze_denominator(2√2)`

 → {'kind': 'single', 'k': 2, 'n': 2}

 3. 执行：

`_rationalize_single(2, 2, 2, env)`

 4. conj = √2

 5. new_num = 2 · √2

 6. new_den_value = 2 · 2 = 4

 7. 结果：

`FractionNode(2√2, 4)`

**输出**：`2√2 / 4`，但期望是 `√2 / 2`。

**已知缺陷**

：

`_reduce_to_lowest`

 无法识别分子

`k·√n`

 中的系数与分母的 gcd。 需要在下一轮修复：识别

`IntegerNode(k) * RootNode(...)`

 结构，提取 k，与分母约分。

---

## 七、局限与已知缺陷

| 情形 | 状态 | 原因 |
| --- | --- | --- |
| 1/(√2 + 1/2) | ❌ 不识别 | _has_single_sqrt 只认整数系数 |
| 1/(1 + √2 + √3) | ❌ 不识别 | 三项，_split_signed 拆一次后左侧仍是复合 |
| 2√2 / 4 未约分 | ⚠️ 部分 | _reduce_to_lowest 不认 k√n 形态 |
| 1/(³√2) | ❌ 按设计 | 只对平方根有理化 |
| 分母 (√2)/2 | ❌ 不识别 | 分母是有理倍数，本无需有理化 |

以上限制都不影响 v1 的核心使用。最常见的形式

`1/√n`

、

`1/(√a ± √b)`

、

`1/(p + √q)`

 都能正确处理。 更复杂的情形（三项分母、系数分数）留到 v2 一并处理。

---

## 八、调用顺序

`FractionNode.simplify` 的整体流程：

1.

`num = self.num.simplify(env)`

 2.

`den = self.den.simplify(env)`

 3. 若

`den`

 是有理数 →

`_reduce_to_lowest(num, den)`

（gcd 约分路径）

 4. 若

`den`

 含平方根 →

`_try_rationalize(num, den, env)`

（有理化路径）

 5. 若都不成功 → 保留

两条路径**互斥**。分母是有理数时走 gcd，分母含平方根时走有理化。

---

## 九、设计要点总结

> **有理化只处理平方根**
>
> ，因为只有
>
> `√a · √a = a`
>
>  和
>
> `(√a ± √b)(√a ∓ √b) = a - b`
>
>  两种共轭技巧能消去根号。
>
> **识别分两类**
>
> ：
>
> `single`
>
> （单个
>
> `√n`
>
>  或
>
> `k√n`
>
> ）和
>
> `pair`
>
> （
>
> `t1 ± t2`
>
> ）。
>
> **只拆顶层**
>
> ，不递归，保证复杂分母（三项及以上）被自然拒绝。
>
> **共轭技巧执行后做二次检查**
>
> `_is_rational_value(new_den)`
>
> ，防止漏网。

- 覆盖面：`1/√n`、`1/(k√n)`、`1/(t1 ± t2)`，其中 t1、t2 是含至多一个平方根的数。
- 已知缺陷：`k√n / m` 的约分未实现，留到下一轮。
- 实现成本低：约 80 行，无新增依赖，复用 `RootNode` 和 `BinaryOpNode` 的折叠。