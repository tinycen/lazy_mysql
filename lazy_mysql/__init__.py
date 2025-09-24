from .sql_config import MySQLConfig, DEFAULT_MYSQL_CONFIG
from .executor import SQLExecutor
from .utils import insert, upsert, select, update, delete

__version__ = "0.1.1"
__author__ = "tinycen"
__email__ = "sky_ruocen@qq.com"

# 提供便捷的导入
__all__ = ['MySQLConfig', 'DEFAULT_MYSQL_CONFIG', 'SQLExecutor', 'insert', 'upsert', 'select', 'update', 'delete']
