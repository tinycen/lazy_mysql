from setuptools import setup, find_packages

# 读取README文件
try:
    with open('README.md', 'r', encoding='utf-8') as f:
        long_description = f.read()
except FileNotFoundError:
    long_description = 'A lazy MySQL client for Python'

setup(
    name='lazy_mysql',
    version='0.1.7',
    packages=find_packages(),
    install_requires=[
        'mysql-connector-python>=9.4.0',
        'pandas>=2.3.1',
    ],
    author='tinycen',
    author_email='sky_ruocen@qq.com',
    description='A lazy MySQL client for Python.',
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
)
