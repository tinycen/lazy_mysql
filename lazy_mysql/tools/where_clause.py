def build_where_clause( where_conditions ) :
    """
    构造WHERE子句和对应的参数列表

    :param where_conditions: WHERE条件，格式为字典，每个值可以是:
        - 简单值: 默认使用 = 比较
        - 元组: (比较运算符, 值) 如 ('>', 100)
    :return: (where_clause, params) - WHERE子句字符串和参数列表
    """
    if not where_conditions :
        return None , None

    clauses = []
    params = []
    
    for field, value in where_conditions.items() :
        if isinstance(value, tuple) and len(value) == 2 :
            operator, val = value
            clauses.append(f"{field} {operator} %s")
            params.append(val)
        else :
            clauses.append(f"{field} = %s")
            params.append(value)
            
    where_clause = ' AND '.join(clauses)
    return where_clause , params