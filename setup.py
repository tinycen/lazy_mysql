from pathlib import Path
from setuptools import setup, find_packages

# 读取README文件    
try:
    with open('README.md', 'r', encoding='utf-8') as f:
        long_description = f.read()
except FileNotFoundError:
    long_description = 'A lazy MySQL client for Python'

__version__ = (Path(__file__).parent / "lazy_mysql" / ".version").read_text().strip()

with open('requirements.txt', 'r', encoding='utf-8') as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]

setup(
    name='lazy_mysql',
    version=f'v{__version__}',
    packages=find_packages(),
    install_requires=requirements,
    author='tinycen',
    author_email='sky_ruocen@qq.com',
    description='A lazy MySQL client for Python that simplifies database operations with intuitive methods for CRUD operations, automatic connection management, and result formatting. Features include easy-to-use SELECT, INSERT, UPDATE, DELETE operations with pandas DataFrame support, where clause builders, and table export capabilities.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/tinycen/lazy_mysql',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.10',
    include_package_data=True,
    zip_safe=False,
    package_data={
        "lazy_mysql": [
            ".version",
        ]
    },
)
