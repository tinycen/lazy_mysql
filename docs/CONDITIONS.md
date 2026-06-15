# WHERE 条件构造指南

本文档详细说明 `lazy_mysql` 中 `conditions` 参数的构造方式，适用于 `select()`、`update()`、`delete()` 等所有需要条件过滤的操作。

## 基础条件格式

### 方式1：等值条件（最常用）

当条件为精确匹配时，直接使用 `字段名: 值` 的形式：

```python
conditions = {
    'status': 'active',
    'age': 25,
    'is_vip': True
}
```

生成的 SQL：`WHERE status = %s AND age = %s AND is_vip = %s`

### 方式2：自定义运算符（元组格式）

当需要使用其他比较运算符时，使用 `(运算符, 值)` 的元组格式：

```python
conditions = {
    'age': ('>', 18),
    'name': ('LIKE', '%John%'),
    'score': ('>=', 90),
    'status': ('IN', ['active', 'pending'])
}
```

生成的 SQL：`WHERE age > %s AND name LIKE %s AND score >= %s AND status IN (%s, %s)`

## 完整运算符支持
**说明：运算符大小写不敏感，会自动转为大写。**

| 运算符 | 示例 | 说明 |
|--------|------|------|
| `=` | `{'status': 'active'}` | 精确匹配（默认） |
| `!=` / `<>` | `{'status': ('!=', 'deleted')}` | 不等于 |
| `>` | `{'score': ('>', 90)}` | 大于 |
| `>=` | `{'age': ('>=', 18)}` | 大于等于 |
| `<` | `{'price': ('<', 100)}` | 小于 |
| `<=` | `{'stock': ('<=', 10)}` | 小于等于 |
| `LIKE` | `{'title': ('LIKE', '%Python%')}` | 模糊匹配 |
| `NOT LIKE` | `{'title': ('NOT LIKE', '%Test%')}` | 反向模糊匹配 |
| `IS NULL` | `{'deleted_at': 'NULL'}` | 为空判断 |
| `IS NOT NULL` | `{'email': 'NOT NULL'}` | 非空判断 |
| `IN` | `{'category': ('IN', ['tech', 'science'])}` | 包含列表 |
| `NOT IN` | `{'status': ('NOT IN', ['archived', 'deleted'])}` | 不包含列表 |

## 空值判断

使用字符串 `'NULL'` 和 `'NOT NULL'` 进行空值判断：

```python
# 查询未删除的用户（软删除场景）
conditions = {'deleted_at': 'NULL'}
# 生成 SQL: WHERE deleted_at IS NULL

# 查询已填写邮箱的用户
conditions = {'email': 'NOT NULL'}
# 生成 SQL: WHERE email IS NOT NULL

# 组合条件
conditions = {
    'deleted_at': 'NULL',
    'email': 'NOT NULL',
    'status': 'active'
}
# 生成 SQL: WHERE deleted_at IS NULL AND email IS NOT NULL AND status = %s
```

## 日期区间筛选（NDayInterval）

用于筛选最近 N 天的数据：

```python
from lazy_mysql.tools.where_clause import NDayInterval

conditions = {
    'order_dateTime': ('>=', NDayInterval(7))  # 最近7天
}
```

生成的 SQL：`WHERE order_dateTime >= DATE_SUB(NOW(), INTERVAL 7 DAY)`

## 复杂条件组合

多个条件会自动使用 `AND` 连接：

```python
conditions = {
    'status': 'active',
    'created_at': ('>=', '2024-01-01'),
    'score': ('>', 80),
    'deleted_at': 'NULL'
}
```

生成的 SQL：`WHERE status = %s AND created_at >= %s AND score > %s AND deleted_at IS NULL`

## 使用示例

### SELECT 查询

```python
from lazy_mysql.executor import SQLExecutor

executor = SQLExecutor(config)

# 等值条件
users = executor.select('users', ['id', 'name'], conditions={'status': 'active'})

# 范围条件
adults = executor.select('users', ['id', 'name'], conditions={'age': ('>=', 18)})

# 模糊查询
results = executor.select('users', ['id', 'name'], conditions={'name': ('LIKE', '%张%')})

# 列表包含
results = executor.select('users', ['id', 'name'], conditions={'status': ('IN', ['active', 'pending'])})

# 空值判断
active_users = executor.select('users', ['id', 'name'], conditions={'deleted_at': 'NULL'})
```

### UPDATE 更新

```python
# 更新指定用户的邮箱
executor.update(
    'users',
    {'email': 'new@example.com'},
    conditions={'id': 1}
)

# 批量更新状态
executor.update(
    'users',
    {'status': 'inactive'},
    conditions={'last_login': ('<', '2024-01-01')}
)
```

### DELETE 删除

```python
# 删除指定用户
executor.delete('users', conditions={'id': 1})

# 删除过期数据
executor.delete('logs', conditions={'created_at': ('<', NDayInterval(30))})
```

## 注意事项

1. **参数安全**：所有值都会使用参数化查询，防止 SQL 注入
2. **numpy 类型**：不支持 numpy 类型数据，请先转换为 Python 原生类型
3. **字典类型**：字典类型的值会自动转换为 JSON 字符串
4. **大小写不敏感**：`'NULL'` 和 `'null'`、`'Null'` 效果相同
