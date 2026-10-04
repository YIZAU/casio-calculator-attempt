# mathmatics.py — 定位、外部输入与终极形态

## 一、文件定位

`mathmatics.py` 是一个**自包含的符号数学核心**。它不依赖 Lexer、Parser、Engine、UI 或 Settings，只负责：

- 定义所有 Node 类型及其行为
- 提供折叠规则注册与分派机制
- 通过运算符重载自动构造 AST

任何外部模块（Parser、Engine、测试脚本）都可以单独导入它使用。

## 二、Node 类型层级

```
Node（基类）
├── IntegerNode            整数
├── DecimalNode            小数
├── FractionNode           分数（num / den）
├── ComplexNode            复数（real / imag）
├── ConstantNode           常量基类
│   ├── PiNode             π
│   ├── EulerNode          e
│   └── ImaginaryNode      i
├── VariableNode           变量（name）
├── NegativeNode           一元负号（child）
├── BinaryOpNode           二元运算（left, right, op）
├── TriangleFunctionNode   三角函数（name, argument）
├── PowerNode              幂（base, exp）
├── RootNode               根号（degree, expression）
├── UnaryFunctionNode      一元函数（name, argument）
└── BinaryFunctionNode     二元函数（name, argument1, argument2）
```

每个 Node 提供：

| 方法 | 用途 | 返回 |
| --- | --- | --- |
| simplify(env=None) | 符号化简 / 数学运算（主路径） | Node |
| evaluate(env=None) | 数值求值（后备，将来由 Engine 接管） | int / float / complex |
| to_str(parent_prec=0) | 字符串输出，可被 Parser 读回 | str |
| __str__() | 语法糖，调用 to_str() | str |

## 三、simplify 的终极形态

> **simplify 是主路径，数值计算是后备。**

- **simplify 承担数学运算和符号化简**，尽可能保持精确结构（分数、根号、π、e）。
- **数值计算只在无法符号化时兜底**（如 `sin(1)`、`ln(2)`、`π^π` 这类超越数）。
- **`evaluate()` 将来会消失**：Engine 从 simplify 的结果上取数值，只在 I/O 模式为小数输出时触发。

这意味着 `simplify` 必须区分两种情形：

| 情形 | 结果 | 示例 |
| --- | --- | --- |
| 可精确折叠 | 仍是 Node | 1/3 + 1/6 → 1/2、sin(30°) → 1/2 |
| 只能数值近似 | 退化到 DecimalNode 或保留原节点 | ln(2)、sin(1) |

## 四、外部输入（重点）

外部调用者向 Node 提供三类输入：**env 字典**、**构造参数**、**注册规则**。

### 4.1 env 字典

`env` 是传给 `simplify(env)` 和 `evaluate(env)` 的上下文，普通 `dict`。

| 键 | 值类型 | 用途 | 是否必须 |
| --- | --- | --- | --- |
| "A" ~ "F" | Node | 用户变量 | 视表达式而定 |
| "x", "y" | Node | 用户变量 | 视表达式而定 |
| "angle_unit" | str（DEG / RAD / GRA） | 三角函数角度制 | 必须 |
| "Ans" | Node | 上次结果（可选） | 视表达式而定 |

**关键约定：**

- `env` 中变量值必须是 `Node` 实例，不是裸数值。
- `angle_unit` 是字符串，是 env 中唯一非 Node 值。
- `TriangleFunctionNode.simplify` 直接索引 `env["angle_unit"]`，缺失会崩。

### 4.2 构造参数

| Node                 | 必填参数                        | 类型约束                      |
|----------------------|-----------------------------|---------------------------|
| IntegerNode          | value: int                  | 自动 int 转换                 |
| DecimalNode          | value: float                | 自动 float 转换               |
| FractionNode         | num, den: Node              | 不做类型检查                    |
| ComplexNode          | real, imag: Node            | 不做类型检查                    |
| VariableNode         | name: str                   | 无约束                       |
| NegativeNode         | child: Node                 | 无约束                       |
| BinaryOpNode         | left, right: Node, op: str  | op 限 + - * /（^ 会崩）        |
| TriangleFunctionNode | name: str, argument: Node   | name 限 6 个三角/反三角          |
| PowerNode            | base, exponent: Node        | 无约束                       |
| RootNode             | degree, expression: Node    | 无约束                       |
| UnaryFunctionNode    | name: str, argument: Node   | name 限 ln/sqrt/sq/cbrt/cb |
| BinaryFunctionNode   | name: str, arg1, arg2: Node | name 限 log/comb/perm      |

外部也可以通过运算符重载构造：

```
IntegerNode(1) + IntegerNode(2)      # → IntegerNode(3)
IntegerNode(1) / IntegerNode(3)      # → FractionNode(1, 3)
VariableNode("x") * IntegerNode(2)   # → BinaryOpNode（不折叠）
```

`__pow__`

 和

`__neg__`

 目前被注释掉，

`2 ** 3`

 和

`-node`

 不生效。

### 4.3 注册规则

`register(op, lt, rt, commutative=False)` 是模块级装饰器，扩展折叠规则：

```
@register("+", IntegerNode, IntegerNode, commutative=True)
def _(a, b):
    return IntegerNode(a.value + b.value)
```

`_TABLE` 是模块级全局字典，注册必须在导入之后立即执行。

## 五、折叠机制的扩展方案

### 5.1 现有注册表的局限

当前 `_TABLE` 的键是 `(op, lt, rt)`，天然适合二元运算符。函数节点的问题：

- 一元函数只有一个参数，键应是 `(name, arg_type)`，不是三元的。
- 二元函数（log / comb / perm）才是 `(name, arg1_type, arg2_type)`。
- 函数名与运算符名混在一起，语义上需区分。

### 5.2 方案：三个独立的注册表

```
_TABLE_BINARY   : (op, lt, rt) → fn(l, r)          # 已有
_TABLE_UNARY    : (name, at)   → fn(a)             # 新增
_TABLE_BINARY_F : (name, at1, at2) → fn(a1, a2)    # 新增
```

对应的注册装饰器：

```
@register_binary("+", IntegerNode, IntegerNode)
@register_unary("ln", IntegerNode)
@register_binary_f("log", IntegerNode, IntegerNode)
```

三个表互不干扰，各自的 simplify 方法查各自的表：

| Node | 查表 |
| --- | --- |
| BinaryOpNode.simplify | _TABLE_BINARY |
| UnaryFunctionNode.simplify | _TABLE_UNARY |
| TriangleFunctionNode.simplify | _TABLE_UNARY |
| BinaryFunctionNode.simplify | _TABLE_BINARY_F |
| RootNode.simplify | _TABLE_BINARY_F（用 "root" 作为 name） |

查不到就返回带化简子节点的原节点（保留符号），这已经是当前行为。

## 六、两类化简任务的区分

### 6.1 单节点数值折叠

- 参数是具体数值 Node
- 结果是另一个数值 Node
- 例子：`ln(1) → 0`、`sqrt(4) → 2`、`sin(30°) → 1/2`、`log(2,8) → 3`

**完全适合注册表**。每个 `(name, arg_type)` 注册一条规则。

### 6.2 跨节点代数化简

- 需要匹配两个或多个节点的模式
- 例子：`ln(a) + ln(b) → ln(a·b)`、`√a · √b → √(a·b)`、`a^x · a^y → a^(x+y)`、`(a/b)/(c/d) → (a·d)/(b·c)`

**不适合单节点注册表**，因为匹配对象是父节点 + 两个子节点的组合。

| 路线 | 做法 | 评价 |
| --- | --- | --- |
| A（推荐） | 在父节点 simplify 里手写模式匹配 | 实际、易懂，规则数量少时最优 |
| B | 引入模式匹配 DSL，声明跨节点规则 | 通用但成本高，等规则积累到十几条再考虑 |

## 七、实施优先级

1. **先扩表，不扩机制**：加 `_TABLE_UNARY`，注册 `ln(1)`、`sqrt(完全平方数)`、`sin/cos/tan(特殊角)`、 `log/comb/perm` 的整数折叠。
2. **再扩符号结构**：`sqrt(8) → 2·sqrt(2)`（提取平方因子）， `sqrt(a·b) → sqrt(a)·sqrt(b)`。
3. **最后上代数化简**：在 `BinaryOpNode.simplify` 里手写 `ln+ln`、`√·√` 等高频规则。
4. **超越数兜底**：`sin(1)`、`ln(2)` 保留原节点， Engine 在输出时按 I/O 模式决定是否 evaluate 成小数。

## 八、外部调用者的最小用法

```
from mathmatics import *

# 1. 构造表达式
expr = VariableNode("A") + FractionNode(IntegerNode(1), IntegerNode(3))

# 2. 提供上下文
env = {
    "A": FractionNode(IntegerNode(1), IntegerNode(3)),
    "angle_unit": "DEG",
}

# 3. 化简（主路径）
result = expr.simplify(env)
print(result.to_str())    # "1 / 2"

# 4. 求值（后备，将来由 Engine 决定是否调用）
value = expr.evaluate(env)
print(value)              # 0.6666...
```

## 九、已知的坑（供外部调用者规避）

1. `env["angle_unit"]` 必填，缺失会崩。
2. `env` 中变量值必须是 `Node`，不能是裸数值。
3. `__pow__` / `__neg__` 被注释，需直接构造 `PowerNode` / `NegativeNode`。
4. `BinaryOpNode` 不支持 `"^"`：`to_str` 和 `evaluate` 都会崩，幂必须用 `PowerNode`。
5. `simplify` 里 `env` 未完全下传，变量替换可能在深层结构失效。
6. `VariableNode.simplify` 常量分支应返回实例（`PiNode()`），不是类。
7. `FractionNode.simplify` 会无条件构造新对象，应加 `if num is self.num and den is self.den: return self`。

## 十、一句话总结

> `mathmatics.py`
>
>  是一个
>
> **自包含的符号数学核心**
>
> 。 外部通过
>
> **构造参数**
>
>  建树、通过
>
> **env 字典**
>
>  注入变量和角度制、通过
>
> **register**
>
>  扩展折叠规则。
>
> **simplify 承载数学运算**
>
> ，数值计算是兜底。 注册表机制可以直接泛化到一元 / 二元函数（开三个表），覆盖绝大多数「单节点数值折叠」。 「跨节点代数化简」需要模式匹配，先手写在父节点里，等规则数量上来再考虑 DSL。
>
> **先扩表、再扩结构、最后上代数，顺序不要乱。**