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


# 批量插入数据
def batch_insert( executor: SQLExecutor, table_name, fields_list, commit=False, self_close=False ) :
    """
    通用的SQL批量插入执行器方法，
    :param table_name: 表名
    :param fields_list: 字段和值的列表，格式为字典列表，如 [{'field1': 'value1', 'field2': 'value2'}, {'field1': 'value3', 'field2': 'value4'}]
    """
    if not fields_list :
        raise ValueError( "fields_list is empty !" )

    # 获取字段名（假设所有字典的键相同）
    field_names = ', '.join( fields_list[ 0 ].keys() )

    # 构造占位符，例如：(%s, %s)
    placeholders = '(' + ', '.join( [ '%s' ] * len( fields_list[ 0 ] ) ) + ')'

    # 构造SQL语句
    sql = f'''INSERT INTO {table_name} ({field_names}) VALUES {placeholders}'''

    # 构造参数列表
    values = [ tuple( item.values() ) for item in fields_list ]

    # 执行SQL
    executor.execute(sql, values, commit, self_close)