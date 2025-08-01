from ..executor import SQLExecutor

def insert(executor: SQLExecutor, table_name, insert_fields, commit=False, self_close=False):
    """
    通用的SQL插入执行器方法，
    :param executor: SQLExecutor 实例
    :param table_name: 表名
    :param insert_fields: 字段和值，格式为字典，如 {'field1': 'value1', 'field2': 'value2'}
    :param commit: 是否自动提交
    :param self_close: 是否自动关闭连接
    :return: None
    """
    # 构造SQL语句
    sql = f'''INSERT INTO {table_name} 
                ({', '.join(insert_fields.keys())}) VALUES ({', '.join(['%s'] * len(insert_fields))});'''
    values = tuple(insert_fields.values())

    executor.execute(sql, values, commit, self_close)