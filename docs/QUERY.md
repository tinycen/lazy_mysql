# 自定义 SQL 查询 (query)

当你需要执行手写 SQL 查询时，使用 `query()` 方法。与 `select()` 不同，`query()` 不自动生成 SQL，而是直接执行你提供的完整 SQL 语句，并通过 `fetch_config` 控制返回格式。

## 与其他方法的区别

`lazy_mysql` 提供以下 SQL 执行方法，根据场景选择：

| 方法 | 定位 | 是否关心返回 | 典型场景 |
|------|------|-------------|--------|
| `execute()` | 通用 SQL 执行器 | 否（返回 None）| INSERT / UPDATE / DELETE 等写操作 |
| `query()` | 手写 SELECT 查询（推荐）| 是（通过 `fetch_config` 控制格式）| 复杂 SELECT、子查询、UNION、窗口函数 |
| `fetch_format()` | 手写 SELECT 查询（底层）| 是（通过分散参数控制格式）| 内部方法，`query()` 的底层实现 |
| `select()` | 结构化 SELECT 查询（ORM 风格）| 是（通过 `fetch_config` 控制格式）| 常规查询，自动构造 SQL，开发效率高 |

- 写操作（INSERT/UPDATE/DELETE）→ 用 `execute()`
- 读操作且手写 SQL → 用 `query()`
- 读操作且希望自动构造 SQL → 用 `select()`

## `query()` 与 `fetch_format()` 的关系

`query()` 是 `fetch_format()` 的上层封装，两者执行相同的底层逻辑，但参数风格不同：

| 对比项 | `query()` | `fetch_format()` |
|--------|-----------|------------------|
| 参数风格 | 统一使用 `fetch_config`（`FetchConfig` 对象或字典）| 分散参数：`fetch_mode`、`output_format`、`show_count`、`data_label` 分别传入 |
| 默认输出格式 | `output_format="df_dict"`（字典列表）| `output_format=""`（原始元组） |
| 适用对象 | 面向用户，推荐使用 | 内部方法，供 `query()`/`select()` 内部调用 |
| 参数校验 | 自动解析 `fetch_config`，填充默认值 | 需调用方自行传入所有参数 |

> **建议**：手写 SQL 查询统一使用 `query()`，`fetch_format()` 通常无需直接调用。

## 适用场景

- `select()` 无法生成的复杂 SQL（如子查询、UNION、窗口函数等）
- 需要直接执行存储过程或特定数据库语法
- 性能调优时手写优化后的 SQL

## 函数签名

### `query()`

```python
query(
    sql: str,
    params=None,
    fetch_config: FetchConfig | dict | None = None,
    self_close: bool = False
)
```

### `fetch_format()`（底层方法，通常无需直接调用）

```python
fetch_format(
    sql: str,
    fetch_mode: str,          # 必填，可选值: "all"、"oneTuple"、"one"
    output_format: str = "",  # 可选值: ""、"list_1"、"df"、"df_dict"
    show_count: bool = False,
    data_label: list | None = None,
    params=None,
    self_close: bool = False
)
```

### 参数说明

#### `query()` 参数

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `sql` | str | 是 | 完整的 SQL 查询语句 |
| `params` | dict/tuple/list | 否 | 参数化查询的参数，支持单条或批量 |
| `fetch_config` | FetchConfig/dict | 否 | 结果格式化配置，详见 [FETCH_CONFIG.md](FETCH_CONFIG.md) |
| `self_close` | bool | 否 | 是否自动关闭数据库连接 |

#### `fetch_format()` 参数（底层方法）

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `sql` | str | 是 | 完整的 SQL 查询语句 |
| `fetch_mode` | str | 是 | 获取模式：`"all"`（所有结果）、`"oneTuple"`（单条元组）、`"one"`（单个值）|
| `output_format` | str | 否 | 输出格式，默认 `""`（原始元组），可选 `"list_1"`、`"df"`、`"df_dict"` |
| `show_count` | bool | 否 | 是否打印并返回结果数量，默认 `False` |
| `data_label` | list | 否 | 列名标签，`output_format` 为 `"df"` / `"df_dict"` 时不能为空 |
| `params` | dict/tuple/list | 否 | 参数化查询的参数 |
| `self_close` | bool | 否 | 是否自动关闭数据库连接 |

## 基础用法

### 简单查询

```python
from lazy_mysql import SQLExecutor

executor = SQLExecutor(config)

# 执行手写 SQL，返回字典列表（默认）
result = executor.query("SELECT id, name, email FROM users WHERE status = %s", params=('active',))
# 返回: [{'id': 1, 'name': '张三', 'email': 'z@e'}, ...]
```

### 获取单条记录

```python
from lazy_mysql import FetchConfig

user = executor.query(
    "SELECT id, name, email FROM users WHERE id = %s",
    params=(1,),
    fetch_config=FetchConfig(fetch_mode="oneTuple")
)
# 返回: (1, '张三', 'z@e')
```

### 获取单个值

```python
count = executor.query(
    "SELECT COUNT(*) FROM users WHERE status = %s",
    params=('active',),
    fetch_config=FetchConfig(fetch_mode="one")
)
# 返回: 150
```

## 结果格式化

`query()` 的 `fetch_config` 参数与 `select()` 完全一致，支持所有输出格式。

### 返回 DataFrame

```python
from lazy_mysql import FetchConfig

df = executor.query(
    "SELECT id, name, email FROM users",
    fetch_config=FetchConfig(
        fetch_mode="all",
        output_format="df",
        data_label=["id", "name", "email"]
    )
)
# 返回: pandas.DataFrame
```

### 返回字典列表

```python
users = executor.query(
    "SELECT id, name, email FROM users WHERE age > %s",
    params=(18,),
    fetch_config=FetchConfig(
        fetch_mode="all",
        output_format="df_dict",
        data_label=["id", "name", "email"]
    )
)
# 返回: [{'id': 1, 'name': '张三', 'email': 'z@e'}, ...]
```

### 扁平化列表

```python
user_ids = executor.query(
    "SELECT id FROM users",
    fetch_config=FetchConfig(
        fetch_mode="all",
        output_format="list_1"
    )
)
# 返回: [1, 2, 3, ...]
```

## 复杂 SQL 示例

### 子查询

```python
result = executor.query(
    """
    SELECT u.id, u.name, o.total
    FROM users u
    INNER JOIN (
        SELECT user_id, SUM(amount) as total
        FROM orders
        WHERE created_at >= %s
        GROUP BY user_id
    ) o ON u.id = o.user_id
    WHERE o.total > %s
    """,
    params=('2024-01-01', 1000),
    fetch_config=FetchConfig(
        output_format="df_dict",
        data_label=["id", "name", "total"]
    )
)
```

### UNION 查询

```python
result = executor.query(
    """
    SELECT id, name, 'user' as type FROM users WHERE status = %s
    UNION ALL
    SELECT id, name, 'admin' as type FROM admins WHERE status = %s
    """,
    params=('active', 'active'),
    fetch_config=FetchConfig(
        output_format="df_dict",
        data_label=["id", "name", "type"]
    )
)
```

### 窗口函数

```python
result = executor.query(
    """
    SELECT
        id,
        name,
        amount,
        RANK() OVER (ORDER BY amount DESC) as rank
    FROM orders
    WHERE created_at >= %s
    """,
    params=('2024-01-01',),
    fetch_config=FetchConfig(
        output_format="df_dict",
        data_label=["id", "name", "amount", "rank"]
    )
)
```

## 与 select() 的对比

| 特性 | `select()` | `query()` |
|------|-----------|-----------|
| SQL 生成 | 自动生成 | 手写完整 SQL |
| 适用场景 | 常规查询 | 复杂 SQL、子查询、UNION 等 |
| WHERE 条件 | 字典传入，自动构建 | 在 SQL 中手写 |
| JOIN | 配置化 | 在 SQL 中手写 |
| 参数防注入 | 自动参数化 | 需手动使用 `%s` + `params` |

## 注意事项

1. **参数化查询**：务必使用 `%s` 占位符 + `params` 参数，防止 SQL 注入
2. **data_label**：当 `output_format` 为 `"df"` 或 `"df_dict"` 时，`data_label` 不能为空
3. **默认输出**：`query()` 默认 `output_format="df_dict"`，与 `select()` 默认 `""` 不同
