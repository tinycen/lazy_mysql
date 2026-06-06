# FetchConfig 配置指南

`FetchConfig` 用于控制查询结果的返回格式和行为，支持 `FetchConfig` 模型实例或字典（兼容旧方式）。

## 配置项说明

### 1. fetch_mode - 获取模式

控制返回数据的数量和格式：

| 值 | 说明 |
|----|------|
| `"all"` (默认) | 获取所有结果 |
| `"oneTuple"` | 获取单条记录（元组格式），也支持通过 `output_format="dict"` 且 `data_label` 不为空时返回字典格式 |
| `"one"` | 获取单个值（第一个字段的值） |

### 2. output_format - 输出格式

仅当 `fetch_mode="all"` 或 `fetch_mode="oneTuple"` 时有效：

| 值 | 说明 | 适用 fetch_mode |
|----|------|----------------|
| `""` (默认) | 返回原始元组列表（`all`）或元组（`oneTuple`） | `all`, `oneTuple` |
| `"list_1"` | 返回扁平化的列表（提取每行的第一个字段） | `all` |
| `"df"` | 返回 pandas DataFrame | `all` |
| `"df_dict"` | 返回字典列表（DataFrame 转 dict） | `all` |
| `"dict"` | 仅在 `fetch_mode="oneTuple"` 且 `data_label` 不为空时有效，返回字典 | `oneTuple` |

### 3. data_label - 自定义列名

- 类型: `list[str]`
- 用于 DataFrame 的列名或字典的键名重命名
- 如果为 `None`，系统会根据 `fields` 自动生成

### 4. show_count - 显示计数

- 类型: `bool`
- 默认值: `False`
- 如果为 `True`，返回 `(数据, 总数)` 元组

## 使用示例

### 使用 FetchConfig 模型（推荐）

```python
from lazy_mysql import FetchConfig

# 获取所有记录并返回 DataFrame
fetch_config = FetchConfig(
    fetch_mode="all",
    output_format="df",
    data_label=["id", "name", "email"],
    show_count=True
)

# 获取单条记录
fetch_config = FetchConfig(
    fetch_mode="oneTuple"
)

# 获取单条记录并转为字典
fetch_config = FetchConfig(
    fetch_mode="oneTuple",
    output_format="dict",
    data_label=["id", "name", "email"]
)

# 获取单个值
fetch_config = FetchConfig(
    fetch_mode="one"
)
```

### 使用字典（兼容旧方式）

```python
# 获取所有记录并返回 DataFrame
fetch_config = {
    "fetch_mode": "all",
    "output_format": "df",
    "data_label": ["id", "name", "email"],
    "show_count": True
}

# 获取单条记录
fetch_config = {
    "fetch_mode": "oneTuple"
}

# 获取单个值
fetch_config = {
    "fetch_mode": "one"
}
```

## 完整示例

```python
from lazy_mysql import SQLExecutor, FetchConfig

# 初始化执行器
executor = SQLExecutor(host="localhost", user="root", password="123456", database="test")

# 查询所有用户并返回 DataFrame
fetch_config = FetchConfig(
    fetch_mode="all",
    output_format="df",
    data_label=["用户ID", "用户名", "邮箱"],
    show_count=True
)
result, count = executor.select(
    table_names="users",
    fields=["id", "name", "email"],
    fetch_config=fetch_config
)
print(f"共查询到 {count} 条记录")
print(result)

# 查询单个用户
fetch_config = FetchConfig(
    fetch_mode="oneTuple",
    output_format="dict",
    data_label=["id", "name", "email"]
)
user = executor.select(
    table_names="users",
    fields=["id", "name", "email"],
    conditions={"id": 1},
    fetch_config=fetch_config
)
print(user)  # {'id': 1, 'name': '张三', 'email': 'zhangsan@example.com'}
```
