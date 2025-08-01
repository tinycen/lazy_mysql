# lazy_mysql

一个简化MySQL数据库操作的Python工具库，提供便捷的CRUD操作接口。

## 功能特性

- 统一的SQL执行接口
- 支持表结构导出为Markdown格式
- 提供查询结果格式化功能
- 简化插入、更新、查询操作
- 支持事务处理

## 安装

```bash
pip install -e .
```

## 快速开始

```python
from lazy_mysql.executor import SQLExecutor

# 初始化连接
config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'password',
    'database': 'test_db'
}

executor = SQLExecutor(config)

# 查询示例
result = executor.select('users', ['id', 'name'])
print(result)

# 插入示例
executor.insert('users', {'name': 'John', 'age': 30}, commit=True)
```

## 文档

详细使用方法请参考各模块文档。

## 贡献

欢迎提交Pull Request或Issue。