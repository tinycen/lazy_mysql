class NDayInterval:
    """
    表示返回N天前的日期，可用于SQL中与 ">=" 运算符配合，筛选最近N天的数据。
    例如: NDayInterval(7) => DATE_SUB(NOW(), INTERVAL 7 DAY)
    用法示例：WHERE date_column >= DATE_SUB(NOW(), INTERVAL 7 DAY)
    """
    def __init__(self, days):
        self.days = days
    def __str__(self):
        return f"DATE_SUB(NOW(), INTERVAL {self.days} DAY)"


def _validate_param_value(param_value, field_name):
    """
    校验参数值是否为numpy类型，如果是则抛出异常
    
    :param param_value: 需要校验的参数值
    :param field_name: 参数字段名，用于错误信息
    :raises: TypeError - 当参数值为numpy类型时
    """
    # 检查是否为numpy类型
    param_type = type(param_value).__name__
    if param_type.startswith('numpy'):
        raise TypeError(f"字段 '{field_name}' 的参数值类型为 {param_type}，numpy类型数据无法直接写入数据库，请先转换为Python原生类型")


def build_where_clause( conditions ) :
    """
    构造WHERE子句和对应的参数列表
    
    该方法用于根据提供的条件字典构建SQL的WHERE子句，支持两种条件格式：
    1. 简单值：自动生成等值比较条件
    2. 元组格式：自定义比较运算符和值
    
        :param conditions: WHERE条件，格式为字典，每个键为字段名，每个值可以是:
        - 简单值: 默认使用 = 比较，如 {'name': '张三', 'age': 25}
        - 元组: (比较运算符, 值) 如 {'age': ('>', 18)}, {'name': ('LIKE', '%张%')}
        - 支持的比较运算符包括: =, !=, <>, >, >=, <, <=, LIKE, NOT LIKE, IN, NOT IN
    
    :return: tuple - (where_clause, params)
        - where_clause: str - 构建好的WHERE子句（不包含WHERE关键字），条件之间用AND连接
        - params: list - 对应的参数值列表，用于防止SQL注入
    
    :raises: ValueError - 当元组格式长度不为2时
    :raises: TypeError - 当参数值为numpy类型时
    
    :example:
        >>> conditions = {'name': '张三', 'age': ('>', 18)}
        >>> clause, params = build_where_clause(conditions)
        >>> print(clause)  # 输出: name = %s AND age > %s
        >>> print(params)  # 输出: ['张三', 18]

        >>> from lazy_mysql.tools.where_clause import NDayInterval
        >>> conditions = {'order_dateTime': ('>=', NDayInterval(7))}
        >>> clause, params = build_where_clause(conditions)
        >>> print(clause)  # 输出: order_dateTime >= DATE_SUB(NOW(), INTERVAL 7 DAY)
        >>> print(params)  # 输出: []

        >>> conditions = {'status': ('IN', [1, 2, 3]), 'create_time': ('>=', '2023-01-01')}
        >>> clause, params = build_where_clause(conditions)
        >>> print(clause)  # 输出: status IN (%s, %s, %s) AND create_time >= %s
        >>> print(params)  # 输出: [1, 2, 3, '2023-01-01']
    """
    if not conditions :
        return None , None

    clauses = []
    params = []
    
    for field, value in conditions.items() :
        if isinstance(value, tuple) and len(value) == 2 :
            operator, val = value
            # 新增：如果val是NDayInterval，拼接SQL表达式
            if isinstance(val, NDayInterval):
                clauses.append(f"{field} {operator} {val}")
            # 处理IN和NOT IN运算符的特殊情况
            elif operator.upper() in ('IN', 'NOT IN') and isinstance(val, (list, tuple)):
                # 校验列表/元组中的每个元素
                for item in val:
                    _validate_param_value(item, field)
                placeholders = ', '.join(['%s'] * len(val))
                clauses.append(f"{field} {operator.upper()} ({placeholders})")
                params.extend(val)
            else:
                # 校验参数值
                _validate_param_value(val, field)
                clauses.append(f"{field} {operator} %s")
                params.append(val)
        else :
            # 校验参数值
            _validate_param_value(value, field)
            clauses.append(f"{field} = %s")
            params.append(value)
            
    where_clause = ' AND '.join(clauses)
    return where_clause , params
