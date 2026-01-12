# Lazy_mysql

[![zread](icon/zread-badge.svg)](https://zread.ai/tinycen/lazy_mysql)

**[简体中文](README.md)** | **[English](README.en.md)**

A lightweight Python library that provides elegant solutions for MySQL database operations.

## ✨ Core Features

- 🔌 **Unified SQL Execution Interface** - Simplify complex database operations
- 📊 **Smart Query Builder** - Support complex conditions, multi-table joins, sorting and limits
- 💾 **Batch Data Operations** - Automatic optimization strategies, support for large-scale data processing
- 🔄 **Upsert Support** - Smart judgment for update-if-exists/insert-if-not-exists
- 🛡️ **SQL Injection Protection** - Parameterized queries with automatic SQL injection prevention
- 📈 **Result Formatting** - Support multiple output formats including DataFrame, dict, list
- 📝 **Table Structure Export** - One-click export to Markdown format documentation
- ⚡ **High Performance Optimization** - LOAD DATA INFILE support, million-level data processing in seconds

## 🚀 Quick Installation

```bash
pip install --upgrade lazy-mysql
```

## 🎯 Quick Start

### 1. Database Connection Initialization

```python
from lazy_mysql.executor import SQLExecutor
from lazy_mysql.sql_config import MySQLConfig
from lazy_mysql.tools.where_clause import NDayInterval

# Create database configuration
config = MySQLConfig(
    host='localhost',
    user='your_username',
    passwd='your_password',
    default_database='your_database'
)

# Create executor instance
executor = SQLExecutor(config)
```

### 2. Smart Query Operations

```python
# Basic query
users = executor.select('users', ['id', 'name', 'email'])
print(users)

# Conditional query + sorting and limits
active_users = executor.select(
    'users',
    ['id', 'name', 'email'],
    conditions={'status': 'active', 'age': ('>', 18)},
    order_by='created_at DESC',
    limit=10
)

# Complex conditional query
results = executor.select(
    'users',
    ['id', 'name', 'score'],
    conditions={
        'status': ('IN', ['active', 'premium']),
        'score': ('BETWEEN', [80, 100]),
        'name': ('LIKE', '%John%'),
        'order_dateTime': ('>=', NDayInterval(7))  # Last 7 days
    },
    fetch_config={'output_format': 'df'}  # Return DataFrame format
)
```

### 3. Batch Data Insertion

```python
# Single insert
executor.insert('users', {'name': 'John', 'email': 'john@example.com'}, commit=True)

# Batch insert (automatic optimization strategy)
users_data = [
    {'name': 'Alice', 'email': 'alice@example.com', 'age': 25},
    {'name': 'Bob', 'email': 'bob@example.com', 'age': 30},
    # ... Support thousands of records
]
inserted_count = executor.insert('users', users_data, commit=True)

# Upsert operation (update if exists, insert if not)
user_data = {
    'id': 1,
    'name': 'John',
    'email': 'new_email@example.com',
    'updated_at': '2024-01-15 10:00:00'
}
executor.upsert('users', user_data, commit=True)
```

### 4. Data Update and Delete

```python
# Conditional update
executor.update(
    'users',
    {'status': 'premium', 'updated_at': '2024-01-15 10:00:00'},
    conditions={'last_login': ('>=', '2024-01-01'), 'points': ('>=', 1000)},
    commit=True
)

# Safe delete (conditions must be specified)
executor.delete('users', conditions={'status': 'inactive', 'last_login': ('<', '2023-01-01')}, commit=True)
```

### 5. Close Connection After Use

```python
executor.close()
```

### 📚 Detailed Documentation

### 🔗 Connection and Configuration
- [Database Connection Initialization](doc/CONNECTION.md) - Connection configuration, error handling, retry mechanisms, best practices

### 🔍 Query Operations
- [SELECT Query Operations](doc/SELECT.md) - Smart query building, complex conditions, multi-table joins, result formatting

### 💾 Data Modification
- [INSERT Operations](doc/INSERT.md) - Batch insertion, Upsert, large data optimization, duplicate handling
- [UPDATE Operations](doc/UPDATE.md) - Conditional updates, batch updates, SQL expressions, performance optimization
- [DELETE Operations](doc/DELETE.md) - Safe deletion, condition combinations, error handling, debugging tips

### 🛠️ SQL Utility Functions
- [SQL Utility Functions](doc/SQL_UTILS.md) - add_limit condition building, string concatenation, operator support

## 🔧 Environment Requirements

- **Python**: 3.7+
- **MySQL**: 8.0.36+
- **Dependencies**:
  - `mysql-connector-python>=9.4.0`
  - `pandas>=2.3.1`

> ⚠️ **Compatibility Note**: Compatibility with versions below the above requirements has not been verified

## 🎯 Applicable Scenarios

- ✅ **Web Application Development** - Rapid prototyping, API backend services
- ✅ **Data Analysis** - DataFrame integration, report generation, data cleaning
- ✅ **Batch Data Processing** - Log import, data migration, ETL processes
- ✅ **Enterprise Applications** - Transaction processing, concurrency control, error retry

## 🏆 Performance Advantages

| Operation Type | Traditional Method | lazy_mysql Optimization | Performance Improvement |
|---------|---------|---------------|----------|
| Batch Insert 10K records | 3-5 seconds | 0.5-1 seconds | **5-10x** |
| Batch Insert 100K records | 30-60 seconds | 2-5 seconds | **15-30x** |
| Complex conditional query | Manual SQL splicing | Smart building | **3x development efficiency** |
| Large data export | High memory usage | Streaming processing | **80% memory savings** |

## 📦 PyPI Project

The project has been published to PyPI and can be accessed through the following link:
- **PyPI Homepage**: https://pypi.org/project/lazy-mysql/

## 📄 Open Source License

This project adopts the MIT open source license - see [LICENSE](LICENSE) file for details