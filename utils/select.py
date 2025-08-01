from ..executor import SQLExecutor
from ..tools.where_clause import build_where_clause

def select(executor: SQLExecutor, table_names, select_fields, where_conditions, order_by=None, limit=None,
           join_conditions=None, self_close=False, fetch_config=None):
    """
    通用的SQL查询执行器方法，支持JOIN操作
    :param executor: SQLExecutor 实例
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
    # 处理select_fields参数
    if isinstance(select_fields, dict):
        # 如果是字典，自动添加表名前缀
        processed_fields = []
        for table, fields in select_fields.items():
            for field in fields:
                processed_fields.append(f"{table}.{field}")
        columns = processed_fields
    else :
        columns = select_fields
    # 构造select子句
    select_clause = ', '.join(columns)

    # 处理表名
    if isinstance(table_names, str):
        # 单个表
        sql = f"SELECT {select_clause} FROM {table_names}"
    elif isinstance(table_names, list):
        # 多个表，需要JOIN
        main_table = table_names[0]
        sql = f"SELECT {select_clause} FROM {main_table}"
        
        # 添加JOIN子句
        if join_conditions:
            # JOIN操作，table_names必须是包含至少两个表名的列表
            if isinstance(table_names, str) or len(table_names) < 2:
                raise ValueError("存在JOIN操作时，table_names必须是包含至少两个表名的列表")
            join_type = join_conditions.get("join_type", "JOIN")
            conditions = join_conditions.get("conditions", [])
            
            # 为每个额外的表添加JOIN子句
            for i, join_table in enumerate(table_names[1:], start=1):
                # 如果提供了具体的JOIN条件，则使用它
                if conditions and len(conditions) >= 3:
                    field1, operator, field2 = conditions[0], conditions[1], conditions[2]
                    # 如果字段名没有表前缀，添加主表前缀
                    if '.' not in field1:
                        field1 = f"{main_table}.{field1}"
                    if '.' not in field2:
                        field2 = f"{join_table}.{field2}"
                    sql += f" {join_type} {join_table} ON {field1} {operator} {field2}"
                else:
                    # 默认使用item_id进行JOIN
                    sql += f" {join_type} {join_table} ON {main_table}.item_id = {join_table}.item_id"
    else:
        raise ValueError("table_names must be a string or a list of strings")

    # 构造WHERE子句
    where_clause, params = build_where_clause(where_conditions)
    if where_clause:
        sql += f" WHERE {where_clause}"

    # 添加ORDER BY子句（如果提供）
    if order_by:
        sql += f" ORDER BY {order_by}"

    # 添加LIMIT子句（如果提供）
    if limit:
        sql += f" LIMIT {limit}"

    if fetch_config is None:
        fetch_config = {}

    fetch_mode = fetch_config["fetch_mode"]
    output_format = fetch_config["output_format"]
    show_count = fetch_config.get("show_count", False)
    
    # 获取data_label参数
    data_label = fetch_config.get("data_label", None)
    
    # 如果data_label为None，则根据select_fields自动生成
    if data_label is None and "df" in output_format :
        if isinstance(select_fields, dict):
            # 如果select_fields是字典，展平为列表
            data_label = []
            for table, fields in select_fields.items():
                for field in fields:
                    if field in data_label :
                        raise ValueError(f"字段值重复：Field '{field}' already exists in data_label")
                    data_label.append(field)
        else:
            # 如果select_fields是列表，直接使用
            data_label = select_fields

    result = executor.fetch_format(sql, fetch_mode, output_format, show_count, data_label, params, self_close)
    return result