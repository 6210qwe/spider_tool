from setuptools import setup, find_packages
import os
import sys


setup(
    name="spider_tool",
    version="0.0.1",
    author="MindLullaby",
    author_email="3203939025@qq.com",
    description="A professional spider tools package",
    url="https://github.com/6210qwe/spider_tool",
    packages=find_packages(include=['spider_tool', 'spider_tool.*']),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Natural Language :: Chinese (Simplified)",
        "Framework :: Pytest",
    ],
    python_requires=">=3.10",
    install_requires=[
        "requests>=2.31.0",
        "lxml>=4.9.0",
        "loguru>=0.7.2",
        "urllib3>=2.0.7",
        "curl_cffi>=0.6.0",
        "aiomysql>=0.2.0",
        "aiohttp>=3.9.1",
        "click>=8.1.7",
    ],
    extras_require={
        'dev': [
            'pytest>=7.4.0',
            'pytest-cov>=4.1.0',
            'black>=23.7.0',
            'isort>=5.12.0',
            'flake8>=6.1.0',
            'mypy>=1.5.1',
        ],
        'docs': [
            'sphinx>=7.1.0',
            'sphinx-rtd-theme>=1.3.0',
        ],
    },
    entry_points={
        'console_scripts': [
            'spider_tool=spider_tool.cli:main',
        ],
    },
    include_package_data=True,
    package_data={
        'spider_tool': ['py.typed'],
    },
)