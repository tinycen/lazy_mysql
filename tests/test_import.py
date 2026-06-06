def test_lazy_mysql_import():
    import lazy_mysql
    from lazy_mysql import MySQLConfig
    assert isinstance(MySQLConfig(), lazy_mysql.MySQLConfig)


def test_mysql_config_import_paths_are_consistent():
    from lazy_mysql import MySQLConfig as RootMySQLConfig
    from lazy_mysql.dataclasses import MySQLConfig as DataclassesMySQLConfig

    assert RootMySQLConfig is DataclassesMySQLConfig
