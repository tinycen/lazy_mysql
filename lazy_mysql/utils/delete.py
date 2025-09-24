from ..tools.where_clause import build_where_clause

def delete(executor, table_name, where_conditions, commit=False, self_close=False):
    """
    通用的SQL删除执行器方法，支持动态构造WHERE子句

    :param executor: SQLExecutor 实例
    :param table_name: 表名
    :param where_conditions: WHERE条件，格式为字典，如 {'field1': 'value1', 'field2': 'value2'}
    :param commit: 是否自动提交
    :param self_close: 是否自动关闭连接
    :return: None
    """

    # 构造WHERE子句
    where_clause, params = build_where_clause(where_conditions)

    # 构造SQL语句
    sql = f'''DELETE FROM {table_name} WHERE {where_clause};'''

    # 执行SQL
    executor.execute(sql, params, commit, self_close)