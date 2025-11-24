# Spider Tools Pro 工具库详细文档

## 项目概述

Spider Tools Pro 是一个专业的爬虫工具包，提供了完整的爬虫开发所需的各种工具和功能模块。该工具包支持文件处理、数据库操作、云存储、文档处理、图像生成等多种功能。

## 项目结构

```
spider_tools/
├── __init__.py              # 包初始化文件，定义对外API
├── file_utils.py            # 文件处理工具
├── utils.py                 # 通用工具函数
├── oss_manager.py           # 阿里云OSS存储管理
├── ragflow_manager.py       # RAGFlow知识库管理
├── docx_utils.py            # DOCX文档处理工具
├── get_mysqldb.py           # MySQL数据库连接池
├── redis_manager.py         # Redis缓存管理
├── time_utils.py            # 时间处理工具
├── image_utils.py           # AI图像生成工具
├── file_download.py         # 文件下载器
└── captcha_solving/         # 验证码识别模块
    ├── __init__.py
    └── test.py
```

---

## 详细模块说明

### 1. `__init__.py` - 包初始化文件

**功能**: 定义包的对外API接口，控制模块的导入和暴露

**主要导出**:
- `OSSManager`: 阿里云OSS存储管理器
- `file_utils`: 文件处理工具模块
- `utils`: 通用工具函数模块
- `BaseProcessor`: RAGFlow知识库处理器基类

**版权信息**: 包含详细的使用条款和版权声明

---

### 2. `file_utils.py` - 文件处理工具

**功能**: 提供全面的文件处理功能，包括文件类型检测、压缩包解压、文件名处理等

#### 主要函数:

##### `clean_name(filename)`
- **功能**: 基于pathvalidate的文件名清理函数，适配Windows系统
- **参数**: `filename` (str) - 待清理的文件名
- **返回**: 清理后的合法文件名
- **特点**: 处理非法字符、保留名，移除&nbsp等特殊字符

##### `get_filename_from_response(response)`
- **功能**: 从HTTP响应头中提取文件名
- **参数**: `response` - requests响应对象
- **返回**: 提取的文件名或None
- **特点**: 支持多种编码格式，使用ftfy修复文件名

##### `extract_file_names(html_content, class_name=None, base_url=None)`
- **功能**: 从HTML内容中提取文件URL地址
- **参数**: 
  - `html_content` (str) - HTML内容
  - `class_name` (str, optional) - CSS类名过滤
  - `base_url` (str, optional) - 基础URL
- **返回**: 文件信息列表
- **特点**: 支持a、iframe标签，过滤HTML链接，支持相对URL转换

##### `extract_archive(archive_content, archive_name)`
- **功能**: 解压各种格式的压缩包
- **参数**: 
  - `archive_content` (bytes) - 压缩包内容
  - `archive_name` (str) - 压缩包文件名
- **返回**: 解压后的文件列表 [(content, filename), ...]
- **支持格式**: ZIP, TAR, RAR, GZ等
- **特点**: 自动处理编码问题，支持中文文件名

##### `start_detect_file_type(file_url=None, file_name=None)`
- **功能**: 检测文件类型（通过URL或文件名）
- **参数**: 
  - `file_url` (str, optional) - 文件URL
  - `file_name` (str, optional) - 文件名
- **返回**: 文件扩展名
- **特点**: 使用正则表达式匹配文件后缀

##### `get_html(html, class_name=None, id=None)`
- **功能**: 从HTML中提取指定class或id的元素
- **参数**: 
  - `html` (str) - HTML内容
  - `class_name` (str, optional) - CSS类名
  - `id` (str, optional) - 元素ID
- **返回**: 提取的HTML片段

##### `extract_item_content(html)`
- **功能**: 提取HTML中的纯文本内容
- **参数**: `html` (str) - HTML内容
- **返回**: 清理后的文本内容
- **特点**: 移除HTML标签、换行符、特殊字符

##### `extract_and_clean_title(title)`
- **功能**: 从标题中提取并清理文本
- **参数**: `title` (str) - 原始标题
- **返回**: 清理后的标题
- **特点**: 去除换行符、制表符、空格等

##### `get_file_extension(url)`
- **功能**: 获取文件扩展名（支持magic库检测）
- **参数**: `url` (str) - 文件URL
- **返回**: 文件扩展名
- **特点**: 支持多种检测方式，有降级方案

##### `split_excel_by_rows(file_path, rows_per_file=1000, output_dir=None)`
- **功能**: 按行数拆分Excel文件
- **参数**: 
  - `file_path` (str) - Excel文件路径
  - `rows_per_file` (int) - 每个文件的行数
  - `output_dir` (str, optional) - 输出目录
- **返回**: 拆分后的文件路径列表
- **特点**: 支持大文件拆分，自动生成文件名

##### `convert_doc_to_docx_from_url(doc_url)`
- **功能**: 从URL下载DOC文件并转换为DOCX
- **参数**: `doc_url` (str) - DOC文件URL
- **返回**: DOCX文件的字节内容
- **特点**: 支持多种转换方式，有降级方案

##### `convert_doc_bytes_to_docx_bytes(doc_bytes)`
- **功能**: 将DOC字节内容转换为DOCX字节内容
- **参数**: `doc_bytes` (bytes) - DOC文件字节内容
- **返回**: DOCX文件字节内容
- **特点**: 支持Windows COM和纯文本两种方式

---

### 3. `utils.py` - 通用工具函数

**功能**: 提供爬虫开发中常用的工具函数

#### 主要函数:

##### `retry(max_retries=8, retry_delay=5)`
- **功能**: 重试装饰器
- **参数**: 
  - `max_retries` (int) - 最大重试次数
  - `retry_delay` (int) - 重试间隔（秒）
- **特点**: 自动重试失败的操作，记录错误日志

##### `to_bs64(s)`
- **功能**: 将字符串转换为Base64编码
- **参数**: `s` (str) - 待编码字符串
- **返回**: Base64编码字符串

##### `get_md5(data)`
- **功能**: 计算字符串的MD5值
- **参数**: `data` (str) - 待计算字符串
- **返回**: MD5哈希值

##### `calculate_md5(data)`
- **功能**: 计算数据的MD5哈希值，支持多种类型
- **参数**: `data` - 支持bytes、str、dict类型
- **返回**: MD5哈希值
- **特点**: 支持字典序列化，处理日期时间类型

##### `generate_date_intervals(start_date, end_date=None, interval_value=1, interval_type='days', format='date')`
- **功能**: 生成日期间隔列表
- **参数**: 
  - `start_date` - 起始日期
  - `end_date` - 结束日期
  - `interval_value` (int) - 间隔值
  - `interval_type` (str) - 间隔类型
  - `format` (str) - 输出格式
- **返回**: 日期间隔列表
- **特点**: 支持多种间隔类型和格式

---

### 4. `oss_manager.py` - 阿里云OSS存储管理

**功能**: 管理阿里云OSS存储，提供文件上传、下载、管理功能

#### 主要类:

##### `OSSManager`
- **功能**: OSS存储管理器
- **初始化参数**: 
  - `endpoint` (str) - OSS端点
  - `bucket_name` (str) - 存储桶名称
  - `directory` (str) - 目录路径
  - `db_config` (dict, optional) - 数据库配置
  - `oss_credentials` (dict, optional) - OSS凭证

#### 主要方法:

##### `get_oss_credentials_from_db(db_config)`
- **功能**: 从数据库获取OSS凭证
- **参数**: `db_config` (dict) - 数据库配置
- **返回**: OSS凭证元组

##### `initialize_oss_bucket(security_token, access_key_id, access_key_secret)`
- **功能**: 初始化OSS存储桶
- **参数**: OSS凭证信息
- **返回**: OSS存储桶对象

##### `upload_file(file_path, object_name=None)`
- **功能**: 上传文件到OSS
- **参数**: 
  - `file_path` (str) - 本地文件路径
  - `object_name` (str, optional) - OSS对象名
- **返回**: 上传结果

##### `upload_bytes(content, object_name)`
- **功能**: 上传字节内容到OSS
- **参数**: 
  - `content` (bytes) - 字节内容
  - `object_name` (str) - OSS对象名
- **返回**: 上传结果

##### `download_file(object_name, local_path)`
- **功能**: 从OSS下载文件
- **参数**: 
  - `object_name` (str) - OSS对象名
  - `local_path` (str) - 本地保存路径
- **返回**: 下载结果

##### `get_file_url(object_name)`
- **功能**: 获取文件访问URL
- **参数**: `object_name` (str) - OSS对象名
- **返回**: 文件URL

##### `delete_file(object_name)`
- **功能**: 删除OSS文件
- **参数**: `object_name` (str) - OSS对象名
- **返回**: 删除结果

##### `list_files(prefix='')`
- **功能**: 列出OSS文件
- **参数**: `prefix` (str) - 文件名前缀
- **返回**: 文件列表

---

### 5. `ragflow_manager.py` - RAGFlow知识库管理

**功能**: 管理RAGFlow知识库，提供数据集创建、文档上传、解析等功能

#### 主要类:

##### `BaseProcessor`
- **功能**: RAGFlow知识库处理器基类
- **初始化参数**: 
  - `dataset_name` (str) - 数据集名称
  - `description` (str) - 数据集描述
  - `ragflow_config` (dict, optional) - RAGFlow配置

#### 主要方法:

##### `get_authorization()`
- **功能**: 获取RAGFlow认证信息
- **返回**: 认证token
- **特点**: 支持移动端和邮箱登录

##### `get_or_create_dataset()`
- **功能**: 获取或创建数据集
- **返回**: 数据集对象
- **特点**: 自动处理数据集不存在的情况

##### `upload_documents(files_info)`
- **功能**: 上传文档到知识库
- **参数**: `files_info` (list) - 文件信息列表
- **返回**: 上传的文档对象列表
- **特点**: 支持批量上传，自动处理文件名

##### `async_parse_documents(doc_ids)`
- **功能**: 异步解析文档
- **参数**: `doc_ids` (list) - 文档ID列表
- **特点**: 支持批量解析，异步处理

##### `reprocess_all_files(dataset, time_sleep=2)`
- **功能**: 重新处理所有文件
- **参数**: 
  - `dataset` - 数据集对象
  - `time_sleep` (int) - 处理间隔
- **特点**: 批量重新处理，支持进度显示

##### `delete_documents(doc_ids=None)`
- **功能**: 删除文档
- **参数**: `doc_ids` (list, optional) - 文档ID列表
- **特点**: 支持批量删除

##### `get_document_status(doc_id)`
- **功能**: 获取文档状态
- **参数**: `doc_id` (str) - 文档ID
- **返回**: 文档状态信息

##### `search_documents(query, top_k=10)`
- **功能**: 搜索文档
- **参数**: 
  - `query` (str) - 搜索查询
  - `top_k` (int) - 返回结果数量
- **返回**: 搜索结果

---

### 6. `docx_utils.py` - DOCX文档处理工具

**功能**: 处理DOCX文档，提供文档解析、转换等功能

#### 主要函数:

##### `to_docx(doc_bytes)`
- **功能**: 将DOC字节内容转换为DOCX
- **参数**: `doc_bytes` (bytes) - DOC文件字节内容
- **返回**: DOCX文件字节内容
- **特点**: 支持Windows COM和纯文本两种方式

##### `remove_blank(text)`
- **功能**: 移除文本中的空格和零宽空格
- **参数**: `text` (str) - 待处理文本
- **返回**: 清理后的文本

##### `extract_docx(file_path=None, content=None)`
- **功能**: 解析DOCX文件为片段列表
- **参数**: 
  - `file_path` (str, optional) - 文件路径
  - `content` (bytes, optional) - 文件内容
- **返回**: 文档片段列表
- **特点**: 支持段落和表格解析，提取标题级别和字体大小

##### `convert_doc_to_docx_pure(doc_path, docx_path)`
- **功能**: 纯文本方式转换DOC到DOCX
- **参数**: 
  - `doc_path` (str) - DOC文件路径
  - `docx_path` (str) - 输出DOCX文件路径
- **特点**: 不依赖Office，仅保留文本内容

##### `sanitize_xml_text(text)`
- **功能**: 清理XML不兼容的字符
- **参数**: `text` (str) - 待清理文本
- **返回**: 清理后的文本
- **特点**: 移除NULL字节和控制字符

---

### 7. `get_mysqldb.py` - MySQL数据库连接池

**功能**: 管理MySQL数据库连接，提供连接池、CRUD操作等功能

#### 主要类:

##### `DatabasePool`
- **功能**: MySQL数据库连接池管理器
- **初始化参数**: 
  - `logger` - 日志记录器
  - `DB_HOST` (str) - 数据库主机
  - `DB_PORT` (int) - 数据库端口
  - `DB_DATABASE` (str) - 数据库名
  - `DB_USER` (str) - 用户名
  - `DB_PASSWORD` (str) - 密码

#### 主要方法:

##### `_get_connection()`
- **功能**: 从连接池获取连接
- **返回**: 数据库连接对象

##### `to_dict(data)`
- **功能**: 将数据转换为字典格式
- **参数**: `data` - 待转换数据
- **返回**: 字典格式数据

##### `execute_many_or_loop(table, sql, values, return_ids=False, operation='insert')`
- **功能**: 执行批量操作或循环操作
- **参数**: 
  - `table` (str) - 表名
  - `sql` (str) - SQL语句
  - `values` (list) - 值列表
  - `return_ids` (bool) - 是否返回ID
  - `operation` (str) - 操作类型
- **返回**: 操作结果

##### `insert(table, data_dict=None, data_list=None, return_ids=False)`
- **功能**: 插入数据
- **参数**: 
  - `table` (str) - 表名
  - `data_dict` (dict, optional) - 单条数据
  - `data_list` (list, optional) - 批量数据
  - `return_ids` (bool) - 是否返回ID
- **返回**: 插入结果

##### `update(table, condition, data_dict=None, data_list=None, return_ids=False)`
- **功能**: 更新数据
- **参数**: 
  - `table` (str) - 表名
  - `condition` (dict) - 更新条件
  - `data_dict` (dict, optional) - 更新数据
  - `data_list` (list, optional) - 批量更新数据
  - `return_ids` (bool) - 是否返回ID
- **返回**: 更新结果

##### `query(table, condition, query_criteria=None, get_results=False, sql=None)`
- **功能**: 查询数据
- **参数**: 
  - `table` (str) - 表名
  - `condition` (dict) - 查询条件
  - `query_criteria` (list, optional) - 查询字段
  - `get_results` (bool) - 是否返回结果
  - `sql` (str, optional) - 自定义SQL
- **返回**: 查询结果

##### `upsert(table, condition, data_dict=None, data_list=None)`
- **功能**: 插入或更新数据
- **参数**: 
  - `table` (str) - 表名
  - `condition` (dict) - 条件
  - `data_dict` (dict, optional) - 数据
  - `data_list` (list, optional) - 批量数据
- **特点**: 使用ON DUPLICATE KEY UPDATE

##### `query_table_data_count(table)`
- **功能**: 查询表数据总数
- **参数**: `table` (str) - 表名
- **返回**: 数据总数

##### `query_table_data_value_count(table, search_value)`
- **功能**: 查询表中包含特定值的记录数
- **参数**: 
  - `table` (str) - 表名
  - `search_value` (str) - 搜索值
- **返回**: 匹配记录数

---

### 8. `redis_manager.py` - Redis缓存管理

**功能**: 管理Redis缓存，提供URL去重、内容去重、状态管理等功能

#### 主要类:

##### `RedisManager`
- **功能**: Redis缓存管理器
- **初始化参数**: 
  - `host` (str) - Redis主机
  - `port` (int) - Redis端口
  - `db` (int) - 数据库编号
  - `password` (str, optional) - 密码

#### 主要方法:

##### `is_url_visited(url, spider_name)`
- **功能**: 检查URL是否已访问
- **参数**: 
  - `url` (str) - URL地址
  - `spider_name` (str) - 爬虫名称
- **返回**: 布尔值

##### `mark_url_visited(url, spider_name)`
- **功能**: 标记URL为已访问
- **参数**: 
  - `url` (str) - URL地址
  - `spider_name` (str) - 爬虫名称

##### `is_content_duplicate(content_hash, spider_name)`
- **功能**: 检查内容是否重复
- **参数**: 
  - `content_hash` (str) - 内容哈希
  - `spider_name` (str) - 爬虫名称
- **返回**: 布尔值

##### `mark_content_processed(content_hash, spider_name)`
- **功能**: 标记内容为已处理
- **参数**: 
  - `content_hash` (str) - 内容哈希
  - `spider_name` (str) - 爬虫名称

##### `save_crawl_state(spider_name, state_data)`
- **功能**: 保存爬虫状态
- **参数**: 
  - `spider_name` (str) - 爬虫名称
  - `state_data` (dict) - 状态数据
- **特点**: 用于断点续爬

##### `get_crawl_state(spider_name)`
- **功能**: 获取爬虫状态
- **参数**: `spider_name` (str) - 爬虫名称
- **返回**: 状态数据

##### `save_incremental_data(spider_name, data)`
- **功能**: 保存增量数据
- **参数**: 
  - `spider_name` (str) - 爬虫名称
  - `data` (dict) - 数据
- **特点**: 支持增量更新

##### `get_incremental_data(spider_name)`
- **功能**: 获取增量数据
- **参数**: `spider_name` (str) - 爬虫名称
- **返回**: 增量数据

---

### 9. `time_utils.py` - 时间处理工具

**功能**: 提供时间处理相关功能

#### 主要函数:

##### `get_current_time()`
- **功能**: 获取当前时间
- **返回**: 格式化的时间字符串

##### `parse_date_string(date_str)`
- **功能**: 解析日期字符串
- **参数**: `date_str` (str) - 日期字符串
- **返回**: 标准格式的日期字符串
- **特点**: 支持多种日期格式，自动清理无效字符

##### `format_timestamp(timestamp)`
- **功能**: 将时间戳转换为日期字符串
- **参数**: `timestamp` - 时间戳
- **返回**: 格式化的日期字符串
- **特点**: 支持秒和毫秒时间戳

##### `get_date_range(start_date, end_date, interval_days=1)`
- **功能**: 生成日期范围列表
- **参数**: 
  - `start_date` (str) - 开始日期
  - `end_date` (str) - 结束日期
  - `interval_days` (int) - 间隔天数
- **返回**: 日期列表
- **特点**: 支持自定义间隔

##### `is_valid_date(date_str)`
- **功能**: 验证日期字符串是否有效
- **参数**: `date_str` (str) - 日期字符串
- **返回**: 布尔值
- **特点**: 支持多种日期格式

---

### 10. `image_utils.py` - AI图像生成工具

**功能**: 提供AI图像生成功能，支持多种生成方式

#### 主要类:

##### `JimengT2IRequest`
- **功能**: 即梦T2I请求参数类
- **属性**: 
  - `req_key` (str) - 请求键
  - `prompt` (str) - 提示词
  - `image_urls` (list) - 图片URL列表
  - `size` (int) - 图片大小
  - `width` (int) - 图片宽度
  - `height` (int) - 图片高度
  - `scale` (float) - 缩放比例
  - `force_single` (bool) - 强制单图
  - `min_ratio` (float) - 最小比例
  - `max_ratio` (float) - 最大比例

##### `ImageResult`
- **功能**: 图像生成结果类
- **属性**: 
  - `success` (bool) - 是否成功
  - `image_urls` (list) - 生成的图片URL列表
  - `error_message` (str) - 错误信息
  - `request_id` (str) - 请求ID
  - `cost` (float) - 成本
  - `usage` (dict) - 使用情况

##### `ImageGenerator`
- **功能**: 图像生成器
- **初始化参数**: 
  - `api_key` (str) - API密钥
  - `base_url` (str) - 基础URL
  - `use_sdk` (bool) - 是否使用SDK

#### 主要方法:

##### `generate_image(prompt, **kwargs)`
- **功能**: 生成图像
- **参数**: 
  - `prompt` (str) - 提示词
  - `**kwargs` - 其他参数
- **返回**: 图像生成结果
- **特点**: 支持多种生成方式

##### `generate_image_sdk(prompt, **kwargs)`
- **功能**: 使用SDK生成图像
- **参数**: 
  - `prompt` (str) - 提示词
  - `**kwargs` - 其他参数
- **返回**: 图像生成结果

##### `generate_image_http(prompt, **kwargs)`
- **功能**: 使用HTTP请求生成图像
- **参数**: 
  - `prompt` (str) - 提示词
  - `**kwargs` - 其他参数
- **返回**: 图像生成结果

##### `download_image(image_url, save_path)`
- **功能**: 下载生成的图像
- **参数**: 
  - `image_url` (str) - 图像URL
  - `save_path` (str) - 保存路径
- **返回**: 下载结果

---

### 11. `file_download.py` - 文件下载器

**功能**: 提供通用文件下载功能，支持多种下载方式

#### 主要类:

##### `FileDownloader`
- **功能**: 通用文件下载器
- **初始化参数**: 
  - `headers` (dict, optional) - 请求头
  - `proxies` (dict, optional) - 代理配置
  - `retry_times` (int) - 重试次数
  - `retry_delay` (int) - 重试延迟
  - `chunk_size` (int) - 分块大小
  - `min_valid_size` (int) - 最小有效大小
  - `timeout` (int) - 超时时间
  - `verify_ssl` (bool) - 是否验证SSL
  - `deny_extensions` (list) - 拒绝的扩展名

#### 主要方法:

##### `download_file(url, save_path=None, filename=None)`
- **功能**: 下载文件
- **参数**: 
  - `url` (str) - 文件URL
  - `save_path` (str, optional) - 保存路径
  - `filename` (str, optional) - 文件名
- **返回**: 下载结果
- **特点**: 支持分块下载，自动重试

##### `download_bytes(url)`
- **功能**: 下载文件为字节内容
- **参数**: `url` (str) - 文件URL
- **返回**: 文件字节内容
- **特点**: 不保存到磁盘，直接返回内容

##### `head_request(url)`
- **功能**: 发送HEAD请求
- **参数**: `url` (str) - 请求URL
- **返回**: 响应头信息
- **特点**: 用于探测文件信息

##### `get_file_info(url)`
- **功能**: 获取文件信息
- **参数**: `url` (str) - 文件URL
- **返回**: 文件信息字典
- **特点**: 包含文件大小、类型等信息

##### `is_valid_file(url)`
- **功能**: 检查文件是否有效
- **参数**: `url` (str) - 文件URL
- **返回**: 布尔值
- **特点**: 检查文件大小、类型等

---

### 12. `captcha_solving/` - 验证码识别模块

**功能**: 提供验证码识别功能

#### 文件结构:
- `__init__.py` - 模块初始化文件
- `test.py` - 测试文件（当前为空）

**说明**: 该模块目前处于开发阶段，具体功能待完善。

---

## 使用示例

### 1. 基本使用

```python
from spider_tools import OSSManager, BaseProcessor
from spider_tools.file_utils import *
from spider_tools.utils import retry

# 使用OSS管理器
oss_manager = OSSManager(
    endpoint="your-endpoint",
    bucket_name="your-bucket",
    directory="uploads/",
    oss_credentials={
        'security_token': 'your-token',
        'access_key_id': 'your-key-id',
        'access_key_secret': 'your-key-secret'
    }
)

# 上传文件
result = oss_manager.upload_file("local_file.pdf", "remote_file.pdf")

# 使用RAGFlow处理器
processor = BaseProcessor(
    dataset_name="my_dataset",
    description="数据集描述",
    ragflow_config={
        'api_key': 'your-api-key',
        'base_url': 'https://your-ragflow.com'
    }
)

# 获取数据集
dataset = processor.get_or_create_dataset()

# 上传文档
files_info = [{
    'display_name': 'document.pdf',
    'blob': file_content
}]
docs = dataset.upload_documents(files_info)
```

### 2. 文件处理示例

```python
from spider_tools.file_utils import *

# 清理文件名
clean_filename = clean_name("invalid<>file|name.pdf")

# 提取HTML中的文件链接
files = extract_file_names(html_content, class_name="file-link")

# 解压文件
extracted_files = extract_archive(archive_content, "archive.zip")

# 拆分Excel文件
split_files = split_excel_by_rows("large_file.xlsx", rows_per_file=1000)
```

### 3. 数据库操作示例

```python
from spider_tools.get_mysqldb import DatabasePool
from loguru import logger

# 创建数据库连接池
db_pool = DatabasePool(
    logger=logger,
    DB_HOST="localhost",
    DB_PORT=3306,
    DB_DATABASE="mydb",
    DB_USER="user",
    DB_PASSWORD="password"
)

# 插入数据
result = db_pool.insert(
    table="users",
    data_dict={"name": "John", "email": "john@example.com"}
)

# 查询数据
users = db_pool.query(
    table="users",
    condition={"status": "active"},
    get_results=True
)
```

### 4. Redis缓存示例

```python
from spider_tools.redis_manager import RedisManager

# 创建Redis管理器
redis_manager = RedisManager(
    host="localhost",
    port=6379,
    db=0
)

# 检查URL是否已访问
if not redis_manager.is_url_visited(url, "my_spider"):
    # 处理URL
    redis_manager.mark_url_visited(url, "my_spider")

# 保存爬虫状态
state_data = {"last_page": 10, "processed_count": 100}
redis_manager.save_crawl_state("my_spider", state_data)
```

### 5. 文档处理示例

```python
from spider_tools.docx_utils import extract_docx, to_docx

# 解析DOCX文件
fragments = extract_docx(file_path="document.docx")

# 转换DOC到DOCX
with open("document.doc", "rb") as f:
    doc_bytes = f.read()
docx_bytes = to_docx(doc_bytes)
```

---

## 依赖项

### 核心依赖
- `requests` - HTTP请求库
- `lxml` - XML/HTML解析
- `loguru` - 日志记录
- `urllib3` - URL处理
- `curl_cffi` - HTTP客户端
- `aiomysql` - 异步MySQL
- `aiohttp` - 异步HTTP
- `click` - 命令行工具
- `html2text` - HTML转文本
- `oss2` - 阿里云OSS
- `pymysql` - MySQL连接
- `DBUtils` - 数据库工具
- `beautifulsoup4` - HTML解析
- `fake-useragent` - 用户代理
- `rarfile` - RAR文件处理
- `pandas` - 数据处理
- `ftfy` - 文本修复
- `redis` - Redis客户端
- `ragflow-sdk` - RAGFlow SDK
- `python-docx` - DOCX处理
- `pathvalidate` - 路径验证
- `pywin32` - Windows COM（Windows系统）

### 可选依赖
- `python-magic` - 文件类型检测（非Windows）
- `python-magic-bin` - 文件类型检测（Windows）
- `volcengine` - 火山引擎SDK（图像生成）

---

## 注意事项

1. **版权声明**: 使用本工具包需要遵守版权声明中的条款
2. **依赖管理**: 某些功能需要特定的系统依赖（如libmagic）
3. **平台兼容**: 部分功能（如Windows COM）仅在特定平台可用
4. **配置安全**: 敏感信息（API密钥、数据库密码）应通过参数传递，避免硬编码
5. **错误处理**: 所有函数都包含错误处理机制，建议查看日志输出
6. **性能优化**: 大文件处理时注意内存使用，可使用分块处理

---

## 更新日志

- **v1.0.0**: 初始版本，包含基础功能模块
- **v1.1.0**: 添加RAGFlow支持，优化文件处理
- **v1.2.0**: 增强数据库操作，添加Redis缓存
- **v1.3.0**: 添加AI图像生成，完善文档处理

---

## 贡献指南

欢迎提交Issue和Pull Request来改进这个工具包。在提交代码前，请确保：

1. 代码符合PEP 8规范
2. 添加适当的文档字符串
3. 包含单元测试
4. 更新相关文档

---

## 许可证

本项目采用MIT许可证，详见LICENSE文件。
