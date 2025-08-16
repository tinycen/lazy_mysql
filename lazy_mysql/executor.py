from .utils.connect import connection

class SQLExecutor :
    """SQL执行器类，提供统一的数据库操作接口"""

    def __init__( self , sql_config ,database=None,use_dict_cursor=False) :
        self.mydb , self.mycursor = connection( sql_config,database,use_dict_cursor )

    # 读取sql文件
    def read_sql( self , sql_path ) :
        with open(sql_path, 'r', encoding='utf-8') as f:
            sql = f.read()
        return sql.strip()

    # 关闭数据库连接
    def close( self ) :
        self.mycursor.close()
        self.mydb.close()

    # 提交并关闭数据库连接
    def commit_close( self ) :
        self.mydb.commit()
        self.close()

    # sql 语句执行器
    def execute( self , sql , params = None , commit = False , self_close = False ) :
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
            print(f"sql: {sql} \n params:{params}")
            # 如果发生错误，回滚事务
            if commit :
                self.mydb.rollback()
            self.mydb.close()
            raise Exception(f"SQL execute failed: {str(e)}")

        # 改为仅在提交成功时关闭连接，避免数据未提交就关闭连接
        if self_close and commit :
            self.close()


    # 定义解析结果程序(格式化返回结果)
    def fetch_format( self , sql , fetch_mode , output_format = "" , show_count = False , data_label = None ,
                      params = None , self_close = False ) :
        """
        定义解析结果程序(格式化返回结果)
        :param sql: SQL语句
        :param fetch_mode: 获取模式
        :param output_format: 输出格式
        :param show_count: 是否显示结果数量
        :param data_label: 数据标签
        :param params: 参数
        :param self_close: 是否自动关闭连接
        :return: 查询结果
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
        :param fetch_config: 获取配置
        :return: 查询结果
        """
        from .utils.select import select as select_func
        return select_func(self, table_names, select_fields, where_conditions, order_by, limit, join_conditions, self_close, fetch_config)


    def fetch_and_response( self,table_names , select_fields , where_conditions = None, 
        join_conditions=None,fetch_config = None,format_func=None , self_close = True ) :
        """
        通用的产品数据获取与格式化方法
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
        :param fetch_config: 获取配置
        :param self_close: 是否自动关闭连接
        :return: 查询结果
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