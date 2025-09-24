# lazy_mysql

A lightweight Python library for simplified MySQL database operations.

## Features

- Unified SQL execution interface
- Export table structure to Markdown format
- Query result formatting
- Simplified insert, update, and select operations
- Transaction support

## Install / upgrade

```bash
pip install --upgrade lazy-mysql
```

## Quick Start

### 1. 安装
```bash
pip install --upgrade lazy-mysql
```

### 2. 初始化连接
```python
from lazy_mysql.executor import SQLExecutor
from lazy_mysql.sql_config import MySQLConfig

# 创建数据库配置
config = MySQLConfig(
    host='localhost',
    user='your_username',
    passwd='your_password',
    default_database='your_database'
)

# 创建执行器实例
executor = SQLExecutor(config)
```

### 3. 基本操作
```python
# 查询示例
result = executor.select('your_table', ['column1', 'column2'])
print(result)

# 插入示例
executor.insert('your_table', {'column1': 'value1', 'column2': 'value2'}, commit=True)

# 使用完毕后关闭连接
executor.close()
```

### 📚 详细文档
- [数据库连接初始化](doc/CONNECTION.md) - 连接配置和最佳实践
- [SELECT 查询操作](doc/SELECT.md) - 数据查询完整指南
- [INSERT 插入操作](doc/INSERT.md) - 数据插入和Upsert
- [UPDATE 更新操作](doc/UPDATE.md) - 数据更新操作
- [DELETE 删除操作](doc/DELETE.md) - 安全删除操作


## Requirements

- mysql-connector-python>=9.4.0
- pandas>=2.3.1

Note: Compatibility with versions below these requirements has not been verified.

## PyPI
Project available on PyPI: https://pypi.org/project/lazy-mysql/

## License
This project is licensed under the MIT License.