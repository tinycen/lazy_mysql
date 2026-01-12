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
| value | Any | 必填 | 字段值，如果为"", "all", "null"则返回空字符串 |
| column_alias | str | "" | 表别名，可选参数 |
| add_and | bool | True | 是否添加AND前缀 |
| operator | str | "=" | 比较运算符，支持 =, !=, <>, >, >=, <, <=, LIKE, NOT LIKE, IN, NOT IN |

### 返回值
- **str**: SQL条件语句片段
- 如果value为"", "all", "null"，返回空字符串

### 支持的运算符

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
# 空值、all、null 返回空字符串
result = add_limit('status', '')
# 输出: ""

result = add_limit('status', 'all')
# 输出: ""

result = add_limit('status', 'null')
# 输出: ""
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
2. **性能考虑**: 对于大量条件组合，建议使用 `build_where_clause` 函数
3. **数据类型**: 所有值都会被转换为字符串并添加引号，数字类型也不例外
4. **大小写敏感**: 运算符不区分大小写，`LIKE` 和 `like` 效果相同

### 相关函数
- [build_where_clause](SELECT.md#build_where_clause) - 构建完整的WHERE子句
- [NDayInterval](SELECT.md#ndayinterval) - 日期区间处理

### 更新日志
- v0.1.1: 从 `where_clause.py` 移动到 `sql_utils.py`