from .utils.connect import connection

# 定义需要重试的错误信息常量
RETRYABLE_ERRORS = [
    "Lost connection to MySQL server",
    "The Read Operation timed out",
    "TimeoutError",
    "connection timeout"
]

class SQLExecutor :
    """SQL执行器类，提供统一的数据库操作接口"""

    def __init__( self , sql_config ,database=None,dict_cursor=False) :
        self.sql_config = sql_config
        self.database = database
        self.dict_cursor = dict_cursor
        self.mydb , self.mycursor = connection( sql_config,database,dict_cursor=dict_cursor )

    # 读取sql文件
    def read_sql( self , sql_path ) :
        with open(sql_path, 'r', encoding='utf-8') as f:
            sql = f.read()
        return sql.strip()

    # 关闭数据库连接
    def close( self ) :
        self.mycursor.close()
        self.mydb.close()

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
        error_str = str(error)
        error_str_lower = error_str.lower()
        
        # 检查是否是可重试的错误（连接丢失或超时错误）
        if retry_count == 0 and any(error.lower() in error_str_lower for error in RETRYABLE_ERRORS):
            try:
                print(f"Connection lost or timeout during {operation_name}. Attempting to reconnect...")
                # 关闭现有连接
                try:
                    self.mydb.close()
                except:
                    pass
                
                # 重新初始化连接
                self.mydb, self.mycursor = connection(self.sql_config, self.database, dict_cursor=self.dict_cursor)
                
                return True  # 重试成功
                
            except Exception as reconnect_error:
                print(f"Reconnection failed during {operation_name}: {str(reconnect_error)}")
                # 继续执行原始的错误处理流程
        
        if sql:
            print(f"sql: {sql} \n params:{params}")
        print(f"{operation_name} failed: {error_str}")
        
        # 如果发生错误，回滚事务
        if needs_rollback:
            try:
                self.mydb.rollback()
            except:
                pass  # 连接可能已经断开，忽略回滚错误
        
        try:
            self.mydb.close()
        except:
            pass  # 连接可能已经断开，忽略关闭错误
            
        raise Exception(f"SQL {operation_name} failed: {str(error)}")

    # 提交数据库
    def commit( self , retry_count = 0 ) :
        """
        提交数据库事务，支持自动重连和回滚
        :param retry_count: 内部参数，用于记录重试次数，避免无限循环
        """
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

        :param sql: SQL语句，支持 %s 和 %(name)s 占位符
        :param retry_count: 内部参数，用于记录重试次数，避免无限循环
        
        """
        try :
            if params :
                if isinstance(params, dict) or isinstance(params, tuple):
                    # 单个字典 或 元组参数
                    self.mycursor.execute(sql, params)
                elif isinstance(params, list):
                    if isinstance(params[0], (dict, tuple, list)):
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
    def fetch_format( self , sql , fetch_mode , output_format = "" , show_count = False , data_label = None ,
                      params = None , self_close = False ) :
        """
        定义解析结果程序(格式化返回结果)
        :param sql: SQL语句
        :param fetch_mode: 获取模式,可选值: all、oneTuple、one
        :param output_format: 输出格式 ,默认 "" , 可选值: list_1、df、df_dict , 仅在 fetch_mode 为 all 时有效
        :param show_count: 是否显示结果数量
        :param data_label: 数据标签，用于DataFrame的列名或字典的键名
        :param params: 参数
        :param self_close: 是否自动关闭连接
        :return: 查询结果，格式根据参数配置而定
            - fetch_mode="all" + output_format="": 返回元组列表，如 [(1, '张三', 'zhang@example.com'), (2, '李四', 'li@example.com')]
            - fetch_mode="all" + output_format="list_1": 返回扁平化列表，如 [1, 2, 3]（提取每行第一个字段）
            - fetch_mode="all" + output_format="df": 返回pandas DataFrame
            - fetch_mode="all" + output_format="df_dict": 返回字典列表，如 [{'id': 1, 'name': '张三'}, {'id': 2, 'name': '李四'}]
            - fetch_mode="oneTuple": 返回单个元组，如 (1, '张三', 'zhang@example.com')
            - fetch_mode="one": 返回单个值，如 1 或 '张三'
        """
        from .tools.result_formatter import fetch_format as fetch_format_func
        return fetch_format_func(self, sql, fetch_mode, output_format, show_count, data_label, params, self_close)


    # 插入数据
    def insert( self , table_name , insert_fields , skip_duplicate = False, commit = False , self_close = False ) :
        """
        智能插入数据到指定表，根据数据量自动选择最优插入策略

        策略选择：
        - 单条数据（dict）: 使用传统insert
        - 数据量 < 1000条: 使用现有executemany
        - 1000-50000条: 使用优化executemany（分批1000条）
        - 50000-100000条: 使用优化executemany（分批5000条）
        - 数据量 >= 100000条: 使用LOAD DATA INFILE（分批50000条）

        :param table_name: 表名
        :param insert_fields: 字段和值，格式为字典或字典列表，如 {'field1': 'value1', 'field2': 'value2'} 或 [{'field1': 'value1'}, {'field1': 'value2'}]
        :param skip_duplicate: 是否跳过重复数据
        :param commit: 是否自动提交
        :param self_close: 是否自动关闭连接
        :return: 插入成功的记录数（int）
        """
        from .utils.insert import insert as insert_func
        return insert_func(self, table_name, insert_fields, skip_duplicate, commit, self_close)


    # 插入或更新数据
    def upsert( self , table_name , insert_fields , update_fields = None, commit = False , self_close = False ) :
        """
        智能 INSERT ... ON DUPLICATE KEY UPDATE 执行器
        存在就更新，不存在就插入
        单条：dict -> 直接 upsert
        多条：list[dict] -> 批量 executemany upsert

        :param table_name: 表名
        :param insert_fields: 字段和值，格式为字典或字典列表，如 {'field1': 'value1', 'field2': 'value2'} 或 [{'field1': 'value1'}, {'field1': 'value2'}]
        :param update_fields: 指定冲突时更新的字段，None 表示更新所有字段
        示例：{'age'} 表示只更新 age 字段，其他字段保持不变
        :param commit: 是否自动提交
        :param self_close: 是否自动关闭连接
        :return: 插入或更新成功的记录数（int）
        """
        from .utils.insert import upsert as upsert_func
        return upsert_func(self, table_name, insert_fields, update_fields, commit, self_close)


    # 更新数据
    def update( self , table_name , update_fields , where_conditions , commit = False , self_close = False ) :
        """
        通用的SQL更新执行器方法，支持动态构造WHERE子句

        :param table_name: 表名
        :param update_fields: 需要更新的字段和值，格式为字典，如 {'field1': 'value1', 'field2': 'value2'}
        :param where_conditions: WHERE条件，格式为字典，如 {'field1': 'value1', 'field2': 'value2'}
        :param commit: 是否自动提交
        :param self_close: 是否自动关闭连接
        :return: None
        """
        from .utils.update import update as update_func
        update_func(self, table_name, update_fields, where_conditions, commit, self_close)

    # 批量更新数据
    def batch_update( self , table_name , update_list , commit = False , self_close = False ) :
        """
        智能批量更新方法，自动判断WHERE条件复杂度并选择最优SQL生成策略
        
        策略选择逻辑：
        1. 如果所有记录的WHERE条件都是单一字段 → 使用简化的 CASE key_field WHEN 语法（性能最优）
        2. 如果WHERE条件包含多字段或复杂条件 → 使用通用的 CASE WHEN ... THEN 语法

        :param table_name: 表名
        :param update_list: 更新数据列表，每个元素包含 update_fields 和 where_conditions
            格式示例: [
                {'update_fields': {'name': '张三', 'age': 25}, 'where_conditions': {'id': 1}},
                {'update_fields': {'name': '李四', 'age': 30}, 'where_conditions': {'id': 2}}
            ]
        :param commit: 是否自动提交
        :param self_close: 是否自动关闭连接
        :return: None
        
        :example:
            # 单一主键条件（自动使用简化语法）
            >>> update_list = [
            ...     {'update_fields': {'name': '张三', 'age': 25}, 'where_conditions': {'id': 1}},
            ...     {'update_fields': {'name': '李四', 'age': 30}, 'where_conditions': {'id': 2}}
            ... ]
            >>> executor.batch_update('users', update_list, commit=True)
            
            # 复杂条件（自动使用通用语法）
            >>> update_list = [
            ...     {'update_fields': {'status': 'active'}, 'where_conditions': {'id': 1, 'type': 'user'}},
            ...     {'update_fields': {'status': 'inactive'}, 'where_conditions': {'id': ('>', 100)}}
            ... ]
            >>> executor.batch_update('users', update_list, commit=True)
        """
        from .utils.update import batch_update as batch_update_func
        batch_update_func(self, table_name, update_list, commit, self_close)

    # 删除数据
    def delete( self , table_name , where_conditions , commit = False , self_close = False ) :
        """
        通用的SQL删除执行器方法，支持动态构造WHERE子句

        :param table_name: 表名
        :param where_conditions: WHERE条件，格式为字典，如 {'field1': 'value1', 'field2': 'value2'}
        :param commit: 是否自动提交
        :param self_close: 是否自动关闭连接
        :return: None
        """
        from .utils.delete import delete as delete_func
        delete_func(self, table_name, where_conditions, commit, self_close)


    # 选择数据
    def select( self , table_names , select_fields , where_conditions = None, order_by = None , limit = None ,
                join_conditions = None ,
                self_close = False , fetch_config = None ) :
        """
        通用的SQL查询执行器方法，支持JOIN操作
        :param table_names: 表名，可以是字符串或列表
        :param select_fields: 要查询的字段列表
        :param where_conditions: WHERE条件，格式为字典
        :param order_by: ORDER BY子句
        :param limit: LIMIT子句
        :param join_conditions: JOIN条件，格式为字典，如 {"join_type": "JOIN", "conditions": ["field1", "=", "field2"]}
        :param self_close: 是否自动关闭连接
        :param fetch_config: 获取配置，用于控制查询结果的返回格式和行为
            
            fetch_config是一个字典，包含以下可选配置项：
            
            1. fetch_mode (str): 获取模式，控制返回数据的数量
               - "all" (默认): 获取所有结果
               - "oneTuple": 获取单条记录（元组格式）
               - "one": 获取单个值（第一个字段的值）
               
            2. output_format (str): 输出格式，仅当fetch_mode="all"时有效
               - "" (默认): 返回原始元组列表
               - "list_1": 返回扁平化的列表（提取每行的第一个字段）
               - "df": 返回pandas DataFrame
               - "df_dict": 返回字典列表（DataFrame转dict）
               
            3. data_label (list): 数据标签，用于DataFrame的列名或字典的键名
               如果为None，系统会根据select_fields自动生成
               
            4. show_count (bool): 是否显示查询结果数量，默认为False
               
            5. order_by (str): ORDER BY子句，如 "id DESC" 或 "name ASC"
            
            6. limit (int): LIMIT子句，限制返回记录数
            
            示例：
                # 获取所有记录并返回DataFrame
                fetch_config = {
                    "fetch_mode": "all",
                    "output_format": "df",
                    "data_label": ["id", "name", "email"],
                    "show_count": True
                }
                
                # 获取单条记录
                fetch_config = {
                    "fetch_mode": "oneTuple"
                }
                
                # 获取单个值
                fetch_config = {
                    "fetch_mode": "one"
                }
                
                # 获取所有记录并返回字典列表
                fetch_config = {
                    "fetch_mode": "all",
                    "output_format": "df_dict",
                    "order_by": "created_at DESC",
                    "limit": 100
                }
        :return: 查询结果，格式根据fetch_config配置而定
        """
        from .utils.select import select as select_func
        return select_func(self, table_names, select_fields, where_conditions, order_by, limit, join_conditions, self_close, fetch_config)


    def fetch_and_response( self,table_names , select_fields , where_conditions = None, 
        join_conditions=None,fetch_config = None,format_func=None , self_close = True ) :
        """
        通用的产品数据获取与格式化方法
        
        :param table_names: 表名，可以是字符串或列表
        :param select_fields: 要查询的字段列表
        :param where_conditions: WHERE条件，格式为字典
        :param join_conditions: JOIN条件，格式为字典
        :param fetch_config: 获取配置，用于控制查询结果的返回格式和行为
            
            fetch_config是一个字典，包含以下可选配置项：
            
            1. fetch_mode (str): 获取模式，控制返回数据的数量
               - "all" (默认): 获取所有结果
               - "oneTuple": 获取单条记录（元组格式）
               - "one": 获取单个值（第一个字段的值）
               
            2. output_format (str): 输出格式，仅当fetch_mode="all"时有效
               - "df_dict" (默认): 返回字典列表
               - "df": 返回pandas DataFrame
               - "list_1": 返回扁平化的列表
               - "": 返回原始元组列表
               
            3. data_label (list): 数据标签，用于DataFrame的列名或字典的键名
               如果为None，系统会根据select_fields自动生成
               
            4. show_count (bool): 是否显示查询结果数量，默认为False
               
            5. order_by (str): ORDER BY子句，如 "id DESC" 或 "name ASC"
            
            6. limit (int): LIMIT子句，限制返回记录数
            
            示例：
                # 获取所有记录并返回字典列表（默认）
                fetch_config = {
                    "output_format": "df_dict",
                    "order_by": "created_at DESC",
                    "limit": 100
                }
                
                # 获取单条记录
                fetch_config = {
                    "fetch_mode": "oneTuple"
                }
        :param format_func: 自定义格式化函数，用于对结果进行额外处理
        :param self_close: 是否自动关闭连接
        :return: 包含success、result、message的字典
        """
        
        if fetch_config is None :
            fetch_config = { "fetch_mode" : "all" , "output_format" : "df_dict" , "data_label" : None }
        order_by = fetch_config.get("order_by", None)
        limit = fetch_config.get("limit", None)
        try :
            # 使用默认的select方法
            result = self.select( table_names , select_fields , where_conditions ,order_by, limit,
                                            join_conditions, self_close , fetch_config )
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

    # 支持复杂查询的执行方法
    def execute_query(self, sql, params=None, fetch_config=None, self_close=False):
        """
        执行自定义SQL查询
        :param sql: SQL语句
        :param params: 参数
        :param fetch_config: 获取配置，用于控制查询结果的返回格式和行为
            
            fetch_config是一个字典，包含以下可选配置项：
            
            1. fetch_mode (str): 获取模式，控制返回数据的数量
               - "all" (默认): 获取所有结果
               - "oneTuple": 获取单条记录（元组格式）
               - "one": 获取单个值（第一个字段的值）
               
            2. output_format (str): 输出格式，仅当fetch_mode="all"时有效
               - "df_dict" (默认): 返回字典列表
               - "df": 返回pandas DataFrame
               - "list_1": 返回扁平化的列表
               - "" (默认): 返回原始元组列表
               
            3. data_label (list): 数据标签，用于DataFrame的列名或字典的键名
               
            4. show_count (bool): 是否显示查询结果数量，默认为False
            
            示例：
                # 获取所有记录并返回DataFrame
                fetch_config = {
                    "fetch_mode": "all",
                    "output_format": "df",
                    "data_label": ["id", "name", "email"],
                    "show_count": True
                }
                
                # 获取单条记录
                fetch_config = {
                    "fetch_mode": "oneTuple"
                }
                
                # 执行聚合查询获取单个值
                fetch_config = {
                    "fetch_mode": "one"
                }
        :param self_close: 是否自动关闭连接
        :return: 查询结果，格式根据fetch_config配置而定
        """
        if fetch_config is None:
            fetch_config = {}
        
        fetch_mode = fetch_config.get("fetch_mode", "all")
        output_format = fetch_config.get("output_format", "df_dict")
        show_count = fetch_config.get("show_count", False)
        data_label = fetch_config.get("data_label", [])
        
        result = self.fetch_format(sql, fetch_mode, output_format, show_count, data_label, params, self_close)
        return result


    # 将 table 中的字段和字段类型，导出为md格式文件
    def export_table_md( self , table_name , save_path=None , self_close=True ) :
        """
        将 table 中的字段和字段类型，导出为md格式文件
        :param table_name: 表名或表名列表，支持字符串或列表.[]/()表示导出所有表
        :param save_path: 保存路径，当导出单个表时为文件路径，导出多个表时为目录路径
        :param self_close: 是否自动关闭连接
        :return: 当导出单个表时为None，导出多个表时返回导出的表名列表
        """
        from .tools.table_export import table_md, tables_md
        
        # 判断table_name类型
        if isinstance(table_name, str):
            # 单个表导出
            table_md(self, table_name, save_path, self_close)
            return None
        elif isinstance(table_name, (list, tuple)):
            # 批量导出
            return tables_md(self, table_name, save_path, self_close)
        else:
            # 默认按字符串处理
            table_md(self, str(table_name), save_path, self_close)
            return None