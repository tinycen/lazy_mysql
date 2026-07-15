import re

# 错误日志中 IN/NOT IN 列表与 params 截断阈值
_IN_TRUNCATION_THRESHOLD = 50     # IN 列表元素超过此数量才截断
_MAX_IN_ITEMS_FOR_LOG = 10        # IN 列表截断后保留的元素数量
_MAX_PARAMS_FOR_LOG = 50          # params 日志最多显示数量
_MAX_PARAMS_HEAD_FOR_LOG = 10     # params 截断后保留头部数量


def truncate_long_in_lists(sql):
    """
    截断 SQL 中过长的 IN/NOT IN 列表，避免 sqlparse 因 token 过多而格式化失败。
    仅用于错误日志输出，不影响实际执行的 SQL。

    :param sql: 原始 SQL 语句
    :return: dict
        - sql: str, 截断后的 SQL 语句
        - truncated: bool, 是否发生过截断
        - details: list[dict], 每个被截断的 IN/NOT IN 列表详情
            - field: str|None, 字段名，无法识别时为 None
            - operator: str, 'IN' 或 'NOT IN'
            - original_count: int, 原始元素数量
            - kept_count: int, 保留元素数量
            - truncated_count: int, 截断元素数量
    """
    if not sql:
        return {'sql': sql, 'truncated': False, 'details': []}

    truncated_details = []

    def replace_in_list(match):
        field = match.group(1)
        operator = match.group(2).upper()
        content = match.group(3)
        items = [item.strip() for item in content.split(',') if item.strip()]
        if len(items) > _IN_TRUNCATION_THRESHOLD:
            kept_count = _MAX_IN_ITEMS_FOR_LOG
            truncated_count = len(items) - kept_count
            truncated_details.append({
                'field': field,
                'operator': operator,
                'original_count': len(items),
                'kept_count': kept_count,
                'truncated_count': truncated_count,
            })
            kept = items[:kept_count]
            return f"{field or ''} {operator}({', '.join(kept)}, ... /* {truncated_count} items truncated */)"
        return match.group(0)

    # 匹配 field IN (...) 或 field NOT IN (...)
    # 字段名支持 table.column 形式，无法识别时 field 为 None
    pattern = re.compile(r'(\w+(?:\.\w+)?)\s+(NOT\s+IN|IN)\s*\(([^)]*)\)', re.IGNORECASE)
    truncated_sql = pattern.sub(replace_in_list, sql)
    return {
        'sql': truncated_sql,
        'truncated': bool(truncated_details),
        'details': truncated_details,
    }


def truncate_params_for_log(params):
    """
    截断过长的参数列表，避免错误日志过大。

    :param params: 原始参数列表或元组
    :return: dict
        - params: list|tuple, 截断后的参数列表或元组
        - truncated: bool, 是否发生过截断
        - original_count: int|None, 原始元素数量
        - kept_count: int|None, 保留元素数量
        - truncated_count: int, 截断元素数量
    """
    if isinstance(params, (list, tuple)) and len(params) > _MAX_PARAMS_FOR_LOG:
        kept_count = _MAX_PARAMS_HEAD_FOR_LOG
        truncated_count = len(params) - kept_count
        marker = f"... ({truncated_count} items truncated)"
        if isinstance(params, list):
            return {
                'params': params[:kept_count] + [marker],
                'truncated': True,
                'original_count': len(params),
                'kept_count': kept_count,
                'truncated_count': truncated_count,
            }
        return {
            'params': params[:kept_count] + (marker,),
            'truncated': True,
            'original_count': len(params),
            'kept_count': kept_count,
            'truncated_count': truncated_count,
        }
    return {
        'params': params,
        'truncated': False,
        'original_count': len(params) if isinstance(params, (list, tuple)) else None,
        'kept_count': None,
        'truncated_count': 0,
    }
