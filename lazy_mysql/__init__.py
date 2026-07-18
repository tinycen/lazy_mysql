from pathlib import Path
from .executor import SQLExecutor
from .models import MySQLConfig, FetchConfig, DEFAULT_MYSQL_CONFIG
from .crud import insert, upsert, select, exists, update, batch_update, delete, merge_update_lists
from .tools import NDayInterval, add_limit, load_sql, resolve_sql, build_where, build_sql_with_where

__version__ = (Path(__file__).parent / ".version").read_text().strip()

__author__ = "tinycen"
__email__ = "sky_ruocen@qq.com"


# 提供便捷的导入
__all__ = ['__version__','MySQLConfig', 'DEFAULT_MYSQL_CONFIG',
           'SQLExecutor', 'FetchConfig', 'NDayInterval',
           'insert', 'upsert', 'select', 'exists',
           'update', 'batch_update', 'delete', 'merge_update_lists',
           'add_limit', 'load_sql', 'resolve_sql', 'build_where', 'build_sql_with_where']
