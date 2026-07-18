from ..utils.value_converter import prepare_db_row
from ..tools.where_clause import build_where

def update(executor, table_name, fields, conditions, commit=False, self_close=False):
    """
    通用的SQL更新执行器方法，支持动态构造WHERE子句

    :param executor: SQLExecutor 实例
    :param table_name: 表名
    :param fields: 需要更新的字段和值，格式为字典，如 {'field1': 'value1', 'field2': 'value2'}
    :param conditions: WHERE条件，格式为字典，如 {'field1': 'value1', 'field2': 'value2'}
    :param commit: 是否自动提交
    :param self_close: 是否自动关闭连接
    :return: 受影响的行数（int）
    """
    if not fields:
        if self_close:
            executor.close()
        raise ValueError("fields 不能为空")

    if not conditions:
        if self_close:
            executor.close()
        raise ValueError("conditions 不能为空，这会导致更新所有记录")

    # 统一处理写入值，保持与 insert / batch_update 一致的类型转换规则
    processed_fields = prepare_db_row(fields)

    # 构造SET子句
    set_clause = ', '.join([f"{field} = %s" for field in processed_fields.keys()])

    # 构造WHERE子句
    where_clause, where_params = build_where(conditions)

    # 合并参数：processed_fields的值 + conditions的值
    params = list(processed_fields.values())
    if where_params:
        params.extend(where_params)

    # 构造SQL语句
    sql = f'''UPDATE {table_name} SET {set_clause} WHERE {where_clause};'''

    # 执行SQL
    executor.execute(sql, params, commit, self_close)
    return executor.mycursor.rowcount