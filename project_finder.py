#!/usr/bin/env python3
"""
LazyMySQL 项目结构检测和修复脚本
自动检测项目结构并创建正确的包结构
"""

import os
import sys
import subprocess
from pathlib import Path

def detect_project_structure():
    """检测当前项目结构"""
    print("=" * 60)
    print("检测项目结构")
    print("=" * 60)
    
    current_dir = Path.cwd()
    print(f"当前目录: {current_dir}")
    
    # 列出当前目录内容
    print("\n当前目录内容:")
    items = list(current_dir.iterdir())
    for item in items:
        if item.is_dir():
            print(f"  📁 {item.name}/")
        else:
            print(f"  📄 {item.name}")
    
    # 检查是否有Python包的迹象
    has_setup_py = (current_dir / "setup.py").exists()
    has_init_py = any((current_dir / item.name / "__init__.py").exists() 
                      for item in items if item.is_dir())
    
    print(f"\n项目特征:")
    print(f"  setup.py: {'✓' if has_setup_py else '✗'}")
    print(f"  包含__init__.py的目录: {'✓' if has_init_py else '✗'}")
    
    return has_setup_py, has_init_py

def find_python_files():
    """查找Python文件"""
    print("\n" + "=" * 60)
    print("查找Python文件")
    print("=" * 60)
    
    current_dir = Path.cwd()
    python_files = list(current_dir.rglob("*.py"))
    
    print(f"找到 {len(python_files)} 个Python文件:")
    for py_file in python_files:
        rel_path = py_file.relative_to(current_dir)
        size = py_file.stat().st_size
        print(f"  {rel_path} ({size} bytes)")
    
    return python_files

def analyze_existing_files():
    """分析现有文件"""
    print("\n" + "=" * 60)
    print("分析现有文件")
    print("=" * 60)
    
    current_dir = Path.cwd()
    
    # 检查关键文件
    key_files = {
        "setup.py": "包安装配置",
        "executor.py": "SQL执行器",
        "__init__.py": "包初始化文件",
        "sql_config.py": "配置文件 (可能缺失)",
    }
    
    found_files = {}
    for filename, description in key_files.items():
        file_path = current_dir / filename
        if file_path.exists():
            print(f"  ✓ {filename} - {description}")
            found_files[filename] = file_path
        else:
            print(f"  ✗ {filename} - {description}")
    
    return found_files

def create_proper_structure():
    """创建正确的包结构"""
    print("\n" + "=" * 60)
    print("创建正确的包结构")
    print("=" * 60)
    
    current_dir = Path.cwd()
    
    # 创建lazy_mysql目录
    lazy_mysql_dir = current_dir / "lazy_mysql"
    lazy_mysql_dir.mkdir(exist_ok=True)
    print(f"✓ 创建目录: {lazy_mysql_dir}")
    
    # 创建子目录
    subdirs = ["utils", "tools"]
    for subdir in subdirs:
        sub_path = lazy_mysql_dir / subdir
        sub_path.mkdir(exist_ok=True)
        print(f"✓ 创建目录: {sub_path}")
        
        # 创建__init__.py
        init_file = sub_path / "__init__.py"
        if not init_file.exists():
            init_file.write_text("")
            print(f"✓ 创建文件: {init_file}")
    
    return lazy_mysql_dir

def move_files_to_package(lazy_mysql_dir):
    """移动文件到包目录"""
    print("\n" + "=" * 60)
    print("移动文件到包目录")
    print("=" * 60)
    
    current_dir = Path.cwd()
    
    # 需要移动的文件映射
    file_mappings = {
        "executor.py": lazy_mysql_dir / "executor.py",
        "__init__.py": lazy_mysql_dir / "__init__.py",
        "utils/connect.py": lazy_mysql_dir / "utils" / "connect.py",
        "utils/insert.py": lazy_mysql_dir / "utils" / "insert.py",
        "utils/select.py": lazy_mysql_dir / "utils" / "select.py",
        "utils/update.py": lazy_mysql_dir / "utils" / "update.py",
        "tools/result_formatter.py": lazy_mysql_dir / "tools" / "result_formatter.py",
        "tools/table_export.py": lazy_mysql_dir / "tools" / "table_export.py",
        "tools/where_clause.py": lazy_mysql_dir / "tools" / "where_clause.py",
    }
    
    moved_files = []
    for source_rel, target_path in file_mappings.items():
        source_path = current_dir / source_rel
        if source_path.exists():
            # 确保目标目录存在
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 如果目标文件不存在，则移动
            if not target_path.exists():
                import shutil
                shutil.copy2(source_path, target_path)
                print(f"✓ 复制: {source_rel} -> {target_path.relative_to(current_dir)}")
                moved_files.append(target_path)
            else:
                print(f"⚠ 跳过: {target_path.relative_to(current_dir)} (已存在)")
        else:
            print(f"✗ 未找到: {source_rel}")
    
    return moved_files

def create_sql_config(lazy_mysql_dir):
    """创建sql_config.py文件"""
    print("\n" + "=" * 60)
    print("创建sql_config.py文件")
    print("=" * 60)
    
    sql_config_path = lazy_mysql_dir / "sql_config.py"
    
    if sql_config_path.exists():
        print(f"⚠ sql_config.py 已存在: {sql_config_path}")
        return sql_config_path
    
    sql_config_content = '''"""
MySQL数据库配置类
"""

class MySQLConfig:
    """MySQL数据库配置类"""
    
    def __init__(self, host='localhost', port=3306, user='root', 
                 passwd='', default_database=None):
        """
        初始化MySQL配置
        
        Args:
            host (str): 数据库主机地址
            port (int): 数据库端口
            user (str): 用户名
            passwd (str): 密码
            default_database (str): 默认数据库名
        """
        self.host = host
        self.port = port
        self.user = user
        self.passwd = passwd
        self.default_database = default_database
    
    def __repr__(self):
        return f"MySQLConfig(host='{self.host}', port={self.port}, user='{self.user}', default_database='{self.default_database}')"


class SQLiteConfig:
    """SQLite数据库配置类（预留）"""
    
    def __init__(self, database_path):
        """
        初始化SQLite配置
        
        Args:
            database_path (str): 数据库文件路径
        """
        self.database_path = database_path
    
    def __repr__(self):
        return f"SQLiteConfig(database_path='{self.database_path}')"


# 默认配置
DEFAULT_MYSQL_CONFIG = MySQLConfig()
'''
    
    try:
        sql_config_path.write_text(sql_config_content, encoding='utf-8')
        print(f"✓ 创建文件: {sql_config_path}")
        return sql_config_path
    except Exception as e:
        print(f"✗ 创建失败: {e}")
        return None

def update_init_file(lazy_mysql_dir):
    """更新__init__.py文件"""
    print("\n" + "=" * 60)
    print("更新__init__.py文件")
    print("=" * 60)
    
    init_path = lazy_mysql_dir / "__init__.py"
    
    init_content = '''from . import sql_config
from . import executor
from .sql_config import MySQLConfig, SQLiteConfig, DEFAULT_MYSQL_CONFIG
from .executor import SQLExecutor

__version__ = "0.1.1"
__author__ = "tinycen"
__email__ = "sky_ruocen@qq.com"

# 提供便捷的导入
__all__ = ['MySQLConfig', 'SQLiteConfig', 'DEFAULT_MYSQL_CONFIG', 'SQLExecutor']
'''
    
    try:
        init_path.write_text(init_content, encoding='utf-8')
        print(f"✓ 更新文件: {init_path}")
        return True
    except Exception as e:
        print(f"✗ 更新失败: {e}")
        return False

def create_setup_py():
    """创建或更新setup.py文件"""
    print("\n" + "=" * 60)
    print("创建/更新setup.py文件")
    print("=" * 60)
    
    current_dir = Path.cwd()
    setup_path = current_dir / "setup.py"
    
    setup_content = '''from setuptools import setup, find_packages

# 读取README文件
try:
    with open('README.md', 'r', encoding='utf-8') as f:
        long_description = f.read()
except FileNotFoundError:
    long_description = 'A lazy MySQL client for Python'

setup(
    name='lazy_mysql',
    version='0.1.1',
    packages=find_packages(),
    install_requires=[
        'mysql-connector-python>=8.0.0',
        'pandas>=1.0.0',
    ],
    author='tinycen',
    author_email='sky_ruocen@qq.com',
    description='A lazy MySQL client for Python',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/tinycen/lazy_mysql',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.7',
    include_package_data=True,
    zip_safe=False,
)
'''
    
    try:
        setup_path.write_text(setup_content, encoding='utf-8')
        print(f"✓ 创建/更新文件: {setup_path}")
        return True
    except Exception as e:
        print(f"✗ 创建/更新失败: {e}")
        return False

def test_package_structure(lazy_mysql_dir):
    """测试包结构"""
    print("\n" + "=" * 60)
    print("测试包结构")
    print("=" * 60)
    
    # 添加当前目录到Python路径进行测试
    current_dir = Path.cwd()
    sys.path.insert(0, str(current_dir))
    
    try:
        import lazy_mysql
        print("✓ import lazy_mysql")
        
        from lazy_mysql import MySQLConfig, SQLExecutor
        print("✓ from lazy_mysql import MySQLConfig, SQLExecutor")
        
        # 测试创建配置
        config = MySQLConfig(host='localhost', user='test')
        print(f"✓ 创建配置成功: {config}")
        
        print("\n🎉 包结构测试通过！")
        return True
        
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        print("\n可能的问题:")
        print("1. 检查所有__init__.py文件是否存在")
        print("2. 检查sql_config.py文件是否正确创建")
        print("3. 检查文件编码是否为UTF-8")
        return False
    finally:
        # 清理sys.path
        if str(current_dir) in sys.path:
            sys.path.remove(str(current_dir))

def install_package():
    """安装包"""
    print("\n" + "=" * 60)
    print("安装包")
    print("=" * 60)
    
    try:
        # 卸载旧版本
        print("卸载旧版本...")
        subprocess.run([sys.executable, "-m", "pip", "uninstall", "lazy-mysql", "-y"], 
                      capture_output=True)
        
        # 安装新版本
        print("安装新版本...")
        result = subprocess.run([sys.executable, "-m", "pip", "install", "-e", "."], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✓ 安装成功")
            print(result.stdout)
            return True
        else:
            print("✗ 安装失败")
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"✗ 安装过程出错: {e}")
        return False

def final_test():
    """最终测试"""
    print("\n" + "=" * 60)
    print("最终测试")
    print("=" * 60)
    
    test_code = '''
import sys
try:
    import lazy_mysql
    from lazy_mysql import MySQLConfig, SQLExecutor
    config = MySQLConfig(host="localhost", user="test", default_database="test_db")
    print("SUCCESS: 包导入和使用正常")
    print(f"版本: {getattr(lazy_mysql, '__version__', '未知')}")
    print(f"配置测试: {config}")
    sys.exit(0)
except Exception as e:
    print(f"FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
'''
    
    try:
        result = subprocess.run([sys.executable, "-c", test_code], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✓ 最终测试通过")
            print(result.stdout)
            return True
        else:
            print("✗ 最终测试失败")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            return False
    except Exception as e:
        print(f"✗ 测试执行失败: {e}")
        return False

def main():
    """主函数"""
    print("LazyMySQL 项目结构检测和修复工具")
    print("=" * 60)
    
    # 检测项目结构
    has_setup, has_init = detect_project_structure()
    
    # 查找Python文件
    python_files = find_python_files()
    
    # 分析现有文件
    found_files = analyze_existing_files()
    
    # 创建正确的包结构
    lazy_mysql_dir = create_proper_structure()
    
    # 移动文件到包目录
    moved_files = move_files_to_package(lazy_mysql_dir)
    
    # 创建sql_config.py
    sql_config_file = create_sql_config(lazy_mysql_dir)
    
    # 更新__init__.py
    init_updated = update_init_file(lazy_mysql_dir)
    
    # 创建setup.py
    setup_created = create_setup_py()
    
    # 测试包结构
    structure_ok = test_package_structure(lazy_mysql_dir)
    
    if structure_ok:
        # 安装包
        installed = install_package()
        
        if installed:
            # 最终测试
            if final_test():
                print("\n🎉🎉🎉 恭喜！LazyMySQL包已成功修复并安装！")
                print("\n现在你可以使用:")
                print("  import lazy_mysql")
                print("  from lazy_mysql import MySQLConfig, SQLExecutor")
            else:
                print("\n❌ 最终测试失败，请检查错误信息")
        else:
            print("\n❌ 安装失败，请手动检查")
    else:
        print("\n❌ 包结构测试失败，请检查文件结构")

if __name__ == "__main__":
    main()
