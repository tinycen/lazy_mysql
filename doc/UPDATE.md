# UPDATE 操作完整指南

> **前提条件**：使用前请先阅读 [CONNECTION.md](CONNECTION.md) 完成数据库连接初始化。

`lazy_mysql` 的 UPDATE 操作采用简洁而强大的设计，让您能够安全高效地更新数据库记录。通过动态SQL构建和参数化查询，既保证了代码的可读性，又防止了SQL注入攻击。

## 函数签名与参数说明

```python
update(
    executor: SQLExecutor,
    table_name: str,
    fields: dict,
    conditions: dict,
    commit: bool = False,
    self_close: bool = False
)
```

### 核心参数

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `executor` | SQLExecutor | 是 | - | SQL执行器实例，负责数据库连接和事务管理 |
| `table_name` | str | 是 | - | 要更新的表名，支持标准SQL表名格式 |
| `fields` | dict | 是 | - | 需要更新的字段和值，格式为 `{'字段名': '新值'}` |
| `conditions` | dict | 是 | - | WHERE条件字典，支持多种运算符和复杂条件 |
| `commit` | bool | 否 | `False` | 是否自动提交事务，`False` 需要手动提交 |
| `self_close` | bool | 否 | `False` | 操作完成后是否自动关闭数据库连接 |

### 参数详解

#### fields 格式说明
`fields` 参数接受一个字典，键为字段名，值为要设置的新值：

```python
# 简单更新
{'name': '张三', 'age': 25, 'status': 'active'}

# 使用SQL表达式（需手动处理参数）
{'balance': ('balance + %s', 100), 'updated_at': ('NOW()',)}
```
> ✅ **自动JSON序列化**
> 
> **列表和字典类型自动处理**：当`fields`中的值为Python列表或字典时，系统会自动将其转换为JSON字符串，无需手动处理。
> 
> **自动转换示例**：
> ```python
> # 系统会自动处理，无需手动转换
> fields = {
>     "config": {"key": "value", "enabled": True},  # dict类型 → 自动JSON序列化
>     "tags": ["python", "mysql", "lazy"],           # list类型 → 自动JSON序列化
>     "name": "张三"                                   # 普通字符串 → 保持原样
> }
> ```
> 
> **生成的SQL**：
> ```sql
> UPDATE table_name SET config = %s, tags = %s, name = %s WHERE ...;
> -- 参数：['{"key": "value", "enabled": true}', '["python", "mysql", "lazy"]', '张三']
> ```
> 
> **兼容性说明**：
> - 支持MySQL 8.0+的JSON数据类型字段
> - 也支持TEXT/VARCHAR字段存储JSON字符串
> - 自动处理确保数据格式正确，避免SQL注入风险


#### conditions 条件格式

`conditions` 参数用于指定更新条件，支持等值条件、比较运算符、空值判断等多种格式。

详细说明请参考 [CONDITIONS.md](CONDITIONS.md)。

```python
# 等值条件
{'status': 'active', 'department': 'IT'}

# 比较运算符
{
    'age': ('>', 18),
    'name': ('LIKE', '%张%'),
    'salary': ('BETWEEN', [5000, 10000]),
    'department': ('IN', ['IT', 'HR', 'Finance'])
}
```

## 基础UPDATE语法

### 单条记录更新

最基本的更新操作，指定表名、更新字段和条件：

```python
from lazy_mysql.executor import SQLExecutor

# 初始化连接（详见 CONNECTION.md）
config = {
    'host': 'localhost',
    'user': 'your_username',
    'password': 'your_password',
    'database': 'your_database'
}
executor = SQLExecutor(config)

# 更新单个用户的信息
executor.update(
    table_name='users',
    fields={'name': '张三', 'email': 'zhangsan@example.com', 'age': 28},
    conditions={'id': 1},
    commit=True
)
```

生成SQL：
```sql
UPDATE users SET name = %s, email = %s, age = %s WHERE id = %s;
```

### 批量条件更新

使用复杂条件更新多条记录：

```python
# 更新所有活跃用户的状态
executor.update(
    table_name='users',
    fields={'status': 'premium', 'updated_at': '2024-01-15 10:00:00'},
    conditions={
        'last_login': ('>=', '2024-01-01'),
        'status': ('IN', ['active', 'trial']),
        'points': ('>=', 1000)
    },
    commit=True
)
```

## 高级WHERE条件系统

### 多条件组合

所有条件默认使用 `AND` 逻辑连接：

```python
# 复杂条件组合
conditions = {
    'department': 'Engineering',
    'salary': ('BETWEEN', [8000, 20000]),
    'hire_date': ('>=', '2023-01-01'),
    'status': ('!=', 'terminated')
}

executor.update(
    table_name='employees',
    fields={'bonus_eligible': True, 'review_date': '2024-03-01'},
    conditions=conditions,
    commit=True
)
```

### 使用SQL表达式

对于需要引用字段值的更新，可以手动构建参数：

```python
# 原子递增操作
executor.execute(
    sql="UPDATE products SET stock = stock - %s, sold = sold + %s WHERE id = %s",
    params=(quantity, quantity, product_id),
    commit=True
)

# 或者使用字段引用
executor.execute(
    sql="UPDATE accounts SET balance = balance + %s WHERE user_id = %s",
    params=(amount, user_id),
    commit=True
)
```

## 性能优化建议

### 1. 索引优化

确保WHERE条件的字段有索引：

```python
# 好的做法：使用索引字段
executor.update(
    table_name='users',
    fields={'status': 'active'},
    conditions={'email': 'user@example.com'}  # email字段应有索引
)

# 避免：使用无索引的大字段
executor.update(
    table_name='users',
    fields={'status': 'active'},
    conditions={'description': ('LIKE', '%关键词%')}  # 性能差
)
```

### 2. 避免全表更新

```python
# 危险：没有WHERE条件会更新全表
# executor.update('users', {'status': 'active'}, {})  # 不要这样做

# 安全：总是指定条件
executor.update(
    table_name='users',
    fields={'status': 'active'},
    conditions={'status': 'inactive'}  # 明确指定范围
)
```

## 错误处理与调试

### 常见错误处理

```python
def safe_update(table, fields, conditions):
    """安全的更新操作包装"""
    try:
        executor.update(
            table_name=table,
            fields=fields,
            conditions=conditions,
            commit=True
        )
        return True, "更新成功"
    except Exception as e:
        error_msg = str(e)
        if "Duplicate entry" in error_msg:
            return False, "数据重复，违反唯一约束"
        elif "foreign key constraint" in error_msg:
            return False, "外键约束违反"
        elif "Data too long" in error_msg:
            return False, "数据长度超出限制"
        else:
            return False, f"更新失败: {error_msg}"
```

### 调试模式

```python
# 打印生成的SQL（开发环境）
def debug_update(table, fields, conditions):
    """调试模式：显示生成的SQL"""
    from lazy_mysql.utils.update import update as update_func
    from lazy_mysql.tools.where_clause import build_where_clause
    
    # 构建SQL
    set_clause = ', '.join([f"{field} = %s" for field in fields.keys()])
    where_clause, params = build_where_clause(conditions)
    
    sql = f"UPDATE {table} SET {set_clause} WHERE {where_clause};"
    print(f"Generated SQL: {sql}")
    print(f"Parameters: {list(fields.values()) + (params or [])}")
    
    # 执行更新
    return executor.update(table, fields, conditions, commit=True)
```

## 批量更新操作 (batch_update)

`batch_update` 是 `lazy_mysql` 提供的高性能批量更新方法，能够智能判断 WHERE 条件复杂度并选择最优的 SQL 生成策略。

### 函数签名

```python
batch_update(
    table_name: str,
    update_list: list,
    commit: bool = False,
    self_close: bool = False
)
```

### 参数说明

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `table_name` | str | 是 | - | 要更新的表名 |
| `update_list` | list | 是 | - | 更新数据列表，每个元素包含 `fields` 和 `conditions` |
| `commit` | bool | 否 | `False` | 是否自动提交事务 |
| `self_close` | bool | 否 | `False` | 操作完成后是否自动关闭数据库连接 |

### 智能策略选择

系统会自动分析更新条件，选择最优的执行策略：

1. **简化模式**（单一主键条件）：使用 `CASE key_field WHEN` 语法，性能最优
2. **复杂模式**（多字段或复杂条件）：使用 `CASE WHEN ... THEN` 语法，功能强大

### 使用示例

#### 示例1：单一主键条件（简化模式）

```python
update_list = [
    {'fields': {'name': '张三', 'age': 25}, 'conditions': {'id': 1}},
    {'fields': {'name': '李四', 'age': 30}, 'conditions': {'id': 2}}
]

executor.batch_update('users', update_list, commit=True)
```

生成的SQL：
```sql
UPDATE users SET 
    name = CASE id WHEN %s THEN %s WHEN %s THEN %s END,
    age = CASE id WHEN %s THEN %s WHEN %s THEN %s END
WHERE id IN (%s, %s);
```

参数：`(1, '张三', 2, '李四', 1, 25, 2, 30, 1, 2)`

#### 示例2：复杂条件（复杂模式）

```python
update_list = [
    {'fields': {'status': 'active'}, 'conditions': {'id': 1, 'type': 'user'}},
    {'fields': {'status': 'inactive'}, 'conditions': {'id': 2}}
]

executor.batch_update('users', update_list, commit=True)
```

生成的SQL：
```sql
UPDATE users SET 
    status = CASE 
        WHEN id = %s AND type = %s THEN %s 
        WHEN id = %s THEN %s 
        ELSE status END
WHERE (id = %s AND type = %s) OR (id = %s);
```

参数：`('active', 1, 'user', 'inactive', 2, 1, 'user', 2)`

### 性能优势

相比逐条执行 `UPDATE`，`batch_update` 具有以下优势：

- **减少网络往返**：单次执行多条更新
- **优化SQL生成**：根据条件复杂度智能选择最优语法
- **事务安全**：支持批量提交，保证数据一致性
- **参数化查询**：防止SQL注入，提高安全性

### 注意事项

1. **WHERE条件不能为空**：每个更新项都必须有明确的WHERE条件
2. **字段一致性**：所有 `fields` 中的字段会被统一处理
3. **数据类型**：列表和字典类型会自动转换为JSON字符串
4. **性能考虑**：适合中等批量更新（100-10000条记录）

## 合并更新列表 (merge_update_lists)

`merge_update_lists` 是一个实用工具函数，用于合并多个 `update_list`，根据相同的 `conditions` 自动合并 `fields`。

### 函数签名

```python
merge_update_lists(*update_lists, on_conflict='error')
```

### 参数说明

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `*update_lists` | list | 是 | - | 一个或多个 update_list |
| `on_conflict` | str | 否 | `'error'` | 冲突处理策略：`'error'` 抛出异常、`'skip'` 保留先出现的值、`'override'` 使用后出现的值覆盖 |

### 合并规则

1. 如果 `conditions` 完全相同（无论是否在同一个 `update_list` 内），则合并 `fields`
2. 如果 `fields` 中有重复字段但值相同，跳过该字段
3. 如果 `fields` 中有重复字段但值不同，根据 `on_conflict` 参数处理

### 使用示例

#### 基础合并

```python
from lazy_mysql.utils.update import merge_update_lists

list1 = [{'fields': {'name': '张三'}, 'conditions': {'id': 1}}]
list2 = [{'fields': {'age': 25}, 'conditions': {'id': 1}}]

merged = merge_update_lists(list1, list2)
# 结果: [{'fields': {'name': '张三', 'age': 25}, 'conditions': {'id': 1}}]
```

#### 配合 batch_update 使用

```python
from lazy_mysql.utils.update import merge_update_lists

# 不同来源的更新数据
updates_from_api = [
    {'fields': {'name': '张三'}, 'conditions': {'id': 1}},
    {'fields': {'name': '李四'}, 'conditions': {'id': 2}}
]

updates_from_cache = [
    {'fields': {'age': 25}, 'conditions': {'id': 1}},
    {'fields': {'age': 30}, 'conditions': {'id': 2}}
]

# 合并后批量更新
merged = merge_update_lists(updates_from_api, updates_from_cache)
executor.batch_update('users', merged, commit=True)
```

#### 冲突处理

```python
list1 = [{'fields': {'name': '张三'}, 'conditions': {'id': 1}}]
list2 = [{'fields': {'name': '李四'}, 'conditions': {'id': 1}}]

# 默认行为：抛出异常
merge_update_lists(list1, list2)  # ValueError: 字段 'name' 存在冲突

# 跳过冲突：保留先出现的值
merge_update_lists(list1, list2, on_conflict='skip')
# 结果: [{'fields': {'name': '张三'}, 'conditions': {'id': 1}}]

# 覆盖冲突：使用后出现的值
merge_update_lists(list1, list2, on_conflict='override')
# 结果: [{'fields': {'name': '李四'}, 'conditions': {'id': 1}}]
```

### 返回值

返回合并后的 `update_list`，其中 `fields` 和 `conditions` 均为深拷贝，不影响原始数据。