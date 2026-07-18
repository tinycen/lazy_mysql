from ..tools.where_clause import build_sql_with_where
from ..models.fetch_config import FetchConfig
from ..tools.result_formatter import fetch_format


def _build_query_sql(select_expr, table_names, conditions=None, join_conditions=None):
    """
    构造 SELECT 语句的 FROM / JOIN / WHERE 部分（select 与 exists 共用）

    :param select_expr: SELECT 关键字后的表达式，如字段列表或 "1"
    :param table_names: 表名，字符串或列表（列表表示需要 JOIN）
    :param conditions: WHERE 条件字典
    :param join_conditions: JOIN 条件字典
    :return: (sql, params)
    """
    # 处理表名
    if isinstance(table_names, str):
        # 单个表
        sql = f"SELECT {select_expr} FROM {table_names}"
    elif isinstance(table_names, list):
        # 多个表，需要JOIN
        main_table = table_names[0]
        sql = f"SELECT {select_expr} FROM {main_table}"

        # 添加JOIN子句
        if join_conditions:
            # JOIN操作，table_names必须是包含至少两个表名的列表
            if len(table_names) < 2:
                raise ValueError("存在JOIN操作时，table_names必须是包含至少两个表名的列表")
            join_type = join_conditions.get("join_type", "JOIN")
            join_conds = join_conditions.get("conditions", [])

            # 为每个额外的表添加JOIN子句
            for join_table in table_names[1:]:
                # 如果提供了具体的JOIN条件，则使用它
                if join_conds and len(join_conds) >= 3:
                    field1, operator, field2 = join_conds[0], join_conds[1], join_conds[2]
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
    sql, params = build_sql_with_where(sql, conditions)
    return sql, params

def select(executor, table_names, fields=None, conditions=None, order_by=None, limit:int|None=None,
           distinct:bool=False, join_conditions=None, self_close:bool=False, fetch_config=None):
    """
    通用的SQL查询执行器方法，支持JOIN操作
    :param executor: SQLExecutor 实例
    :param table_names: 表名，可以是字符串或列表
    :param fields: 要查询的字段列表
    :param conditions: WHERE条件，格式为字典
        - 支持 NDayInterval 用于最近N天区间筛选，例如：
        {'order_dateTime': ('>=', NDayInterval(7))}  # 最近7天
    :param order_by: ORDER BY子句
    :param limit: LIMIT子句
    :param distinct: 是否使用DISTINCT去重，默认为False
    :param join_conditions: JOIN条件，格式为字典，如 {"join_type": "JOIN", "conditions": ["field1", "=", "field2"]}
    :param self_close: 是否自动关闭连接
    :param fetch_config: 获取配置，用于控制查询结果的返回格式和行为。
        可以是 FetchConfig 模型实例或字典（兼容旧方式）。

        fetch_config包含以下可选配置项：

        1. fetch_mode (str): 获取模式，控制返回数据的数量
           - "all" (默认): 获取所有结果
           - "oneTuple": 获取单条记录（元组格式）
           - "one": 获取单个值（第一个字段的值）

        2. output_format (str): 输出格式，仅当fetch_mode="all" 或 fetch_mode = "oneTuple" 时有效
           - "" (默认): 返回原始元组列表
           - "list_1": 返回扁平化的列表（提取每行的第一个字段）
           - "df": 返回pandas DataFrame
           - "df_dict": 返回字典列表（DataFrame转dict）

        3. data_label (list): 数据标签，用于DataFrame的列名或字典的键名
           如果为None，系统会根据fields自动生成

        4. show_count (bool): 是否显示查询结果数量，默认为False

        示例（使用字典，兼容旧方式）：
            # 获取所有记录并返回DataFrame
            fetch_config = {
                "fetch_mode": "all",
                "output_format": "df",
                "data_label": ["id", "name", "email"],
                "show_count": True
            }

        示例（使用 FetchConfig 模型）：
            from lazy_mysql.models import FetchConfig

            # 获取所有记录并返回DataFrame
            fetch_config = FetchConfig(
                fetch_mode="all",
                output_format="df",
                data_label=["id", "name", "email"],
                show_count=True
            )
    :return: 查询结果，格式根据fetch_config配置而定
    """
    if fields is None:
        raise ValueError("fields 参数不能为空")

    # 处理fields参数
    if isinstance(fields, dict):
        # 如果是字典，自动添加表名前缀
        processed_fields = []
        for table, table_fields in fields.items():
            for field in table_fields:
                processed_fields.append(f"{table}.{field}")
        columns = processed_fields
    else :
        columns = fields
    # 构造select子句
    select_clause = ', '.join(columns)

    # 处理DISTINCT
    distinct_clause = "DISTINCT " if distinct else ""

    # 构造FROM/JOIN/WHERE子句
    select_expr = f"{distinct_clause}{select_clause}"
    sql, params = _build_query_sql(select_expr, table_names, conditions, join_conditions)

    # 添加ORDER BY子句（如果提供）
    if order_by:
        sql += f" ORDER BY {order_by}"

    # 添加LIMIT子句（如果提供）
    if limit:
        sql += f" LIMIT {limit}"

    # 处理 fetch_config，支持 FetchConfig 模型和旧的字典方式
    if fetch_config is None:
        fetch_config = FetchConfig()
    elif isinstance(fetch_config, dict):
        fetch_config = FetchConfig(**fetch_config)
    # 如果已经是 FetchConfig 实例，直接使用

    fetch_mode = fetch_config.fetch_mode
    output_format = fetch_config.output_format
    show_count = fetch_config.show_count

    # 获取data_label参数
    data_label = fetch_config.data_label
    
    # 如果data_label为None，则根据fields自动生成
    if data_label is None and ("df" in output_format or "dict" in output_format) :
        if isinstance(fields, dict):
            # 如果fields是字典，展平为列表
            data_label = []
            for table, table_fields in fields.items():
                for field in table_fields:
                    if field in data_label :
                        raise ValueError(f"字段值重复：Field '{field}' already exists in data_label")
                    data_label.append(field)
        else:
            # 如果fields是列表，直接使用
            data_label = fields

    result = fetch_format(executor, sql, fetch_mode, output_format, show_count, data_label, params, self_close)
    return result


def exists(executor, table_names, conditions=None, join_conditions=None, self_close:bool=False) -> bool:
    """
    快速判断指定条件的数据是否在数据库中存在

    使用 SELECT 1 ... LIMIT 1 优化性能，找到第一条记录即返回，避免全表扫描。
    相比 select 方法，此方法专注于判断存在性，性能更优。

    :param executor: SQLExecutor 实例
    :param table_names: 表名，可以是字符串或列表
    :param conditions: WHERE条件，格式为字典，如 {'field1': 'value1', 'field2': 'value2'}
        - 支持 NDayInterval 用于最近N天区间筛选，例如：
        {'order_dateTime': ('>=', NDayInterval(7))}  # 最近7天
    :param join_conditions: JOIN条件，格式为字典，如 {"join_type": "JOIN", "conditions": ["field1", "=", "field2"]}
    :param self_close: 是否自动关闭连接
    :return: 如果存在符合条件的记录返回 True，否则返回 False

    :example:
        # 判断单个表中是否存在指定条件的数据
        >>> executor.exists('users', {'id': 1})
        True

        # 判断多表JOIN后是否存在符合条件的数据
        >>> executor.exists(['orders', 'users'], 
        ...                 {'orders.status': 'pending'},
        ...                 {'join_type': 'JOIN', 'conditions': ['user_id', '=', 'id']})
        True

        # 判断最近7天内是否有订单
        >>> from lazy_mysql.tools import NDayInterval
        >>> executor.exists('orders', {'created_at': ('>=', NDayInterval(7))})
        True
    """
    # 构造FROM/JOIN/WHERE子句（SELECT 1 ... LIMIT 1 优化）
    sql, params = _build_query_sql("1", table_names, conditions, join_conditions)

    # 添加 LIMIT 1 优化性能
    sql += " LIMIT 1"

    # 执行查询
    result = fetch_format(executor, sql, "one", "", False, None, params, self_close)

    # 如果有结果返回 True，否则返回 False
    return result is not None