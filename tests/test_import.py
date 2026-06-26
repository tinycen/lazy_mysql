import importlib
import inspect

import lazy_mysql


def test_lazy_mysql_import():
    from lazy_mysql import MySQLConfig
    assert isinstance(MySQLConfig(), lazy_mysql.MySQLConfig)


def test_mysql_config_import_paths_are_consistent():
    from lazy_mysql import MySQLConfig as RootMySQLConfig
    from lazy_mysql.models import MySQLConfig as ModelsMySQLConfig

    assert RootMySQLConfig is ModelsMySQLConfig


def test_all_exports_are_importable():
    """确保 __all__ 中声明的每个符号都能从 lazy_mysql 正常导入"""
    for name in lazy_mysql.__all__:
        obj = getattr(lazy_mysql, name)
        assert obj is not None, f"lazy_mysql.{name} 导入结果为 None"


def test_all_exports_match_all_submodules():
    """确保各子模块 __all__ 中的符号都已汇总到顶层 __all__"""
    top_level_all = set(lazy_mysql.__all__)

    submodule_names = ['models', 'tools', 'utils']
    for mod_name in submodule_names:
        mod = importlib.import_module(f"lazy_mysql.{mod_name}")
        if hasattr(mod, '__all__'):
            for symbol in mod.__all__:
                assert symbol in top_level_all, (
                    f"lazy_mysql.{mod_name}.__all__ 中的 '{symbol}' "
                    f"未出现在顶层 lazy_mysql.__all__ 中"
                )


def test_no_extra_exports():
    """确保顶层 __all__ 中的符号确实存在于模块中"""
    for name in lazy_mysql.__all__:
        assert hasattr(lazy_mysql, name), (
            f"lazy_mysql.__all__ 声明了 '{name}'，但模块中不存在该属性"
        )


def test_public_classes_are_types():
    """确保公开的类确实是类（而非意外变成了其他类型）"""
    class_names = ['MySQLConfig', 'FetchConfig', 'SQLExecutor']
    for name in class_names:
        obj = getattr(lazy_mysql, name)
        assert inspect.isclass(obj), f"lazy_mysql.{name} 应该是一个类"


def test_public_functions_are_callable():
    """确保公开的函数确实可调用"""
    func_names = [
        'insert', 'upsert', 'select', 'exists',
        'update', 'batch_update', 'delete', 'merge_update_lists',
        'add_limit', 'load_sql', 'resolve_sql',
    ]
    for name in func_names:
        obj = getattr(lazy_mysql, name)
        assert callable(obj), f"lazy_mysql.{name} 应该是可调用的"


def test_all_exports_are_unique():
    """确保 __all__ 中没有重复的符号"""
    assert len(lazy_mysql.__all__) == len(set(lazy_mysql.__all__)), (
        "lazy_mysql.__all__ 中存在重复的符号"
    )
