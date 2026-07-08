import re


def validate_table_name(table_name: str) -> str:
    """校验表名，仅允许字母、数字、下划线，防止 SQL 注入"""
    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', table_name):
        raise ValueError(f"Invalid table name: {table_name}")
    return table_name