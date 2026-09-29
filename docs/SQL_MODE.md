# SQL Mode 与注释剥离的兼容性说明

## 什么是 `sql_mode`

`sql_mode` 是 **MySQL 服务器端** 的系统变量，控制 SQL 语法解析和校验行为。它影响：
- 字符串中反斜杠 `\` 是否作为转义符
- 日期/除零等非法值的处理严格程度
- 引号含义（`ANSI_QUOTES` 模式下 `"` 为标识符而非字符串）

lazy_mysql **不设置** `sql_mode`，仅作为客户端读取服务端配置来调整参数转义。

## 与注释剥离相关的模式

### `NO_BACKSLASH_ESCAPES`

| 模式 | 字符串中 `\'` 的含义 | 字符串中 `\\` 的含义 |
|---|---|---|
| **默认**（未开启） | 转义序列，表示字面量 `'` | 转义序列，表示字面量 `\` |
| **NO_BACKSLASH_ESCAPES** | 两个普通字符：`\` 和 `'` | 两个普通字符：`\` 和 `\` |

#### 对注释剥离的影响

注释剥离状态机按 **MySQL 默认模式** 实现：遇到 `\'` 时跳过 2 字符（认为 `'` 被转义，字符串未结束）。

若服务端开启 `NO_BACKSLASH_ESCAPES`，该假设不成立：

```sql
-- 示例 SQL
SELECT 'a\'  -- 注释 %s
```

| 模式 | 解析结果 | 剥离行为 |
|---|---|---|
| 默认 | `\'` 是转义，字符串到 `--` 前的 `'` 才结束，`--` 是注释 | ✅ 正确剥离 `--` 注释 |
| NO_BACKSLASH_ESCAPES | `\` 是普通字符，字符串在 `a\` 处结束，后面的 `' -- 注释 %s` 是代码 | ⚠️ 漏剥 `--` 注释 |

**失败方向是「少剥」而非「错改」**：不会篡改 SQL 本体，只是注释残留。此时若注释中含 `%s`，预检会按内联 SQL 处理（注释 `%s` 参与计数），可能报 `E101` 而非静默通过。

#### 如何检查当前模式

```sql
SELECT @@sql_mode;
-- 或
SELECT @@SESSION.sql_mode;
```

MySQL 8.0 默认 `sql_mode` 为：
```
ONLY_FULL_GROUP_BY,STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION
```
**不包含** `NO_BACKSLASH_ESCAPES`。

#### 何时会用到

- 从其他数据库（如 PostgreSQL、Oracle）迁移，希望 `\` 保持字面量含义
- 处理大量 Windows 路径（`C:\path\to\file`）时避免双写反斜杠

#### 建议

若必须使用 `NO_BACKSLASH_ESCAPES`：
1. 避免在 `.sql` 文件中使用「以 `\` 结尾的字符串」
2. 或改用 `strip_comments=False` 加载，自行确保注释中无 `%` / `{}`

### `ANSI_QUOTES`

| 模式 | `"` 的含义 |
|---|---|
| **默认** | 字符串定界符（与 `'` 等价） |
| **ANSI_QUOTES** | 标识符定界符（与 `` ` `` 等价） |

注释剥离状态机对 `"` 和 `` ` `` 分别处理，无论服务端是否开启 `ANSI_QUOTES` 都能正确识别边界，**不受影响**。

## 驱动层的 `sql_mode` 使用

mysql-connector 在参数转义时会读取服务端 `sql_mode`：

```python
# mysql/connector/conversion.py
if sql_mode is not None and SQLMode.NO_BACKSLASH_ESCAPES in sql_mode:
    return value.replace("'", "''")  # 不用反斜杠转义，改用双写
```

这意味着：**驱动会自动适配服务端的 `sql_mode`**，但注释剥离发生在驱动之前（`resolve_sql` 阶段），无法感知服务端配置，只能按默认模式假设。

## 相关文档

- [SQL 工具函数 - 编写 .sql 文件的红线](SQL_UTILS.md#编写-sql-文件的红线注释中禁止出现--占位符)
- [SQL 工具函数 - 已知限制](SQL_UTILS.md#已知限制)

## 更新日志

- 0.7.4: 新增本文档，说明 `sql_mode` 与注释剥离的兼容性
