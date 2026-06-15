# UPSERT 操作完整指南

> **⚠️ 危险警告**：`upsert()` 与 `insert()` 的行为有本质区别。`upsert()` 的 `fields` 参数决定的是 **INSERT 时要写入的完整字段集合**，而非"只更新指定的字段"。传入不完整的数据会导致未包含的字段被设为 `NULL`，可能对生产数据造成不可逆的破坏。请务必完整阅读本文档的[危险警告与常见误区](#危险警告与常见误区)章节。

`lazy_mysql` 的 `upsert` 方法基于 MySQL 的 `INSERT ... ON DUPLICATE KEY UPDATE` 语句实现，提供"存在则更新，不存在则插入"的智能数据处理能力。

## 目录

1. [危险警告与常见误区](#危险警告与常见误区)
2. [核心原则](#核心原则)
3. [函数签名与参数说明](#函数签名与参数说明)
4. [基本 UPSERT 用法](#基本-upsert-用法)
5. [选择性字段更新](#选择性字段更新)
6. [批量 Upsert](#批量-upsert)
7. [特殊场景：表字段与传入字段完全一致](#特殊场景表字段与传入字段完全一致)
8. [Upsert 与 Insert 的区别](#upsert-与-insert-的区别)
9. [最佳实践建议](#最佳实践建议)

## 危险警告与常见误区

### ❌ 错误用法（可能导致数据丢失）

假设数据库已存在以下记录：

```
id: 1, name: 'Alice Smith', email: 'alice@example.com', age: 27
```

如果你只想更新年龄，**下面这种写法是错误的**：

```python
# ❌ 错误！这会导致 name 和 email 被清空为 NULL
executor.upsert('users', {'id': 1, 'age': 26}, commit=True)
```

**实际执行的 SQL：**

```sql
INSERT INTO users (id, age) VALUES (1, 26)
ON DUPLICATE KEY UPDATE id = VALUES(id), age = VALUES(age)
```

**执行结果：**

| 字段 | 原值 | 执行后 | 说明 |
|------|------|--------|------|
| `id` | 1 | 1 | 不变 |
| `name` | 'Alice Smith' | **NULL** | ⚠️ 数据丢失！ |
| `email` | 'alice@example.com' | **NULL** | ⚠️ 数据丢失！ |
| `age` | 27 | 26 | 正确更新 |

**原因**：`upsert()` 的 `fields` 参数定义的是 INSERT 语句的字段集合。`name` 和 `email` 没有出现在 `fields` 中，MySQL 会将它们作为缺失字段处理，在插入时设为 `NULL`。

### ✅ 正确用法

必须传入**完整的数据**，并通过 `fields_update` 参数控制**只更新指定的字段**：

```python
# ✅ 正确！传入完整数据，fields_update 控制只更新 age
executor.upsert(
    'users',
    {
        'id': 1,
        'name': 'Alice Smith',        # 必须包含，保持原值
        'email': 'alice@example.com', # 必须包含，保持原值
        'age': 26
    },
    fields_update={'age'},            # 只有 age 会被更新
    commit=True
)
```

**实际执行的 SQL：**

```sql
INSERT INTO users (id, name, email, age)
VALUES (1, 'Alice Smith', 'alice@example.com', 26)
ON DUPLICATE KEY UPDATE age = VALUES(age)
```

**执行结果：**

| 字段 | 原值 | 执行后 | 说明 |
|------|------|--------|------|
| `id` | 1 | 1 | 不变 |
| `name` | 'Alice Smith' | 'Alice Smith' | 保持不变 |
| `email` | 'alice@example.com' | 'alice@example.com' | 保持不变 |
| `age` | 27 | 26 | 正确更新 |

## 核心原则

> **`fields` = 你要插入的完整数据行（所有字段）**
> **`fields_update` = 冲突时实际要更新的字段子集**

`fields_update` 的默认值为 `None`，表示冲突时更新 `fields` 中的**所有字段**。如果你只想更新部分字段，**必须显式传入 `fields_update`**。

### `fields` 中的值是否影响更新结果？

**取决于 `fields_update` 的设置：**

- 当 `fields_update=None`（默认值）时：`fields` 中**所有字段的值都会影响更新结果**，冲突时会全部覆盖
- 当 `fields_update` 显式指定了字段集合时：只有 `fields_update` 中包含的字段会被更新，其值取自 `fields` 中对应字段；未包含的字段**不会**被覆盖

这意味着：
- 使用 `fields_update` 时，`fields` 中未出现在 `fields_update` 里的字段，其值**不会**覆盖数据库中的现有值
- 你可以放心地在 `fields` 中填入当前已知数据，配合 `fields_update` 使用时不用担心会意外覆盖不想更新的字段

**示例**：假设数据库已有 `id=1, name='Alice Smith', email='alice@example.com', age=27`，执行：

```python
executor.upsert(
    'users',
    {
        'id': 1,
        'name': 'Temporary Name',     # 这个值不会覆盖数据库中的 name
        'email': 'temp@example.com',  # 这个值不会覆盖数据库中的 email
        'age': 26
    },
    fields_update={'age'},            # 只有 age 会被更新
    commit=True
)
```

**执行结果**：

| 字段 | 原值 | 执行后 | 说明 |
|------|------|--------|------|
| `id` | 1 | 1 | 不变 |
| `name` | 'Alice Smith' | **'Alice Smith'** | 保持不变，`fields` 中的值未生效 |
| `email` | 'alice@example.com' | **'alice@example.com'** | 保持不变 |
| `age` | 27 | **26** | 被更新为 `fields` 中的值 |

## 函数签名与参数说明

```python
upsert(
    executor: SQLExecutor,
    table_name,
    fields,
    fields_update=None,
    commit=False,
    self_close=False
)
```

### 核心参数

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `executor` | SQLExecutor | 是 | SQL执行器实例 |
| `table_name` | str | 是 | 目标表名 |
| `fields` | dict/list | 是 | **完整的插入数据**，支持单条字典或字典列表。⚠️ 必须包含所有字段，缺失字段会被设为 `NULL` |
| `fields_update` | set/list | 否 | 冲突时更新的字段集合，默认 `None` 表示更新 `fields` 中的所有字段 |
| `commit` | bool | 否 | 是否自动提交事务，默认 `False` |
| `self_close` | bool | 否 | 是否自动关闭连接，默认 `False` |

## 基本 UPSERT 用法

### 单条记录 Upsert

```python
from lazy_mysql import SQLExecutor, MySQLConfig

# 配置数据库连接（详见 CONNECTION.md）
config = MySQLConfig(
    host='localhost',
    user='your_username',
    passwd='your_password',
    default_database='your_database'
)
executor = SQLExecutor(config)

# 用户数据，如果存在则更新，不存在则插入
user_data = {
    'id': 1,
    'name': 'John Doe',
    'email': 'john.updated@example.com',
    'age': 31,
    'updated_at': '2023-12-01 10:00:00'
}

# 执行 upsert 操作（更新所有字段）
executor.upsert('users', user_data, commit=True)
print("Upsert 操作完成！")
```

## 选择性字段更新

通过 `fields_update` 参数可以精确控制冲突时只更新特定字段，其他字段保持不变：

```python
# 只更新 age 和 updated_at 字段，name 和 email 保持不变
user_data = {
    'id': 1,
    'name': 'Temporary Name',      # 这个字段不会被更新
    'email': 'temp@example.com',   # 这个字段不会被更新
    'age': 32,
    'updated_at': '2023-12-01 15:00:00'
}

# 指定只更新特定字段
executor.upsert('users', user_data, fields_update={'age', 'updated_at'}, commit=True)
print("选择性字段更新完成！")
```

生成的 SQL：

```sql
INSERT INTO users (id, name, email, age, updated_at)
VALUES (1, 'Temporary Name', 'temp@example.com', 32, '2023-12-01 15:00:00')
ON DUPLICATE KEY UPDATE age = VALUES(age), updated_at = VALUES(updated_at)
```

## 批量 Upsert

```python
# 批量 upsert 多个用户记录
users_data = [
    {'id': 1, 'name': 'Alice Smith', 'email': 'alice@example.com', 'age': 26},
    {'id': 2, 'name': 'Bob Johnson', 'email': 'bob.updated@example.com', 'age': 36},
    {'id': 3, 'name': 'Carol Williams', 'email': 'carol@example.com', 'age': 29}
]

# 批量 upsert（更新所有字段）
upserted_count = executor.upsert('users', users_data, commit=True)
print(f"成功处理 {upserted_count} 条记录！")
```

批量 upsert 同样支持 `fields_update`：

```python
# 批量 upsert，但冲突时只更新 age 字段
executor.upsert('users', users_data, fields_update={'age'}, commit=True)
```

## 特殊场景：表字段与传入字段完全一致

当表的所有字段恰好就是你想要 upsert 的字段时（没有额外字段），可以直接传入部分字段，无需担心数据丢失。

### 场景示例

假设 `scenes` 表结构如下：

```sql
CREATE TABLE scenes (
    task VARCHAR(50),
    scene VARCHAR(50),
    environment VARCHAR(20),
    model_index INT,
    sort_order INT,
    UNIQUE KEY uk_scene (task, scene, environment, model_index, sort_order)
);
```

表只有这 5 个字段，没有 `id`、`created_at` 等其他字段：

```python
# ✅ 正确！表只有这 5 个字段，传入完整字段集合即可
executor.upsert('scenes', {
    "task": "product_listing",
    "scene": "generate_title",
    "environment": "local",
    "model_index": 10,
    "sort_order": 1
}, commit=True)
```

**执行结果**：
- 记录不存在：插入这 5 个字段的值
- 记录存在（唯一索引冲突）：更新这 5 个字段的值

### ⚠️ 重要提醒

这种简化写法**仅在表字段与传入字段完全一致时**才安全。如果表还有其他字段（如 `config`、`created_at` 等），未传入的字段会被设为 `NULL`：

```sql
-- 危险！如果表还有其他字段
CREATE TABLE scenes (
    task VARCHAR(50),
    scene VARCHAR(50),
    environment VARCHAR(20),
    model_index INT,
    sort_order INT,
    config JSON,           -- 额外字段！
    created_at DATETIME,   -- 额外字段！
    UNIQUE KEY uk_scene (...)
);
```

```python
# ❌ 错误！config 和 created_at 会被设为 NULL
executor.upsert('scenes', {
    "task": "product_listing",
    "scene": "generate_title",
    "environment": "local",
    "model_index": 10,
    "sort_order": 1
}, commit=True)
```

**安全做法**：确认表结构后再使用简化写法，或使用 `fields_update` 配合完整数据。

## Upsert 与 Insert 的区别

| 场景 | insert() | upsert() |
|------|----------|----------|
| 主键冲突 | 报错或跳过（skip_duplicate=True） | 自动更新冲突记录 |
| 唯一索引冲突 | 报错或跳过（skip_duplicate=True） | 自动更新冲突记录 |
| 数据存在性 | 需要预先检查 | 自动处理 |
| 适用场景 | 纯插入操作 | 插入或更新操作 |
| 字段完整性要求 | 可只传部分字段 | **必须传入完整字段，否则未传字段会被清空** |

## 最佳实践建议

1. **始终传入完整数据**：`fields` 必须包含表的所有字段，缺失字段会被设为 `NULL`
2. **使用 `fields_update` 控制更新范围**：避免不必要的字段更新，同时保护其他字段不被覆盖
3. **确保主键或唯一索引**：表必须有适当的主键或唯一索引来触发冲突检测
4. **批量处理**：大批量数据使用列表格式获得更好性能
5. **事务管理**：复杂业务逻辑中手动控制提交时机
6. **生产环境先测试**：在应用到生产环境前，务必在测试环境验证 upsert 行为
