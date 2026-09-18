# SQL工具函数

## ⚠️ 编写 .sql 文件的红线：注释中禁止出现 `%` / `{}` 占位符

> **适用范围**：`load_sql()`、`resolve_sql()`，以及所有直接传给 `execute()` / `query()` / `fetch_format()` 的 `.sql` 文件路径。
> **结论先行**：SQL 文件的**注释里禁止写 `%` 和 `{}`**。其中 `%s` / `%(name)s` 一旦出现在注释中，**只要调用时传了 `params` 就必定抛异常**。

### 根因：驱动按纯文本扫描整条 SQL，不区分代码与注释

`load_sql()` 只做「读文件 → `strip()` → 返回字符串」，**不做任何占位符校验**；返回的整条 SQL 文本会原样交给 `mysql-connector-python` 处理。而驱动的占位符解析是**纯文本正则扫描**，不解析注释语法：

| 传入的 params 类型 | 驱动使用的正则 | 匹配到的内容 |
|---|---|---|
| 元组 / 列表 `('张三', 25)` | `RE_PY_PARAM = /(%s)/` | 文本中**每一个** `%s`，注释里的也算 |
| 字典 `{'name': '张三'}` | `RE_PY_MAPPING_PARAM = /%\((?P<key>[^)]+)\)(?P<type>[diouxXeEfFgGcrs%])/` | 文本中**每一个** `%(name)s`，注释里的也算 |

扫描出 N 个占位符，就要求 `params` 恰好提供 N 个值：

- 占位符多于参数 → `ProgrammingError: Not enough parameters for the SQL statement`
- 参数多于占位符 → `ProgrammingError: Not all parameters were used in the SQL statement`
- 字典参数扫到未提供的键 → `ProgrammingError: Failed processing format-parameters; ...`（底层为 `KeyError`）

> **隐蔽性提醒**：驱动仅在 `params` 非空时才做替换。所以注释里写了 `%s` 但**不传 params** 时不会报错（注释被 MySQL 服务端忽略），等到某次调用补上 `params` 就突然崩溃 —— 这类问题往往在上线后才暴露。

### 实测结论（mysql-connector-python 9.6.0，复用驱动自身正则验证）

| # | SQL 片段 | params | 实测结果 |
|---|---|---|---|
| A | `-- 说明：id 由 %s 传入` + 正文 1 个真实 `%s` | `('1',)` | ❌ `Not enough parameters for the SQL statement` |
| B | `-- 模糊查询示例：name LIKE '%s%'` | `('1',)` | ❌ `Not enough parameters for the SQL statement` |
| C | `DATE_FORMAT(created_at, '%Y-%m-%d %H:%i:%s')`（非注释，秒的 `%s`） | `('1',)` | ❌ `Not enough parameters for the SQL statement` |
| D | 改写为 `'%Y-%m-%d %H:%i:%%s'` 想转义 | `('1',)` | ❌ 仍然报错，**驱动层 `%%` 无效** |
| E | 格式串改走参数：`DATE_FORMAT(created_at, %s)` | `('%Y-%m-%d %H:%i:%s', '1')` | ✅ 正常 |
| F | `-- 仅统计折扣 50% 以上`（裸 `%`，后面不是 `s`） | `('1',)` | ⚠️ 通过，但属高危写法（见下文） |
| G | `-- 示例 %(not_exist)s` | `{'uid': '1'}` | ❌ `Failed processing format-parameters`（`KeyError`） |
| H | `-- 占位符 %(uid)s 由调用方传入` | `{'uid': '1'}` | ⚠️ 不报错，但**注释被静默替换成参数值** |
| I | `-- 模板示例 {table} {where}` | 元组或字典 | ✅ lazy_mysql 直接执行**不报错** |
| J | 对含 `-- 模板 {}` 的 SQL 自行 `sql.format()` | — | ❌ `IndexError: Replacement index 0 out of range` |
| K | 对含 `-- 折扣 50%` 的 SQL 自行 `sql % params` | `('1',)` | ❌ `ValueError: unsupported format character` |

### 关于 `%`：分两级看待，但统一禁止

- **必崩级**：`%s`、`%(name)s` 出现在注释或非占位符位置。传了 params 就一定报错（A/B/C）。
- **高危级**：裸 `%`（如 `折扣 50%`）在 lazy_mysql + mysql-connector 路径下实测**不报错**，但它之所以安全只是因为「`%` 后面恰好不是 `s`」。一旦你手写 `sql % params`、换用 PyMySQL 之类做 `%` 插值的驱动，或注释文字微调（`50% success` → 中间有空格仍安全，但 `50%s` 就崩），就会立刻炸（K）。**因此统一禁止，不留判断成本。**

### 关于 `{}`：直接执行安全，但依旧禁止

- 实测：交给 lazy_mysql 的 `execute()` / `query()` / `fetch_format()` 直接执行时，`{}` **不会被任何一层解析**，不会引发异常（I）。
- 但仍**必须禁止**：一旦 SQL 文本后续被 `str.format()` / f-string 模板化（下游项目常见做法），`{}` 就变成模板占位符 —— 键存在则注释被静默篡改，键不存在或空 `{}` 则直接抛 `KeyError` / `IndexError`（J）。与其赌调用链，不如从源头不写。

### 必须遵守的规则

1. 注释中**禁止**出现 `%`，尤其是 `%s`、`%(name)s`、`%(name)d`
2. 注释中**禁止**出现 `{}`、`{name}`、`{0}`
3. 非注释代码里，`%s` / `%(name)s` **只能作为真实占位符**出现
4. `%%` **不是**驱动层转义（实测无效），需要字面量 `%` 请参数化：`LIKE %s` + `params=('%关键字%',)`
5. `DATE_FORMAT` 等含 `%s`（秒）的格式串，**必须改成参数传入**（见示例 E）
6. 需要表达百分比语义时用中文替代：`折扣 50% 以上` → `折扣 50 个点以上` / `discount > 0.5`

### 正确 / 错误写法对照

```sql
-- ❌ 错误：注释里的 %s 会被计入占位符
-- 说明：user_id 由 %s 传入
SELECT id, name FROM users WHERE user_id = %s;

-- ✅ 正确：避免在注释中出现 %
-- 说明：user_id 由调用方通过参数传入
SELECT id, name FROM users WHERE user_id = %s;
```

```sql
-- ❌ 错误：注释里示范 LIKE 写法，同样会崩
-- 模糊匹配示例：name LIKE '%s%'
SELECT id FROM users WHERE name LIKE %s;

-- ✅ 正确：把完整匹配串放进 params（'%' 不会触发占位符解析）
-- 模糊匹配：匹配串整体由参数传入
SELECT id FROM users WHERE name LIKE %s;   -- params=('%张%',)
```

```sql
-- ❌ 错误：DATE_FORMAT 里的 %s（秒）被当成占位符，且 %%s 转义无效
SELECT DATE_FORMAT(created_at, '%Y-%m-%d %H:%i:%s') AS t FROM orders WHERE id > %s;

-- ✅ 正确：格式串作为参数传入
SELECT DATE_FORMAT(created_at, %s) AS t FROM orders WHERE id > %s;
-- params=('%Y-%m-%d %H:%i:%s', 100)
```

```sql
-- ❌ 错误：注释里使用花括号模板
-- 动态拼接：{table} / {where}
SELECT * FROM orders WHERE status = %s;

-- ✅ 正确：注释只写中文说明
-- 动态拼接：表名与条件由调用方组装
SELECT * FROM orders WHERE status = %s;
```

### 可选：入库前的自检脚本

把注释段摘出来单独检查，不误伤正文中的真实占位符：

```python
import re
from pathlib import Path

COMMENT = re.compile(r"(--[^\n]*)|(/\*.*?\*/)", re.S)
RISK = re.compile(r"(%|\{|\})")   # 注释中出现 % 或 {} 即视为违规


def check_sql_file(path: Path) -> list[tuple[int, str]]:
    """返回 [(行号, 命中的字符), ...]，空列表表示通过。"""
    text = path.read_text(encoding="utf-8")
    hits = []
    for m in COMMENT.finditer(text):
        line = text[:m.start()].count("\n") + 1
        for r in RISK.finditer(m.group(0)):
            hits.append((line, r.group(0)))
    return hits


for f in Path("sql").rglob("*.sql"):
    for line, ch in check_sql_file(f):
        print(f"{f}:{line} 注释中存在占位符字符 {ch!r}")
```

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
4. **⚠️ 注释禁止占位符**: 函数只做读取，不校验内容。**SQL 文件的注释中禁止出现 `%` 和 `{}`**，否则整条 SQL 交给驱动解析时会把注释里的 `%s` / `%(name)s` 当真实占位符，传 `params` 时报
   `ProgrammingError: Not enough parameters for the SQL statement`。详见 [编写 .sql 文件的红线](#sql-placeholder-rule)

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
5. **⚠️ 注释禁止占位符**: 读取到的 SQL 会整条交给驱动做占位符扫描，注释里的 `%s` / `%(name)s` 会被计入占位符数量。
   **SQL 文件的注释中禁止出现 `%` 和 `{}`**，详见 [编写 .sql 文件的红线](#sql-placeholder-rule)

### 相关函数
- [load_sql](#load_sql---载入sql文件) - 直接从文件读取 SQL 内容
- [add_limit](#add_limit---sql条件语句构建) - 构建 SQL 条件语句

### 更新日志
- 新增: 支持 `str` 和 `os.PathLike` 两种路径格式，内置于 `execute()` 和 `fetch_format()` 方法