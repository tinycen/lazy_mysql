# 基础设施层：连接管理与重试逻辑。
# 这些符号仅供包内部使用，不应出现在顶层 lazy_mysql.__all__ 中，
# 因此本模块不定义 __all__。
from .connect import connection
from .connection_retry import should_retry_connection_error
