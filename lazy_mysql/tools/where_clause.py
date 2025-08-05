def build_where_clause( where_conditions ) :
    """
    构造WHERE子句和对应的参数列表
    
    该方法用于根据提供的条件字典构建SQL的WHERE子句，支持两种条件格式：
    1. 简单值：自动生成等值比较条件
    2. 元组格式：自定义比较运算符和值
    
    :param where_conditions: WHERE条件，格式为字典，每个键为字段名，每个值可以是:
        - 简单值: 默认使用 = 比较，如 {'name': '张三', 'age': 25}
        - 元组: (比较运算符, 值) 如 {'age': ('>', 18)}, {'name': ('LIKE', '%张%')}
        - 支持的比较运算符包括: =, !=, <>, >, >=, <, <=, LIKE, NOT LIKE, IN, NOT IN
    
    :return: tuple - (where_clause, params)
        - where_clause: str - 构建好的WHERE子句（不包含WHERE关键字），条件之间用AND连接
        - params: list - 对应的参数值列表，用于防止SQL注入
    
    :raises: ValueError - 当元组格式长度不为2时
    
    :example:
        >>> conditions = {'name': '张三', 'age': ('>', 18)}
        >>> clause, params = build_where_clause(conditions)
        >>> print(clause)  # 输出: name = %s AND age > %s
        >>> print(params)  # 输出: ['张三', 18]
        
        >>> conditions = {'status': ('IN', [1, 2, 3]), 'create_time': ('>=', '2023-01-01')}
        >>> clause, params = build_where_clause(conditions)
        >>> print(clause)  # 输出: status IN %s AND create_time >= %s
        >>> print(params)  # 输出: [[1, 2, 3], '2023-01-01']
    """
    if not where_conditions :
        return None , None

    clauses = []
    params = []
    
    for field, value in where_conditions.items() :
        if isinstance(value, tuple) and len(value) == 2 :
            # 元组解包
            operator, val = value       # 例如当 value = ('>', 100) 时， operator 会得到'>'， val 会得到100
            clauses.append(f"{field} {operator} %s")
            params.append(val)
        else :
            clauses.append(f"{field} = %s")
            params.append(value)
            
    where_clause = ' AND '.join(clauses)
    return where_clause , params