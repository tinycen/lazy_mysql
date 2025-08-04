from ..executor import SQLExecutor

def insert(executor: SQLExecutor, table_name, insert_fields, skip_duplicate=False, commit=False, self_close=False):
    """
    通用的SQL插入执行器方法，
    :param executor: SQLExecutor 实例
    :param table_name: 表名
    :param insert_fields: 字段和值，格式为字典，如 {'field1': 'value1', 'field2': 'value2'}
    :param skip_duplicate: 是否跳过重复数据(基于主键或唯一索引判断)
        注意: 只有主键或当索引被明确设置为UNIQUE时才会触发跳过重复记录的行为,普通索引(如INDEX)不会导致跳过重复记录。
    :param commit: 是否自动提交
    :param self_close: 是否自动关闭连接
    :return: None
    """
    if isinstance(insert_fields, dict):
        # 单条插入
        sql = f'''INSERT INTO {table_name} 
                    ({', '.join(insert_fields.keys())}) VALUES ({', '.join(['%s'] * len(insert_fields))});'''
        values = tuple(insert_fields.values())
        executor.execute(sql, values, commit, self_close)
    elif isinstance(insert_fields, list):
        # 批量插入

        # 获取字段名（假设所有字典的键相同）
        field_names = ', '.join(insert_fields[0].keys())

        # 构造占位符，例如：(%s, %s)
        placeholders = '(' + ', '.join(['%s'] * len(insert_fields[0])) + ')'

        # 构造SQL语句
        insert_keyword = 'INSERT IGNORE' if skip_duplicate else 'INSERT'
        sql = f'''{insert_keyword} INTO {table_name} ({field_names}) VALUES {placeholders}'''

        # 构造参数列表
        values = [tuple(item.values()) for item in insert_fields]

        # 执行SQL
        executor.execute(sql, values, commit, self_close)
    else:
        executor.close()
        raise ValueError("insert_fields must be a dict or a list of dicts")