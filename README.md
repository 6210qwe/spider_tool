# Spider Tool

一个专业的爬虫工具包，提供了一系列用于爬虫开发的实用工具。

## 特性

- 文件处理工具
- OSS存储管理
- Redis缓存管理
- Ragflow集成
- 时间工具
- User-Agent工具
- XPath工具
- 正则工具

## 安装

```bash
pip install spider_tool
```

## 开发环境设置

1. 克隆仓库：
```bash
git clone https://github.com/6210qwe/spider_tool.git
cd spider_tool
```

2. 创建虚拟环境：
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

3. 安装开发依赖：
```bash
pip install -e ".[dev]"
```

## 使用示例

```python
from spider_tool import FileUtils, OSSManager, RedisManager

# 文件处理
valid_filename = FileUtils.validate_and_fix_filename("test/file:name.txt")

# OSS存储
oss_manager = OSSManager(
    db_config={
        'host': 'localhost',
        'user': 'root',
        'password': 'password',
        'database': 'test'
    },
    endpoint='oss-cn-hangzhou.aliyuncs.com',
    bucket_name='test-bucket'
)

# Redis缓存
redis_manager = RedisManager(host='localhost', port=6379)
```

## 开发

### 代码格式化

```bash
black .
isort .
```

### 类型检查

```bash
mypy .
```

### 运行测试

```bash
pytest
```

## 文档

构建文档：
```bash
cd docs
make html
```

## 许可证

MIT License 