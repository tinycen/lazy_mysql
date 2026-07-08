# Lazy_mysql

[![zread](icon/zread-badge.svg)](https://zread.ai/tinycen/lazy_mysql)

**[简体中文](README.md)**

一个轻量级的Python库，为MySQL数据库操作提供简洁优雅的解决方案。

## ✨ 核心特性

- 🔌 **统一SQL执行接口** - 简化复杂的数据库操作流程
- 📊 **智能查询构建器** - 支持复杂条件、多表关联、排序限制
- 💾 **批量数据操作** - 自动优化策略，支持超大数量级数据处理
- 🔄 **Upsert支持** - 智能判断存在更新/不存在插入
- 🛡️ **安全防注入** - 参数化查询，自动SQL注入防护
- 📈 **结果格式化** - 支持DataFrame、字典、列表等多种格式输出
- 📝 **表结构导出** - 一键导出Markdown格式文档
- ⚡ **高性能优化** - LOAD DATA INFILE支持，百万级数据秒级处理

## 🚀 快速安装

```bash
pip install --upgrade lazy-mysql
```

## 🎯 快速开始

### 1. 数据库连接初始化

```python
from lazy_mysql import SQLExecutor, MySQLConfig, NDayInterval

# 创建数据库配置
config = MySQLConfig(
    host='localhost',
    user='your_username',
    passwd='your_password',
    database='your_database'
)

# 指定数据库
executor = SQLExecutor(config, database='database')

# 不传入配置时自动从环境变量读取：
# LAZY_MYSQL_HOST / LAZY_MYSQL_PORT / LAZY_MYSQL_USER / LAZY_MYSQL_PASSWD / LAZY_MYSQL_DATABASE

# 支持混合配置：host/user/passwd 从环境变量读取，database 由参数指定
executor = SQLExecutor(database='another_db')
```
### 2. 智能查询操作

```python
# 基础查询（select 自动构造 SQL）
users = executor.select('users', ['id', 'name', 'email'])
print(users)

# 手写复杂 SQL（query 直接执行）
result = executor.query(
    "SELECT id, name, RANK() OVER (ORDER BY score DESC) as rank FROM users",
    fetch_config={'output_format': 'df_dict', 'data_label': ['id', 'name', 'rank']}
)

# 条件查询 + 排序限制
active_users = executor.select(
    'users',
    ['id', 'name', 'email'],
    conditions={'status': 'active', 'age': ('>', 18)},
    order_by='created_at DESC',
    limit=10
)

# 复杂条件查询
results = executor.select(
    'users',
    ['id', 'name', 'score'],
    conditions={
        'status': ('IN', ['active', 'premium']),
        'score': ('BETWEEN', [80, 100]),
        'name': ('LIKE', '%John%'),
        'order_dateTime': ('>=', NDayInterval(7))  # 最近7天
    },
    fetch_config={'output_format': 'df'}  # 返回DataFrame格式
)

```

### 3. 使用完毕后关闭连接

```python
# 直接关闭数据库连接
executor.close()
# 提交数据并关闭连接
executor.commit_close()
```

### 📚 详细文档

### 🔗 连接与配置
- [数据库连接初始化](docs/CONNECTION.md) - 连接配置、错误处理、重试机制、最佳实践
- [WHERE 条件构造](docs/CONDITIONS.md) - 等值条件、比较运算符、空值判断、日期筛选

### 🔍 查询操作
- [SELECT 查询操作](docs/SELECT.md) - 智能查询构建、复杂条件、多表关联、结果格式化
- [自定义 SQL 查询](docs/QUERY.md) - 手写 SQL 执行、子查询、UNION、窗口函数
- [FetchConfig 配置](docs/FETCH_CONFIG.md) - fetch_mode、output_format、data_label 等结果格式化参数

### 💾 数据修改
- [INSERT 插入操作](docs/INSERT.md) - 批量插入、大数据优化、重复处理
- [UPSERT 插入或更新](docs/UPSERT.md) - 存在则更新、不存在则插入
- [UPDATE 更新操作](docs/UPDATE.md) - 条件更新、批量更新、SQL表达式、性能优化
- [DELETE 删除操作](docs/DELETE.md) - 安全删除、条件组合、错误处理、调试技巧

### 🛠️ SQL工具函数
- [SQL工具函数](docs/SQL_UTILS.md) - add_limit条件构建、build_where/build_sql_with_where WHERE子句构建、resolve_sql智能路径解析、load_sql文件加载

### 🗂️ 表结构工具
- [Table 表结构工具](docs/table.md) - 表/视图结构一键导出为 Markdown、TEXT 列 JSON 修复、表名校验防注入

## 📦 PyPI 项目

项目已发布到PyPI，可通过以下链接访问：
- **PyPI主页**: https://pypi.org/project/lazy-mysql/

## 🔧 环境要求

- **Python**: 3.10+
- **MySQL**: 8.0.36+
- **依赖库**:
  - `mysql-connector-python>=9.4.0`
  - `pandas>=2.3.1`

## 📄 开源协议

本项目采用MIT开源协议 - 详见 [LICENSE](LICENSE) 文件
