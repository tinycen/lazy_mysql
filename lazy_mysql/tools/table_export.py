def export_table_md( executor , table_name , save_path = None , self_close = True ) :
    """
    将 table 中的字段和字段类型,字段描述,是否主键,索引导出为md格式文件
    :param executor: SQLExecutor 实例
    :param table_name: 表名
    :param save_path: 保存路径
    :param self_close: 是否自动关闭连接
    :return: None
    """
    # 检查表是否存在
    executor.execute(f"SHOW TABLES LIKE '{table_name}'", self_close=False)
    if not executor.mycursor.fetchone():
        executor.close()
        raise ValueError(f"{table_name} not exist")
        
    # 执行查询获取表结构(使用SHOW FULL COLUMNS)
    query = f"SHOW FULL COLUMNS FROM {table_name}"
    print(f"execute: {query}")  # 调试输出
    # 执行查询但不关闭连接，因为后面还需要获取结果
    executor.execute(query , self_close = False)

    # 获取查询结果
    if executor.mycursor.with_rows:
        result = executor.mycursor.fetchall()
    else:
        raise ValueError(f"查询 '{query}' 没有返回结果集")
    # print(f"原始查询结果: {result}")  # 调试输出
    
    # 获取主键信息
    executor.execute(f"SHOW KEYS FROM {table_name} WHERE Key_name = 'PRIMARY'", self_close=False)
    primary_keys = [row[4] for row in executor.mycursor.fetchall()]
    
    # 获取索引信息
    executor.execute(f"SHOW INDEX FROM {table_name}", self_close=False)
    index_results = executor.mycursor.fetchall()
    
    # 获取表的字符集和排序规则信息
    executor.execute(f"SHOW TABLE STATUS LIKE '{table_name}'", self_close=False)
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
    if save_path is None :
        save_path = f"{table_name}.md"
    with open(save_path, 'w', encoding='utf-8') as md_file:
        md_file.write(md_content)