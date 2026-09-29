# SQL工具函数
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


# ---------------------------------------------------------------------------
# 词法状态机：注释剥离 / 词法区间标记
# ---------------------------------------------------------------------------

# 词法单元类型
LEX_STRING = "string"          # '...' / "..." 字符串字面量
LEX_IDENTIFIER = "identifier"  # `...` 反引号标识符
LEX_COMMENT = "comment"        # 被剥离的注释区间（/*! */ 与 /*+ */ 不计入）
LEX_EXECUTABLE = "executable"  # /*! ... */ 可执行注释、/*+ ... */ 优化器 Hint（原样保留）

# 行注释起点允许的后续字符（MySQL 规则：-- 后必须是空白/控制字符或 EOF）
_LINE_COMMENT_FOLLOW = frozenset(" \t\r\n\x0b\f\0")


def _scan_sql(sql):
    """
    单次逐字符扫描 SQL，产出词法区间列表。

    :param sql: SQL 文本
    :return: list[(start, end, kind)]，kind 为 LEX_STRING / LEX_IDENTIFIER /
             LEX_COMMENT / LEX_EXECUTABLE 之一；区间左闭右开、互不重叠、按序排列。
             不在任何区间内的字符即为普通 SQL 代码。
    """
    spans = []
    n = len(sql)
    i = 0
    while i < n:
        ch = sql[i]

        # 字符串 / 标识符
        if ch in ("'", '"', '`'):
            kind = LEX_IDENTIFIER if ch == '`' else LEX_STRING
            start = i
            i += 1
            while i < n:
                c = sql[i]
                if c == '\\' and ch != '`':
                    # MySQL 默认模式下的反斜杠转义（\'、\"、\\ 等），消费 2 字符。
                    # 注：sql_mode=NO_BACKSLASH_ESCAPES 时该假设不成立，属已知限制。
                    i += 2
                    continue
                if c == ch:
                    if i + 1 < n and sql[i + 1] == ch:
                        i += 2  # 双写转义（''、""、``）
                        continue
                    i += 1
                    break
                i += 1
            spans.append((start, i, kind))
            continue

        # -- 行注释：仅当第 3 个字符是空白/控制字符或已到 EOF 时才是注释
        if ch == '-' and sql.startswith('--', i):
            nxt = sql[i + 2] if i + 2 < n else ''
            if nxt == '' or nxt in _LINE_COMMENT_FOLLOW:
                start = i
                j = sql.find('\n', i + 2)
                i = n if j == -1 else j
                spans.append((start, i, LEX_COMMENT))
                continue
            i += 1  # a--b 等双负号/减法场景，不是注释
            continue

        # # 行注释（MySQL 扩展，无需后跟空格）
        if ch == '#':
            start = i
            j = sql.find('\n', i + 1)
            i = n if j == -1 else j
            spans.append((start, i, LEX_COMMENT))
            continue

        # 块注释
        if ch == '/' and sql.startswith('/*', i):
            start = i
            j = sql.find('*/', i + 2)
            i = n if j == -1 else j + 2
            if sql.startswith('/*!', start) or sql.startswith('/*+', start):
                # 版本条件可执行注释 / 优化器 Hint：原样保留
                spans.append((start, i, LEX_EXECUTABLE))
            else:
                spans.append((start, i, LEX_COMMENT))
            continue

        i += 1
    return spans


def strip_sql_comments(sql):
    """
    剥离 SQL 注释，注释区间以「等长空格」替换（换行符保留），行列号不漂移。

    规则：
    - -- 行注释（须后跟空白/控制字符或 EOF，a--b 不视为注释）、# 行注释、块注释均被剥离
    - '...'、"..."、`...` 内的内容原样保留，不识别注释起点
    - /*! ... */ 可执行注释、/*+ ... */ 优化器 Hint 原样保留
    - 幂等：剥离后的文本再次调用结果不变

    :param sql: SQL 文本
    :return: (stripped_text, comment_spans)
        comment_spans 为 [(start, end, comment_text), ...]，供 lint 使用
    """
    spans = _scan_sql(sql)
    comment_spans = [(s, e, sql[s:e]) for s, e, k in spans if k == LEX_COMMENT]
    if not comment_spans:
        return sql, []

    chars = list(sql)
    for s, e, _ in comment_spans:
        for pos in range(s, e):
            if chars[pos] != '\n':
                chars[pos] = ' '
    return ''.join(chars), comment_spans


# ---------------------------------------------------------------------------
# 占位符预检
# ---------------------------------------------------------------------------

# 驱动正则（mysql.connector.cursor）为 bytes 模式；这里复用其 pattern 编译 str 版本，
# 以便报告字符级行列号。mapping 正则的 pattern 依赖 re.VERBOSE（pattern 内含空白与换行）。
try:
    from mysql.connector.cursor import RE_PY_PARAM as _DRV_RE_PY_PARAM
    from mysql.connector.cursor import RE_PY_MAPPING_PARAM as _DRV_RE_PY_MAPPING_PARAM
    _RE_PY_PARAM = re.compile(_DRV_RE_PY_PARAM.pattern.decode())
    _RE_PY_MAPPING_PARAM = re.compile(_DRV_RE_PY_MAPPING_PARAM.pattern.decode(), re.VERBOSE)
except Exception:  # pragma: no cover - 驱动内部结构变更时的兜底
    _RE_PY_PARAM = re.compile(r"(%s)")
    _RE_PY_MAPPING_PARAM = re.compile(
        r"%\((?P<mapping_key>[^)]+)\)(?P<conversion_type>[diouxXeEfFgGcrs%])"
    )


@dataclass(frozen=True)
class SQLIssue:
    """占位符预检 / lint 产出的单个问题。"""
    line: int
    column: int
    end_column: int
    severity: Literal["error", "warning"]
    code: str      # E101-E104 / W101 / W103-W105
    message: str
    snippet: str   # 命中位置所在行的原文


class SQLPlaceholderError(ValueError):
    """占位符预检失败。issues 属性携带全部 error 级 SQLIssue。"""

    def __init__(self, issues):
        self.issues = list(issues)
        detail = "\n".join(
            f"  [{i.code}] 第{i.line}行第{i.column}列: {i.message}" for i in self.issues
        )
        super().__init__(f"SQL 占位符预检失败，共 {len(self.issues)} 个问题：\n{detail}")


def _offset_to_line_col(text, offset):
    """将字符偏移转换为 1-based (行号, 列号)。"""
    line = text.count('\n', 0, offset) + 1
    line_start = text.rfind('\n', 0, offset) + 1
    return line, offset - line_start + 1


def _line_snippet(text, offset):
    """取 offset 所在行的原文（去除换行符）。"""
    line_start = text.rfind('\n', 0, offset) + 1
    line_end = text.find('\n', offset)
    if line_end == -1:
        line_end = len(text)
    return text[line_start:line_end]


def _make_issue(text, start, end, severity, code, message):
    line, col = _offset_to_line_col(text, start)
    _, end_col = _offset_to_line_col(text, end)
    return SQLIssue(
        line=line, column=col, end_column=end_col,
        severity=severity, code=code, message=message,
        snippet=_line_snippet(text, start),
    )


def _in_spans(pos, spans, kinds):
    """判断偏移 pos 是否落在指定类型的词法区间内。"""
    return any(k in kinds and s <= pos < e for s, e, k in spans)


def validate_placeholders(sql, params=None):
    """
    对 SQL 做占位符预检，复用驱动自身的占位符正则与替换语义，不抛异常只返回 issues。

    与 mysql-connector-python 行为对齐的关键点：
    - params 为空（None/()/[]/{}）时不做任何检查（驱动此时不扫描占位符）
    - 位置参数按方向分别判定：占位符多于参数 → E101；少于参数 → E102
    - 字典参数：占位符键缺失 → E103；驱动不支持的转换类型（如 %(name)d）→ E104；
      params 中多余的键不检查（驱动静默忽略）
    - 字符串字面量内的占位符 → W105（驱动不看引号仍会替换，仅提示）
    - 其余非占位符 %（裸 %、%Y、%% 等）→ W103

    :param sql: SQL 文本（对 .sql 文件路径来源的文本，注释通常已被剥离；
                对内联 SQL，注释区间内的 % 不参与 W103 扫描）
    :param params: 将传给 execute 的参数（tuple/list/dict）
    :return: list[SQLIssue]，空列表表示未发现问题
    """
    if params is None or params in ((), [], {}):
        return []

    spans = _scan_sql(sql)
    executable_kinds = (LEX_EXECUTABLE,)
    issues = []

    if isinstance(params, dict):
        issues = _validate_mapping(sql, params, spans, executable_kinds)
    elif isinstance(params, tuple) or (
        isinstance(params, list) and params and not isinstance(params[0], (dict, tuple, list))
    ):
        # 元组 / 标量列表 → 位置参数
        issues = _validate_positional(sql, params, spans, executable_kinds)
    elif isinstance(params, list) and params and isinstance(params[0], dict):
        # 批量 list[dict]：对每条 dict 分别校验（executemany 会逐条替换，任何一条缺键都会报错）
        issues = []
        for item in params:
            issues.extend(_validate_mapping(sql, item, spans, executable_kinds))
    elif isinstance(params, list) and params:
        # 批量 list[tuple|list]：对每条分别做位置校验
        issues = []
        for item in params:
            issues.extend(_validate_positional(sql, item, spans, executable_kinds))
    # params 为 [] 已在入口拦截；其他非法类型由 execute() 自己报错，预检不重复

    issues.extend(_scan_bare_percent(sql, spans, executable_kinds))
    return issues


def _validate_positional(sql, params, spans, executable_kinds):
    """位置参数（%s）校验：数量按方向分别判定，字符串内占位符记 W105。"""
    issues = []
    matches = [
        m for m in _RE_PY_PARAM.finditer(sql)
        if not _in_spans(m.start(), spans, executable_kinds)
    ]
    n_placeholders = len(matches)
    n_params = len(params)

    for m in matches:
        if _in_spans(m.start(), spans, (LEX_STRING,)):
            issues.append(_make_issue(
                sql, m.start(), m.end(), "warning", "W105",
                "字符串字面量内出现占位符 '%s'：驱动不看引号仍会对其替换；"
                "若为 DATE_FORMAT 等时间格式串，请将格式串整体作为参数传入",
            ))

    if n_placeholders > n_params:
        m = matches[n_params]
        issues.append(_make_issue(
            sql, m.start(), m.end(), "error", "E101",
            f"SQL 中包含 {n_placeholders} 个 '%s' 占位符，但仅提供了 {n_params} 个参数"
            f"（驱动将报 Not enough parameters for the SQL statement）；"
            f"请检查是否有占位符被误写入字符串字面量",
        ))
    elif n_placeholders < n_params:
        issues.append(_make_issue(
            sql, 0, 0, "error", "E102",
            f"SQL 中仅有 {n_placeholders} 个 '%s' 占位符，但提供了 {n_params} 个参数"
            f"（驱动将报 Not all parameters were used in the SQL statement）",
        ))
    return issues


def _validate_mapping(sql, params, spans, executable_kinds):
    """命名参数（%(name)s）校验：缺键 E103，驱动不支持的转换类型 E104。"""
    issues = []
    for m in _RE_PY_MAPPING_PARAM.finditer(sql):
        if _in_spans(m.start(), spans, executable_kinds):
            continue
        key = m.group("mapping_key")
        conv = m.group("conversion_type")
        if conv == '%':
            continue  # %(...)% 是字面量百分号
        if conv != 's':
            issues.append(_make_issue(
                sql, m.start(), m.end(), "error", "E104",
                f"占位符 '%({key}){conv}' 使用了驱动不支持的转换类型 '{conv}'"
                f"（mysql-connector 仅支持 's'），请改为 %({key})s",
            ))
        if key not in params:
            issues.append(_make_issue(
                sql, m.start(), m.end(), "error", "E103",
                f"占位符 '%({key}){conv}' 在 params 中缺少键 '{key}'"
                f"（驱动将报 Failed processing pyformat-parameters）",
            ))
        if _in_spans(m.start(), spans, (LEX_STRING,)):
            issues.append(_make_issue(
                sql, m.start(), m.end(), "warning", "W105",
                f"字符串字面量内出现占位符 '%({key}){conv}'：驱动不看引号仍会对其替换",
            ))
    return issues


def _scan_bare_percent(sql, spans, executable_kinds):
    """扫描未参与占位符匹配的 %：注释与 /*! */ /*+ */ 区间内的跳过（降噪）。"""
    covered = [False] * len(sql)
    for m in _RE_PY_PARAM.finditer(sql):
        for pos in range(m.start(), m.end()):
            covered[pos] = True
    for m in _RE_PY_MAPPING_PARAM.finditer(sql):
        for pos in range(m.start(), m.end()):
            covered[pos] = True

    issues = []
    for m in re.finditer('%', sql):
        pos = m.start()
        if covered[pos]:
            continue
        if _in_spans(pos, spans, (LEX_COMMENT, LEX_EXECUTABLE)):
            continue
        nxt = sql[pos + 1] if pos + 1 < len(sql) else ''
        if nxt == '%':
            message = "'%%' 不是 mysql-connector 的转义写法，需要字面量 % 请通过参数传入"
        else:
            message = (
                "非占位符 '%' 字符：当前驱动下安全，但换用其他驱动或手动 % 插值时危险，"
                "建议通过参数传入"
            )
        issues.append(_make_issue(sql, pos, pos + 1, "warning", "W103", message))
    return issues


# ---------------------------------------------------------------------------
# lint 工具（入库前 / CI）
# ---------------------------------------------------------------------------

def lint_sql_text(sql):
    """
    对 SQL 文本做静态检查（不依赖 params）：
    - 注释中出现 % → W101；出现 { 或 } → W104（对应 SQL 文件编写红线）
    - 剥离注释后的可执行文本中，字符串内占位符 → W105、非占位符 % → W103

    :param sql: SQL 文本
    :return: list[SQLIssue]
    """
    stripped, comment_spans = strip_sql_comments(sql)
    issues = []
    for s, e, comment in comment_spans:
        for m in re.finditer(r'[%{}]', comment):
            ch = m.group(0)
            if ch == '%':
                code, message = "W101", "注释中出现 '%'（含 %s / %(name)s 会被驱动计入占位符，请勿在注释中书写）"
            else:
                code, message = "W104", "注释中出现 '{' / '}'（下游若对 SQL 做 format 模板化会被当作占位符，请勿在注释中书写）"
            issues.append(_make_issue(sql, s + m.start(), s + m.end(), "warning", code, message))

    spans = _scan_sql(stripped)
    executable_kinds = (LEX_EXECUTABLE,)
    for regex in (_RE_PY_PARAM, _RE_PY_MAPPING_PARAM):
        for m in regex.finditer(stripped):
            if _in_spans(m.start(), spans, executable_kinds):
                continue
            if _in_spans(m.start(), spans, (LEX_STRING,)):
                issues.append(_make_issue(
                    stripped, m.start(), m.end(), "warning", "W105",
                    "字符串字面量内出现占位符，若为 DATE_FORMAT 等时间格式串请整体参数化",
                ))
    issues.extend(_scan_bare_percent(stripped, spans, executable_kinds))
    return issues


def lint_sql_file(sql_path):
    """
    对单个 .sql 文件做静态检查。

    :param sql_path: .sql 文件路径
    :return: list[SQLIssue]
    """
    text = Path(sql_path).read_text(encoding='utf-8')
    return lint_sql_text(text)


def lint_sql_dir(dir_path, pattern="**/*.sql"):
    """
    递归检查目录下的 .sql 文件。

    :param dir_path: 目录路径
    :param pattern: glob 模式，默认 **/*.sql
    :return: list[(Path, list[SQLIssue])]，仅包含有问题的文件
    """
    results = []
    for f in sorted(Path(dir_path).rglob(pattern)):
        issues = lint_sql_file(f)
        if issues:
            results.append((f, issues))
    return results


# ---------------------------------------------------------------------------
# SQL 文件载入
# ---------------------------------------------------------------------------

# 载入sql文件
def load_sql( sql_path , strip_comments = True ) :
    """
    从文件读取 SQL 内容（UTF-8，去除首尾空白）。

    :param sql_path: SQL 文件路径
    :param strip_comments: 是否剥离注释（默认 True）。剥离后注释中的 %s / %(name)s
        不会再被 mysql-connector 误计为占位符；/*! */ 与 /*+ */ 原样保留。
    :return: SQL 内容字符串
    """
    with open(sql_path, 'r', encoding='utf-8') as f:
        sql = f.read().strip()
    if strip_comments:
        sql = strip_sql_comments(sql)[0].strip()
    return sql


# 智能解析 SQL 参数：自动判断是 SQL 文本还是 .sql 文件路径
def resolve_sql(sql, strip_comments=True):
    """
    智能解析 SQL 参数：自动判断是 SQL 文本还是 .sql 文件路径

    检测规则：
    1. os.PathLike 对象（如 pathlib.Path） → 视为文件路径，读取文件内容
    2. 字符串且以 .sql 结尾（不区分大小写） → 视为文件路径，读取文件内容
    3. 其他字符串 → 视为 SQL 文本，原样返回

    :param sql: SQL语句字符串 或 .sql 文件路径（支持 str / os.PathLike）
    :param strip_comments: 仅对文件路径加载生效：是否剥离注释（默认 True）；
        对已是 SQL 文本的输入无效果（保持幂等契约，不做静默改写）
    :return: 解析后的 SQL 语句字符串
    """
    if isinstance(sql, os.PathLike):
        return load_sql(sql, strip_comments=strip_comments)
    if isinstance(sql, str) and sql.strip().lower().endswith('.sql'):
        return load_sql(sql, strip_comments=strip_comments)
    if not isinstance(sql, str):
        raise TypeError(f"SQL 必须是字符串或 .sql 文件路径，收到 {type(sql).__name__}")
    return sql


# 构建SQL条件限制语句
def add_limit( column , value , column_alias = "" , add_and = True , operator = "=" ) : 
    """
    构建SQL条件限制语句，支持多种比较运算符
    
    :param column: 字段名
    :param value: 字段值，如果为"", "all", "null"则返回空字符串
    :param column_alias: 表别名，可选
    :param add_and: 是否添加AND前缀
    :param operator: 比较运算符，支持 =, !=, <>, >, >=, <, <=, LIKE, NOT LIKE, IN, NOT IN
    :return: SQL条件语句片段
    
    :example:
        >>> add_limit('status', 'active')
        "AND status = 'active'"
        >>> add_limit('age', 18, 'u', operator='>=')
        "AND u.age >= 18"
        >>> add_limit('name', '%张%', operator='LIKE')
        "AND name LIKE '%张%'"
        >>> add_limit('type', ['admin', 'user'], operator='IN')
        "AND type IN ('admin', 'user')"
    """

    if value in ("", "all", "null", None, [], ()) : 
        return "" 

    if column_alias != "" : 
        column_alias += "." 
    
    # 处理IN/NOT IN运算符的特殊情况
    if operator.upper() in ('IN', 'NOT IN') and isinstance(value, (list, tuple)):
        value_str = ', '.join([str(v) if isinstance(v, (int, float)) else f"'{v}'" for v in value])
        condition = f"{column_alias}{column} {operator.upper()} ({value_str})"
    else:
        # 处理数字类型，不需要加单引号
        if isinstance(value, (int, float)):
            condition = f"{column_alias}{column} {operator.upper()} {value}"
        else:
            condition = f"{column_alias}{column} {operator.upper()} '{value}'"
    
    if add_and : 
        return f"AND {condition}" 
    else : 
        return condition
