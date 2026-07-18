"""MySQL 连接异常的重试判定。"""

# 仅匹配已知的连接中断或超时错误；实际重连次数由调用方控制。
_RETRYABLE_CONNECTION_ERRORS = (
    "Lost connection to MySQL server",
    "The Read Operation timed out",
    "TimeoutError",
    "connection timeout",
)


def should_retry_connection_error(error, retry_count: int) -> bool:
    """在首次遇到可重试的连接异常时返回 ``True``。"""
    if retry_count != 0:
        return False

    error_message = str(error).lower()
    return any(
        keyword.lower() in error_message
        for keyword in _RETRYABLE_CONNECTION_ERRORS
    )
