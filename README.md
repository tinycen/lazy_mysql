# lazy_mysql

A lightweight Python library for simplified MySQL database operations.

## Features

- Unified SQL execution interface
- Export table structure to Markdown format
- Query result formatting
- Simplified insert, update, and select operations
- Transaction support

## Install / upgrade / uninstall

```bash
pip install lazy-mysql
```

```bash
pip install --upgrade lazy-mysql
```

```bash
pip uninstall lazy-mysql
```

## Quick Start

```python
from lazy_mysql.executor import SQLExecutor

# Initialize connection
config = {
    'host': 'your_mysql_host',
    'user': 'your_username',
    'password': 'your_password',
    'database': 'your_database'
}

executor = SQLExecutor(config)

# Query example
result = executor.select('your_table', ['column1', 'column2'])
print(result)

# Insert example
executor.insert('your_table', {'column1': 'value1', 'column2': 'value2'}, commit=True)
```


## Requirements

- mysql-connector-python>=9.4.0
- pandas>=2.3.1

Note: Compatibility with versions below these requirements has not been verified.

## PyPI
Project available on PyPI: https://pypi.org/project/lazy-mysql/

## License
This project is licensed under the MIT License.