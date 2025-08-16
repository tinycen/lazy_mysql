import time
import mysql.connector
from mysql.connector.errors import ConnectionTimeoutError

# 获取数据库连接和游标
def connection(sql_config, database=None,dict_cursor=False, max_retries=5,
    retry_delay_base=5):
    """
    建立数据库连接并返回连接对象和游标对象

    Args:
        sql_config (object): 数据库配置对象，包含host, port, user, passwd, default_database等属性
        database (str, optional): 数据库名称，database参数优先使用，默认使用 sql_config.default_database
        max_retries (int, optional): 最大重试次数，默认为5次
        retry_delay_base (int, optional): 重试延迟基数（秒），默认为5秒，第n次重试延迟为 retry_delay_base * n 秒
    Returns:
        tuple: (数据库连接对象, 游标对象)
    """
    if database is not None:
        database = database
    elif not hasattr(sql_config, 'default_database') or sql_config.default_database is None:
        database = "new_schema"
    else:
        database = sql_config.default_database
    
    retry_count = 0
    last_exception = None
    '''
    mysql.connector.connect 支持的详细连接参数介绍：
        https://dev.mysql.com/doc/connector-python/en/connector-python-connectargs.html
    '''
    
    while retry_count <= max_retries:
        try:
            # 新版本使用password参数和推荐参数
            # buffered=True - 缓冲查询结果，避免多次查询时出现'Unread result found'错误
            # pool_size=5 - 连接池最大连接数，控制并发连接数量，
            # pool_reset_session=True - 连接返回池时重置会话变量，确保连接状态干净
            # pool_name="shop_pool" - 连接池名称，用于标识和管理连接池 
            # 如果设置了 pool_reset_session 就必须设置 pool_name ，省略会报错- AttributeError: 
            # Pool name 'rm-wz93y5aqe2f5gvu5uto.mysql.rds.aliyuncs.com_3306_root_yqq_new_schema' is too long
            # use_pure=True - 使用纯Python实现而非C扩展，提高兼容性，减少外部依赖（实测，设置在为False会导致连接失败！）
            # allow_local_infile=True - 启用LOAD DATA LOCAL INFILE功能，允许从本地文件加载数据
            mydb = mysql.connector.connect(
                host=sql_config.host,
                port=sql_config.port,
                user=sql_config.user,
                password=sql_config.passwd,
                database=database,
                buffered=True,
                use_pure=True,
                allow_local_infile=True  
            )
            mycursor = mydb.cursor(buffered=True,dictionary=dict_cursor)    
            # dictionary = True 查询返回字典列表[{'id': 1, 'name': 'a'}, {'id': 2, 'name': 'b'}]  
            # dictionary = False 查询返回元组列表[(1, 'a'), (2, 'b')]  
            
            # 检查版本是否过时
            if tuple(map(int, mysql.connector.__version__.split('.')[:2])) < (9, 4):
                print(f"警告: MySQL连接器版本{mysql.connector.__version__}已过时，建议升级到9.4.0或更高版本")
                print("pip install --upgrade mysql-connector-python")
                
            return mydb, mycursor

            
        except TypeError as e:
            # 检查版本是否过时，但保留原始错误信息
            if tuple(map(int, mysql.connector.__version__.split('.')[:2])) < (9, 4):
                print(f"警告: MySQL连接器版本{mysql.connector.__version__}已过时，建议升级到9.4.0或更高版本")
                print("pip install --upgrade mysql-connector-python")
            # 重新抛出原始的TypeError，保留详细错误信息
            raise TypeError(f"数据库连接参数类型错误: {str(e)}") from e
                
        except ConnectionTimeoutError as e:
            last_exception = e
            if retry_count < max_retries:
                retry_count += 1
                delay = retry_delay_base * retry_count
                print(f"MySQL 连接超时，正在进行第 {retry_count}/{max_retries} 次重试，等待 {delay} 秒...")
                time.sleep(delay)
            else:
                break
        except Exception as e:
            # 其他异常直接抛出
            raise e
    
    # 如果重试次数用完仍然失败，抛出最后一次的异常
    if last_exception:
        raise last_exception
    else:
        raise Exception("连接失败，已达到最大重试次数")