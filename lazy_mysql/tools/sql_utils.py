# SQL工具函数
import os

# 载入sql文件
def load_sql( sql_path ) :
    with open(sql_path, 'r', encoding='utf-8') as f:
        sql = f.read().strip()
    return sql


# 智能解析 SQL 参数：自动判断是 SQL 文本还是 .sql 文件路径
def resolve_sql(sql):
    """
    智能解析 SQL 参数：自动判断是 SQL 文本还是 .sql 文件路径

    检测规则：
    1. os.PathLike 对象（如 pathlib.Path） → 视为文件路径，读取文件内容
    2. 字符串且以 .sql 结尾（不区分大小写） → 视为文件路径，读取文件内容
    3. 其他字符串 → 视为 SQL 文本，原样返回

    :param sql: SQL语句字符串 或 .sql 文件路径（支持 str / os.PathLike）
    :return: 解析后的 SQL 语句字符串
    """
    if isinstance(sql, os.PathLike):
        return load_sql(sql)
    if isinstance(sql, str) and sql.strip().lower().endswith('.sql'):
        return load_sql(sql)
    return sql


# 构建SQL条件限制语句
def add_limit( column , value , column_alias = "" , add_and = True , operator = "=" ) : 
    """
    构建SQL条件限制语句，支持多种比较运算符
    
    :param column: 字段名
    :param value: 字段值，如果为"", "all", "null"则返回空字符串
    :param column_alias: 表别名，可选
    :param add_and: 是否添加AND前缀
    :param operator: 比较运算符，支持 =, !=, <>, >, >=, <, <=, LIKE, NOT LIKE, IN, NOT IN
    :return: SQL条件语句片段
    
    :example:
        >>> add_limit('status', 'active')
        "AND status = 'active'"
        >>> add_limit('age', 18, 'u', operator='>=')
        "AND u.age >= 18"
        >>> add_limit('name', '%张%', operator='LIKE')
        "AND name LIKE '%张%'"
        >>> add_limit('type', ['admin', 'user'], operator='IN')
        "AND type IN ('admin', 'user')"
    """

    if value in ("", "all", "null", None, [], ()) : 
        return "" 

    if column_alias != "" : 
        column_alias += "." 
    
    # 处理IN/NOT IN运算符的特殊情况
    if operator.upper() in ('IN', 'NOT IN') and isinstance(value, (list, tuple)):
        value_str = ', '.join([str(v) if isinstance(v, (int, float)) else f"'{v}'" for v in value])
        condition = f"{column_alias}{column} {operator.upper()} ({value_str})"
    else:
        # 处理数字类型，不需要加单引号
        if isinstance(value, (int, float)):
            condition = f"{column_alias}{column} {operator.upper()} {value}"
        else:
            condition = f"{column_alias}{column} {operator.upper()} '{value}'"
    
    if add_and : 
        return f"AND {condition}" 
    else : 
        return condition
