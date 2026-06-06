from lazy_mysql import MySQLConfig, SQLExecutor
from lazy_mysql.utils.connect import connection


def test_mysql_config_from_env(monkeypatch):
    monkeypatch.setenv("LAZY_MYSQL_HOST", "db.example.com")
    monkeypatch.setenv("LAZY_MYSQL_PORT", "3307")
    monkeypatch.setenv("LAZY_MYSQL_USER", "app_user")
    monkeypatch.setenv("LAZY_MYSQL_PASSWD", "secret")
    monkeypatch.setenv("LAZY_MYSQL_DATABASE", "app_db")

    config = MySQLConfig.from_env()

    assert config.host == "db.example.com"
    assert config.port == 3307
    assert config.user == "app_user"
    assert config.passwd == "secret"
    assert config.database == "app_db"


def test_mysql_config_resolve_none_reads_from_env(monkeypatch):
    monkeypatch.setenv("LAZY_MYSQL_HOST", "env-host")
    monkeypatch.setenv("LAZY_MYSQL_PASSWD", "env-pass")

    config = MySQLConfig.resolve(None)

    assert isinstance(config, MySQLConfig)
    assert config.host == "env-host"


def test_mysql_config_resolve_accepts_dict():
    config = MySQLConfig.resolve({
        "host": "dict-host",
        "port": "3308",
        "user": "dict-user",
        "passwd": "dict-secret",
        "database": "dict-db",
    })

    assert isinstance(config, MySQLConfig)
    assert config.host == "dict-host"
    assert config.port == 3308
    assert config.user == "dict-user"
    assert config.passwd == "dict-secret"
    assert config.database == "dict-db"


def test_mysql_config_resolve_dict_fills_missing_values_from_env(monkeypatch):
    monkeypatch.setenv("LAZY_MYSQL_HOST", "env-host")
    monkeypatch.setenv("LAZY_MYSQL_PORT", "3310")
    monkeypatch.setenv("LAZY_MYSQL_USER", "env-user")
    monkeypatch.setenv("LAZY_MYSQL_PASSWD", "env-secret")

    config = MySQLConfig.resolve({"database": "param-db"})

    assert config.host == "env-host"
    assert config.port == 3310
    assert config.user == "env-user"
    assert config.passwd == "env-secret"
    assert config.database == "param-db"


def test_sql_executor_accepts_optional_sql_config(monkeypatch):
    captured = {}

    class DummyConnection:
        def close(self):
            pass

    class DummyCursor:
        def close(self):
            pass

    def fake_connection(sql_config=None, database=None, dict_cursor=False):
        captured["sql_config"] = sql_config
        captured["database"] = database
        captured["dict_cursor"] = dict_cursor
        return DummyConnection(), DummyCursor()

    monkeypatch.setenv("LAZY_MYSQL_HOST", "executor-host")
    monkeypatch.setenv("LAZY_MYSQL_PASSWD", "executor-pass")
    monkeypatch.setattr("lazy_mysql.executor.connection", fake_connection)

    executor = SQLExecutor()
    executor.close()

    assert isinstance(captured["sql_config"], MySQLConfig)
    assert captured["sql_config"].host == "executor-host"
    assert captured["database"] is None
    assert captured["dict_cursor"] is False


def test_sql_executor_accepts_dict_sql_config(monkeypatch):
    captured = {}

    class DummyConnection:
        def close(self):
            pass

    class DummyCursor:
        def close(self):
            pass

    def fake_connection(sql_config=None, database=None, dict_cursor=False):
        captured["sql_config"] = sql_config
        captured["database"] = database
        captured["dict_cursor"] = dict_cursor
        return DummyConnection(), DummyCursor()

    monkeypatch.setattr("lazy_mysql.executor.connection", fake_connection)

    executor = SQLExecutor({
        "host": "executor-dict-host",
        "passwd": "executor-secret",
        "database": "executor-db",
    })
    executor.close()

    assert isinstance(captured["sql_config"], MySQLConfig)
    assert captured["sql_config"].host == "executor-dict-host"
    assert captured["sql_config"].passwd == "executor-secret"
    assert captured["sql_config"].database == "executor-db"


def test_connection_does_not_force_database(monkeypatch):
    captured = {}

    class DummyConnection:
        def cursor(self, buffered=True, dictionary=False):
            return object()

    def fake_connect(**kwargs):
        captured.update(kwargs)
        return DummyConnection()

    monkeypatch.delenv("LAZY_MYSQL_DATABASE", raising=False)
    monkeypatch.setenv("LAZY_MYSQL_HOST", "env-host")
    monkeypatch.setenv("LAZY_MYSQL_PASSWD", "env-secret")
    monkeypatch.setattr("lazy_mysql.utils.connect.mysql.connector.connect", fake_connect)

    connection(max_retries=0)

    assert captured["host"] == "env-host"
    assert captured["password"] == "env-secret"
    assert captured["database"] is None


def test_connection_database_argument_overrides_config(monkeypatch):
    captured = {}

    class DummyConnection:
        def cursor(self, buffered=True, dictionary=False):
            return object()

    def fake_connect(**kwargs):
        captured.update(kwargs)
        return DummyConnection()

    monkeypatch.setattr("lazy_mysql.utils.connect.mysql.connector.connect", fake_connect)

    connection({"database": "config-db"}, database="argument-db", max_retries=0)

    assert captured["database"] == "argument-db"
