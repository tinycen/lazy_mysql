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
    indexes = {}
    for row in executor.mycursor.fetchall():
        if row[2] not in indexes:
            indexes[row[2]] = []
        indexes[row[2]].append(row[4])
    
    if self_close:
        executor.close()

    # 解析结果(取Field,Type,Comment字段)
    result = [(row[0], row[1], row[8]) for row in result]
    # 解析结果并生成Markdown内容
    md_content = f"## {table_name} 表结构\n\n"
    md_content += "| 字段名 | 字段类型 | 字段描述 | 是否主键 | 索引 |\n"
    md_content += "| --- | --- | --- | --- | --- |\n"
    for row in result:
        field_name, field_type, field_comment = row
        is_primary = "是" if field_name in primary_keys else "-"
        field_indexes = []
        # 如果是主键，添加主键索引标识
        if field_name in primary_keys:
            field_indexes.append("PRIMARY / PRIMARY KEY")
        for index_name, columns in indexes.items():
            if field_name in columns and index_name != "PRIMARY":
                # 获取索引类型
                executor.execute(f"SHOW INDEX FROM {table_name} WHERE Key_name = '{index_name}'", self_close=False)
                index_info = executor.mycursor.fetchone()
                # Non_unique字段: 0表示唯一索引(UNIQUE), 1表示普通索引
                index_type = "UNIQUE(唯一索引)" if index_info[1] == 0 else "INDEX(普通索引)"
                field_indexes.append(f"{index_name} / {index_type}")
        indexes_str = ", ".join(field_indexes) if field_indexes else "-"
        md_content += f"| {field_name} | {field_type} | {field_comment} | {is_primary} | {indexes_str} |\n"

    # 写入Markdown文件
    if save_path is None :
        save_path = f"{table_name}.md"
    with open(save_path, 'w', encoding='utf-8') as md_file:
        md_file.write(md_content)