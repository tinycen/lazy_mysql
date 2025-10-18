import json
import pandas as pd
from ...tools.where_clause import build_where_clause


def batch_update(executor, table_name, update_list, commit=False, self_close=False):
    """
    智能批量更新方法，自动判断WHERE条件复杂度并选择最优SQL生成策略
    
    策略选择逻辑：
    1. 如果所有记录的WHERE条件都是单一字段 → 使用简化的 CASE key_field WHEN 语法（性能最优）
    2. 如果WHERE条件包含多字段或复杂条件 → 使用通用的 CASE WHEN ... THEN 语法
    
    :param executor: SQLExecutor 实例
    :param table_name: 表名
    :param update_list: 更新数据列表，每个元素包含 update_fields 和 where_conditions
        格式示例: [
            {'update_fields': {'name': '张三', 'age': 25}, 'where_conditions': {'id': 1}},
            {'update_fields': {'name': '李四', 'age': 30}, 'where_conditions': {'id': 2}}
        ]
    :param commit: 是否自动提交
    :param self_close: 是否自动关闭连接
    :return: None
    
    :example:
        # 单一主键条件（自动使用简化语法）
        >>> update_list = [
        ...     {'update_fields': {'name': '张三', 'age': 25}, 'where_conditions': {'id': 1}},
        ...     {'update_fields': {'name': '李四', 'age': 30}, 'where_conditions': {'id': 2}}
        ... ]
        >>> executor.batch_update('users', update_list, commit=True)
        
        # 复杂条件（自动使用通用语法）
        >>> update_list = [
        ...     {'update_fields': {'status': 'active'}, 'where_conditions': {'id': 1, 'type': 'user'}},
        ...     {'update_fields': {'status': 'inactive'}, 'where_conditions': {'id': ('>', 100)}}
        ... ]
        >>> executor.batch_update('users', update_list, commit=True)
    """
    if not update_list:
        raise ValueError("update_list 不能为空")
    
    # 验证数据格式
    for item in update_list:
        if 'update_fields' not in item or 'where_conditions' not in item:
            raise ValueError("update_list 中每个元素必须包含 'update_fields' 和 'where_conditions'")
        
        # 防御：检查 where_conditions 不能为空或None
        if not item['where_conditions']:
            raise ValueError("where_conditions 不能为空，这会导致更新所有记录")
    
    # 使用 pandas 分析 WHERE 条件的复杂度
    df_conditions = pd.DataFrame([item['where_conditions'] for item in update_list])
    
    # 判断是否使用简化模式
    is_simple_case, key_field = _check_simple_case(df_conditions)
    
    # 收集所有更新字段
    df_updates = pd.DataFrame([item['update_fields'] for item in update_list])
    all_update_fields = df_updates.columns.tolist()
    
    # 根据模式选择不同的SQL构建策略
    if is_simple_case:
        sql, params = _build_simple_update_sql(
            table_name, update_list, all_update_fields, key_field, df_conditions
        )
    else:
        sql, params = _build_complex_update_sql(
            table_name, update_list, all_update_fields
        )
    
    # 执行SQL
    executor.execute(sql, params, commit, self_close)


def _check_simple_case(df_conditions):
    """
    检查是否可以使用简化的 CASE WHEN 语法
    
    :param df_conditions: WHERE条件的DataFrame
    :return: (is_simple_case, key_field) - 是否简化模式及主键字段名
    """
    if len(df_conditions.columns) != 1:
        return False, None
    
    key_field = df_conditions.columns[0]
    sample_values = df_conditions[key_field].tolist()
    
    # 检查是否所有值都是简单值（非元组）
    if any(isinstance(v, tuple) for v in sample_values):
        return False, None
    
    return True, key_field


def _process_update_value(value):
    """
    处理更新值，将dict和list类型转换为JSON字符串
    
    :param value: 原始值
    :return: 处理后的值
    """
    if isinstance(value, (dict, list)):
        return json.dumps(value)
    return value


def _build_case_clauses_simple(update_list, all_update_fields, key_field):
    """
    构建简化模式的CASE子句数据结构
    
    :param update_list: 更新数据列表
    :param all_update_fields: 所有更新字段
    :param key_field: 主键字段名
    :return: case_clauses - CASE子句数据字典
        格式: {field: [(key_value, value), ...]}
    """
    case_clauses = {field: [] for field in all_update_fields}
    
    for item in update_list:
        update_fields = item['update_fields']
        key_value = item['where_conditions'][key_field]
        
        for field in all_update_fields:
            if field in update_fields:
                value = _process_update_value(update_fields[field])
                case_clauses[field].append((key_value, value))
    
    return case_clauses


def _build_case_clauses_complex(update_list, all_update_fields):
    """
    构建复杂模式的CASE子句数据结构
    
    :param update_list: 更新数据列表
    :param all_update_fields: 所有更新字段
    :return: (case_clauses, all_where_conditions) - CASE子句数据和WHERE条件列表
        case_clauses 格式: {field: [(where_clause, where_params, value), ...]}
        all_where_conditions 格式: [(where_clause, where_params), ...]
    """
    case_clauses = {field: [] for field in all_update_fields}
    all_where_conditions = []
    
    for item in update_list:
        update_fields = item['update_fields']
        where_conditions = item['where_conditions']
        
        # 构建WHERE条件
        where_clause, where_params = build_where_clause(where_conditions)
        
        # 防御：检查 where_clause 不能为 None
        if where_clause is None or where_params is None:
            raise ValueError(f"where_conditions 构建失败: {where_conditions}")
        
        all_where_conditions.append((where_clause, where_params))
        
        for field in all_update_fields:
            if field in update_fields:
                value = _process_update_value(update_fields[field])
                case_clauses[field].append((where_clause, where_params, value))
    
    return case_clauses, all_where_conditions


def _build_set_clause_simple(case_clauses, key_field):
    """
    构建简化模式的SET子句
    
    :param case_clauses: CASE子句数据
    :param key_field: 主键字段名
    :return: (set_clause, params) - SET子句字符串和对应的参数列表
    
    参数顺序说明：
    对于 SQL: name = CASE id WHEN %s THEN %s WHEN %s THEN %s END
    参数顺序为: [key_value1, value1, key_value2, value2, ...]
    """
    set_parts = []
    params = []
    
    for field, cases in case_clauses.items():
        if not cases:
            continue
        
        case_sql = f"{field} = CASE {key_field}"
        for key_value, value in cases:
            case_sql += " WHEN %s THEN %s"
            params.append(key_value)
            params.append(value)
        case_sql += f" ELSE {field} END"
        set_parts.append(case_sql)
    
    return ', '.join(set_parts), params


def _build_set_clause_complex(case_clauses):
    """
    构建复杂模式的SET子句
    
    :param case_clauses: CASE子句数据
    :return: (set_clause, params) - SET子句字符串和对应的参数列表
    
    参数顺序说明：
    对于 SQL: status = CASE WHEN id = %s AND type = %s THEN %s WHEN id > %s THEN %s END
    参数顺序为: [value1, where_param1_1, where_param1_2, value2, where_param2_1, ...]
    即：先value，再where_params
    """
    set_parts = []
    params = []
    
    for field, cases in case_clauses.items():
        if not cases:
            continue
        
        case_sql = f"{field} = CASE"
        for where_clause, where_params, value in cases:
            case_sql += f" WHEN {where_clause} THEN %s"
            params.append(value)
            params.extend(where_params)
        case_sql += f" ELSE {field} END"
        set_parts.append(case_sql)
    
    return ', '.join(set_parts), params


def _build_simple_update_sql(table_name, update_list, all_update_fields, key_field, df_conditions):
    """
    构建简化模式的完整UPDATE SQL
    
    生成SQL示例:
    UPDATE users SET
        name = CASE id WHEN %s THEN %s WHEN %s THEN %s END,
        age = CASE id WHEN %s THEN %s WHEN %s THEN %s END
    WHERE id IN (%s, %s);
    
    参数顺序：
    1. SET子句的所有参数 (key_value, value pairs)
    2. WHERE IN 子句的所有 key_values
    
    :return: (sql, params) - SQL语句和参数元组
    """
    # 构建CASE子句
    case_clauses = _build_case_clauses_simple(update_list, all_update_fields, key_field)
    
    # 构建SET子句并收集参数
    set_clause, set_params = _build_set_clause_simple(case_clauses, key_field)
    
    # 构建WHERE IN子句
    key_values = df_conditions[key_field].tolist()
    placeholders = ', '.join(['%s'] * len(key_values))
    where_clause = f"{key_field} IN ({placeholders})"
    
    # 组装所有参数：先 SET 的参数，再 WHERE 的参数
    all_params = set_params + key_values
    
    # 组装SQL
    sql = f"UPDATE {table_name} SET {set_clause} WHERE {where_clause};"
    return sql, tuple(all_params)


def _build_complex_update_sql(table_name, update_list, all_update_fields):
    """
    构建复杂模式的完整UPDATE SQL
    
    生成SQL示例:
    UPDATE users SET 
        status = CASE 
            WHEN id = %s AND type = %s THEN %s 
            WHEN id > %s THEN %s 
            ELSE status END
    WHERE (id = %s AND type = %s) OR (id > %s);
    
    参数顺序：
    1. SET子句的所有参数 (value + where_params for each CASE WHEN)
    2. WHERE子句的所有参数 (where_params for each condition)
    
    注意：
    - 不同记录的WHERE条件用OR连接（表示更新满足任一条件的记录）
    - 每条记录内部的多个条件用AND连接（由build_where_clause处理）
    - CASE WHEN会精确匹配每个条件并更新对应的值
    
    :return: (sql, params) - SQL语句和参数元组
    """
    # 构建CASE子句
    case_clauses, all_where_conditions = _build_case_clauses_complex(update_list, all_update_fields)
    
    # 构建SET子句并收集参数
    set_clause, set_params = _build_set_clause_complex(case_clauses)
    
    # 构建WHERE子句并收集参数
    # 使用OR连接不同记录的条件是合理的，因为：
    # 1. 我们要更新多条不同的记录，需要匹配任一条件
    # 2. CASE WHEN 会精确判断每个条件并应用对应的更新值
    # 3. 即使WHERE匹配了多条记录，CASE WHEN的ELSE子句会保持原值（不会误更新）
    final_where_parts = []
    where_params = []
    for where_clause, params in all_where_conditions:
        final_where_parts.append(f"({where_clause})")
        where_params.extend(params)
    where_clause = ' OR '.join(final_where_parts)
    
    # 组装所有参数：先 SET 的参数，再 WHERE 的参数
    all_params = set_params + where_params
    
    # 组装SQL
    sql = f"UPDATE {table_name} SET {set_clause} WHERE {where_clause};"
    return sql, tuple(all_params)