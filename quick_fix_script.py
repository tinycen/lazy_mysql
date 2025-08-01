#!/usr/bin/env python3
"""
LazyMySQL 快速修复脚本
自动创建缺失的文件并重新安装包
"""

import os
import subprocess
import sys
from pathlib import Path

def run_command(cmd, cwd=None):
    """运行命令"""
    print(f"执行命令: {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
        if result.returncode == 0:
            print("✓ 成功")
            if result.stdout:
                print(f"输出: {result.stdout}")
        else:
            print("✗ 失败")
            if result.stderr:
                print(f"错误: {result.stderr}")
        return result.returncode == 0
    except Exception as e:
        print(f"✗ 执行失败: {e}")
        return False

def create_sql_config():
    """创建sql_config.py文件"""
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

# 默认配置
DEFAULT_MYSQL_CONFIG = MySQLConfig()
'''
    
    # 确保lazy_mysql目录存在
    lazy_mysql_dir = Path("lazy_mysql")
    if not lazy_mysql_dir.exists():
        print("✗ lazy_mysql 目录不存在，请确保在正确的项目根目录运行此脚本")
        return False
    
    # 创建sql_config.py文件
    sql_config_path = lazy_mysql_dir / "sql_config.py"
    
    try:
        with open(sql_config_path, 'w', encoding='utf-8') as f:
            f.write(sql_config_content)
        print(f"✓ 创建文件: {sql_config_path}")
        return True
    except Exception as e:
        print(f"✗ 创建文件失败: {e}")
        return False

def update_init_py():
    """更新__init__.py文件"""
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
    
    init_path = Path("lazy_mysql") / "__init__.py"
    
    try:
        with open(init_path, 'w', encoding='utf-8') as f:
            f.write(init_content)
        print(f"✓ 更新文件: {init_path}")
        return True
    except Exception as e:
        print(f"✗ 更新文件失败: {e}")
        return False

def update_setup_py():
    """更新setup.py文件"""
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
    
    setup_path = Path("setup.py")
    
    try:
        with open(setup_path, 'w', encoding='utf-8') as f:
            f.write(setup_content)
        print(f"✓ 更新文件: {setup_path}")
        return True
    except Exception as e:
        print(f"✗ 更新文件失败: {e}")
        return False

def check_project_structure():
    """检查项目结构"""
    print("\n检查项目结构:")
    
    required_files = [
        "setup.py",
        "lazy_mysql/__init__.py",
        "lazy_mysql/executor.py",
        "lazy_mysql/sql_config.py",
        "lazy_mysql/utils/__init__.py",
        "lazy_mysql/tools/__init__.py",
    ]
    
    all_exist = True
    for file_path in required_files:
        path = Path(file_path)
        if path.exists():
            size = path.stat().st_size
            print(f"  ✓ {file_path} ({size} bytes)")
        else:
            print(f"  ✗ {file_path} (缺失)")
            all_exist = False
    
    return all_exist

def test_import():
    """测试导入"""
    print("\n测试本地导入:")
    
    # 添加当前目录到Python路径
    current_dir = os.getcwd()
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
    
    try:
        import lazy_mysql
        print("✓ import lazy_mysql")
        
        from lazy_mysql import MySQLConfig, SQLExecutor
        print("✓ from lazy_mysql import MySQLConfig, SQLExecutor")
        
        # 测试创建对象
        config = MySQLConfig(host='localhost', user='test')
        print(f"✓ 创建配置: {config}")
        
        return True
    except Exception as e:
        print(f"✗ 导入失败: {e}")
        return False
    finally:
        # 清理sys.path
        if current_dir in sys.path:
            sys.path.remove(current_dir)

def main():
    """主函数"""
    print("LazyMySQL 快速修复工具")
    print("=" * 50)
    
    # 检查当前目录
    if not Path("lazy_mysql").exists():
        print("✗ 当前目录不是LazyMySQL项目根目录")
        print("请切换到包含'lazy_mysql'文件夹的目录")
        return
    
    print("当前目录:", os.getcwd())
    
    # 步骤1: 卸载现有包
    print("\n1. 卸载现有包")
    run_command("pip uninstall lazy-mysql -y")
    
    # 步骤2: 创建缺失文件
    print("\n2. 创建/更新文件")
    create_sql_config()
    update_init_py()
    update_setup_py()
    
    # 步骤3: 检查项目结构
    print("\n3. 检查项目结构")
    if not check_project_structure():
        print("✗ 项目结构不完整，请检查缺失的文件")
        return
    
    # 步骤4: 测试本地导入
    print("\n4. 测试本地导入")
    if not test_import():
        print("✗ 本地导入测试失败")
        return
    
    # 步骤5: 清理旧的构建文件
    print("\n5. 清理旧的构建文件")
    for clean_dir in ["build", "dist", "*.egg-info"]:
        run_command(f"rmdir /s /q {clean_dir}", cwd=".")
    
    # 步骤6: 重新安装
    print("\n6. 重新安装包")
    if run_command("pip install -e ."):
        print("✓ 开发模式安装成功")
        
        # 最终测试
        print("\n7. 最终导入测试")
        if test_final_import():
            print("\n🎉 修复成功！包现在可以正常导入了。")
        else:
            print("\n❌ 修复失败，请检查错误信息。")
    else:
        print("✗ 安装失败")

def test_final_import():
    """最终导入测试"""
    try:
        # 重新启动Python解释器进行测试
        test_code = '''
import sys
try:
    import lazy_mysql
    from lazy_mysql import MySQLConfig, SQLExecutor
    config = MySQLConfig(host="localhost", user="test")
    print("SUCCESS: 导入测试通过")
    print(f"配置: {config}")
    sys.exit(0)
except Exception as e:
    print(f"FAILED: {e}")
    sys.exit(1)
'''
        
        result = subprocess.run([sys.executable, "-c", test_code], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✓ 最终导入测试通过")
            print(result.stdout)
            return True
        else:
            print("✗ 最终导入测试失败")
            print(result.stderr)
            return False
    except Exception as e:
        print(f"✗ 最终测试执行失败: {e}")
        return False

if __name__ == "__main__":
    main()
