from ..tools.where_clause import build_sql_with_where

def delete(executor, table_name, conditions, commit=False, self_close=False):
    """
    通用的SQL删除执行器方法，支持动态构造WHERE子句

    :param executor: SQLExecutor 实例
    :param table_name: 表名
    :param conditions: WHERE条件，格式为字典，如 {'field1': 'value1', 'field2': 'value2'}
    :param commit: 是否自动提交
    :param self_close: 是否自动关闭连接
    :return: 受影响的行数（int）
    """
    if not conditions:
        if self_close:
            executor.close()
        raise ValueError("conditions 不能为空，这会导致删除所有记录")

    # 构造SQL语句
    sql, params = build_sql_with_where(f"DELETE FROM {table_name}", conditions)
    sql += ";"

    # 执行SQL
    executor.execute(sql, params, commit, self_close)
    return executor.mycursor.rowcount