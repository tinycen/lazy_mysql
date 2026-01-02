# SELECT 操作完整指南

> **前提条件**：使用前请先阅读 [CONNECTION.md](CONNECTION.md) 完成数据库连接初始化。

`lazy_mysql` 的 SELECT 操作采用模块化设计，由以下核心组件协同工作：

- **SQLExecutor**: 主接口类，提供统一的查询入口
- **select()**: 智能查询构建器，支持复杂SQL自动生成
- **build_where_clause()**: 动态WHERE条件构建器，防SQL注入
- **fetch_format()**: 多格式结果处理器，支持DataFrame/字典/元组等格式

## 函数签名与参数说明

```python
select(
    executor: SQLExecutor,
    table_names,
    select_fields,
    where_conditions,
    order_by=None,
    limit=None,
    join_conditions=None,
    self_close=False,
    fetch_config=None
)
```

### 核心参数

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `executor` | SQLExecutor | 是 | SQL执行器实例 |
| `table_names` | str/list | 是 | 表名，支持单表字符串或多表列表 |
| `select_fields` | list/dict | 是 | 查询字段列表，支持字典格式指定表前缀 |
| `where_conditions` | dict | 是 | WHERE条件字典，支持多种运算符 |
| `order_by` | str | 否 | 排序子句，如 `"id DESC"` |
| `limit` | int | 否 | 限制返回记录数 |
| `join_conditions` | dict | 否 | JOIN配置，格式见下方说明 |
| `self_close` | bool | 否 | 是否自动关闭数据库连接 |
| `fetch_config` | dict | 否 | 结果格式化配置，详见下方说明 |

### fetch_config 详细配置

`fetch_config` 是一个字典，用于控制查询结果的返回格式和行为：

#### 1. fetch_mode - 获取模式
控制返回数据的数量和格式：
- `"all"` (默认): 获取所有结果
- `"oneTuple"`: 获取单条记录（元组格式）
- `"one"`: 获取单个值（第一个字段的值）

#### 2. output_format - 输出格式
仅当 `fetch_mode="all"` 时有效：
- `""` (默认): 返回原始元组列表
- `"list_1"`: 返回扁平化的列表（提取每行的第一个字段）
- `"df"`: 返回 pandas DataFrame
- `"df_dict"`: 返回字典列表（DataFrame转dict）

#### 3. data_label - 自定义列名
用于 DataFrame 的列名或字典的键名重命名：
- 类型: `list[str]`
- 如果为 `None`，系统会根据 `select_fields` 自动生成

#### 4. show_count - 显示计数
- 类型: `bool`
- 默认值: `False`
- 如果为 `True`，返回 `(数据, 总数)` 元组

#### 5. order_by & limit
- `order_by`: 排序子句，优先级高于外层参数
- `limit`: 限制记录数，优先级高于外层参数

### fetch_config 配置示例

```python
# 示例1: 获取所有记录并返回DataFrame
fetch_config = {
    "fetch_mode": "all",
    "output_format": "df",
    "data_label": ["用户ID", "用户名", "邮箱"],
    "show_count": True
}

# 示例2: 获取单条记录
fetch_config = {
    "fetch_mode": "oneTuple"
}

# 示例3: 获取单个值
fetch_config = {
    "fetch_mode": "one"
}

# 示例4: 获取字典列表并排序限制
fetch_config = {
    "fetch_mode": "all",
    "output_format": "df_dict",
    "order_by": "created_at DESC",
    "limit": 100
}
```

## 基础查询

### 单表查询

最基础的数据检索，只需指定表名和字段列表：

```python
from lazy_mysql.executor import SQLExecutor

# 初始化连接（详见 CONNECTION.md）
executor = SQLExecutor(config)

# 查询所有用户的基础信息
users = executor.select('users', ['id', 'username', 'email'])
print(users)  # [{'id': 1, 'username': 'alice', 'email': 'alice@example.com'}, ...]
```

生成的SQL：`SELECT id, username, email FROM users`

### 多字段别名查询

支持字段重命名和表前缀指定：

```python
# 使用字典指定字段和表
result = executor.select(
    'users',
    {'users': ['id', 'name', 'email'], 'profiles': ['bio', 'avatar']},
    join_conditions={
        'join_type': 'LEFT JOIN',
        'conditions': ['users.id', '=', 'profiles.user_id']
    }
)
```

## WHERE条件系统

### 基础条件格式

支持三种条件定义方式：

```python
# 方式1：等值条件（推荐）
conditions = {
    'status': 'active',
    'age': 25
}

# 方式2：自定义运算符（元组格式）
conditions = {
    'age': ('>', 18),
    'name': ('LIKE', '%John%'),
    'status': ('IN', ['active', 'pending'])
}

# 方式3：最近N天区间（NDayInterval）
from lazy_mysql.tools.where_clause import NDayInterval
conditions = {
    'order_dateTime': ('>=', NDayInterval(7))  # 最近7天
}
```

### 完整运算符支持

| 运算符 | 示例 | 说明 |
|--------|------|------|
| `=` | `{'status': 'active'}` | 精确匹配 |
| `!=`/`\<>` | `{'status': ('!=', 'deleted')}` | 不等于 |
| `>` | `{'score': ('>', 90)}` | 大于 |
| `>=` | `{'age': ('>=', 18)}` | 大于等于 |
| `<` | `{'price': ('<', 100)}` | 小于 |
| `<=` | `{'stock': ('<=', 10)}` | 小于等于 |
| `LIKE` | `{'title': ('LIKE', '%Python%')}` | 模糊匹配 |
| `NOT LIKE` | `{'title': ('NOT LIKE', '%Test%')}` | 反向模糊匹配 |
| `NDayInterval` | `{'time': ('>=', NDayInterval(7))}` | 最近N天日期区间 |
| `IN` | `{'category': ('IN', ['tech', 'science'])}` | 包含列表 |
| `NOT IN` | `{'status': ('NOT IN', ['archived', 'deleted'])}` | 不包含列表 |

### 复杂条件组合

```python
# 多条件AND组合
conditions = {
    'status': 'active',
    'created_at': ('>=', '2024-01-01'),
    'score': ('BETWEEN', [80, 100])
}

result = executor.select(
    'users',
    ['id', 'username', 'score'],
    where_conditions=conditions,
    order_by='score DESC',
    limit=50
)
```

## 排序和限制结果

过滤数据后，您通常希望对结果进行排序并限制返回的结果数量。lazy_mysql 为这些常见操作提供了直接的参数。

### 基础排序和限制

```python
# 排序和限制结果
result = executor.select(
    'users',
    ['id', 'name', 'email'],
    where_conditions={'status': 'active'},
    order_by='registration_date DESC',  # 按最新注册时间排序
    limit=10  # 只获取前 10 条结果
)
```
将转换为 SQL：`SELECT id, name, email FROM users WHERE status = %s ORDER BY registration_date DESC LIMIT 10`

### 多列排序

`order_by` 参数接受任何有效的 SQL ORDER BY 子句，包括多列：

```python
# 多列排序
result = executor.select(
    'users',
    ['id', 'name', 'email'],
    order_by='status ASC, last_login DESC'  # 先按状态排序，然后按最后登录时间排序
)
```

### 仅限制结果数量

```python
# 只限制数量，不排序
recent_users = executor.select(
    'users',
    ['id', 'name', 'email'],
    limit=5  # 获取前5条记录
)

# 只排序，不限制数量
sorted_users = executor.select(
    'users',
    ['id', 'name', 'email'],
    order_by='created_at ASC'
)
```

### 分页查询

结合排序和限制实现分页：

```python
# 第2页，每页10条记录
page = 2
per_page = 10
offset = (page - 1) * per_page

result = executor.select(
    'users',
    ['id', 'name', 'email'],
    order_by='id ASC',
    limit=per_page,
    offset=offset
)
```

## JOIN操作详解

### 基础JOIN语法

支持所有标准JOIN类型：

```python
# INNER JOIN - 获取有订单的用户
result = executor.select(
    ['users', 'orders'],
    ['users.id', 'users.username', 'orders.total', 'orders.created_at'],
    join_conditions={
        'join_type': 'INNER JOIN',
        'conditions': ['users.id', '=', 'orders.user_id']
    }
)
```

### 多表JOIN链式操作

```python
# 三表JOIN：用户-订单-商品
result = executor.select(
    ['users', 'orders', 'order_items', 'products'],
    [
        'users.username',
        'orders.order_number',
        'products.name',
        'order_items.quantity',
        'order_items.price'
    ],
    join_conditions={
        'join_type': 'INNER JOIN',
        'conditions': ['users.id', '=', 'orders.user_id']
    },
    where_conditions={'orders.status': 'completed'}
)
```

### JOIN类型完整支持

- `INNER JOIN`: 只返回匹配的记录
- `LEFT JOIN`: 返回左表所有记录，右表不匹配为NULL
- `RIGHT JOIN`: 返回右表所有记录，左表不匹配为NULL
- `FULL OUTER JOIN`: 返回两表所有记录

## 结果格式化系统

### 游标类型控制 (dict_cursor)

`lazy_mysql` 支持两种游标返回格式，通过 `dict_cursor` 参数控制：

- **`dict_cursor=False`** (默认): 返回元组列表 `[(1, 'Alice'), (2, 'Bob')]`
- **`dict_cursor=True`**: 返回字典列表 `[{'id': 1, 'name': 'Alice'}, {'id': 2, 'name': 'Bob'}]`

```python
# 初始化时指定游标类型为字典格式
executor = SQLExecutor(config, dict_cursor=True)

# 此时所有查询默认返回字典格式
users = executor.select('users', ['id', 'name', 'email'])
# 返回: [{'id': 1, 'name': 'Alice', 'email': 'alice@example.com'}, ...]

# 也可以在单次查询中覆盖默认设置
users_tuple = executor.select(
    'users', 
    ['id', 'name'], 
    dict_cursor=False  # 强制使用元组格式
)
# 返回: [(1, 'Alice'), (2, 'Bob'), ...]
```

### 获取模式 (fetch_mode)

```python
# 获取所有记录（默认）
all_users = executor.select('users', ['id', 'name'], fetch_config={'fetch_mode': 'all'})

# 获取单条记录（元组格式）
single_user = executor.select(
    'users',
    ['id', 'name', 'email'],
    where_conditions={'id': 1},
    fetch_config={'fetch_mode': 'oneTuple'}
)
# 返回: (1, 'Alice', 'alice@example.com')

# 获取单个值
user_count = executor.select(
    'users',
    ['COUNT(*)'],
    fetch_config={'fetch_mode': 'one'}
)
# 返回: 150
```

### 输出格式 (output_format)

仅当`fetch_mode='all'`时有效：

```python
# 原始元组列表（性能最优）
raw_data = executor.select(
    'users',
    ['id', 'name'],
    fetch_config={'fetch_mode': 'all', 'output_format': ''}
)
# 返回: [(1, 'Alice'), (2, 'Bob'), ...]

# 字典列表（默认）
dict_data = executor.select(
    'users',
    ['id', 'name', 'email'],
    fetch_config={'fetch_mode': 'all', 'output_format': 'df_dict'}
)
# 返回: [{'id': 1, 'name': 'Alice', 'email': 'alice@example.com'}, ...]

# 当 dict_cursor=True 时，output_format 可以省略
executor_dict = SQLExecutor(config, dict_cursor=True)
users = executor_dict.select('users', ['id', 'name', 'email'])
# 返回: [{'id': 1, 'name': 'Alice', 'email': 'alice@example.com'}, ...]
# 此时 无需显式指定 output_format 参数

# Pandas DataFrame
df_data = executor.select(
    'users',
    ['id', 'name', 'age'],
    fetch_config={'fetch_mode': 'all', 'output_format': 'df'}
)
# 返回: pandas.DataFrame对象

# 扁平化列表（提取第一列）
id_list = executor.select(
    'users',
    ['id'],
    fetch_config={'fetch_mode': 'all', 'output_format': 'list_1'}
)
# 返回: [1, 2, 3, 4, 5, ...]
```

### 自定义列名

```python
# 使用data_label重命名列
result = executor.select(
    'users',
    ['id', 'username', 'email'],
    fetch_config={
        'fetch_mode': 'all',
        'output_format': 'df_dict',
        'data_label': ['用户ID', '用户名', '邮箱地址']
    }
)
# 返回: [{'用户ID': 1, '用户名': 'alice', '邮箱地址': 'alice@example.com'}, ...]
```

### 结果计数

```python
# 同时获取数据和总数
users, total = executor.select(
    'users',
    ['id', 'name', 'email'],
    where_conditions={'status': 'active'},
    fetch_config={
        'fetch_mode': 'all',
        'output_format': 'df_dict',
        'show_count': True
    }
)
print(f"找到 {total} 个活跃用户")
```

## 连接管理最佳实践

### 自动连接关闭

```python
# 单次查询自动关闭
result = executor.select('users', ['id', 'name'], self_close=True)

# 批量操作手动管理
try:
    users = executor.select('users', ['id', 'name'])
    orders = executor.select('orders', ['id', 'total'])
    # ... 其他操作
finally:
    executor.close()
```

## 性能优化指南

### 1. 字段选择优化

```python
# ✅ 好：只查询需要的字段
users = executor.select('users', ['id', 'username'])

# ❌ 避免：查询所有字段
users = executor.select('users', ['*'])
```

### 2. WHERE条件优化

```python
# ✅ 好：数据库层面过滤
active_users = executor.select(
    'users',
    ['id', 'name'],
    where_conditions={'status': 'active', 'last_login': ('>', '2024-01-01')}
)

# ❌ 避免：应用层过滤
all_users = executor.select('users', ['id', 'name', 'status', 'last_login'])
active_users = [u for u in all_users if u['status'] == 'active']
```

### 3. 索引利用

```python
# 确保WHERE条件的字段有索引
indexed_query = executor.select(
    'users',
    ['id', 'email'],
    where_conditions={'email': 'user@example.com'}  # email字段应有索引
)
```

### 4. JOIN优化

```python
# ✅ 好：使用小表驱动大表
result = executor.select(
    ['users', 'orders'],  # users表通常较小
    ['users.id', 'orders.total'],
    join_conditions={'join_type': 'INNER JOIN', 'conditions': ['users.id', '=', 'orders.user_id']}
)
```

## 常见错误处理

### 1. 字段重复处理

```python
# 当多个表有相同字段名时，使用表前缀
result = executor.select(
    ['users', 'profiles'],
    ['users.id', 'profiles.id', 'users.name', 'profiles.bio'],
    join_conditions={'join_type': 'LEFT JOIN', 'conditions': ['users.id', '=', 'profiles.user_id']}
)
```

### 2. 空结果处理

```python
# 安全处理空结果
result = executor.select(
    'users',
    ['id', 'name'],
    where_conditions={'email': 'nonexistent@example.com'},
    fetch_config={'fetch_mode': 'all', 'output_format': 'df_dict'}
)

if not result:
    print("未找到匹配记录")
else:
    print(f"找到 {len(result)} 条记录")
```

## 高级用法示例

### 复杂业务查询

```python
# 获取最近30天的高价值订单用户信息
recent_high_value = executor.select(
    ['users', 'orders'],
    [
        'users.id',
        'users.username',
        'users.email',
        'COUNT(orders.id) as order_count',
        'SUM(orders.total) as total_spent',
        'MAX(orders.created_at) as last_order_date'
    ],
    join_conditions={
        'join_type': 'INNER JOIN',
        'conditions': ['users.id', '=', 'orders.user_id']
    },
    where_conditions={
        'orders.created_at': ('>=', '2024-11-01'),
        'orders.status': 'completed'
    },
    order_by='total_spent DESC',
    limit=100,
    fetch_config={
        'fetch_mode': 'all',
        'output_format': 'df_dict'
    }
)
```