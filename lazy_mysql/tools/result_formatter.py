import pandas as pd

def fetch_format( executor , sql , fetch_mode , output_format = "" , show_count = False , data_label = None ,
                  params = None , self_close = False ) :
    """
    定义解析结果程序(格式化返回结果)
    :param executor: SQLExecutor 实例
    :param sql: SQL语句
    :param fetch_mode: 获取模式
    :param output_format: 输出格式
    :param show_count: 是否显示结果数量
    :param data_label: 数据标签
    :param params: 参数
    :param self_close: 是否自动关闭连接
    :return: 查询结果
    """
    executor.execute( sql , params , self_close = self_close )

    if data_label is None :
        data_label = [ ]

    if fetch_mode == "all" :
        myresult = executor.mycursor.fetchall()  # 接收全部的返回结果行,返回结果为 tuple（元组）
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
        myresult = executor.mycursor.fetchone()  # 接收全部的返回结果行,返回结果为 tuple（元组）
    else :
        result = executor.mycursor.fetchone()
        myresult = result[ 0 ] if result else None

    if show_count :
        num = len( myresult )
        print( f"查询结果数量：{num}" )
        return myresult , num
    return myresult