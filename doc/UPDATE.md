# UPDATE 操作完整指南

`lazy_mysql` 的 UPDATE 操作采用简洁而强大的设计，让您能够安全高效地更新数据库记录。通过动态SQL构建和参数化查询，既保证了代码的可读性，又防止了SQL注入攻击。

## 函数签名与参数说明

```python
update(
    executor: SQLExecutor,
    table_name: str,
    update_fields: dict,
    where_conditions: dict,
    commit: bool = False,
    self_close: bool = False
)
```

### 核心参数

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `executor` | SQLExecutor | 是 | - | SQL执行器实例，负责数据库连接和事务管理 |
| `table_name` | str | 是 | - | 要更新的表名，支持标准SQL表名格式 |
| `update_fields` | dict | 是 | - | 需要更新的字段和值，格式为 `{'字段名': '新值'}` |
| `where_conditions` | dict | 是 | - | WHERE条件字典，支持多种运算符和复杂条件 |
| `commit` | bool | 否 | `False` | 是否自动提交事务，`False` 需要手动提交 |
| `self_close` | bool | 否 | `False` | 操作完成后是否自动关闭数据库连接 |

### 参数详解

#### update_fields 格式说明
`update_fields` 参数接受一个字典，键为字段名，值为要设置的新值：

```python
# 简单更新
{'name': '张三', 'age': 25, 'status': 'active'}

# 使用SQL表达式（需手动处理参数）
{'balance': ('balance + %s', 100), 'updated_at': ('NOW()',)}
```
> ✅ **自动JSON序列化**
> 
> **列表和字典类型自动处理**：当`update_fields`中的值为Python列表或字典时，系统会自动将其转换为JSON字符串，无需手动处理。
> 
> **自动转换示例**：
> ```python
> # 系统会自动处理，无需手动转换
> update_fields = {
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


#### where_conditions 条件格式

**方式1：等值条件（推荐）**
```python
{'status': 'active', 'department': 'IT'}
# 生成: WHERE status = %s AND department = %s
```

**方式2：自定义运算符（元组格式）**
```python
{
    'age': ('>', 18),
    'name': ('LIKE', '%张%'),
    'salary': ('BETWEEN', [5000, 10000]),
    'department': ('IN', ['IT', 'HR', 'Finance'])
}
```

### 完整运算符支持

| 运算符 | 示例 | 生成SQL | 说明 |
|--------|------|---------|------|
| `=` | `{'status': 'active'}` | `status = %s` | 精确匹配（默认） |
| `!=`/`<> ` | `{'status': ('!=', 'deleted')}` | `status != %s` | 不等于 |
| `>` | `{'score': ('>', 90)}` | `score > %s` | 大于 |
| `>=` | `{'age': ('>=', 18)}` | `age >= %s` | 大于等于 |
| `<` | `{'price': ('<', 100)}` | `price < %s` | 小于 |
| `<=` | `{'stock': ('<=', 10)}` | `stock <= %s` | 小于等于 |
| `LIKE` | `{'title': ('LIKE', '%Python%')}` | `title LIKE %s` | 模糊匹配 |
| `NOT LIKE` | `{'title': ('NOT LIKE', '%Test%')}` | `title NOT LIKE %s` | 反向模糊匹配 |
| `IN` | `{'category': ('IN', ['tech', 'science'])}` | `category IN (%s, %s)` | 包含列表 |
| `NOT IN` | `{'status': ('NOT IN', ['archived', 'deleted'])}` | `status NOT IN (%s, %s)` | 不包含列表 |
| `BETWEEN` | `{'score': ('BETWEEN', [80, 100])}` | `score BETWEEN %s AND %s` | 范围查询 |

## 基础UPDATE语法

### 单条记录更新

最基本的更新操作，指定表名、更新字段和条件：

```python
from lazy_mysql.executor import SQLExecutor

# 初始化连接
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
    update_fields={'name': '张三', 'email': 'zhangsan@example.com', 'age': 28},
    where_conditions={'id': 1},
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
    update_fields={'status': 'premium', 'updated_at': '2024-01-15 10:00:00'},
    where_conditions={
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
    update_fields={'bonus_eligible': True, 'review_date': '2024-03-01'},
    where_conditions=conditions,
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
    update_fields={'status': 'active'},
    where_conditions={'email': 'user@example.com'}  # email字段应有索引
)

# 避免：使用无索引的大字段
executor.update(
    table_name='users',
    update_fields={'status': 'active'},
    where_conditions={'description': ('LIKE', '%关键词%')}  # 性能差
)
```

### 2. 避免全表更新

```python
# 危险：没有WHERE条件会更新全表
# executor.update('users', {'status': 'active'}, {})  # 不要这样做

# 安全：总是指定条件
executor.update(
    table_name='users',
    update_fields={'status': 'active'},
    where_conditions={'status': 'inactive'}  # 明确指定范围
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
            update_fields=fields,
            where_conditions=conditions,
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