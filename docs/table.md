# Table 表结构工具

`lazy_mysql.table` 模块提供表结构元数据导出与表数据修复相关的实用工具，让你无需离开 Python 即可一键生成数据库文档、修复历史脏数据。

## 📦 导入方式

该模块未在主包中直接暴露，需从 `lazy_mysql.table` 显式导入：

> **前提条件**：使用前请先阅读 [CONNECTION.md](CONNECTION.md) 完成数据库连接初始化。

`lazy_mysql.table` 对外导出以下函数：

| 函数 | 说明 |
| --- | --- |
| `export_md` | 将表/视图结构导出为 Markdown 文档 |
| `fix_json` | 将 TEXT 列中不符合 JSON 规范的值修复为合法 JSON |
| `validate_table_name` | 表名校验（防 SQL 注入，内部使用，也可单独调用） |

---

## 📝 export_md — 表结构导出

`export_md(executor, table_name, save_path=None, self_close=True)`

将表或视图的字段、字段类型、字段描述、主键、索引等信息导出为 Markdown 文件。函数会根据 `table_name` 的类型自动选择导出模式：

- **字符串**：导出单个表或视图（内部自动识别视图）。
- **列表 / 元组**：批量导出多个表与视图，表与视图分别写入不同目录。

### 参数说明

| 参数 | 类型 | 说明 |
| --- | --- | --- |
| `executor` | `SQLExecutor` | 已初始化的执行器实例 |
| `table_name` | `str` / `list` / `tuple` | 表名，或表名列表；传入 `list`/`tuple` 触发批量导出 |
| `save_path` | `str` \| `None` | 单个表时为文件路径，批量时为目录路径；默认当前目录 |
| `self_close` | `bool` | 导出完成后是否自动关闭连接，默认 `True` |

### 单个表导出

```python
from lazy_mysql.table import export_md

# 导出单个表，默认保存为 "users.md"
export_md(executor, 'users')

# 指定保存路径
export_md(executor, 'users', save_path='docs/users.md')

# 复用连接，不自动关闭（适合连续多次操作）
export_md(executor, 'users', self_close=False)
# ... 后续操作
executor.close()
```

导出的 Markdown 包含：

- **表信息**：字符集、排序规则
- **字段信息**：字段名、字段类型、编码/排序规则、字段描述、默认值、是否主键
- **索引信息**：索引名、索引类型（主键/唯一/普通）、包含字段、备注（复合索引会标注字段数）

### 视图导出

传入视图名时，`export_md` 会自动识别并委托视图导出逻辑，除字段信息外还会附带**源 SQL**（已格式化）。

```python
# 视图会自动识别，导出内容包含字段信息与源 SQL
export_md(executor, 'user_order_view', save_path='docs/user_order_view.md')
```

### 批量导出

传入列表或元组时进入批量模式，返回包含 `'tables'` 与 `'views'` 两个列表的结果字典；表写入 `save_dir`，视图写入 `save_dir/views` 子目录。

```python
# 批量导出指定表与视图
result = export_md(executor, ['users', 'orders', 'user_order_view'], save_dir='docs/table_docs')
print(result)
# {'tables': ['users', 'orders'], 'views': ['user_order_view']}

# 传入空列表，导出数据库中所有表与视图
export_md(executor, [], save_dir='docs/table_docs')
```

> 提示：批量导出时请勿将 `self_close` 设为 `False`，除非你在外层统一管理连接生命周期。

---

## 🔧 fix_json — JSON 列修复

`fix_json(executor, table_name, index_column, target_column, commit=False, self_close=False)`

历史数据中常出现以 TEXT 存储、却使用单引号（Python 风格）或其它非标准格式的「伪 JSON」字符串，导致 `JSON_VALID()` 校验失败。该函数扫描这些非法值，使用 `ast.literal_eval` 解析后重新序列化为标准 JSON（双引号），并通过 `batch_update` 写回。

### 参数说明

| 参数 | 类型 | 说明 |
| --- | --- | --- |
| `executor` | `SQLExecutor` | 已初始化的执行器实例 |
| `table_name` | `str` | 表名 |
| `index_column` | `str` | 用于定位行的索引列（如主键 `id`） |
| `target_column` | `str` | 待修复的 JSON/文本列名 |
| `commit` | `bool` | 是否提交事务，默认 `False`（仅预览不写入） |
| `self_close` | `bool` | 是否关闭连接，默认 `False` |

### 使用示例

```python
from lazy_mysql.table import fix_json

# 先预览，不提交（默认 commit=False）
failed = fix_json(
    executor,
    table_name='events',
    index_column='id',
    target_column='payload',
    self_close=False,
)
# 控制台输出：成功修复 N 行，失败 M 行
# 返回无法修复的行列表 [(id, 错误原因), ...]

# 确认无误后再提交
fix_json(
    executor,
    table_name='events',
    index_column='id',
    target_column='payload',
    commit=True,
)
executor.close()
```

返回值 `failed` 为无法解析的行列表（元素为 `(index, 错误信息)`），便于你进一步人工处理。建议先以 `commit=False` 试运行，确认修复数量符合预期后再提交。

---

## 🛡️ validate_table_name — 表名校验

`validate_table_name(table_name)` -> `str`

仅允许以字母或下划线开头、后续由字母/数字/下划线组成的表名，用于防止 `FROM`/`SHOW` 等不支持参数化的子句遭受 SQL 注入。该函数在 `export_md` 与 `fix_json` 内部自动调用，你也可在拼接动态表名时单独使用：

```python
from lazy_mysql.table import validate_table_name

validate_table_name('users_2024')   # 'users_2024'
validate_table_name('users; DROP')  # 抛出 ValueError: Invalid table name: ...
```

---

## 💡 最佳实践

- **文档自动化**：将 `export_md` 接入部署脚本或 CI，每次表结构变更后自动刷新 `docs/table_docs`，保证数据库文档与代码同步。
- **修复前先预览**：使用 `fix_json` 时务必先以 `commit=False` 确认影响行数，再决定是否提交。
- **连接复用**：在脚本中连续导出多张表时，统一创建一次 `executor`，各调用传 `self_close=False`，最后统一 `executor.close()`，避免频繁建立连接。
