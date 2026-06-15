# 数据库连接初始化

本文档介绍如何使用 lazy_mysql 建立数据库连接。所有其他操作（SELECT、INSERT、UPDATE、DELETE）都需要先完成连接初始化。

## 快速开始

### 方法1：使用 MySQLConfig 类（推荐）

```python
from lazy_mysql import SQLExecutor, MySQLConfig

# 创建数据库配置
config = MySQLConfig(
    host='localhost',           # 数据库主机地址（必填）
    user='your_username',     # 数据库用户名（必填）
    passwd='your_password',   # 数据库密码（必填）
    database='your_database'  # 默认数据库名称（选填）
)

# 创建执行器实例
executor = SQLExecutor(config)

# 指定数据库（覆盖配置中的 database）
executor = SQLExecutor(config, database='another_db')

# 使用字典游标返回结果
executor = SQLExecutor(config, dict_cursor=True)

# 现在可以使用 executor 执行各种数据库操作
# ... 你的数据库操作代码 ...

# 使用完毕后关闭连接
executor.close()
```

### 方法2：使用字典配置

```python
from lazy_mysql.executor import SQLExecutor

# 使用字典配置
config = {
    'host': 'localhost',
    'user': 'your_username',
    'passwd': 'your_password',
    'database': 'your_database'
}

executor = SQLExecutor(config)

# 指定数据库并启用字典游标
executor = SQLExecutor(config, database='another_db', dict_cursor=True)

```

### 方法3：从环境变量读取配置

不传入配置时，`SQLExecutor` 会自动从系统环境变量读取 MySQL 连接信息。

支持的环境变量：

| 环境变量 | 说明 | 默认值 |
|----------|------|--------|
| `LAZY_MYSQL_HOST` | 数据库主机地址 | `localhost` |
| `LAZY_MYSQL_PORT` | 数据库端口 | `3306` |
| `LAZY_MYSQL_USER` | 用户名 | `root` |
| `LAZY_MYSQL_PASSWD` | 密码 | 空字符串 |
| `LAZY_MYSQL_DATABASE` | 默认数据库 | `None` |

也支持混合配置：未传入的字段从环境变量读取，显式传入的参数优先级更高。详见下方[配置参数优先级](#配置参数优先级)章节。

```python
from lazy_mysql.executor import SQLExecutor

# host / port / user / passwd 从环境变量读取，database 通过参数指定
executor = SQLExecutor(database='another_db')

# host / port / user / passwd 从环境变量读取，database 通过字典指定
executor = SQLExecutor({'database': 'another_db'})
```


**注意**：目前 `MySQLConfig` 仅支持 `host`、`user`、`passwd`、`port` 和 `database` 参数。其他高级连接参数（如 `charset`、`collation`、`autocommit`、`time_zone` 等）需要通过底层连接对象进行配置。

## 配置参数优先级

数据库连接参数遵循以下优先级规则（高 → 低）：

```
SQLExecutor 显式 database 参数 > MySQLConfig 显式参数 / 字典配置 > 环境变量
```

具体说明：

| 优先级 | 来源 | 说明 |
|--------|------|------|
| 1（最高） | `SQLExecutor(database='xxx')` | 创建执行器时传入的 `database` 参数，优先级最高 |
| 2 | `MySQLConfig` 显式参数 | `MySQLConfig(host='...', database='...')` 中的字段值 |
| 3 | 字典配置 | 传入 `SQLExecutor({'host': '...', 'database': '...'})` 的字典值 |
| 4（最低） | 环境变量 | `LAZY_MYSQL_HOST`、`LAZY_MYSQL_DATABASE` 等系统环境变量 |

**重要规则**：空值（`None` 或 `''`）不会覆盖已有值。即如果高优先级来源提供了有效值，低优先级的空值不会将其覆盖；反之，如果高优先级来源为空，则向下查找第一个非空值。

### 优先级示例

```python
import os
from lazy_mysql import SQLExecutor, MySQLConfig

# 示例1：显式参数覆盖一切
os.environ['LAZY_MYSQL_HOST'] = 'env_host'
config = MySQLConfig(host='config_host', database='config_db')
executor = SQLExecutor(config, database='explicit_db')
# 最终使用的数据库：explicit_db（SQLExecutor 的 database 参数优先级最高）

# 示例2：配置对象覆盖环境变量
os.environ['LAZY_MYSQL_HOST'] = 'env_host'
config = MySQLConfig(host='config_host')
executor = SQLExecutor(config)
# 最终使用的主机：config_host（MySQLConfig 显式参数覆盖环境变量）

# 示例3：字典配置覆盖环境变量
os.environ['LAZY_MYSQL_HOST'] = 'env_host'
executor = SQLExecutor({'host': 'dict_host'})
# 最终使用的主机：dict_host（字典配置覆盖环境变量）

# 示例4：空值不覆盖已有值
os.environ['LAZY_MYSQL_HOST'] = 'env_host'
config = MySQLConfig(host='config_host')
executor = SQLExecutor(config, database=None)
# database 为 None，不会覆盖 config 中的值；最终使用 config_db
```

## 高级连接配置

### 使用底层连接函数

如需进行更高级的连接配置，可以直接使用 `lazy_mysql.utils.connect` 模块中的 `connection` 函数：

```python
from lazy_mysql.utils.connect import connection

# 获取底层连接对象进行高级配置
mydb, mycursor = connection(
    sql_config=config,
    database='your_database',     # 覆盖默认数据库
    dict_cursor=True,              # 使用字典游标
    max_retries=5,                 # 最大重试次数
    retry_delay_base=5            # 重试延迟基数（秒）
)
```

### 连接参数说明

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `sql_config` | object | - | 数据库配置对象 |
| `database` | str | None | 指定数据库（优先级高于配置中的 database） |
| `dict_cursor` | bool | False | 是否使用字典游标 |
| `max_retries` | int | 5 | 连接失败时的最大重试次数 |
| `retry_delay_base` | int | 5 | 重试延迟基数，第n次重试延迟为 retry_delay_base * n 秒 |

### 配置高级连接参数

目前 `MySQLConfig` 仅支持基础连接参数。如需配置字符集、时区等高级参数，可以在创建连接后通过 MySQL 命令进行设置：

```python
executor = SQLExecutor(config)

# 设置字符集和排序规则
executor.execute("SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci")

# 设置时区
executor.execute("SET time_zone = '+8:00'")

# 设置自动提交模式
executor.execute("SET autocommit = 0")
```

## 错误处理与重试机制

### 自动重试

以下连接失败时会自动重试：
- **连接超时** (`ConnectionTimeoutError`)
- **无法连接** (`InterfaceError`，如 DNS 解析失败、网络不可达等)

默认重试配置：
- 最大重试次数：5次
- 重试延迟：递增延迟（5秒、10秒、15秒...）

```python
# 自定义重试配置
config = MySQLConfig(
    host='your_host',
    user='your_user',
    passwd='your_password',
    database='your_database'
)

# 创建执行器，指定数据库并启用字典游标
executor = SQLExecutor(config, database='your_database', dict_cursor=True)
```

### 常见连接错误

```python
try:
    executor = SQLExecutor(config)
    
    # 测试连接
    result = executor.execute("SELECT 1", fetch=True)
    print("连接成功！")
    
except Exception as e:
    error_msg = str(e)
    
    if "Access denied" in error_msg:
        print("错误：用户名或密码错误")
    elif "Can't connect" in error_msg:
        print("错误：无法连接到数据库服务器")
    elif "Unknown database" in error_msg:
        print("错误：指定的数据库不存在")
    elif "Connection timeout" in error_msg:
        print("错误：连接超时，请检查网络")
    else:
        print(f"连接错误：{error_msg}")
```

## 连接最佳实践

### 1. 使用上下文管理器

```python
from lazy_mysql.executor import SQLExecutor
from lazy_mysql.sql_config import MySQLConfig

config = MySQLConfig(
    host='localhost',
    user='your_username',
    passwd='your_password',
    database='your_database'
)

# 使用 try-finally 确保连接关闭
try:
    executor = SQLExecutor(config)
    
    # 执行数据库操作
    result = executor.select('users', ['id', 'name'])
    print(result)
    
finally:
    if 'executor' in locals():
        executor.close()
```

### 2. 连接复用

```python
class DatabaseManager:
    def __init__(self, config):
        self.config = config
        self.executor = None
    
    def __enter__(self):
        self.executor = SQLExecutor(self.config)
        return self.executor
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.executor:
            self.executor.close()

# 使用方式
config = MySQLConfig(host='localhost', user='user', passwd='pass', database='db')

with DatabaseManager(config) as executor:
    # 在此区域内使用 executor
    users = executor.select('users', ['id', 'name'])
    print(users)
# 自动关闭连接
```

### 3. 环境变量配置

```python
import os
from lazy_mysql.sql_config import MySQLConfig

# 从环境变量读取配置
config = MySQLConfig(
    host=os.getenv('DB_HOST', 'localhost'),
    user=os.getenv('DB_USER', 'root'),
    passwd=os.getenv('DB_PASSWORD', ''),
    database=os.getenv('DB_NAME', 'test_db'),
    port=int(os.getenv('DB_PORT', '3306'))
)

executor = SQLExecutor(config)
```

## 版本兼容性

### MySQL 版本支持
- 支持 MySQL 5.7+
- 推荐 MySQL 8.0+
- 完全支持 MySQL 8.0.36

### Python 连接器版本
```python
import mysql.connector

# 检查当前版本
print(f"当前 MySQL 连接器版本: {mysql.connector.__version__}")

# 建议升级到最新版本
# pip install --upgrade mysql-connector-python
```

### 版本检查
连接时会自动检查连接器版本，如果版本过时会显示警告：
```
警告: MySQL连接器版本8.0.33已过时，建议升级到9.4.0或更高版本
pip install --upgrade mysql-connector-python
```

## 相关文档

- [SELECT 查询操作](SELECT.md) - 数据查询
- [INSERT 插入操作](INSERT.md) - 数据插入
- [UPDATE 更新操作](UPDATE.md) - 数据更新
- [DELETE 删除操作](DELETE.md) - 数据删除
- [UPSERT 插入或更新](UPSERT.md) - 存在则更新、不存在则插入
