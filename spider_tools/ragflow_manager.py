import json
import os
import time
import requests
import re
from urllib.parse import urlparse
from ragflow_sdk import RAGFlow
from ragflow_sdk.modules.dataset import DataSet
from get_mysqldb import DatabasePool
from loguru import logger
from typing import Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type


class BaseProcessor:
    def __init__(self, dataset_name):
        """
        初始化基础处理器
        :param dataset_name: 数据集名称
        """
        """
        初始化RAG处理器
        """
        self.rag_object = RAGFlow(
            api_key="ragflow-E2NGY5ZTZjMDYxNTExZjBiOTYzMDI0Mm",
            base_url="https://yutubang3-rag.yutumed.cn"
        )
        self.dataset: Optional[DataSet] = None
        self.dataset_name = dataset_name
        self.MAX_FILENAME_LENGTH = 100


    def get_or_create_dataset(self) -> DataSet:
        """
        创建或获取数据集
        :return: 数据集对象
        """
        try:
            dataset = self.rag_object.list_datasets(name=self.dataset_name)
            if dataset:
                self.dataset = dataset[0]
                return self.dataset
        except Exception as e:
            self.dataset = self.rag_object.create_dataset(
                name=self.dataset_name,
                avatar="",
                description="Agent助手",
                embedding_model="BAAI/bge-large-zh-v1.5",
                permission="team",
                chunk_method="naive",
            )
            return self.dataset

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((requests.exceptions.RequestException, ConnectionError)),
        before_sleep=lambda retry_state: logger.warning(f"第 {retry_state.attempt_number} 次重试下载文件...")
    )
    def download_file_from_url(self, url):
        """
        从URL下载文件, 一般是从OSS下载文件
        :param url: 文件URL
        :return: 文件内容
        """
        response = requests.get(url, stream=True)
        response.raise_for_status()
        return response.content

    def process_filename(self, title: str, url: str = None) -> str:
        """
        处理文件名，确保符合长度限制
        :param title: 原始标题
        :param url: 文件URL，用于提取扩展名
        :return: 处理后的文件名
        """
        # 移除HTML实体
        title = title.replace('&quot;', '"').replace('&amp;', '&')

        # 移除非法字符
        title = re.sub(r'[<>:"/\\|?*]', '', title)

        # 如果标题太长，进行截断
        if len(title) > self.MAX_FILENAME_LENGTH:
            # 保留前N个字符
            title = title[:self.MAX_FILENAME_LENGTH - 4]  # 预留扩展名的空间


        filename = os.path.basename(urlparse(url).path)
        # 获取扩展名
        _, ext = os.path.splitext(filename)
        if ext:
            return title



    def upload_urls_file(self, urls, titles):
        """ 文件批量上传 """
        global doc_id
        try:
            doc_id = self.upload_url_file(url, title)
            if doc_id:
                self.dataset.async_parse_documents([doc_id])
                logger.info("开始解析文档...")
                return doc_id
            else:
                logger.error(f"文件上传失败: {url}")
                self.delete_documents([doc_id])
                return False
        except Exception as e:
            logger.error(f"处理文档时出错: {e}")
            self.delete_documents([doc_id])
            return False


    def upload_url_file(self, url, title):
        """
        上传URL文件到数据集
        :param url: 文件URL
        :param title: 文件标题
        :return: 文档ID或False
        """
        try:
            content = self.download_file_from_url(url)
            if not content:
                return False
            title = self.process_filename(title, url)
            data = self.dataset.upload_documents([{
                "display_name": title,
                "blob": content
            }])
            return data[0].id
        except Exception as e:
            logger.error(f"上传文件时出错: {e}")
            return False

    def process_documents(self, url, title):
        """
        处理文档
        :param url: URL
        :param title: 标题
        :return: 文档ID或False
        """
        global doc_id
        try:
            doc_id = self.upload_url_file(url, title)
            if doc_id:
                self.dataset.async_parse_documents([doc_id])
                logger.info("开始解析文档...")
                return doc_id
            else:
                logger.error(f"文件上传失败: {url}")
                self.delete_documents([doc_id])
                return False
        except Exception as e:
            logger.error(f"处理文档时出错: {e}")
            self.delete_documents([doc_id])
            return False

    def delete_documents(self, doc_ids):
        """
        删除指定文档
        :param doc_ids: 文档ID列表
        """
        self.dataset.delete_documents(doc_ids)
