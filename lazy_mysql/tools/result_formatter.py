import pandas as pd

def fetch_format( executor , sql , fetch_mode , output_format = "" , show_count = False , data_label = None ,
                  params = None , self_close = False ) :
    """
    定义解析结果程序(格式化返回结果)
    :param executor: SQLExecutor 实例
    :param sql: SQL语句
    :param fetch_mode: 获取模式,可选值: all、oneTuple、one
    :param output_format: 输出格式 ,默认 "" , 可选值: list_1、df、df_dict , 仅在 fetch_mode 为 all 时有效
    :param show_count: 是否显示结果数量
    :param data_label: 数据标签，用于DataFrame的列名或字典的键名
    :param params: 参数
    :param self_close: 是否自动关闭连接
    :return: 查询结果，格式根据参数配置而定
        
        返回结果类型说明：
        - fetch_mode="all" + output_format="": 返回元组列表，如 [(1, '张三', 'zhang@example.com'), (2, '李四', 'li@example.com')]
        - fetch_mode="all" + output_format="list_1": 返回扁平化列表，如 [1, 2, 3]（提取每行第一个字段）
        - fetch_mode="all" + output_format="df": 返回pandas DataFrame
        - fetch_mode="all" + output_format="df_dict": 返回字典列表，如 [{'id': 1, 'name': '张三'}, {'id': 2, 'name': '李四'}]
        - fetch_mode="oneTuple": 返回单个元组，如 (1, '张三', 'zhang@example.com')
        - fetch_mode="one": 返回单个值，如 1 或 '张三'
    """

    if data_label is None :
        data_label = [ ]

    # 验证：当输出格式为df时，data_label不能为空
    if output_format in ["df", "df_dict"] and not data_label:
        raise ValueError("当 output_format 为 'df' 或 'df_dict' 时，data_label 参数不能为空!")

    executor.execute( sql , params , self_close = False )

    if fetch_mode == "all" :
        myresult = executor.mycursor.fetchall()  # 接收全部的返回结果行,返回结果为 [tuple（元组）]
        if output_format == "list_1" :
            if myresult is None :
                return [ ]
            data = [ myresult[ 0 ] for myresult in myresult ] if myresult else [ ]
            myresult = data
        elif "df" in output_format :
            myresult = pd.DataFrame( myresult , columns = data_label )
            if "dict" in output_format :
                myresult = myresult.to_dict( "records" )
    elif fetch_mode == "oneTuple" :
        myresult = executor.mycursor.fetchone()  # 接收返回结果行,返回结果为 tuple（元组）,如果没有结果,则仅返回 None
    elif fetch_mode == "one" :
        result = executor.mycursor.fetchone()
        if result is None:
            myresult = None
        elif isinstance(result,tuple):
            myresult = result[ 0 ] if result else None
        else:
            myresult = result
    else :
        executor.close()
        raise ValueError( f"fetch_mode error :{fetch_mode} , only supported [ all , oneTuple , one ]" )

    if self_close :
        executor.close()

    if show_count and fetch_mode == "all" :
        # 处理不同fetch_mode下的结果计数
        num = len(myresult) if myresult is not None else 0
        print( f"查询结果数量：{num}" )
        return myresult , num
    return myresult