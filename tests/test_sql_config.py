from lazy_mysql import MySQLConfig, SQLExecutor


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
    assert config.default_database == "app_db"


def test_mysql_config_from_env_supports_legacy_password_and_database_names(monkeypatch):
    monkeypatch.delenv("LAZY_MYSQL_PASSWD", raising=False)
    monkeypatch.delenv("LAZY_MYSQL_DATABASE", raising=False)
    monkeypatch.setenv("LAZY_MYSQL_PASSWD", "legacy_secret")
    monkeypatch.setenv("LAZY_MYSQL_DEFAULT_DATABASE", "legacy_db")

    config = MySQLConfig.from_env()

    assert config.passwd == "legacy_secret"
    assert config.default_database == "legacy_db"


def test_mysql_config_resolve_none_reads_from_env(monkeypatch):
    monkeypatch.setenv("LAZY_MYSQL_HOST", "env-host")

    config = MySQLConfig.resolve(None)

    assert isinstance(config, MySQLConfig)
    assert config.host == "env-host"


def test_mysql_config_resolve_accepts_dict():
    config = MySQLConfig.resolve({
        "host": "dict-host",
        "port": "3308",
        "user": "dict-user",
        "passwd": "dict-secret",
        "default_database": "dict-db",
    })

    assert isinstance(config, MySQLConfig)
    assert config.host == "dict-host"
    assert config.port == 3308
    assert config.user == "dict-user"
    assert config.passwd == "dict-secret"
    assert config.default_database == "dict-db"


def test_mysql_config_resolve_accepts_dict_aliases():
    config = MySQLConfig.resolve({
        "host": "alias-host",
        "password": "alias-secret",
        "database": "alias-db",
    })

    assert config.host == "alias-host"
    assert config.passwd == "alias-secret"
    assert config.default_database == "alias-db"


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
        "password": "executor-secret",
        "database": "executor-db",
    })
    executor.close()

    assert isinstance(captured["sql_config"], MySQLConfig)
    assert captured["sql_config"].host == "executor-dict-host"
    assert captured["sql_config"].passwd == "executor-secret"
    assert captured["sql_config"].default_database == "executor-db"
