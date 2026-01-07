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

### WHERE条件系统

#### 1. 基础等值条件

最简单的条件格式，直接指定字段和值的精确匹配：

```python
# 删除ID为1001的用户
executor.delete(
    table_name='users',
    conditions={'id': 1001},
    commit=True
)
# 生成SQL: DELETE FROM users WHERE id = %s

# 删除特定邮箱的用户
executor.delete(
    table_name='users',
    conditions={'email': 'spam@example.com', 'status': 'unverified'},
    commit=True
)
# 生成SQL: DELETE FROM users WHERE email = %s AND status = %s
```

#### 2. 高级比较运算符

支持完整的SQL比较运算符：

| 运算符 | 示例 | 说明 |
|--------|------|------|
| `=` | `{'status': 'active'}` | 精确匹配 |
| `!=`/`<>` | `{'status': ('!=', 'deleted')}` | 不等于 |
| `>` | `{'age': ('>', 18)}` | 大于 |
| `>=` | `{'score': ('>=', 90)}` | 大于等于 |
| `<` | `{'created_at': ('<', '2024-01-01')}` | 小于 |
| `<=` | `{'price': ('<=', 100)}` | 小于等于 |
| `LIKE` | `{'title': ('LIKE', '%spam%')}` | 模糊匹配 |
| `NOT LIKE` | `{'title': ('NOT LIKE', '%test%')}` | 反向模糊匹配 |
| `IN` | `{'status': ('IN', ['inactive', 'suspended'])}` | 包含列表 |
| `NOT IN` | `{'type': ('NOT IN', ['temp', 'draft'])}` | 不包含列表 |
| `BETWEEN` | `{'score': ('BETWEEN', [80, 100])}` | 区间匹配 |

#### 3. 复杂条件组合

多个条件自动使用 AND 连接：

```python
# 删除长时间未登录的非活跃用户
executor.delete(
    table_name='users',
    conditions={
        'last_login': ('<', '2023-01-01'),
        'status': ('IN', ['inactive', 'suspended']),
        'login_attempts': ('>=', 5),
        'email_verified': False
    },
    commit=True
)
# 生成SQL: DELETE FROM users WHERE last_login < %s AND status IN %s AND login_attempts >= %s AND email_verified = %s
```

#### 4. 子查询条件

虽然 WHERE 条件主要是字段级别的，但可以通过构建复杂条件实现类似子查询的效果：

```python
# 删除没有任何订单的用户（通过关联查询确认）
# 第1步：找出无订单的用户ID
orphan_users = executor.select(
    'users',
    ['id'],
    conditions={'id': ('NOT IN', executor.select('orders', ['user_id'], fetch_config={'fetch_mode': 'list_1'}))}
)

# 第2步：删除这些用户
if orphan_users:
    executor.delete(
        table_name='users',
        conditions={'id': ('IN', [u['id'] for u in orphan_users])},
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
