# INSERT 操作完整指南

`lazy_mysql` 的 INSERT 操作采用智能多策略系统，根据数据量自动选择最优插入策略：

| 数据规模 | 自动选择策略 | 批次大小 | 性能特征 |
| --- | --- | --- | --- |
| 单条记录（dict） | 传统 INSERT | - | 单次操作最快 |
| < 1,000 条 | 标准 executemany | - | 小批量处理最佳平衡 |
| 1,000 - 50,000 条 | 优化 executemany | 1,000 条/批 | 内存与性能平衡 |
| 50,000 - 100,000 条 | 优化 executemany | 5,000 条/批 | 中等数据集优化 |
| ≥ 100,000 条 | LOAD DATA INFILE | 50,000 条/批 | 比传统方法快 20-50 倍 |

## 函数签名与参数说明

```python
insert(
    executor: SQLExecutor,
    table_name,
    insert_fields,
    skip_duplicate=False,
    commit=False,
    self_close=False,
    temp_dir=None
)
```

### 核心参数

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `executor` | SQLExecutor | 是 | SQL执行器实例 |
| `table_name` | str | 是 | 目标表名 |
| `insert_fields` | dict/list | 是 | 插入数据，支持单条字典或字典列表 |
| `skip_duplicate` | bool | 否 | 是否跳过重复记录，默认False |
| `commit` | bool | 否 | 是否自动提交事务，默认False |
| `self_close` | bool | 否 | 是否自动关闭连接，默认False |
| `temp_dir` | str | 否 | 临时文件目录，用于LOAD DATA INFILE |

### 智能策略选择

系统根据数据量自动选择最优插入策略，无需手动配置：

- **单条数据（dict）**: 使用传统INSERT
- **数据量 < 1000条**: 使用标准executemany
- **1000-50000条**: 使用优化executemany（分批1000条）
- **50000-100000条**: 使用优化executemany（分批5000条）
- **数据量 ≥ 100000条**: 使用LOAD DATA INFILE（分批50000条）


## 基本 INSERT 用法

让我们从基础开始。在插入数据之前，您需要使用 SQLExecutor 类建立数据库连接：

```python
from lazy_mysql import SQLExecutor, MySQLConfig
 
# 配置数据库连接
config = MySQLConfig(
    host='localhost',
    user='your_username',
    passwd='your_password',
    default_database='your_database'
)
 
# 创建执行器实例
executor = SQLExecutor(config)
```

现在您可以准备插入数据。最简单的情况是插入单条记录：

```python
# 插入单个用户记录
user_data = {
    'name': 'John Doe',
    'email': 'john@example.com',
    'age': 30,
    'created_at': '2023-01-01 00:00:00'
}
 
# 插入记录并提交事务
executor.insert('users', user_data, commit=True)
print("记录插入成功！")
```
### insert() 方法参数说明

**必需参数：**
- `table_name`：目标表名（字符串）
- `insert_fields`：字段-值对的字典或字典列表

**可选参数：**
- `skip_duplicate`：是否跳过重复记录（默认：False）
  - 基于主键或唯一索引判断重复
  - 使用 `INSERT IGNORE` 实现跳过机制
- `commit`：是否自动提交事务（默认：False）
- `self_close`：是否自动关闭连接（默认：False）
- `temp_dir`：临时文件目录，用于 LOAD DATA INFILE（默认：系统临时目录）

**事务管理建议：**
- 单次操作：设置 `commit=True` 立即提交
- 批量操作：手动控制提交时机以确保数据一致性


## 多条记录的批量插入

当需要一次插入多条记录时，只需传递字典列表而不是单个字典：

```python
# 插入多个用户记录
users_data = [
    {'name': 'Alice Smith', 'email': 'alice@example.com', 'age': 25},
    {'name': 'Bob Johnson', 'email': 'bob@example.com', 'age': 35},
    {'name': 'Carol Williams', 'email': 'carol@example.com', 'age': 28}
]
 
# 在一次操作中插入所有记录
inserted_count = executor.insert('users', users_data, commit=True)
print(f"成功插入 {inserted_count} 条记录！")
```
该库会自动检测您传递的是列表并切换到批处理模式。对于小批量（少于 1,000 条记录），它使用 MySQL 的 executemany 功能，这比执行单独的 INSERT 语句效率高得多。

## 处理重复记录

在实际场景中，您经常遇到某些记录可能已存在于数据库中的情况。lazy_mysql 通过 skip_duplicate 参数提供了简单的解决方案：

```python
# 插入记录，跳过重复项
users_data = [
    {'name': 'Alice Smith', 'email': 'alice@example.com', 'age': 25},
    {'name': 'Bob Johnson', 'email': 'bob@example.com', 'age': 35},
    {'name': 'David Brown', 'email': 'david@example.com', 'age': 40}
]
 
# 跳过会违反唯一约束的记录
inserted_count = executor.insert('users', users_data, skip_duplicate=True, commit=True)
print(f"插入了 {inserted_count} 条新记录（重复项已跳过）")
```
当 skip_duplicate=True 时，库使用 INSERT IGNORE 而不是常规的 INSERT。这意味着会违反主键或唯一约束的记录将被静默跳过，而不会导致错误。

**重要提醒：**
- `skip_duplicate=True` 仅对主键和显式 `UNIQUE` 索引生效
- 普通 `INDEX` 索引不会触发重复跳过行为
- 使用 `INSERT IGNORE` 实现，违反唯一约束的记录会被静默跳过

**技术实现：**
- 单条插入：使用 `INSERT` 或 `INSERT IGNORE`
- 批量插入：根据数据量自动选择最优策略
- 大数据量：使用 `LOAD DATA LOCAL INFILE` 实现超高速导入

## 超大数据集处理（100,000+ 记录）

当数据量达到或超过 100,000 条记录时，系统自动启用 **LOAD DATA INFILE** 策略，这是处理超大数据集的最优方案。

### 性能基准
- **160 万条记录**：30-60 秒完成
- **性能提升**：比传统方法快 20-50 倍
- **内存优化**：流式处理，内存占用极低
- **批次策略**：50,000 条/批次，避免单次文件过大

### 实际应用示例
```python
# 生成测试数据集（实际业务中可能来自文件、API 或数据流）
massive_dataset = [
    {'id': i, 'name': f'User_{i}', 'email': f'user_{i}@example.com'}
    for i in range(1, 150001)  # 150,000 条记录
]

# 系统自动启用 LOAD DATA INFILE 策略
inserted_count = executor.insert('users', massive_dataset, commit=True)
print(f"超高速批量插入完成：{inserted_count} 条记录")
```

### 实时进度反馈
系统提供详细的批次处理进度：

```
[LOAD DATA] Starting to process - total_records : 150000, total_batches : 3, batch_size : 50000 records
[LOAD DATA] Processing batch 1/3 (0-49999)...
[LOAD DATA] Batch 1/3 completed, inserted 50000/150000 records
[LOAD DATA] Processing batch 2/3 (50000-99999)...
[LOAD DATA] Batch 2/3 completed, inserted 100000/150000 records
[LOAD DATA] Processing batch 3/3 (100000-149999)...
[LOAD DATA] Batch 3/3 completed, inserted 150000/150000 records
[LOAD DATA] All completed! Total 150000 records inserted
```

### 技术特性
- **临时文件管理**：自动创建/清理 CSV 临时文件
- **字符编码**：UTF-8 编码确保数据完整性
- **错误处理**：批次级错误隔离，单批次失败不影响整体
- **资源清理**：异常情况下自动清理临时资源
## 高级最佳实践

### 1. 事务管理策略

**自动提交模式**（推荐用于独立操作）：
```python
# 单次操作自动完成
executor.insert('users', user_data, commit=True, self_close=True)
```

**手动事务控制**（用于复杂业务流程）：
```python
try:
    # 多个相关操作作为原子事务
    executor.insert('orders', order_data)
    executor.insert('order_items', items_data)
    executor.insert('inventory_logs', log_data)
    executor.mydb.commit()  # 全部成功才提交
except Exception as e:
    executor.mydb.rollback()  # 任何错误回滚所有操作
    raise e
finally:
    executor.close()  # 确保连接释放
```

### 生产环境配置建议

**MySQL 服务器优化**：
```sql
-- 确保启用 LOCAL INFILE
SET GLOBAL local_infile = 1;

-- 调整相关参数以优化大批量插入
SET GLOBAL max_allowed_packet = 256M;
SET GLOBAL innodb_buffer_pool_size = 2G;
```

**连接池管理**：
```python
# 重用连接避免频繁创建/销毁
executor = SQLExecutor(config)
try:
    # 多次复用同一连接
    executor.insert('table1', data1)
    executor.insert('table2', data2)
    executor.insert('table3', data3)
finally:
    executor.close()  # 最后统一关闭
```
