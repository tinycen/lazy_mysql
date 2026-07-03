# SQL工具函数

## add_limit - SQL条件语句构建

`add_limit` 函数用于构建SQL条件限制语句，支持多种比较运算符和灵活的参数配置。

### 函数签名
```python
def add_limit(column, value, column_alias="", add_and=True, operator="=")
```

### 参数说明

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| column | str | 必填 | 字段名 |
| value | Any | 必填 | 字段值，如果为"", "all", "null", None, [], ()则返回空字符串 |
| column_alias | str | "" | 表别名，可选参数 |
| add_and | bool | True | 是否添加AND前缀 |
| operator | str | "=" | 比较运算符，支持 =, !=, <>, >, >=, <, <=, LIKE, NOT LIKE, IN, NOT IN |

### 返回值
- **str**: SQL条件语句片段
- 如果value为"", "all", "null", None, [], ()，返回空字符串

### 支持的运算符

> **注意**：所有运算符不区分大小写，`LIKE` 和 `like` 效果相同。

| 运算符 | 说明 | 示例 |
|--------|------|------|
| = | 等于 | `add_limit('status', 'active')` |
| !=, <> | 不等于 | `add_limit('status', 'inactive', operator='!=')` |
| > | 大于 | `add_limit('age', 18, operator='>')` |
| >= | 大于等于 | `add_limit('age', 18, operator='>=')` |
| < | 小于 | `add_limit('age', 18, operator='<')` |
| <= | 小于等于 | `add_limit('age', 18, operator='<=')` |
| LIKE | 模糊匹配 | `add_limit('name', '%张%', operator='LIKE')` |
| NOT LIKE | 不匹配 | `add_limit('name', '%test%', operator='NOT LIKE')` |
| IN | 在列表中 | `add_limit('type', ['admin', 'user'], operator='IN')` |
| NOT IN | 不在列表中 | `add_limit('type', ['guest'], operator='NOT IN')` |

### 使用示例

#### 基本用法
```python
from lazy_mysql import add_limit

# 基本等值比较
result = add_limit('status', 'active')
# 输出: "AND status = 'active'"

# 使用表别名
result = add_limit('age', 25, 'u')
# 输出: "AND u.age = '25'"

# 不同的比较运算符
result = add_limit('age', 18, operator='>=')
# 输出: "AND age >= '18'"
```

#### 模糊匹配
```python
# LIKE 模糊匹配
result = add_limit('name', '%张%', operator='LIKE')
# 输出: "AND name LIKE '%张%'"

# NOT LIKE 不匹配
result = add_limit('email', '%test%', operator='NOT LIKE')
# 输出: "AND email NOT LIKE '%test%'"
```

#### 列表操作
```python
# IN 操作符
result = add_limit('type', ['admin', 'user', 'moderator'], operator='IN')
# 输出: "AND type IN ('admin', 'user', 'moderator')"

# NOT IN 操作符
result = add_limit('status', ['deleted', 'banned'], operator='NOT IN')
# 输出: "AND status NOT IN ('deleted', 'banned')"
```

#### 特殊值处理
```python
# 空值、all、null、None、空列表、空元组 返回空字符串
result = add_limit('status', '')
# 输出: ""

result = add_limit('status', 'all')
# 输出: ""

result = add_limit('status', 'null')
# 输出: ""

result = add_limit('status', None)
# 输出: ""

result = add_limit('status', [])
# 输出: ""

result = add_limit('status', ())
# 输出: ""

# 注意：数字 0 和 0.0 是有效值，会正常生成条件
result = add_limit('age', 0)
# 输出: "AND age = 0"

result = add_limit('score', 0.0)
# 输出: "AND score = 0.0"
```

#### 组合条件
```python
# 不添加 AND 前缀
result = add_limit('status', 'active', add_and=False)
# 输出: "status = 'active'"

# 结合表别名和自定义运算符
result = add_limit('create_time', '2023-01-01', 'u', operator='>=')
# 输出: "AND u.create_time >= '2023-01-01'"
```

### 注意事项

1. **SQL注入防护**: 函数会自动为字符串值添加引号，但在实际使用中建议结合参数化查询
2. **性能考虑**: 对于大量条件组合，建议使用 `build_where` 函数
3. **数据类型**: 所有值都会被转换为字符串并添加引号，数字类型也不例外
4. **大小写敏感**: 运算符不区分大小写，`LIKE` 和 `like` 效果相同

## load_sql - 载入SQL文件

`load_sql` 函数用于从文件中读取SQL语句，支持UTF-8编码。

### 函数签名
```python
def load_sql(sql_path)
```

### 参数说明

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| sql_path | str | 必填 | SQL文件路径 |

### 返回值
- **str**: 读取的SQL内容（去除首尾空白字符）

### 使用示例

```python
from lazy_mysql import load_sql

# 从文件载入SQL
sql_content = load_sql('queries/select_users.sql')
print(sql_content)
```

### 注意事项

1. **文件编码**: 默认使用UTF-8编码读取文件
2. **空白处理**: 返回的SQL内容会自动去除首尾空白字符
3. **错误处理**: 如果文件不存在或无法读取，会抛出相应的文件操作异常

### 相关函数
- [resolve_sql](#resolve_sql---智能解析SQL参数) - 自动判断 SQL 文本或文件路径
- [build_where](CONDITIONS.md#build_where) - 构建WHERE子句和参数列表
- [build_sql_with_where](CONDITIONS.md#build_sql_with_where) - 在基础SQL后拼接WHERE子句
- [NDayInterval](CONDITIONS.md#日期区间筛选ndayinterval) - 日期区间处理

### 更新日志
- v0.1.1: 从 `where_clause.py` 移动到 `sql_utils.py`

## resolve_sql - 智能解析SQL参数

`resolve_sql` 函数用于智能判断传入参数是 SQL 文本还是 `.sql` 文件路径，并自动加载文件内容。已内置于 `execute()` 和 `fetch_format()` 方法中，用户可直接传入文件路径而无需手动调用。

### 函数签名
```python
def resolve_sql(sql)
```

### 参数说明

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| sql | str \| os.PathLike | 必填 | SQL语句字符串、`.sql` 文件路径 或 `os.PathLike` 对象 |

### 返回值
- **str**: 解析后的 SQL 语句字符串

### 检测规则

| 优先级 | 输入类型 | 处理方式 |
|--------|---------|----------|
| 1 | `os.PathLike` 对象（如 `pathlib.Path`） | 视为文件路径，读取文件内容 |
| 2 | 字符串且以 `.sql` 结尾（不区分大小写） | 视为文件路径，读取文件内容 |
| 3 | 其他字符串 | 视为 SQL 文本，原样返回 |

### 使用示例

#### 直接使用
```python
from lazy_mysql.tools import resolve_sql
from pathlib import Path

# SQL 文本 → 原样返回
sql = resolve_sql('SELECT * FROM users WHERE age > 18')
# 输出: 'SELECT * FROM users WHERE age > 18'

# .sql 文件路径字符串 → 读取文件内容
sql = resolve_sql('queries/select_users.sql')
# 输出: 文件中的 SQL 内容

# pathlib.Path 对象 → 读取文件内容
sql = resolve_sql(Path('queries/select_users.sql'))
# 输出: 文件中的 SQL 内容

# 自定义 os.PathLike 对象 → 读取文件内容
class MyPath(os.PathLike):
    def __init__(self, path):
        self._path = path
    def __fspath__(self):
        return self._path

sql = resolve_sql(MyPath('queries/select_users.sql'))
# 输出: 文件中的 SQL 内容
```

#### 在 SQLExecutor 中使用（推荐）

`execute()` 和 `fetch_format()` 方法已内置 `resolve_sql`，可直接传入文件路径：

```python
from lazy_mysql import SQLExecutor

executor = SQLExecutor(sql_config)

# 直接传入 .sql 文件路径
executor.execute('sql/insert_users.sql', ('张三', 25), commit=True)
executor.query('sql/query_users.sql', fetch_config={'output_format': 'df_dict'})

# 也支持 pathlib.Path
from pathlib import Path
executor.execute(Path('sql/insert_users.sql'), commit=True)

# 原有的 SQL 文本方式完全不受影响
executor.execute("INSERT INTO users (name, age) VALUES (%s, %s)", ('张三', 25), commit=True)
```

### 注意事项

1. **幂等性**: 对已经是 SQL 文本的字符串调用会原样返回，因此可安全地多次调用
2. **大小写不敏感**: `.sql`、`.SQL`、`.Sql` 均可识别为文件路径
3. **空白容忍**: 路径前后的空白字符会被自动去除后再判断（`strip()`）
4. **错误处理**: 如果文件不存在或无法读取，会抛出相应的文件操作异常

### 相关函数
- [load_sql](#load_sql---载入sql文件) - 直接从文件读取 SQL 内容
- [add_limit](#add_limit---sql条件语句构建) - 构建 SQL 条件语句

### 更新日志
- 新增: 支持 `str` 和 `os.PathLike` 两种路径格式，内置于 `execute()` 和 `fetch_format()` 方法