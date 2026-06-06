"""
MySQL数据库配置类
"""

import os


class MySQLConfig:
    """MySQL数据库配置类"""

    ENV_HOST = "LAZY_MYSQL_HOST"
    ENV_PORT = "LAZY_MYSQL_PORT"
    ENV_USER = "LAZY_MYSQL_USER"
    ENV_PASSWD = "LAZY_MYSQL_PASSWD"
    ENV_DATABASE = "LAZY_MYSQL_DATABASE"
    ENV_DEFAULT_DATABASE = "LAZY_MYSQL_DEFAULT_DATABASE"

    def __init__(self, host=None, port=None, user=None, passwd=None, default_database=None):
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
        self.port = None if self._is_empty_value(port) else int(port)
        self.user = user
        self.passwd = passwd
        self.default_database = default_database

    @staticmethod
    def _is_empty_value(value) -> bool:
        return value is None or value == ""

    @classmethod
    def _get_env(cls, env_key, cast=None):
        if cls._is_empty_value(env_key):
            return None
        raw = os.getenv(env_key)
        if cls._is_empty_value(raw):
            return None
        if cast is None:
            return raw
        try:
            return cast(raw)
        except Exception:
            return None

    @classmethod
    def _first_non_empty(cls, *values):
        for value in values:
            if not cls._is_empty_value(value):
                return value
        return None

    @classmethod
    def from_env(cls, *, host=None, port=None, user=None, passwd=None, default_database=None):
        """从系统环境变量读取MySQL配置；显式传入的字段优先级更高，空值不会覆盖已有值。"""
        env_host = cls._get_env(cls.ENV_HOST)
        env_port = cls._get_env(cls.ENV_PORT, cast=int)
        env_user = cls._get_env(cls.ENV_USER)
        env_passwd = cls._get_env(cls.ENV_PASSWD)
        env_default_database = cls._first_non_empty(
            cls._get_env(cls.ENV_DATABASE),
            cls._get_env(cls.ENV_DEFAULT_DATABASE),
        )

        return cls(
            host=cls._first_non_empty(host, env_host),
            port=cls._first_non_empty(port, env_port),
            user=cls._first_non_empty(user, env_user),
            passwd=cls._first_non_empty(passwd, env_passwd),
            default_database=cls._first_non_empty(default_database, env_default_database),
        )

    @classmethod
    def from_dict(cls, sql_config):
        """从字典读取MySQL配置；空值不覆盖，缺失字段从环境变量补齐。"""
        return cls.resolve(sql_config)

    @classmethod
    def resolve(cls, sql_config=None, *, host=None, port=None, user=None, passwd=None, default_database=None):
        """
        统一解析配置来源，优先级：显式参数 > 字典/配置对象 > 环境变量。

        空值（None 或 ''）不会覆盖已有值。
        """
        base_host = None
        base_port = None
        base_user = None
        base_passwd = None
        base_default_database = None

        config_dict = None
        if isinstance(sql_config, dict):
            config_dict = dict(sql_config)
        elif sql_config is not None:
            base_host = getattr(sql_config, "host", None)
            base_port = getattr(sql_config, "port", None)
            base_user = getattr(sql_config, "user", None)
            base_passwd = getattr(sql_config, "passwd", None)
            base_default_database = getattr(sql_config, "default_database", None)

        if config_dict is not None:
            if "database" in config_dict and "default_database" not in config_dict:
                config_dict["default_database"] = config_dict.pop("database")

            base_host = cls._first_non_empty(base_host, config_dict.get("host"))
            base_port = cls._first_non_empty(base_port, config_dict.get("port"))
            base_user = cls._first_non_empty(base_user, config_dict.get("user"))
            base_passwd = cls._first_non_empty(base_passwd, config_dict.get("passwd"))
            base_default_database = cls._first_non_empty(
                base_default_database,
                config_dict.get("default_database"),
            )

        merged_host = cls._first_non_empty(host, base_host)
        merged_port = cls._first_non_empty(port, base_port)
        merged_user = cls._first_non_empty(user, base_user)
        merged_passwd = cls._first_non_empty(passwd, base_passwd)
        merged_default_database = cls._first_non_empty(default_database, base_default_database)

        return cls.from_env(
            host=merged_host,
            port=merged_port,
            user=merged_user,
            passwd=merged_passwd,
            default_database=merged_default_database,
        )

# 默认配置
DEFAULT_MYSQL_CONFIG = MySQLConfig()
