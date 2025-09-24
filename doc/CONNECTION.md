# 数据库连接初始化

本文档介绍如何使用 lazy_mysql 建立数据库连接。所有其他操作（SELECT、INSERT、UPDATE、DELETE）都需要先完成连接初始化。

## 快速开始

### 方法1：使用 MySQLConfig 类（推荐）

```python
from lazy_mysql.executor import SQLExecutor
from lazy_mysql.sql_config import MySQLConfig

# 创建数据库配置
config = MySQLConfig(
    host='localhost',           # 数据库主机地址（必填）
    user='your_username',     # 数据库用户名（必填）
    passwd='your_password',   # 数据库密码（必填）
    default_database='your_database'  # 默认数据库名称（选填），默认 "new_schema"
)

# 创建执行器实例
executor = SQLExecutor(config)

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
    'password': 'your_password',
    'database': 'your_database'
}

executor = SQLExecutor(config)

# ... 你的数据库操作代码 ...

executor.close()
```


**注意**：目前 `MySQLConfig` 仅支持 `host`、`user`、`passwd`、`port` 和 `default_database` 参数。其他高级连接参数（如 `charset`、`collation`、`autocommit`、`time_zone` 等）需要通过底层连接对象进行配置。

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
| `database` | str | None | 指定数据库（优先级高于配置中的default_database） |
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

连接失败时，系统会自动重试，默认配置：
- 最大重试次数：5次
- 重试延迟：递增延迟（5秒、10秒、15秒...）

```python
# 自定义重试配置
config = MySQLConfig(
    host='your_host',
    user='your_user',
    passwd='your_password',
    default_database='your_database'
)

# 创建带自定义重试的执行器
executor = SQLExecutor(config, max_retries=3, retry_delay_base=3)
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
    default_database='your_database'
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
config = MySQLConfig(host='localhost', user='user', passwd='pass', default_database='db')

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
    default_database=os.getenv('DB_NAME', 'test_db'),
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

## 完整示例

```python
from lazy_mysql.executor import SQLExecutor
from lazy_mysql.sql_config import MySQLConfig
import sys

def init_database_connection():
    """初始化数据库连接"""
    try:
        # 创建配置
        config = MySQLConfig(
            host='localhost',
            user='your_username',
            passwd='your_password',
            default_database='your_database'
        )
        
        # 创建执行器
        executor = SQLExecutor(config)
        
        # 测试连接
        test_result = executor.execute("SELECT VERSION()", fetch=True)
        print(f"数据库连接成功！版本: {test_result[0]['VERSION()']}")
        
        return executor
        
    except Exception as e:
        print(f"数据库连接失败: {e}")
        sys.exit(1)

# 使用示例
if __name__ == "__main__":
    executor = init_database_connection()
    
    try:
        # 执行数据库操作
        users = executor.select('users', ['id', 'username', 'email'])
        print(f"找到 {len(users)} 个用户")
        
    finally:
        # 确保关闭连接
        executor.close()
        print("数据库连接已关闭")
```

## 相关文档

- [SELECT 查询操作](SELECT.md) - 数据查询
- [INSERT 插入操作](INSERT.md) - 数据插入  
- [UPDATE 更新操作](UPDATE.md) - 数据更新
- [DELETE 删除操作](DELETE.md) - 数据删除