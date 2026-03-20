# DELETE 操作完整指南

> **前提条件**：使用前请先阅读 [CONNECTION.md](CONNECTION.md) 完成数据库连接初始化。

`lazy_mysql` 的 DELETE 操作采用安全优先设计，通过强制 WHERE 条件验证和灵活的参数系统，有效防止意外数据丢失。与原始 SQL 不同（可能会因遗漏 WHERE 子句而删除所有记录），该库要求明确指定删除条件，确保只删除目标数据。


## 函数签名与参数说明

```python
delete(
    executor: SQLExecutor,
    table_name: str,
    conditions: dict,
    commit=False,
    self_close=False
)
```

### 核心参数

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `executor` | SQLExecutor | 是 | SQL执行器实例 |
| `table_name` | str | 是 | 目标表名 |
| `conditions` | dict | 是 | WHERE条件字典，支持多种运算符 |
| `commit` | bool | 否 | 是否自动提交事务，默认False |
| `self_close` | bool | 否 | 是否自动关闭数据库连接，默认False |

### WHERE 条件

`conditions` 参数用于指定删除条件，支持等值条件、比较运算符、空值判断等多种格式。

详细说明请参考 [CONDITIONS.md](CONDITIONS.md)。

#### 快速示例

```python
# 等值条件 - 删除指定ID用户
executor.delete(table_name='users', conditions={'id': 1001}, commit=True)

# 比较运算符 - 删除过期数据
executor.delete(
    table_name='logs',
    conditions={'created_at': ('<', '2023-01-01')},
    commit=True
)

# 列表包含 - 删除指定状态的用户
executor.delete(
    table_name='users',
    conditions={'status': ('IN', ['inactive', 'suspended'])},
    commit=True
)

# 复杂条件组合
executor.delete(
    table_name='users',
    conditions={
        'last_login': ('<', '2023-01-01'),
        'status': ('IN', ['inactive', 'suspended']),
        'login_attempts': ('>=', 5)
    },
    commit=True
)
```

## 错误处理与调试

### 1. 常见错误场景

```python
try:
    executor.delete(
        table_name='users',
        conditions={'id': 'invalid_id'},  # 类型不匹配
        commit=True
    )
except Exception as e:
    print(f"删除失败：{e}")
    # 可能的错误：
    # - 外键约束违反
    # - 数据类型不匹配
    # - 表或字段不存在
    # - 权限不足
```

### 2. 调试技巧

```python
def debug_delete(executor, table, conditions):
    """调试删除操作"""
    
    # 1. 检查表结构
    schema = executor.execute("DESCRIBE " + table, fetch=True)
    print(f"表结构：{schema}")
    
    # 2. 验证条件字段存在
    valid_fields = [col['Field'] for col in schema]
    for field in conditions.keys():
        if field not in valid_fields:
            print(f"警告：字段 {field} 不存在")
    
    # 3. 预览删除结果
    preview = executor.select(
        table,
        ['*'],
        conditions=conditions,
        limit=10
    )
    print(f"将要删除的前10条记录：{preview}")
    
    # 4. 获取准确的删除数量
    count = executor.select(
        table,
        ['COUNT(*) as total'],
        conditions=conditions,
        fetch_config={'fetch_mode': 'one'}
    )
    print(f"总计将删除 {count} 条记录")
```

## 完整使用示例

```python
from lazy_mysql.executor import SQLExecutor
import datetime

# 初始化连接（详见 CONNECTION.md）
executor = SQLExecutor(config)

try:
    # 示例1：安全删除单条记录
    user_id = 12345
    
    # 先验证记录存在
    user = executor.select(
        'users',
        ['id', 'username', 'email'],
        conditions={'id': user_id},
        fetch_config={'fetch_mode': 'oneTuple'}
    )
    
    if user:
        print(f"找到用户：{user}")
        executor.delete(
            table_name='users',
            conditions={'id': user_id},
            commit=True
        )
        print("用户删除成功")
    else:
        print("用户不存在")
    
    # 示例2：基于时间的批量清理
    cutoff_date = datetime.datetime.now() - datetime.timedelta(days=30)
    
    # 统计将要删除的日志数量
    old_logs = executor.select(
        'system_logs',
        ['COUNT(*) as count'],
        conditions={'created_at': ('<', cutoff_date.strftime('%Y-%m-%d'))},
        fetch_config={'fetch_mode': 'one'}
    )
    
    if old_logs > 0:
        print(f"准备删除 {old_logs} 条过期日志")
        
        executor.delete(
            table_name='system_logs',
            conditions={'created_at': ('<', cutoff_date.strftime('%Y-%m-%d'))},
            commit=True
        )
        
        print("过期日志清理完成")
    
    # 示例3：复杂条件删除
    executor.delete(
        table_name='notifications',
        conditions={
            'is_read': True,
            'created_at': ('<', '2024-01-01'),
            'priority': ('IN', ['low', 'medium'])
        },
        commit=True
    )
    print("已清理已读的低优先级旧通知")

finally:
    executor.close()
```
