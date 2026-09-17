# 修复 delete/update 在 self\_close=True 时 rowcount 报 AttributeError 的 bug

## 问题描述 / 需求背景

* 下游开发者（Django 项目，Python 3.14，lazy\_mysql 安装自 PyPI 的 site-packages）调用 `executor.delete(table_name, conditions, commit=True, self_close=True)` 时抛出异常：

  ```
  File ".../site-packages/lazy_mysql/crud/delete.py", line 25, in delete
      return executor.mycursor.rowcount
  Exception Type:    AttributeError
  Exception Value:   'NoneType' object has no attribute 'rowcount'
  ```

* 关键现象：**数据实际已被成功删除**，但返回受影响行数时报错。即删除/提交均已完成，只是事后读取 `rowcount` 失败。

* 触发条件：`self_close=True`（调用方要求执行后自动关闭连接）。

## 原因分析

通过阅读本项目 `executor.py` 与 mysql-connector-python 源码（本机安装路径 `...\site-packages\mysql\connector\`），确认根因有两层：

### 第一层（直接原因）：close() 将 mycursor 置为 None

`SQLExecutor.close()`（`lazy_mysql/executor.py` 原 L50-L51）在关闭游标和连接后：

```python
self.mycursor = None
self.mydb = None
```

而 `crud/delete.py` 原 L24-L25 的调用顺序是：

```python
executor.execute(sql, params, commit, self_close)   # self_close=True 时内部已执行 close()
return executor.mycursor.rowcount                   # 此时 mycursor 已是 None → AttributeError
```

### 第二层（更隐蔽）：即使保留游标引用也不行

阅读连接器源码发现，纯 Python 游标 `MySQLCursor.close()`（`cursor.py` L259-L271）会调用 `_reset_result()`，而游标构造函数中 `_rowcount` 初始值即 `-1`（L214）。也就是说 **`rowcount`** **必须在游标 close 之前读取**，close 之后要么对象为 None，要么值被重置为 -1。

DML 执行后 `_rowcount` 的赋值来源：`_handle_result()` → `self._rowcount = res["affected_rows"]`（cursor.py L321），DELETE 成功后该值已就位，因此"数据删成功但读行数报错"与源码行为完全吻合。

C 扩展游标 `CMySQLCursor.rowcount`（cursor\_cext.py L499-L503）在 `_rowcount == -1` 时回退返回 `_affected_rows`，行为略有差异，但同样依赖"close 前读取"。

### 影响面排查

* 全局搜索 `rowcount`：仅 `crud/delete.py:25` 和 `crud/update.py:45` 两处在 `execute(self_close=...)` 之后访问 `executor.mycursor.rowcount`，**update.py 存在一模一样的 bug**。

* 全局搜索 `\.execute\(`：共 25 处内部调用（executor.py 5 处、crud 10 处、table/export.py 10 处），其余调用方均为语句式调用（忽略返回值）或 `self_close=False`，不受影响。

## 解决方案

核心思路：**让** **`execute()`** **在执行** **`close()`** **之前读取** **`rowcount`** **并作为返回值返回**，crud 层直接使用该返回值。

### 1. `lazy_mysql/executor.py`（execute 方法，现 L252-L260）

```python
        except Exception as e :
            if self._handle_connection_error(e, "execute", retry_count, sql=sql, params=params, needs_rollback=commit):
                return self.execute(sql, params, commit, self_close, retry_count=1)

        # 必须在 close() 之前读取 rowcount：
        # 1. self.close() 会将 mycursor 置为 None，之后再访问 rowcount 会抛 AttributeError
        # 2. mysql-connector 纯 Python 游标的 close() 会调用 _reset_result()，将 _rowcount 重置为 -1
        rowcount = self.mycursor.rowcount if self.mycursor is not None else -1

        # 关闭连接
        if self_close:
            self.close()
        return rowcount
```

同时在 `execute()` docstring 补充返回值说明（现 L208-L209）：

```
:return: 受影响的行数（int）。在关闭连接前读取，因此 self_close=True 时仍可正确返回；
    SELECT 等未产生影响行的语句可能返回 -1
```

### 2. `lazy_mysql/crud/delete.py`（现 L23-L24）

```python
    # 执行SQL并返回受影响行数（execute 会在关闭连接前读取 rowcount，避免 self_close 后 mycursor 为 None 报错）
    return executor.execute(sql, params, commit, self_close)
```

### 3. `lazy_mysql/crud/update.py`（现 L43-L44）

```python
    # 执行SQL并返回受影响行数（execute 会在关闭连接前读取 rowcount，避免 self_close 后 mycursor 为 None 报错）
    return executor.execute(sql, params, commit, self_close)
```

## 影响评估（execute 为底层基础方法，已逐调用点核对）

结论：**改动安全，无破坏性影响**。

| 调用方                                         | 用法                                  | 影响               |
| ------------------------------------------- | ----------------------------------- | ---------------- |
| `crud/delete.py`                            | `return executor.execute(...)`      | 正向受益（本次修复目标）     |
| `crud/update.py`                            | `return executor.execute(...)`      | 正向受益（同 bug 一并修复） |
| `crud/insert.py` 6 处、`crud/batch_update.py` | 语句式调用，忽略返回值                         | 无影响              |
| `table/export.py` 10 处                      | `self_close=False`，忽略返回值            | 无影响              |
| `tools/result_formatter.py` L50             | `self_close=False`，之后仍 `fetchall()` | 无影响              |
| `executor.py` 内部重试递归                        | `return self.execute(...)`          | 返回值语义一致，正确向上传递   |

要点说明：

1. **返回值变化 None → int**：原 `execute()` 正常路径隐式返回 `None`，成功与否靠异常机制而非返回值判断，变为返回行数是纯增量增强，向后兼容。
2. **执行路径与异常路径未动**：修改只插在 try/except 之后、`close()` 之前，SQL 执行、参数处理、commit、重连重试逻辑一行未改。
3. **读取 rowcount 无副作用**：`rowcount` 是纯属性读取（cursor\_cext.py L499-L503），不消耗结果集、不发起网络 IO，不影响 `result_formatter.py` 后续的 `fetchall()`。
4. **唯一语义变化**：外部直接调用 `execute()` 执行 SELECT 时返回 `-1`（非缓冲游标 fetch 前行数未知）；内部无任何调用方在 SELECT 后读取返回值。
5. **既有语义（非本次引入）**：commit 失败触发重连时递归会重发整条 SQL，第二次 rowcount 可能为 0；本次修改只是让其"可见"，未改变重试行为。

## 验证结果

* 对三个修改文件执行 `python -m py_compile`，编译检查全部通过（无语法错误）。

* 按用户规则，本项目不额外编写测试脚本/使用示例；正确性由根因分析（连接器源码逐行比对）支撑：

  * DML 执行成功后 `_rowcount = res["affected_rows"]` 已就位；

  * 读取发生在 `close()` 之前，避开 None 引用与 -1 重置两个坑。

## 后续事项

* 当前包版本为 `0.7.0`（`lazy_mysql/.version`）。要让 PyPI 用户拿到修复，需升级版本号并重新构建发布，是否升级由用户决定。

## 相关文件

| 文件                                           | 说明                                                          |
| -------------------------------------------- | ----------------------------------------------------------- |
| `lazy_mysql/executor.py`                     | `execute()` 在 close 前读取并返回 rowcount；docstring 补充 :return 说明 |
| `lazy_mysql/crud/delete.py`                  | 改用 `execute()` 返回值，删除对 `executor.mycursor.rowcount` 的直接访问   |
| `lazy_mysql/crud/update.py`                  | 同 delete.py，修复相同 bug                                        |
| `mysql/connector/cursor.py`（第三方源码，只读分析）      | 确认 `close()` → `_reset_result()` 会将 `_rowcount` 重置为 -1      |
| `mysql/connector/cursor_cext.py`（第三方源码，只读分析） | 确认 C 扩展游标 rowcount 属性行为                                     |

