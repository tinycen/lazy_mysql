import ast
import json
from .validate import validate_table_name
from ..executor import SQLExecutor


def fix_json(executor: SQLExecutor, table_name: str, index_column: str, target_column: str,
            commit = False , self_close = False):
    """修复 JSON 类型列, 把 TEXT 类型列 > 转为 JSON 类型列
        :param executor: SQLExecutor 实例
        :param table_name: 表名
        :param index_column: 索引列名
        :param target_column: 目标列名
        :param commit: 是否提交事务
        :param self_close: 是否关闭连接池
       """
    validate_table_name(table_name)
    # 查找无效的 JSON 值（表名/列名是标识符，不能走 SQL 参数占位符，需用 Python 字符串格式化）
    sql = f""" SELECT {index_column}, {target_column}
        FROM {table_name} WHERE {target_column} IS NOT NULL AND NOT JSON_VALID({target_column}) """
    result = executor.fetch_format(sql, fetch_mode="all")

    if not result:  # pyright: ignore
        print("没有需要修复的 JSON 值")
        if self_close:
            executor.close()
        return []

    fixed = 0
    failed = []
    update_list = []
    for index, old_value in result: # pyright: ignore
        try:
            # ast.literal_eval 能解析单引号的 Python 字面量
            obj = ast.literal_eval(old_value)
            # 转为标准 JSON（双引号）
            new_value = json.dumps(obj, ensure_ascii=False)
            update_list.append({
                'fields': {target_column: new_value},
                'conditions': {index_column: index},
            })
            fixed += 1
        except Exception as e:
            failed.append((index, str(e)[:100]))

    if update_list:
        executor.batch_update(table_name, update_list, commit=commit, self_close=self_close)
    elif self_close:
        executor.close()

    print(f"成功修复 {fixed} 行，失败 {len(failed)} 行")
    for f in failed:
        print(f)
    return failed
