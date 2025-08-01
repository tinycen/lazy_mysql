def test_lazy_mysql_import():
    import lazy_mysql
    from lazy_mysql import MySQLConfig
    assert isinstance(MySQLConfig(), lazy_mysql.MySQLConfig)
