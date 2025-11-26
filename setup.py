# -*- coding:utf-8 -*-
"""
@Author   : MindLullaby
@Website  : https://pypi.org/project/spider-tools-pro/
@Copyright: (c) 2020 by g1879, Inc. All Rights Reserved.
"""

from setuptools import setup, find_packages
import os
import sys
__version__ = '0.0.0.19'


setup(
    name="spider-tools-pro",
    version=__version__,
    author="MindLullaby",
    description="A professional spider tools package",
    license="MIT",
    packages=find_packages(include=['spider_tools', 'spider_tools.*']),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
        "Natural Language :: Chinese (Simplified)",
        "Framework :: Pytest",
    ],
    install_requires=[
        "requests",
        "lxml",
        "loguru",
        "urllib3",
        "curl_cffi",
        "aiomysql",
        "aiohttp",
        "click",
        "html2text",
        "oss2",
        "pymysql",
        "DBUtils",
        "beautifulsoup4",
        "fake-useragent",
        "rarfile",
        "pandas",
        "ftfy",
        "redis",
        "ragflow-sdk",
        "python-magic; platform_system!='Windows'",
        "python-magic-bin; platform_system=='Windows'",
        "python-docx",
        "pywin32; platform_system=='Windows'",
        "comtypes; platform_system=='Windows'",
    ],
    extras_require={
        'dev': [
            'pytest',
            'pytest-cov',
            'black',
            'isort',
            'flake8',
            'mypy',
        ],
        'docs': [
            'sphinx',
            'sphinx-rtd-theme',
        ],
    },
    entry_points={
        'console_scripts': [
            'spider-tools-pro=spider_tools.cli:main',
        ],
    },
    include_package_data=True,
    package_data={
        'spider_tools': ['py.typed'],
    },
)