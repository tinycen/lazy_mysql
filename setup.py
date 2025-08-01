from setuptools import setup, find_packages

setup(
    name='lazy_mysql',
    version='0.1.0',
    packages=find_packages(),
    install_requires=[
        'pymysql',
    ],
    author='tinycen',
    author_email='sky_ruocen@qq.com',
    description='A lazy MySQL client for Python',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/tinycen/lazy_mysql',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.10',
)