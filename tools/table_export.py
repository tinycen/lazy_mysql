def export_table_md( executor , table_name , save_path = None , self_close = True ) :
    """
    将 table 中的字段和字段类型，导出为md格式文件
    :param executor: SQLExecutor 实例
    :param table_name: 表名
    :param save_path: 保存路径
    :param self_close: 是否自动关闭连接
    :return: None
    """
    # 检查表是否存在
    executor.execute(f"SHOW TABLES LIKE '{table_name}'", self_close=False)
    if not executor.mycursor.fetchone():
        raise ValueError(f"表 {table_name} 不存在")
        
    # 执行查询获取表结构(使用SHOW FULL COLUMNS)
    query = f"SHOW FULL COLUMNS FROM {table_name}"
    print(f"执行查询: {query}")  # 调试输出
    executor.execute(query , self_close = self_close)
    # 获取查询结果
    result = executor.mycursor.fetchall()
    # print(f"原始查询结果: {result}")  # 调试输出
    
    # 解析结果(取Field,Type,Comment字段)
    result = [(row[0], row[1], row[8]) for row in result]
    # 解析结果并生成Markdown内容
    md_content = f"## {table_name} 表结构\n\n"
    md_content += "| 字段名 | 字段类型 | 字段描述 |\n"
    md_content += "| --- | --- | --- |\n"
    for row in result:
        field_name, field_type, field_comment = row
        md_content += f"| {field_name} | {field_type} | {field_comment} |\n"
    # 写入Markdown文件
    if save_path is None :
        save_path = f"{table_name}.md"
    with open(save_path, 'w', encoding='utf-8') as md_file:
        md_file.write(md_content)