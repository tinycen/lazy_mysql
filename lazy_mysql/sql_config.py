"""
MySQL数据库配置类
"""

class MySQLConfig:
    """MySQL数据库配置类"""
    
    def __init__(self, host='localhost', port=3306, user='root', 
                 passwd='', default_database=None):
        """
        初始化MySQL配置
        
        Args:
            host (str): 数据库主机地址
            port (int): 数据库端口
            user (str): 用户名
            passwd (str): 密码
            default_database (str): 默认数据库名
        """
        self.host = host
        self.port = port
        self.user = user
        self.passwd = passwd
        self.default_database = default_database
    
    def __repr__(self):
        return f"MySQLConfig(host='{self.host}', port={self.port}, user='{self.user}', default_database='{self.default_database}')"


# 默认配置
DEFAULT_MYSQL_CONFIG = MySQLConfig()
