import json
from ..tools.where_clause import build_where_clause

def update(executor, table_name, update_fields, where_conditions, commit=False, self_close=False):
    """
    通用的SQL更新执行器方法，支持动态构造WHERE子句

    :param executor: SQLExecutor 实例
    :param table_name: 表名
    :param update_fields: 需要更新的字段和值，格式为字典，如 {'field1': 'value1', 'field2': 'value2'}
    :param where_conditions: WHERE条件，格式为字典，如 {'field1': 'value1', 'field2': 'value2'}
    :param commit: 是否自动提交
    :param self_close: 是否自动关闭连接
    :return: None
    """
    # 处理update_fields中的dict和list类型，自动执行json.dumps
    processed_fields = update_fields.copy()
    for field, value in processed_fields.items():
        if isinstance(value, (dict, list)):
            processed_fields[field] = json.dumps(value)

    # 构造SET子句
    set_clause = ', '.join([f"{field} = %s" for field in processed_fields.keys()])

    # 构造WHERE子句
    where_clause, where_params = build_where_clause(where_conditions)

    # 合并参数：processed_fields的值 + where_conditions的值
    params = list(processed_fields.values())
    if where_params:
        params.extend(where_params)

    # 构造SQL语句
    sql = f'''UPDATE {table_name} SET {set_clause} WHERE {where_clause};'''

    # 执行SQL
    executor.execute(sql, params, commit, self_close)