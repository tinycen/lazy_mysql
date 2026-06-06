"""
MySQL数据库配置类
"""

import os
from typing import Any, ClassVar

from pydantic import BaseModel, field_validator

class MySQLConfig(BaseModel):
    """MySQL数据库配置类"""

    _ENV_HOST: ClassVar[str] = "LAZY_MYSQL_HOST"
    _ENV_PORT: ClassVar[str] = "LAZY_MYSQL_PORT"
    _ENV_USER: ClassVar[str] = "LAZY_MYSQL_USER"
    _ENV_PASSWD: ClassVar[str] = "LAZY_MYSQL_PASSWD"
    _ENV_DATABASE: ClassVar[str] = "LAZY_MYSQL_DATABASE"

    host: str | None = None
    port: int | None = None
    user: str | None = None
    passwd: str | None = None
    database: str | None = None

    @field_validator("host", "user", "passwd", "database", mode="before")
    @classmethod
    def _empty_str_to_none(cls, v: Any) -> Any:
        if v == "":
            return None
        return v

    @field_validator("port", mode="before")
    @classmethod
    def _coerce_port(cls, v: Any) -> Any:
        if v is None or v == "":
            return None
        try:
            return int(v)
        except (TypeError, ValueError) as e:
            raise ValueError(f"MySQL port 必须是整数，收到：{v!r}") from e

    @staticmethod
    def _is_empty_value(value: Any) -> bool:
        return value is None or value == ""

    @classmethod
    def _read_env(cls) -> dict[str, Any]:
        def _get(key: str) -> str | None:
            raw = os.getenv(key)
            if cls._is_empty_value(raw):
                return None
            return raw

        return {
            "host": _get(cls._ENV_HOST),
            "port": _get(cls._ENV_PORT),
            "user": _get(cls._ENV_USER),
            "passwd": _get(cls._ENV_PASSWD),
            "database": _get(cls._ENV_DATABASE),
        }

    @classmethod
    def _first_non_empty(cls, *values: Any) -> Any:
        for value in values:
            if not cls._is_empty_value(value):
                return value
        return None

    @classmethod
    def from_env(cls, *, host=None, port=None, user=None, passwd=None, database=None):
        """从系统环境变量读取MySQL配置；显式传入的字段优先级更高，空值不会覆盖已有值。"""
        env = cls._read_env()

        return cls(
            host=cls._first_non_empty(host, env["host"]),
            port=cls._first_non_empty(port, env["port"]),
            user=cls._first_non_empty(user, env["user"]),
            passwd=cls._first_non_empty(passwd, env["passwd"]),
            database=cls._first_non_empty(database, env["database"]),
        )

    @classmethod
    def from_dict(cls, sql_config):
        """从字典读取MySQL配置；空值不覆盖，缺失字段从环境变量补齐。"""
        return cls.resolve(sql_config)

    @classmethod
    def resolve(cls, sql_config=None, *, host=None, port=None, user=None, passwd=None, database=None):
        """
        统一解析配置来源，优先级：显式参数 > 字典/配置对象 > 环境变量。

        空值（None 或 ''）不会覆盖已有值。
        """
        base_host = None
        base_port = None
        base_user = None
        base_passwd = None
        base_database = None

        config_dict = None
        if isinstance(sql_config, dict):
            config_dict = dict(sql_config)
        elif sql_config is not None:
            base_host = getattr(sql_config, "host", None)
            base_port = getattr(sql_config, "port", None)
            base_user = getattr(sql_config, "user", None)
            base_passwd = getattr(sql_config, "passwd", None)
            base_database = getattr(sql_config, "database", None)

        if config_dict is not None:
            base_host = cls._first_non_empty(base_host, config_dict.get("host"))
            base_port = cls._first_non_empty(base_port, config_dict.get("port"))
            base_user = cls._first_non_empty(base_user, config_dict.get("user"))
            base_passwd = cls._first_non_empty(base_passwd, config_dict.get("passwd"))
            base_database = cls._first_non_empty(
                base_database,
                config_dict.get("database"),
            )

        merged_host = cls._first_non_empty(host, base_host)
        merged_port = cls._first_non_empty(port, base_port)
        merged_user = cls._first_non_empty(user, base_user)
        merged_passwd = cls._first_non_empty(passwd, base_passwd)
        merged_database = cls._first_non_empty(database, base_database)

        return cls.from_env(
            host=merged_host,
            port=merged_port,
            user=merged_user,
            passwd=merged_passwd,
            database=merged_database,
        )
# 默认配置
DEFAULT_MYSQL_CONFIG = MySQLConfig.resolve()
