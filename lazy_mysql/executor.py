import pandas as pd
from .utils.connect import connection

class SQLExecutor :
    """SQL执行器类，提供统一的数据库操作接口"""

    def __init__( self , sql_config ,database=None) :
        self.mydb , self.mycursor = connection( sql_config,database )

    # 关闭数据库连接
    def close( self ) :
        self.mycursor.close()
        self.mydb.close()

    # sql 语句执行器
    def execute( self , sql , params = None , commit = False , self_close = False ) :
        """
        SQL语句执行方法，自动判断是否批量执行
        :param params: 参数，单个参数为元组，批量参数为元组列表，如 [(value1, value2), (value3, value4)]
        """
        try :
            if params :
                # 判断是否为批量参数（列表且第一个元素是元组）
                if isinstance(params, list) and len(params) > 0 and isinstance(params[0], (tuple, list)):
                    self.mycursor.executemany(sql, params)
                else:
                    self.mycursor.execute(sql, params)
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

        if self_close :
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
    def insert( self , table_name , insert_fields , commit = False , self_close = False ) :
        """
        通用的SQL插入执行器方法，
        :param table_name: 表名
        :param insert_fields: 字段和值，格式为字典，如 {'field1': 'value1', 'field2': 'value2'}
        :param commit: 是否自动提交
        :param self_close: 是否自动关闭连接
        :return: None
        """
        from .utils.insert import insert as insert_func
        insert_func(self, table_name, insert_fields, commit, self_close)


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
            message = f"sql run failed > {str(e)}"
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
    def export_table_md( self , table_name , save_path , self_close = True ) :
        """
        将 table 中的字段和字段类型，导出为md格式文件
        :param table_name: 表名
        :param self_close: 是否自动关闭连接
        :return: None
        """
        from .tools.table_export import export_table_md as export_table_md_func
        export_table_md_func(self, table_name, save_path, self_close)
