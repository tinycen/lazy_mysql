import mysql.connector

# 获取数据库连接和游标
def connection( sql_config ,database=None ) :

    """
    建立数据库连接并返回连接对象和游标对象

    Args:
        sql_config (object): 数据库配置对象，包含host, port, user, passwd, default_database等属性
        database (str, optional): 数据库名称，database参数优先使用，默认使用 sql_config.default_database
    Returns:
        tuple: (数据库连接对象, 游标对象)
    """
    if database is not None :
        database = database
    elif not hasattr(sql_config, 'default_database') or sql_config.default_database is None:
        database = "new_schema"
    else:
        database = sql_config.default_database
        
    try:
        # 新版本使用password参数和推荐参数
        # buffered=True - 缓冲查询结果，避免多次查询时出现'Unread result found'错误
        # pool_size=5 - 连接池最大连接数，控制并发连接数量，
        # pool_reset_session=True - 连接返回池时重置会话变量，确保连接状态干净
        # pool_name="shop_pool" - 连接池名称，用于标识和管理连接池 
        # 如果设置了 pool_reset_session 就必须设置 pool_name ，省略会报错- AttributeError: 
        # Pool name 'rm-wz93y5aqe2f5gvu5uto.mysql.rds.aliyuncs.com_3306_root_yqq_new_schema' is too long
        # use_pure=True - 使用纯Python实现而非C扩展，提高兼容性，减少外部依赖（实测，设置在为False会导致连接失败！）

        mydb = mysql.connector.connect(
            host=sql_config.host,
            port=sql_config.port,
            user=sql_config.user,
            password=sql_config.passwd,
            database=database,
            buffered=True,
            use_pure=True
         )
        mycursor = mydb.cursor(buffered=True)
    except TypeError:
        # 旧版本兼容模式
        mydb = mysql.connector.connect(
            host=sql_config.host,
            port=sql_config.port,
            user=sql_config.user,
            passwd=sql_config.passwd,
            database=database,
            use_pure=True
        )
        mycursor = mydb.cursor()
    
    # 检查版本是否过时
    if tuple(map(int, mysql.connector.__version__.split('.')[:2])) < (9, 4):
        print(f"警告: MySQL连接器版本{mysql.connector.__version__}已过时，建议升级到9.4.0或更高版本")
        print("pip install --upgrade mysql-connector-python")
    return mydb , mycursor