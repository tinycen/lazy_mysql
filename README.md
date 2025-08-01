# lazy_mysql

A lightweight Python library for simplified MySQL database operations.

## Features

- Unified SQL execution interface
- Export table structure to Markdown format
- Query result formatting
- Simplified insert, update, and select operations
- Transaction support

## Installation

```bash
pip install lazy-mysql
```

## Quick Start

```python
from lazy_mysql.executor import SQLExecutor

# Initialize connection
config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'password',
    'database': 'test_db'
}

executor = SQLExecutor(config)

# Query example
result = executor.select('users', ['id', 'name'])
print(result)

# Insert example
executor.insert('users', {'name': 'John', 'age': 30}, commit=True)
```

## Requirements

- mysql-connector-python>=9.4.0
- pandas>=2.3.1

Note: Compatibility with versions below these requirements has not been verified.


## License
This project is licensed under the MIT License.