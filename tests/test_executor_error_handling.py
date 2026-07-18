import logging
from unittest.mock import Mock

import pytest
from sqlparse.exceptions import SQLParseError

from lazy_mysql.executor import SQLExecutor
from lazy_mysql.utils.connection_retry import should_retry_connection_error
from lazy_mysql.tools.log_utils import format_sql_for_log


def make_executor():
    executor = object.__new__(SQLExecutor)
    executor.logger = Mock(spec=logging.Logger)
    executor.sql_config = object()
    executor.database = "test_db"
    executor.dict_cursor = False
    executor.mydb = Mock()
    executor.mycursor = Mock(statement="SELECT * FROM users WHERE id = 1")
    executor.close = Mock()
    return executor


def test_should_retry_connection_error_only_retries_known_first_failure():
    error = Exception("Lost connection to MySQL server")

    assert should_retry_connection_error(error, retry_count=0) is True
    assert should_retry_connection_error(error, retry_count=1) is False
    assert should_retry_connection_error(Exception("syntax error"), retry_count=0) is False


def test_handle_connection_error_reconnects_once(monkeypatch):
    executor = make_executor()
    new_db, new_cursor = object(), object()
    reconnect = Mock(return_value=(new_db, new_cursor))
    monkeypatch.setattr("lazy_mysql.executor.connection", reconnect)

    retried = executor._handle_connection_error(
        Exception("Lost connection to MySQL server"), "execute"
    )

    assert retried is True
    assert (executor.mydb, executor.mycursor) == (new_db, new_cursor)
    executor.close.assert_called_once_with()
    reconnect.assert_called_once_with(executor.sql_config, "test_db", dict_cursor=False)


def test_handle_connection_error_logs_rolls_back_closes_and_raises():
    executor = make_executor()

    with pytest.raises(Exception, match="SQL execute failed: syntax error"):
        executor._handle_connection_error(
            Exception("syntax error"),
            "execute",
            sql="select * from users where id = %s",
            params=(1,),
            needs_rollback=True,
        )

    executor.mydb.rollback.assert_called_once_with()
    executor.close.assert_called_once_with()
    assert any(
        call.args[0] == "SQL:\n%s" for call in executor.logger.error.call_args_list
    )
    assert any(
        call.args[0] == "Params: %s" for call in executor.logger.error.call_args_list
    )
    assert any(
        call.args[0] == "Full SQL (with params):\n%s"
        for call in executor.logger.error.call_args_list
    )


def test_format_sql_for_log_returns_raw_sql_when_parser_fails(monkeypatch):
    sql = "select * from users"

    def raise_parse_error(*args, **kwargs):
        raise SQLParseError("invalid SQL")

    monkeypatch.setattr("lazy_mysql.tools.log_utils.sqlparse.format", raise_parse_error)

    assert format_sql_for_log(sql) == sql
