import os
import sqlparse
from .validate import validate_table_name
from ..executor import SQLExecutor



def table_md(executor: SQLExecutor, table_name, save_path=None, self_close=True):
    """
    将 table/view 中的字段和字段类型,字段描述,是否主键,索引导出为md格式文件
    - 自动识别视图并委托 view_md 处理
    :param executor: SQLExecutor 实例
    :param table_name: 表名或视图名
    :param save_path: 保存路径
    :param self_close: 是否自动关闭连接
    :return: None
    """
    table_name = validate_table_name(table_name)

    # 自动识别视图，委托 view_md 处理
    if _is_view(executor, table_name):
        view_md(executor, table_name, save_path, self_close)
        return

    # 检查表是否存在（LIKE 子句支持参数化查询）
    executor.execute("SHOW TABLES LIKE %s", params=(table_name,), self_close=False)
    if not executor.mycursor.fetchone():
        executor.close()
        raise ValueError(f"{table_name} not exist")
        
    # 执行查询获取表结构(使用SHOW FULL COLUMNS，FROM 子句不支持参数化，已通过表名校验防护)
    query = f"SHOW FULL COLUMNS FROM {table_name}"
    executor.execute(query, self_close=False)

    # 获取查询结果
    if executor.mycursor.with_rows:
        result = executor.mycursor.fetchall()
    else:
        raise ValueError(f"查询 '{query}' 没有返回结果集")
    # print(f"原始查询结果: {result}")  # 调试输出
    
    # 获取主键信息（FROM 子句不支持参数化，已通过表名校验防护）
    executor.execute(f"SHOW KEYS FROM {table_name} WHERE Key_name = 'PRIMARY'", self_close=False)
    primary_keys = [row[4] for row in executor.mycursor.fetchall()]
    
    # 获取索引信息（FROM 子句不支持参数化，已通过表名校验防护）
    executor.execute(f"SHOW INDEX FROM {table_name}", self_close=False)
    index_results = executor.mycursor.fetchall()
    
    # 获取表的字符集和排序规则信息（LIKE 子句支持参数化查询）
    executor.execute("SHOW TABLE STATUS LIKE %s", params=(table_name,), self_close=False)
    table_status = executor.mycursor.fetchone()
    table_charset = table_status[14] if table_status and len(table_status) > 14 else "未知"
    table_collation = table_status[15] if table_status and len(table_status) > 15 else "未知"
    
    # 处理索引信息，按索引名分组
    indexes = {}
    for row in index_results:
        index_name = row[2]  # Key_name
        column_name = row[4]  # Column_name
        non_unique = row[1]   # Non_unique (0=唯一索引, 1=普通索引)
        seq_in_index = row[3] # Seq_in_index (索引中的列顺序)
        
        if index_name not in indexes:
            indexes[index_name] = {
                'columns': [],
                'is_unique': non_unique == 0,
                'type': 'PRIMARY' if index_name == 'PRIMARY' else ('UNIQUE' if non_unique == 0 else 'INDEX')
            }
        
        # 按序号插入列名，确保复合索引的列顺序正确
        while len(indexes[index_name]['columns']) < seq_in_index:
            indexes[index_name]['columns'].append(None)
        
        if seq_in_index <= len(indexes[index_name]['columns']):
            indexes[index_name]['columns'][seq_in_index - 1] = column_name
        else:
            indexes[index_name]['columns'].append(column_name)
    
    if self_close:
        executor.close()

    # 解析结果(取Field,Type,Collation,Default,Comment字段)
    result = [(row[0], row[1], row[2], row[5], row[8]) for row in result]
    
    # 生成Markdown内容
    md_content = f"## {table_name} 表结构\n\n"
    
    # 表级编码信息
    md_content += "### 表信息\n\n"
    md_content += f"- **字符集**: {table_charset}\n"
    md_content += f"- **排序规则**: {table_collation}\n\n"
    
    # 字段信息表
    md_content += "### 字段信息\n\n"
    md_content += "| 字段名 | 字段类型 | 编码/排序规则 | 字段描述 | 默认值 | 是否主键 |\n"
    md_content += "| --- | --- | --- | --- | --- | --- |\n"
    for row in result:
        field_name, field_type, collation, default_value, field_comment = row
        is_primary = "是" if field_name in primary_keys else "-"
        field_comment = field_comment if field_comment else "-"
        collation = collation if collation else "-"
        default_value = str(default_value) if default_value is not None else "-"
        md_content += f"| {field_name} | {field_type} | {collation} | {field_comment} | {default_value} | {is_primary} |\n"
    
    # 索引信息表
    if indexes:
        md_content += "\n### 索引信息\n\n"
        md_content += "| 索引名 | 索引类型 | 包含字段 | 备注 |\n"
        md_content += "| --- | --- | --- | --- |\n"
        
        for index_name, index_info in indexes.items():
            # 过滤掉None值并连接列名
            columns = [col for col in index_info['columns'] if col is not None]
            columns_str = ", ".join(columns)
            
            index_type = index_info['type']
            if index_type == 'PRIMARY':
                type_desc = "主键"
                remark = "主键索引"
            elif index_type == 'UNIQUE':
                type_desc = "唯一索引"
                remark = "保证字段值唯一性"
            else:
                type_desc = "普通索引"
                remark = "-"
            
            # 如果是复合索引，在备注中说明
            if len(columns) > 1:
                remark += f"（复合索引，共{len(columns)}个字段）"
            
            md_content += f"| {index_name} | {type_desc} | {columns_str} | {remark} |\n"

    # 写入Markdown文件
    if save_path is None:
        save_path = f"{table_name}.md"
    with open(save_path, 'w', encoding='utf-8') as md_file:
        md_file.write(md_content)


def _is_view(executor: SQLExecutor, table_name: str) -> bool:
    """判断表名是否为视图"""
    executor.execute("SHOW FULL TABLES LIKE %s", params=(table_name,), self_close=False)
    row = executor.mycursor.fetchone()
    if row and len(row) > 1:
        return row[1].upper() == 'VIEW'
    return False


def _get_view_source(executor: SQLExecutor, view_name: str) -> str:
    """获取视图的源 SQL 文本，并格式化为可读格式"""
    executor.execute(f"SHOW CREATE VIEW {view_name}", self_close=False)
    row = executor.mycursor.fetchone()
    if row and len(row) > 1:
        raw_sql = row[1]
        return sqlparse.format(
            raw_sql,
            reindent=True,
            keyword_case='upper',
            indent_width=4,
            strip_comments=False,
        )
    return ""


def view_md(executor: SQLExecutor, view_name, save_path=None, self_close=True):
    """
    将视图的字段结构、字段描述和源 SQL 导出为 md 格式文件
    :param executor: SQLExecutor 实例
    :param view_name: 视图名
    :param save_path: 保存路径
    :param self_close: 是否自动关闭连接
    :return: None
    """
    view_name = validate_table_name(view_name)

    # 检查视图是否存在
    executor.execute("SHOW FULL TABLES LIKE %s", params=(view_name,), self_close=False)
    row = executor.mycursor.fetchone()
    if not row or (len(row) > 1 and row[1].upper() != 'VIEW'):
        executor.close()
        raise ValueError(f"{view_name} is not a view or does not exist")

    # 获取视图源 SQL
    view_source = _get_view_source(executor, view_name)

    # 执行查询获取视图字段结构
    query = f"SHOW FULL COLUMNS FROM {view_name}"
    executor.execute(query, self_close=False)
    if executor.mycursor.with_rows:
        result = executor.mycursor.fetchall()
    else:
        raise ValueError(f"查询 '{query}' 没有返回结果集")

    if self_close:
        executor.close()

    # 解析结果(取Field,Type,Collation,Default,Comment字段)
    result = [(row[0], row[1], row[2], row[5], row[8]) for row in result]

    # 生成Markdown内容
    md_content = f"## {view_name} 视图结构\n\n"

    # 字段信息表
    md_content += "### 字段信息\n\n"
    md_content += "| 字段名 | 字段类型 | 编码/排序规则 | 字段描述 | 默认值 |\n"
    md_content += "| --- | --- | --- | --- | --- |\n"
    for row in result:
        field_name, field_type, collation, default_value, field_comment = row
        field_comment = field_comment if field_comment else "-"
        collation = collation if collation else "-"
        default_value = str(default_value) if default_value is not None else "-"
        md_content += f"| {field_name} | {field_type} | {collation} | {field_comment} | {default_value} |\n"

    # 视图源 SQL
    md_content += "\n### 源 SQL\n\n"
    md_content += f"```sql\n{view_source}\n```\n\n"

    # 写入Markdown文件
    if save_path is None:
        save_path = f"{view_name}.md"
    with open(save_path, 'w', encoding='utf-8') as md_file:
        md_file.write(md_content)


def tables_md(executor: SQLExecutor, table_names=None, save_dir=None, self_close=True):
    """
    批量导出表结构和视图结构为md格式文件
    - 表导出到 save_dir 目录
    - 视图导出到 save_dir/views 子目录
    :param executor: SQLExecutor 实例
    :param table_names: 表名列表，如果为None或空列表则导出所有表和视图
    :param save_dir: 保存目录路径，默认为当前目录下的table_docs文件夹
    :param self_close: 是否自动关闭连接
    :return: dict，包含 'tables' 和 'views' 两个列表
    """
    try:
        # 设置保存目录
        if save_dir is None:
            save_dir = "table_docs"

        # 创建保存目录
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        # 获取所有表和视图名
        if table_names is None or len(table_names) == 0:
            executor.execute("SHOW FULL TABLES", self_close=False)
            all_rows = executor.mycursor.fetchall()
            table_names = [row[0] for row in all_rows]
        
        if not table_names:
            print("No tables found.")
            return {'tables': [], 'views': []}

        # 区分表和视图
        tables_list = []
        views_list = []
        for name in table_names:
            if _is_view(executor, name):
                views_list.append(name)
            else:
                tables_list.append(name)

        exported_tables = []
        exported_views = []

        # 创建视图子目录
        views_dir = os.path.join(save_dir, "views")
        if views_list and not os.path.exists(views_dir):
            os.makedirs(views_dir)

        # 导出每个表的结构
        for table_name in tables_list:
            try:
                save_path = os.path.join(save_dir, f"{table_name}.md")
                table_md(executor, table_name, save_path, self_close=False)
                exported_tables.append(table_name)
                print(f"Success export table: {table_name}")
            except Exception as e:
                print(f"Export failed (table): {table_name} - {e}")
                continue

        # 导出每个视图的结构
        for view_name in views_list:
            try:
                save_path = os.path.join(views_dir, f"{view_name}.md")
                view_md(executor, view_name, save_path, self_close=False)
                exported_views.append(view_name)
                print(f"Success export view: {view_name}")
            except Exception as e:
                print(f"Export failed (view): {view_name} - {e}")
                continue
        
        if self_close:
            executor.close()

        print(f"Batch export completed.")
        if exported_tables:
            print(f"  Tables ({len(exported_tables)}): {save_dir}")
        if exported_views:
            print(f"  Views ({len(exported_views)}): {os.path.join(save_dir, 'views')}")
        return {'tables': exported_tables, 'views': exported_views}
        
    except Exception as e:
        if self_close:
            executor.close()
        raise Exception(f"Batch export failed: {str(e)}")


def export_md(executor: SQLExecutor, table_name:str, save_path=None, self_close=True):
    """
    将 table/view 中的字段和字段类型，导出为md格式文件
    :param executor: SQLExecutor 实例
    :param table_name: 表名或表名列表，支持字符串或列表.[]/()表示导出所有表和视图
    :param save_path: 保存路径，当导出单个表时为文件路径，导出多个表时为目录路径
    :param self_close: 是否自动关闭连接
    :return: 当导出单个表时为None，导出多个表时返回 dict（含 'tables' 和 'views'）
    """
    # 判断table_name类型
    if isinstance(table_name, str):
        # 单个表/视图导出，table_md 内部自动识别视图
        table_md(executor, table_name, save_path, self_close)
        return None
    elif isinstance(table_name, (list, tuple)):
        # 批量导出
        return tables_md(executor, table_name, save_path, self_close)
    else:
        # 默认按字符串处理
        table_md(executor, str(table_name), save_path, self_close)
        return None
