import json
import logging
from typing import Literal
from mysql.connector.abstracts import MySQLConnectionAbstract, MySQLCursorAbstract
from mysql.connector.pooling import PooledMySQLConnection
from .models import FetchConfig, MySQLConfig
from .utils.connect import connection
from .tools.log_utils import format_sql_for_log, truncate_long_in_lists, truncate_params_for_log
from .tools.sql_utils import resolve_sql

# 定义需要重试的错误信息常量
_RETRYABLE_ERRORS = [
    "Lost connection to MySQL server",
    "The Read Operation timed out",
    "TimeoutError",
    "connection timeout"
]

class SQLExecutor :
    """SQL执行器类，提供统一的数据库操作接口"""

    mydb: MySQLConnectionAbstract | PooledMySQLConnection | None = None
    mycursor: MySQLCursorAbstract | None = None

    def __init__( self , sql_config=None ,database=None,dict_cursor=False) :
        self.sql_config = MySQLConfig.resolve(sql_config)
        self.database = database or getattr(self.sql_config, "database", None)
        if not self.database:
            raise ValueError(
                "未指定数据库名称！请通过 database 参数 或 sql_config.database 属性或环境变量 LAZY_MYSQL_DATABASE 提供数据库名。"
            )
        self.dict_cursor = dict_cursor
        self.mydb , self.mycursor = connection( self.sql_config, self.database, dict_cursor=dict_cursor )
        self.logger = logging.getLogger(__name__)


    # 关闭数据库连接
    def close( self ) :
        try:
            if self.mycursor is not None:
                self.mycursor.close()
        except Exception:
            pass
        try:
            if self.mydb is not None:
                self.mydb.close()
        except Exception:
            pass
        # 将 self.mycursor 和 self.mydb 置为 None，最大程度减少程序退出时的 __del__ 调用
        # 降低 PyCharm 调试器与 mysql-connector-python 的兼容性问题
        self.mycursor = None
        self.mydb = None

    def __del__(self):
        # 兜底：如果用户忘记调用 close()，在对象销毁时尝试清理
        # 使用 getattr 避免在解释器关闭时访问已销毁的属性
        try:
            mycursor = getattr(self, 'mycursor', None)
            mydb = getattr(self, 'mydb', None)
            if mycursor is not None:
                mycursor.close()
            if mydb is not None:
                mydb.close()
        except Exception:
            pass

    def _handle_connection_error(self, error, operation_name, retry_count=0, sql=None, params=None, needs_rollback=False):
        """
        统一的连接错误处理逻辑
        
        :param error: 异常对象
        :param operation_name: 操作名称（用于日志）
        :param retry_count: 重试次数
        :param sql: SQL语句（可选，用于日志）
        :param params: 参数（可选，用于日志）
        :param needs_rollback: 是否需要回滚事务
        :return: 如果重试成功返回True，否则抛出异常
        """
        if self._should_retry(error, retry_count) and self._try_reconnect(operation_name):
            return True

        self._log_failed_statement(sql, params)
        self._rollback_if_needed(needs_rollback)
        self.close()
        raise Exception(f"SQL {operation_name} failed: {str(error)}")

    @staticmethod
    def _should_retry(error, retry_count):
        """判断异常是否尚可进行一次自动重连。"""
        error_str_lower = str(error).lower()
        return retry_count == 0 and any(
            keyword.lower() in error_str_lower for keyword in _RETRYABLE_ERRORS
        )

    def _try_reconnect(self, operation_name):
        """关闭旧连接并重新建立连接，返回重连是否成功。"""
        try:
            self.logger.warning(
                "Connection lost or timeout during %s. Attempting to reconnect...",
                operation_name,
            )
            self.close()
            self.mydb, self.mycursor = connection(
                self.sql_config, self.database, dict_cursor=self.dict_cursor,
            )
            return True
        except Exception as reconnect_error:
            self.logger.error("Reconnection failed during %s: %s", operation_name, reconnect_error)
            return False

    def _log_failed_statement(self, sql, params):
        """记录失败 SQL、参数及驱动已填充参数后的完整 SQL。"""
        if not sql:
            return

        sql_truncation_details = self._log_sql("SQL", sql)
        if params is None:
            return

        self._log_params(params)
        self._log_full_statement(sql_truncation_details)

    def _log_sql(self, label, sql):
        """记录一段 SQL，并返回其 IN/NOT IN 列表截断详情。"""
        sql_for_log = truncate_long_in_lists(sql)
        if sql_for_log['truncated']:
            self.logger.warning(
                "%s 中以下 IN/NOT IN 列表已截断（仅用于日志展示）：\n%s",
                label,
                json.dumps(sql_for_log['details'], ensure_ascii=False, indent=2),
            )
        self.logger.error("%s:\n%s", label, format_sql_for_log(sql_for_log['sql']))
        return sql_for_log['details']

    def _log_params(self, params):
        """记录参数，并在参数过长时仅记录其摘要。"""
        log_params = truncate_params_for_log(params)
        if log_params['truncated']:
            self.logger.warning(
                "Params 列表已截断（仅用于日志展示）：\n%s",
                json.dumps(
                    {key: value for key, value in log_params.items() if key != 'params'},
                    ensure_ascii=False,
                    indent=2,
                ),
            )
        self.logger.error("Params: %s", log_params['params'])

    def _log_full_statement(self, sql_truncation_details):
        """记录游标中已代入参数的完整 SQL，避免重复截断警告。"""
        full_statement = getattr(self.mycursor, 'statement', None)
        if not full_statement:
            return

        statement_for_log = truncate_long_in_lists(full_statement)
        if (
            statement_for_log['truncated']
            and statement_for_log['details'] != sql_truncation_details
        ):
            self.logger.warning(
                "Full SQL 中以下 IN/NOT IN 列表已截断（仅用于日志展示）：\n%s",
                json.dumps(statement_for_log['details'], ensure_ascii=False, indent=2),
            )
        self.logger.error(
            "Full SQL (with params):\n%s",
            format_sql_for_log(statement_for_log['sql']),
        )

    def _rollback_if_needed(self, needs_rollback):
        """在需要且可能时回滚；连接已断开时忽略回滚异常。"""
        if not needs_rollback or self.mydb is None:
            return
        try:
            self.mydb.rollback()
        except Exception:
            pass

    # 提交数据库
    def commit( self , retry_count = 0 ) :
        """
        提交数据库事务，支持自动重连和回滚
        :param retry_count: 内部参数，用于记录重试次数，避免无限循环
        """
        if self.mydb is None:
            raise RuntimeError("数据库连接已关闭，无法提交事务")
        try :
            self.mydb.commit()
        except Exception as e :
            if self._handle_connection_error(e, "commit", retry_count, needs_rollback=True):
                return self.commit(retry_count=1)

    # 提交并关闭数据库连接
    def commit_close( self ) :
        self.commit()
        self.close()

    # sql 语句执行器
    def execute( self , sql , params = None , commit = False , self_close = False , retry_count = 0 ) :
        """
        SQL语句执行方法，支持多种参数格式，自动判断单条/批量执行
        
        params 参数格式详解：
        1. 单个元组：用于【位置参数】（%s占位符）
           示例：("张三", 25) 对应 SQL: "INSERT INTO users (name, age) VALUES (%s, %s)"
        
        2. 单个字典：用于【命名参数】（%(name)s占位符）
           示例：{"name": "张三", "age": 25} 对应 SQL: "INSERT INTO users (name, age) VALUES (%(name)s, %(age)s)"
        
        3. 单个列表：自动转换为元组，示例：["张三", 25] → 转换为("张三", 25)
        
        4. 批量执行：用于executemany（仅适用于INSERT/UPDATE/DELETE等DML语句）
           元组列表：[("张三", 25), ("李四", 30)] 
           字典列表：[{"name": "张三", "age": 25}, {"name": "李四", "age": 30}]

        :param sql: SQL语句（支持直接传入SQL文本或 .sql 文件路径），支持 %s 和 %(name)s 占位符
        :param retry_count: 内部参数，用于记录重试次数，避免无限循环
        
        """
        try:
            sql = resolve_sql(sql)
        except Exception:
            self.close()
            raise
        if self.mycursor is None or self.mydb is None:
            raise RuntimeError("数据库连接已关闭，无法执行SQL")
        try :
            if params :
                if isinstance(params, dict) or isinstance(params, tuple):
                    # 单个字典 或 元组参数
                    self.mycursor.execute(sql, params)
                elif isinstance(params, list):
                    if not params:
                        self.mycursor.execute(sql)
                    elif isinstance(params[0], (dict, tuple, list)):
                        if any(p in (None, [], (), {}) for p in params):
                            raise ValueError("批量执行参数列表中存在空参数集（None/[]/()/{}），请检查 params")
                        # 简单高效地检测SELECT查询（检查SQL开头）
                        sql_start = sql.lstrip()[:10].upper()
                        if sql_start.startswith('SELECT'):
                            raise ValueError("SELECT查询不支持批量执行（会严重影响性能）！")

                        # 批量参数处理：参数列表的列表/元组/字典
                        self.mycursor.executemany(sql, params)
                    else:
                        # 单个列表参数，转换为元组
                        params = tuple(params)
                        self.mycursor.execute(sql, params)
                else:
                    raise ValueError(f"Invalid params format: {params}")
            else :
                self.mycursor.execute(sql)

            if commit :
                # 提交事务
                self.mydb.commit()

        except Exception as e :
            if self._handle_connection_error(e, "execute", retry_count, sql=sql, params=params, needs_rollback=commit):
                return self.execute(sql, params, commit, self_close, retry_count=1)

        # 关闭连接
        if self_close:
            self.close()


    # 定义解析结果程序(格式化返回结果)
    def fetch_format( self , sql , fetch_mode: Literal["all", "oneTuple", "one"] ,
                      output_format: Literal["", "list_1", "df", "df_dict"] | Literal["dict"] = "" ,
                      show_count = False , data_label = None ,
                      params = None , self_close = False ) :
        """
        定义解析结果程序(格式化返回结果)
        :param sql: SQL语句（支持直接传入SQL文本或 .sql 文件路径）
        :param fetch_mode: 获取模式,可选值: all、oneTuple、one
        :param output_format: 输出格式 ,默认 "" , 可选值: list_1、df、df_dict（fetch_mode="all" 时有效）、dict（仅 fetch_mode="oneTuple" 时有效）
        :param show_count: 是否显示结果数量
        :param data_label: 数据标签，用于DataFrame的列名或字典的键名
        :param params: 参数
        :param self_close: 是否自动关闭连接
        :return: 查询结果，格式根据参数配置而定
            - fetch_mode="all" + output_format="": 返回元组列表，如 [(1, '张三', 'zhang@example.com'), (2, '李四', 'li@example.com')]
            - fetch_mode="all" + output_format="list_1": 返回扁平化列表，如 [1, 2, 3]（提取每行第一个字段）
            - fetch_mode="all" + output_format="df": 返回pandas DataFrame
            - fetch_mode="all" + output_format="df_dict": 返回字典列表，如 [{'id': 1, 'name': '张三'}, {'id': 2, 'name': '李四'}]
            - fetch_mode="oneTuple":
                - output_format=="dict" 且 data_label 不为空时，返回字典，如 {'id': 1, 'name': '张三'}
                - 其他情况返回单个元组，如 (1, '张三', 'zhang@example.com')
            - fetch_mode="one": 返回单个值，如 1 或 '张三'
        """
        try:
            sql = resolve_sql(sql)
        except Exception:
            self.close()
            raise
        from .tools.result_formatter import fetch_format as fetch_format_func
        return fetch_format_func(self, sql, fetch_mode, output_format, show_count, data_label, params, self_close)


    # 插入数据
    def insert( self , table_name , fields , skip_duplicate = False, commit = False , self_close = False ) :
        """
        智能插入数据到指定表，根据数据量自动选择最优插入策略

        策略选择：
        - 单条数据（dict）: 使用传统insert
        - 数据量 < 1000条: 使用现有executemany
        - 1000-50000条: 使用优化executemany（分批1000条）
        - 50000-100000条: 使用优化executemany（分批5000条）
        - 数据量 >= 100000条: 使用LOAD DATA INFILE（分批50000条）

        :param table_name: 表名
        :param fields: 字段和值，格式为字典或字典列表，如 {'field1': 'value1', 'field2': 'value2'} 或 [{'field1': 'value1'}, {'field1': 'value2'}]
        :param skip_duplicate: 是否跳过重复数据
        :param commit: 是否自动提交
        :param self_close: 是否自动关闭连接
        :return: 插入成功的记录数（int）
        """
        from .utils.insert import insert as insert_func
        return insert_func(self, table_name, fields, skip_duplicate, commit, self_close)


    # 插入或更新数据
    def upsert( self , table_name , fields , fields_update = None, commit = False , self_close = False ) :
        """
        智能 INSERT ... ON DUPLICATE KEY UPDATE 执行器
        存在就更新，不存在就插入
        单条：dict -> 直接 upsert
        多条：list[dict] -> 批量 executemany upsert

        :param table_name: 表名
        :param fields: 字段和值，格式为字典或字典列表，如 {'field1': 'value1', 'field2': 'value2'} 或 [{'field1': 'value1'}, {'field1': 'value2'}]
        :param fields_update: 指定冲突时更新的字段集合，None 表示更新所有字段
        示例：{'age'} 表示只更新 age 字段，其他字段保持不变
        :param commit: 是否自动提交
        :param self_close: 是否自动关闭连接
        :return: 插入或更新成功的记录数（int）
        """
        from .utils.insert import upsert as upsert_func
        return upsert_func(self, table_name, fields, fields_update, commit, self_close)


    # 更新数据
    def update( self , table_name , fields , conditions , commit = False , self_close = False ) :
        """
        通用的SQL更新执行器方法，支持动态构造WHERE子句

        :param table_name: 表名
        :param fields: 需要更新的字段和值，格式为字典，如 {'field1': 'value1', 'field2': 'value2'}
        :param conditions: WHERE条件，格式为字典，如 {'field1': 'value1', 'field2': 'value2'}
        :param commit: 是否自动提交
        :param self_close: 是否自动关闭连接
        :return: 受影响的行数（int）
        """
        from .utils.update import update as update_func
        return update_func(self, table_name, fields, conditions, commit, self_close)

    # 批量更新数据
    def batch_update( self , table_name , update_list , commit = False , self_close = False ) :
        """
        智能批量更新方法，自动判断WHERE条件复杂度并选择最优SQL生成策略
        
        策略选择逻辑：
        1. 如果所有记录的WHERE条件都是单一字段 → 使用简化的 CASE key_field WHEN 语法（性能最优）
        2. 如果WHERE条件包含多字段或复杂条件 → 使用通用的 CASE WHEN ... THEN 语法

        :param table_name: 表名
        :param update_list: 更新数据列表，每个元素包含 fields 和 conditions
            格式示例: [
                {'fields': {'name': '张三', 'age': 25}, 'conditions': {'id': 1}},
                {'fields': {'name': '李四', 'age': 30}, 'conditions': {'id': 2}}
            ]
        :param commit: 是否自动提交
        :param self_close: 是否自动关闭连接
        :return: None
        
        :example:
            # 单一主键条件（自动使用简化语法）
            >>> update_list = [
            ...     {'fields': {'name': '张三', 'age': 25}, 'conditions': {'id': 1}},
            ...     {'fields': {'name': '李四', 'age': 30}, 'conditions': {'id': 2}}
            ... ]
            >>> executor.batch_update('users', update_list, commit=True)
            
            # 复杂条件（自动使用通用语法）
            >>> update_list = [
            ...     {'fields': {'status': 'active'}, 'conditions': {'id': 1, 'type': 'user'}},
            ...     {'fields': {'status': 'inactive'}, 'conditions': {'id': ('>', 100)}}
            ... ]
            >>> executor.batch_update('users', update_list, commit=True)
        """
        from .utils.update import batch_update as batch_update_func
        batch_update_func(self, table_name, update_list, commit, self_close)

    # 删除数据
    def delete( self , table_name , conditions , commit = False , self_close = False ) :
        """
        通用的SQL删除执行器方法，支持动态构造WHERE子句

        :param table_name: 表名
        :param conditions: WHERE条件，格式为字典，如 {'field1': 'value1', 'field2': 'value2'}
        :param commit: 是否自动提交
        :param self_close: 是否自动关闭连接
        :return: 受影响的行数（int）
        """
        from .utils.delete import delete as delete_func
        return delete_func(self, table_name, conditions, commit, self_close)


    # 选择数据
    def select( self , table_names , fields = None , conditions = None, order_by = None , limit:int|None=None,
                distinct:bool=False , join_conditions = None ,
                self_close:bool=False , fetch_config: FetchConfig | dict | None = None ) :
        """
        通用的SQL查询执行器方法，支持JOIN操作
        :param table_names: 表名，可以是字符串或列表
        :param fields: 要查询的字段列表
        :param conditions: WHERE条件，格式为字典
            - 支持 NDayInterval 用于最近N天区间筛选，例如：
                {'order_dateTime': ('>=', NDayInterval(7))}  # 最近7天
        :param order_by: ORDER BY子句
        :param limit: LIMIT子句
        :param distinct: 是否使用DISTINCT去重，默认为False
        :param join_conditions: JOIN条件，格式为字典，如 {"join_type": "JOIN", "conditions": ["field1", "=", "field2"]}
        :param self_close: 是否自动关闭连接
        :param fetch_config: 获取配置，用于控制查询结果的返回格式和行为。
            可以是 FetchConfig 模型实例或字典（兼容旧方式）。

            fetch_config包含以下可选配置项：

            1. fetch_mode (str): 获取模式，控制返回数据的数量
               - "all" (默认): 获取所有结果
               - "oneTuple": 获取单条记录（元组格式）
               - "one": 获取单个值（第一个字段的值）

            2. output_format (str): 输出格式，仅当fetch_mode="all" 或 fetch_mode = "oneTuple" 时有效
               - "" (默认): 返回原始元组列表
               - "list_1": 返回扁平化的列表（提取每行的第一个字段）
               - "df": 返回pandas DataFrame
               - "df_dict": 返回字典列表（DataFrame转dict）

            3. data_label (list): 数据标签，用于DataFrame的列名或字典的键名
               如果为None，系统会根据fields自动生成

            4. show_count (bool): 是否显示查询结果数量，默认为False

            示例（使用字典，兼容旧方式）：
                # 获取所有记录并返回DataFrame
                fetch_config = {
                    "fetch_mode": "all",
                    "output_format": "df",
                    "data_label": ["id", "name", "email"],
                    "show_count": True
                }

            示例（使用 FetchConfig 模型）：
                from lazy_mysql.models import FetchConfig

                # 获取所有记录并返回DataFrame
                fetch_config = FetchConfig(
                    fetch_mode="all",
                    output_format="df",
                    data_label=["id", "name", "email"],
                    show_count=True
                )
        :return: 查询结果，格式根据fetch_config配置而定
        """
        if fields is None:
            raise ValueError("fields 参数不能为空")

        from .utils.select import select as select_func
        return select_func(self, table_names, fields, conditions, order_by, limit, distinct, join_conditions, self_close, fetch_config)


    def exists(self, table_names, conditions=None, join_conditions=None, self_close:bool=False) -> bool:
        """
        快速判断指定条件的数据是否在数据库中存在

        使用 SELECT 1 ... LIMIT 1 优化性能，找到第一条记录即返回，避免全表扫描。
        相比 select 方法，此方法专注于判断存在性，性能更优。

        :param table_names: 表名，可以是字符串或列表
        :param conditions: WHERE条件，格式为字典，如 {'field1': 'value1', 'field2': 'value2'}
            - 支持 NDayInterval 用于最近N天区间筛选，例如：
            {'order_dateTime': ('>=', NDayInterval(7))}  # 最近7天
        :param join_conditions: JOIN条件，格式为字典，如 {"join_type": "JOIN", "conditions": ["field1", "=", "field2"]}
        :param self_close: 是否自动关闭连接
        :return: 如果存在符合条件的记录返回 True，否则返回 False

        :example:
            # 判断单个表中是否存在指定条件的数据
            >>> executor.exists('users', {'id': 1})
            True

            # 判断多表JOIN后是否存在符合条件的数据
            >>> executor.exists(['orders', 'users'],
            ...                 {'orders.status': 'pending'},
            ...                 {'join_type': 'JOIN', 'conditions': ['user_id', '=', 'id']})
            True

            # 判断最近7天内是否有订单
            >>> from lazy_mysql.tools import NDayInterval
            >>> executor.exists('orders', {'created_at': ('>=', NDayInterval(7))})
            True
        """
        from .utils.select import exists as exists_func
        return exists_func(self, table_names, conditions, join_conditions, self_close)


    def fetch_and_response( self,table_names , fields = None , conditions = None,
        distinct:bool=False, join_conditions=None, fetch_config: FetchConfig | dict | None = None,
        order_by=None, limit:int|None=None, format_func=None , self_close:bool=True ) :
        """
        通用的产品数据获取与格式化方法

        :param table_names: 表名，可以是字符串或列表
        :param fields: 要查询的字段列表
        :param conditions: WHERE条件，格式为字典
        :param distinct: 是否使用DISTINCT去重，默认为False
        :param join_conditions: JOIN条件，格式为字典
        :param fetch_config: 获取配置，用于控制查询结果的返回格式和行为。
            可以是 FetchConfig 模型实例或字典（兼容旧方式）。

            fetch_config包含以下可选配置项：

            1. fetch_mode (str): 获取模式，控制返回数据的数量
               - "all" (默认): 获取所有结果
               - "oneTuple": 获取单条记录（元组格式）
               - "one": 获取单个值（第一个字段的值）

            2. output_format (str): 输出格式，仅当fetch_mode="all" 或 fetch_mode = "oneTuple" 时有效
               - "df_dict" (默认): 返回字典列表
               - "df": 返回pandas DataFrame
               - "list_1": 返回扁平化的列表
               - "": 返回原始元组列表

            3. data_label (list): 数据标签，用于DataFrame的列名或字典的键名
                    如果为None，系统会根据fields自动生成

            4. show_count (bool): 是否显示查询结果数量，默认为False

            示例（使用字典，兼容旧方式）：
                # 获取所有记录并返回字典列表
                fetch_config = {
                    "output_format": "df_dict"
                }

            示例（使用 FetchConfig 模型）：
                from lazy_mysql.models import FetchConfig

                # 获取单条记录
                fetch_config = FetchConfig(
                    fetch_mode="oneTuple"
                )

        :param order_by: ORDER BY子句，如 "id DESC" 或 "name ASC"
        :param limit: LIMIT子句，限制返回记录数
        :param format_func: 自定义格式化函数，用于对结果进行额外处理
        :param self_close: 是否自动关闭连接
        :return: 包含success、result、message的字典
        """
        if fields is None:
            raise ValueError("fields 参数不能为空")

        # 处理 fetch_config，支持 FetchConfig 模型和旧的字典方式
        if fetch_config is None:
            fetch_config = FetchConfig(output_format="df_dict")
        elif isinstance(fetch_config, dict):
            # 设置默认 output_format 为 df_dict
            config_dict = {"output_format": "df_dict"}
            config_dict.update(fetch_config)
            fetch_config = FetchConfig(**config_dict)  # pyright: ignore[reportArgumentType]

        try :
            # 使用默认的select方法
            result = self.select( table_names , fields , conditions ,order_by, limit,
                                            distinct, join_conditions, self_close , fetch_config )
            success = True
            message = "success"
            
            if format_func is not None :
                try :
                    result = format_func(result)
                except Exception as e :
                    success = False
                    message = f"sql run success > format failed > {result} > {format_func.__name__} > {str(e)}"

        except Exception as e :
            success = False
            result = { }
            error_msg = str(e)
            message = f"sql run failed > {error_msg}"
            if "No result set to fetch from" in error_msg:
                message += f''' : note > The query statement did not return a result set. 
                 Please check if the database connection self.mycursor in the pip package was closed prematurely.'''
            success = False
            result = { }
            
        return { "success" : success , "result" : result , "message" : message }

    # 支持复杂查询的执行方法（手写SQL查询）
    def query(self, sql, params=None, fetch_config: FetchConfig | dict | None = None, self_close=False):
        """
        执行自定义SQL查询
        :param sql: SQL语句
        :param params: 参数
        :param fetch_config: 获取配置，用于控制查询结果的返回格式和行为。
            可以是 FetchConfig 模型实例或字典（兼容旧方式）。

            fetch_config包含以下可选配置项：

            1. fetch_mode (str): 获取模式，控制返回数据的数量
               - "all" (默认): 获取所有结果
               - "oneTuple": 获取单条记录（元组格式）
               - "one": 获取单个值（第一个字段的值）

            2. output_format (str): 输出格式，仅当fetch_mode="all" 或 fetch_mode="oneTuple"时有效
               - "" (默认): 返回原始元组列表（all）或元组（oneTuple）
               - "list_1": 返回扁平化的列表（提取每行的第一个字段，仅all）
               - "df": 返回pandas DataFrame（仅all）
               - "df_dict": 返回字典列表（仅all）
               - "dict": 返回字典（仅oneTuple，需data_label）

            3. data_label (list): 数据标签，用于DataFrame的列名或字典的键名
               当output_format为"df"/"df_dict"/"dict"时不能为空

            4. show_count (bool): 是否显示查询结果数量，默认为False
               为True时返回(数据, 总数)元组，仅fetch_mode="all"时有效

            返回值示例（假设查询结果包含id/name/email三列）：

            fetch_mode="all", output_format=""        -> [(1,'张三','z@e'), (2,'李四','l@e')]
            fetch_mode="all", output_format="list_1"  -> [1, 2]
            fetch_mode="all", output_format="df"      -> pandas DataFrame
            fetch_mode="all", output_format="df_dict" -> [{'id':1,'name':'张三',...}, ...]
            fetch_mode="all", show_count=True         -> (数据, 数量)
            fetch_mode="oneTuple", output_format=""   -> (1, '张三', 'z@e')
            fetch_mode="oneTuple", output_format="dict" -> {'id':1, 'name':'张三',...}
            fetch_mode="one"                          -> 1

            示例（使用字典，兼容旧方式）：
                fetch_config = {
                    "fetch_mode": "all",
                    "output_format": "df",
                    "data_label": ["id", "name", "email"],
                    "show_count": True
                }

            示例（使用 FetchConfig 模型）：
                from lazy_mysql.models import FetchConfig
                fetch_config = FetchConfig(
                    fetch_mode="all",
                    output_format="df",
                    data_label=["id", "name", "email"],
                    show_count=True
                )
        :param self_close: 是否自动关闭连接
        :return: 查询结果，格式根据fetch_config配置而定
        """
        # 处理 fetch_config，支持 FetchConfig 模型和旧的字典方式
        if fetch_config is None:
            fetch_config = FetchConfig(output_format="df_dict")
        elif isinstance(fetch_config, dict):
            # 设置默认 output_format 为 df_dict（与原方法保持一致）
            config_dict = {"output_format": "df_dict"}
            config_dict.update(fetch_config)
            fetch_config = FetchConfig(**config_dict)  # pyright: ignore[reportArgumentType]

        # 从 FetchConfig 中提取具体配置项
        fetch_mode = fetch_config.fetch_mode
        output_format = fetch_config.output_format
        show_count = fetch_config.show_count
        data_label = fetch_config.data_label or []

        # 调用底层 fetch_format 执行查询并格式化结果
        result = self.fetch_format(sql, fetch_mode, output_format, show_count, data_label, params, self_close)
        return result
