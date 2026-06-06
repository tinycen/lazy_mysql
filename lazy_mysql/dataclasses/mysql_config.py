"""
MySQL数据库配置类
"""

import os


class MySQLConfig:
    """MySQL数据库配置类"""

    ENV_HOST = "LAZY_MYSQL_HOST"
    ENV_PORT = "LAZY_MYSQL_PORT"
    ENV_USER = "LAZY_MYSQL_USER"
    ENV_PASSWORD = "LAZY_MYSQL_PASSWORD"
    ENV_PASSWD = "LAZY_MYSQL_PASSWD"
    ENV_DATABASE = "LAZY_MYSQL_DATABASE"
    ENV_DEFAULT_DATABASE = "LAZY_MYSQL_DEFAULT_DATABASE"

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
        self.port = int(port)
        self.user = user
        self.passwd = passwd
        self.default_database = default_database

    @classmethod
    def from_env(cls):
        """从系统环境变量读取MySQL配置，未设置的字段沿用默认值。"""
        return cls(
            host=os.getenv(cls.ENV_HOST, 'localhost'),
            port=os.getenv(cls.ENV_PORT, 3306),
            user=os.getenv(cls.ENV_USER, 'root'),
            passwd=os.getenv(cls.ENV_PASSWORD, os.getenv(cls.ENV_PASSWD, '')),
            default_database=os.getenv(
                cls.ENV_DATABASE,
                os.getenv(cls.ENV_DEFAULT_DATABASE)
            ),
        )

    @classmethod
    def resolve(cls, sql_config=None):
        """兼容旧配置对象；传入None时从环境变量创建配置。"""
        if sql_config is None:
            return cls.from_env()
        return sql_config

    def __repr__(self):
        return f"MySQLConfig(host='{self.host}', port={self.port}, user='{self.user}', default_database='{self.default_database}')"


# 默认配置
DEFAULT_MYSQL_CONFIG = MySQLConfig()
