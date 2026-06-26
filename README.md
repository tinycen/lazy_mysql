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

# 创建执行器实例
executor = SQLExecutor(config)

# 指定数据库（覆盖配置中的 database）
executor = SQLExecutor(config, database='another_db')

# 使用字典游标返回结果
executor = SQLExecutor(config, dict_cursor=True)

# 不传入配置时自动从环境变量读取：
# LAZY_MYSQL_HOST / LAZY_MYSQL_PORT / LAZY_MYSQL_USER / LAZY_MYSQL_PASSWD / LAZY_MYSQL_DATABASE
executor = SQLExecutor()

# 也支持混合配置：host/user/passwd 从环境变量读取，database 由参数指定
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

### 3. 批量数据插入

```python
# 单条插入
executor.insert('users', {'name': '张三', 'email': 'zhang@example.com'}, commit=True)

# 批量插入（自动优化策略）
users_data = [
    {'name': '李四', 'email': 'li@example.com', 'age': 25},
    {'name': '王五', 'email': 'wang@example.com', 'age': 30},
    # ... 支持数千条记录
]
inserted_count = executor.insert('users', users_data, commit=True)

# Upsert操作（存在更新，不存在插入）
user_data = {
    'id': 1,
    'name': '张三',
    'email': 'new_email@example.com',
    'updated_at': '2024-01-15 10:00:00'
}
executor.upsert('users', user_data, commit=True)
```

### 4. 数据更新与删除

```python
# 条件更新
executor.update(
    'users',
    {'status': 'premium', 'updated_at': '2024-01-15 10:00:00'},
    conditions={'last_login': ('>=', '2024-01-01'), 'points': ('>=', 1000)},
    commit=True
)

# 安全删除（必须指定条件）
executor.delete('users', conditions={'status': 'inactive', 'last_login': ('<', '2023-01-01')}, commit=True)
```

### 5. 使用完毕后关闭连接

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
- [SQL工具函数](docs/SQL_UTILS.md) - add_limit条件构建、resolve_sql智能路径解析、load_sql文件加载


## 🔧 环境要求

- **Python**: 3.7+
- **MySQL**: 8.0.36+
- **依赖库**:
  - `mysql-connector-python>=9.4.0`
  - `pandas>=2.3.1`

> ⚠️ **兼容性说明**: 低于上述版本要求的兼容性尚未验证

## 🎯 适用场景

- ✅ **Web应用开发** - 快速原型开发、API后端服务
- ✅ **数据分析** - DataFrame集成、报表生成、数据清洗
- ✅ **批量数据处理** - 日志导入、数据迁移、ETL流程
- ✅ **企业级应用** - 事务处理、并发控制、错误重试

## 🏆 性能优势

| 操作类型 | 传统方式 | lazy_mysql优化 | 性能提升 |
|---------|---------|---------------|----------|
| 批量插入1万条 | 3-5秒 | 0.5-1秒 | **5-10倍** |
| 批量插入10万条 | 30-60秒 | 2-5秒 | **15-30倍** |
| 复杂条件查询 | 手动拼接SQL | 智能构建 | **开发效率3倍** |
| 大数据导出 | 内存占用高 | 流式处理 | **内存节省80%** |

## 📦 PyPI 项目

项目已发布到PyPI，可通过以下链接访问：
- **PyPI主页**: https://pypi.org/project/lazy-mysql/

## 📄 开源协议

本项目采用MIT开源协议 - 详见 [LICENSE](LICENSE) 文件
