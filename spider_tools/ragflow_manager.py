import base64
import os
import time
import requests
from urllib.parse import urlparse
from ragflow_sdk import RAGFlow
from ragflow_sdk.modules.dataset import DataSet
from loguru import logger
from typing import Optional
from spider_tools.file_utils import convert_doc_to_docx_from_url
from spider_tools.utils import retry, calculate_md5
from spider_tools.file_download import FileDownloader
import threading
import math
from concurrent.futures import ThreadPoolExecutor, as_completed
from encrypt_util import rsa_encrypt
# ragflow-sdk 常用操作
# 获取所有的知识库 self.rag_object.list_datasets()
# 删除一个知识库下所有的文件, 要删除的文档的 ID。如果未指定，则数据集中的所有文档都将被删除。None  self.dataset.delete_documents()
class BaseProcessor:
    def __init__(self, dataset_name, description,ragflow_config=None, user_info=None):
        self.ragflow_config = ragflow_config or {}
        if not self.ragflow_config.get('api_key'):
            raise ValueError("缺少RAGFlow API密钥配置")
        if not self.ragflow_config.get('base_url'):
            raise ValueError("缺少RAGFlow基础URL配置")
        self.user_info = user_info or {}
        self.rag_object = RAGFlow(
            api_key=self.ragflow_config['api_key'],
            base_url=self.ragflow_config['base_url']
        )
        self.dataset: Optional[DataSet] = None
        self.dataset_name = dataset_name
        self.description = description
        self.MAX_FILENAME_LENGTH = 100
        self.base_url = str(self.ragflow_config['base_url']).rstrip('/')
        self.headers = {
            'accept': 'application/json',
            'accept-language': 'zh-CN,zh;q=0.9',
            'authorization': self.get_authorization(),
            'cache-control': 'no-cache',
            'client': 'pc',
            'content-type': 'application/json;charset=UTF-8',
            'origin': self.base_url,
            'pragma': 'no-cache',
            'priority': 'u=1, i',
            'referer': f'{self.base_url}/knowledge/dataset',
            'sec-ch-ua': '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'timestamp': str(int(time.time() * 1000)),
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
            'cookie': f'session={self.ragflow_config.get("session_cookie", "")}',
        }
    # 获取账号token授权用于后续操作
    def get_authorization(self):
        headers = {
            'accept': 'application/json',
            'accept-language': 'zh-CN,zh;q=0.9',
            'authorization': '',
            'cache-control': 'no-cache',
            'client': 'pc',
            'content-type': 'application/json;charset=UTF-8',
            'origin': self.base_url,
            'pragma': 'no-cache',
            'priority': 'u=1, i',
            'referer': f'{self.base_url}/login',
            'sec-ch-ua': '"Chromium";v="136", "Google Chrome";v="136", "Not.A/Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'timestamp': str(int(time.time() * 1000)),
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
        }
        public_key_pem = """ -----BEGIN PUBLIC KEY-----
        MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEArq9XTUSeYr2+N1h3Afl/
        z8Dse/2yD0ZGrKwx+EEEcdsBLca9Ynmx3nIB5obmLlSfmskLpBo0UACBmB5rEjBp
        2Q2f3AG3Hjd4B+gNCG6BDaawuDlgANIhGnaTLrIqWrrcm4EMzJOnAOI1fgzJRsOO
        UEfaS318Eq9OVO3apEyCCt0lOQK6PuksduOjVxtltDav+guVAA068NrPYmRNabVK
        RNLJpL8w4D44sfth5RvZ3q9t+6RTArpEtc5sh5ChzvqPOzKGMXW83C95TxmXqpbK
        6olN4RevSfVjEAgCydH6HN6OhtOQEcnrU97r9H0iZOWwbw3pVrZiUkuRD1R56Wzs
        2wIDAQAB
        -----END PUBLIC KEY-----"""
        # 明文（需要加密的内容）
        plaintext = base64.b64encode(self.user_info['password'].encode('utf-8')).decode('utf-8')
        # 执行加密
        ciphertext = rsa_encrypt(public_key_pem, plaintext)
        # logger.info(f"明文：{plaintext}")
        # logger.info(f"密文（十六进制）：{ciphertext}")
        bytes_ciphertext = bytes.fromhex(ciphertext)  # 先转回字节
        b64_ciphertext = base64.b64encode(bytes_ciphertext).decode("utf-8")
        json_data = {
            'email': self.user_info['email'],
            'mobile': '',
            'password': b64_ciphertext,
            'login_type': 'email',
            'login_type_key': 'password',
        }
        response = requests.post(f'{self.base_url}/v1/user/login', headers=headers, json=json_data)
        authorization = response.json()['data']['authorization']
        logger.info(f"获取账号token授权成功：{authorization}")
        return authorization

    # 获取数据集对象
    def get_or_create_dataset(self) -> DataSet:
        """
        创建数据集, 如果没有则直接创建
        :return: 数据集对象
        """
        try:
            dataset = self.rag_object.list_datasets(name=self.dataset_name)
            if dataset:
                self.dataset = dataset[0]
                self.dataset.list_documents()
                return self.dataset
        except Exception as e:
            self.dataset = self.rag_object.create_dataset(
                name=self.dataset_name,
                # avatar="",
                description=self.description,
                embedding_model="BAAI/bge-large-zh-v1.5@BAAI",
                permission="team",
                chunk_method="naive",
            )
            return self.dataset

    # 批量上传文件
    def upload_files(self, dataset, files):
        """批量上传所有文件，仅调用一次upload_documents"""
        doc_list = dataset.upload_documents(files)
        doc_ids = [doc.id for doc in doc_list]
        logger.info(f"成功批量上传{len(doc_ids)} 个文件")
        return doc_list

    # 文件解析--因为没有未解析文件的查询接口, 需要遍历整个知识库
    # 因为服务器解析性能问题, 需要控制解析文件的数量, 要不然会在队列钟卡住
    # 控制文件数量, 需要定时获取解析文件的状态
    # def reprocess_all_files(self, dataset, time_sleep=10):
    #     parse_lock = threading.Lock()
    #     page_size = 100
    #     total_docs = dataset.document_count
    #     logger.info("一共{}页".format(total_docs))
    #     if total_docs == 0:
    #         logger.info("无文档可处理")
    #         return
    #     total_pages = math.ceil(total_docs / page_size)
    #     # 3. 单页处理函数（多线程遍历，解析时加锁串行）
    #     def process_page(page):
    #         try:
    #             # 3.1 多线程并行拉取分页文档（遍历加速）
    #             documents = self.dataset.list_documents(page=page, page_size=page_size)
    #             if not documents:
    #                 return
    #             # 3.2 遍历当前页文档（保持原有筛选逻辑）
    #             for doc in documents:
    #                 if doc.name.lower().endswith('.doc'):
    #                     continue
    #                 if doc.run in ["UNSTART", "CANCEL"]:
    #                     # 核心：通过锁强制解析串行化（同一时间仅1个文档解析）
    #                     with parse_lock:  # 所有线程竞争这把锁，只有拿到锁的才能执行以下代码
    #                         self.dataset.async_parse_documents([doc.id])
    #                         logger.info(f"解析{doc.name}")
    #                         time.sleep(time_sleep)  # 串行等待，和原代码行为一致
    #         except Exception as e:
    #             logger.error(f"第{page}页处理出错: {str(e)}")
    #     with ThreadPoolExecutor(max_workers=10) as executor:
    #         futures = [executor.submit(process_page, page) for page in range(1, total_pages + 1)]
    #         for future in as_completed(futures):
    #             pass
    #     logger.info("所有文档遍历完成")

    # 后续直接使用/v1/document/ids/list接口, 通过状态为2进行查询,run为3是已经解析成功, run为2是已经取消状态, run为1是正在解析中, 0为未解析
    def reprocess_all_files(self, dataset, time_sleep=10):
        parse_lock = threading.Lock()
        page_size = 100
        total = self.get_pages(dataset.id, status=0)['data']['total']
        logger.info("一共{}未解析文档".format(total))
        total_cancel= self.get_pages(dataset.id, status=2)['data']['total']
        logger.info("一共{}个取消文档".format(total_cancel))
        if total == 0:
            logger.info("无文档可处理")
            return
        total_pages = math.ceil(total / page_size)
        running_count = self.get_pages(dataset.id, status=1)['data']['total']  # 当前解析文件的数量
        logger.info("当前解析文件数量为{}".format(running_count))
        max_parse_count = 8
        check_interval = 20
        last_monitor_time = 0
        flag = True
        while flag:
            try:
                # 单个文档进行解析, 每隔20秒查询队列中的数量, 如果大于8个, 则等待
                while running_count < max_parse_count:
                    response_one = self.get_pages(dataset.id, status=0)
                    # for page in range(1, total_pages + 1):
                    #     response = self.get_pages(dataset.id, '0', page)
                    doc_list = response_one['data']['docs']
                    for doc in doc_list:
                        doc_id = doc['id']
                        doc_name = doc['name']
                        run = doc['run']
                        if run == 0 or run == 2:
                            self.parse_files(doc_id, doc_name)
                            running_count += 1
                            time.sleep(5)
                    response_two = self.get_pages(dataset.id, status=2)
                    doc_list = response_two['data']['docs']
                    running_count = response_two['data']['total']
                    if running_count:
                        for doc in doc_list:
                            doc_id = doc['id']
                            doc_name = doc['name']
                            run = doc['run']
                            if run == 0 or run == 2:
                                self.parse_files(doc_id, doc_name)
                                running_count += 1
                                time.sleep(5)
                    else:
                        break
                current_time = time.time()
                if current_time - last_monitor_time >= check_interval:
                    # 查询并打印正在解析的数量
                    running_response = self.get_pages(dataset.id, status=1)
                    running_count = running_response['data']['total']
                    logger.info(f"【监控】当前正在解析的文件数量：{running_count}/{max_parse_count}")
                    last_monitor_time = current_time  # 更新上次监控时间
                else:
                    time.sleep(10)
            except Exception as e:
                logger.error(f"处理出错: {str(e)}")
                self.headers['authorization'] = self.get_authorization()
        logger.info("所有文档遍历完成")

    def parse_files(self, doc_ids, doc_name):
        json_data = {
            'doc_ids': [
                doc_ids,
            ],
            'run': 1,
            'delete': False,
        }
        response = requests.post('https://www.yutubang.com/v1/document/run', headers=self.headers,json=json_data)
        if response.json()['message'] == "success":
            logger.info(f"{doc_name}开始解析")
    @retry(max_retries=3, retry_delay=2)
    def get_pages(self, kb_id, status, page=10):
        """
        获取所有文件分页
        :return: 所有文件分页
        """
        params = {
            'kb_id': kb_id,
            'keywords': '',
            'page_size': '100',
            'page': str(page),
            'run_status': status
        }
        json_data = {}
        response = requests.post('https://www.yutubang.com/v1/document/ids/list', params=params, headers=self.headers,json=json_data).json()
        return response

    def cancel_all_files(self, dataset):
        """
        批量停止解析文件
        :param dataset: 数据集对象
        """
        doc_ids = []
        response = self.get_pages(dataset.id, status=1)
        total = response['data']['total']
        logger.info("一共{}个正在解析的文件".format(total))
        total_pages = math.ceil(total / 100)
        for page in range(1, total_pages + 1):
            response = self.get_pages(dataset.id, '1', page)
            doc_list = response['data']['docs']
            for doc in doc_list:
                doc_id = doc['id']
                run = doc['run']
                if run == '1':
                    doc_ids.append(doc_id)
                    if len(doc_ids) == 500:
                        self.cancel_doc(doc_ids)
                        doc_ids.clear()
        # 处理剩余文档
        print(doc_ids)
        if doc_ids:
            self.cancel_doc(doc_ids)


    def cancel_doc(self, doc_ids):
        json_data = {
            'doc_ids': doc_ids,
            'run': 2,
            'delete': False,
        }
        response = requests.post('https://www.yutubang.com/v1/document/run', headers=self.headers, json=json_data)
        logger.info(response.json())


    # 所有文件停止解析--遍历整个知识库, 获取所有文档,并停止解析
    # def cancel_all_files(self, dataset):
    #     """
    #     批量停止解析文件
    #     :param dataset: 数据集对象
    #     """
    #     for page in range(1, dataset.document_count // 30 + 30):
    #         documents = dataset.list_documents(page=page)
    #         for doc in documents:
    #             if doc.status == 'parsing':
    #                 dataset.cancel_document(doc.id)

    # 对已经解析的文档进行分块处理



    def delete_files_by_status(self, dataset, status):
        """
        根据状态删除知识库文件
        :param dataset: 数据集对象
        :param status: 状态
        """
        for page in range(1, dataset.document_count // 30 + 30):
            documents = dataset.list_documents(page=page)
            for doc in documents:
                if doc.status == status:
                    dataset.delete_documents([doc.id])

    # def delete_repeat_files(self, dataset):
    #     """删除重复文件"""
    #     for page in range(1, dataset.document_count // 30 + 30):
    #         documents = dataset.list_documents(page=page)
    #         for doc in documents:
    #             if '(' in doc.name:
    #                 dataset.delete_documents([doc.id])

    def delete_repeat_files(self, dataset):
        """批量删除名称中包含'('的重复文件"""
        batch_size = 100  # 每批删除的ID数量（可根据API限制调整）
        delete_ids = []  # 存储待删除的文档ID
        # 分页获取所有文档，收集需删除的ID
        page = 1
        while True:
            try:
                documents = dataset.list_documents(page=page)
                if not documents:
                    break  # 所有页已处理完毕

                # 筛选名称含'('的文档ID
                for doc in documents:
                    if '(' in doc.name:
                        delete_ids.append(doc.id)

                # 当收集的ID达到批量阈值时，执行删除
                if len(delete_ids) >= batch_size:
                    dataset.delete_documents(delete_ids)
                    logger.info(f"已删除第{page}页批次，共{len(delete_ids)}个文档")
                    delete_ids = []  # 清空列表，继续收集

                page += 1

            except Exception as e:
                logger.info(f"获取第{page}页文档失败：{str(e)}")
                break

        # 处理剩余不足一批的ID
        if delete_ids:
            dataset.delete_documents(delete_ids)
            logger.info(f"处理剩余文档，共删除{len(delete_ids)}个文档")

        logger.info("重复文件批量删除完成")

    def upload_files(self, dataset, urls):
        """
        批量上传文件到数据集
        :param dataset: 数据集对象
        :param urls: 文件URL列表
        """
        for url in urls:
            content = self.download_file_from_url(url)
            title = self.process_filename(url)
            data = self.dataset.upload_documents([{
                "display_name": title,
                "blob": content
            }])
            return data[0].id, data[0].dataset_id

    def get_status(self, dataset):
        for page in range(1, dataset.document_count // 30 + 30):
            documents = self.dataset.list_documents(page=page)
            for doc in documents:
                logger.info(f'{doc.run}, {doc.name}')


    # def reprocess_all_files(self, dataset, time_sleep=10):
    #     for page in range(1, dataset.document_count // 30 + 30):
    #         documents = dataset.list_documents(page=page)
    #         for doc in documents:
    #             logger.info(f'{doc.run}, {doc.name}')
    #             if doc.name.lower().endswith('.doc'):
    #                 continue
    #             if doc.run == "UNSTART" or doc.run == "CANCEL":
    #                 self.reprocess_files(dataset, doc, time_sleep)
    #             if doc.run == "FAIL":
    #                 self.reprocess_files(dataset, doc, time_sleep)

    def check_file_status(self, dataset, doc):
        try:
            params = {
                'kb_id': dataset.id,
                'keywords': doc.name,
                'page_size': '10',
                'page': '1',
            }
            response = requests.get(f'{self.base_url}/v1/document/list', params=params, headers=self.headers)
            logger.info(response.text)
            return response.json()
        except Exception as e:
            logger.error(e)

    def cancel_files(self, doc):
        try:
            json_data = {
                'doc_ids': [
                    doc.id,
                ],
                'run': 2,
                'delete': True,
            }
            response = requests.post(f'{self.base_url}/v1/document/run', headers=self.headers,
                                     json=json_data)
            logger.info(response.text)
        except Exception as e:
            logger.error(e)



    def reprocess_files(self, dataset, doc, time_sleep=10):
        try:
            json_data = {
                'doc_ids': [
                    doc.id
                ],
                'run': 1,
                'delete': False,
            }
            response = requests.post(f'{self.base_url}/v1/document/run', headers=self.headers,
                                     json=json_data)
            logger.info(response.text)
            time.sleep(time_sleep)
            # self.check_file_status(dataset, doc)
        except Exception as e:
            logger.error(e)


    def _process_pending_doc(self, doc, dataset, time_sleep, max_wait):
        try:
            """处理待启动或已取消的文档"""
            dataset.async_parse_documents([doc.id])
            logger.info(f"启动解析文档: {doc.name}")
            # 等待文档解析完成
            wait_time = 0
            while wait_time < max_wait:
                # 检查文档状态
                updated_doc = dataset.list_documents(id=str(doc.id))
                if updated_doc.run == "DONE":
                    logger.info(f"文档 {doc.name} 解析完成，状态: {updated_doc.run}")
                    break
                if updated_doc.run == "FAIL":
                    logger.error(f"文档 {doc.name} 解析失败")
                    break
                wait_time += time_sleep
                logger.info(f"等待文档 {doc.name} 解析中，已等待 {wait_time} 秒")
                time.sleep(time_sleep)
            if wait_time >= max_wait:
                logger.warning(f"文档 {doc.name} 解析超时，最大等待时间已到")
        except Exception as e:
            logger.error(f"处理文档 {doc.name} 时发生错误: {e}")

    def _process_failed_doc(self, doc, dataset, time_sleep, max_wait):
        try:
            """处理失败的文档"""
            logger.info(f"重新解析失败文档: {doc.name}")
            chunks = doc.list_chunks()
            if chunks:
                doc.delete_chunks()
            dataset.async_cancel_parse_documents([doc.id])
            logger.info(f"重新启动解析，文档ID: {doc.id}")

            # 等待文档重新解析完成
            wait_time = 0
            while wait_time < max_wait:
                updated_doc = dataset.list_documents(id=str(doc.id))[0]
                if updated_doc.run == "DONE":
                    logger.info(f"文档 {doc.name} 重新解析完成")
                    break
                elif updated_doc.run == "FAIL":
                    logger.warning(f"失败文档 {doc.name} 重新解析仍失败")
                    break

                wait_time += time_sleep
                time.sleep(time_sleep)
                logger.info(f"等待失败文档 {doc.name} 重新解析，已等待 {wait_time} 秒")


            if wait_time >= max_wait:
                logger.warning(f"失败文档 {doc.name} 重新解析超时")
        except Exception as e:
            logger.error(f"处理文档 {doc.name} 时发生错误: {e}")

    def _get_updated_document(self, doc_id, dataset):
        """获取更新的文档信息"""
        try:
            return dataset.list_documents([doc_id])
        except Exception as e:
            logger.error(f"获取文档 {doc_id} 信息失败: {e}")
            return None



    def fix_double_dot_in_filename(self,filename):
        """将文件名中的双点(..)替换为单点(.)"""
        # 使用正则表达式替换连续的两个点为单个点
        import re
        return re.sub(r'\.\.', '.', filename)

    def reprocess_all_files_two(self, dataset):
        for page in range(1, dataset.document_count // 30 + 30):
            documents = self.dataset.list_documents(page=page)
            for doc in documents:
                if doc.name.lower().endswith('.docx'):
                    fixed_name = self.fix_double_dot_in_filename(doc.name)
                    doc.update({"name": fixed_name})
                    logger.info(doc.name)



    def cancle_all_files(self, dataset):
        for page in range(1, dataset.document_count // 30 + 30):
            documents = self.dataset.list_documents(page=page)
            for doc in documents:
                logger.info(f"{doc.run}, {doc.name}")
                if doc.run == "RUNNING":
                    try:
                        self.cancel_files(doc)
                        logger.info(f"{doc.name} 取消成功")
                    except Exception as e:
                        logger.error(f"处理文档 {doc.name} 时出错: {e}")  # 添加异常捕获


    def upload_file(self, dataset, files):
        """
        上传单个文件
        :param dataset: 数据集对象
        :param url: 文件URL
        """
        authorization = self.get_authorization()
        headers = {
            'accept': 'application/json',
            'accept-language': 'zh-CN,zh;q=0.9',
            'authorization': authorization,
            'cache-control': 'no-cache',
            'client': 'pc',
            'origin': self.base_url,
            'pragma': 'no-cache',
            'sec-ch-ua': '"Chromium";v="136", "Google Chrome";v="136", "Not.A/Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'timestamp': str(int(time.time() * 1000)),
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
            'content-type': 'multipart/form-data; boundary=----WebKitFormBoundaryPBd18zhngU409CSz'
        }
        for file in files:
            file_name = file['file_name']
            content = file['content']
            data = (
                '------WebKitFormBoundaryPBd18zhngU409CSz\r\n'
                'Content-Disposition: form-data; name="kb_id"\r\n\r\n'
                f'{dataset.id}\r\n'
                '------WebKitFormBoundaryPBd18zhngU409CSz\r\n'
                f'Content-Disposition: form-data; name="file"; filename={file_name}\r\n'
                'Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet\r\n\r\n'
            )
            logger.info(dataset.id, file_name)


    def delete_doc_files(self, dataset):
        authorization = self.get_authorization()
        headers = {
            'accept': 'application/json',
            'accept-language': 'zh-CN,zh;q=0.9',
            'authorization': authorization,
            'cache-control': 'no-cache',
            'client': 'pc',
            'origin': self.base_url,
            'pragma': 'no-cache',
            'referer': f'{self.base_url}/knowledge/dataset?id={dataset.id}&page=1&size=10',
            'sec-ch-ua': '"Chromium";v="136", "Google Chrome";v="136", "Not.A/Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'timestamp': str(int(time.time() * 1000)),
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
            'content-type': 'multipart/form-data; boundary=----WebKitFormBoundaryPBd18zhngU409CSz'
        }
        for page in range(1, dataset.document_count // 30 + 30):
            documents = self.dataset.list_documents(page=page)
            for doc in documents:
                if doc.name.lower().endswith('.doc'):
                    logger.info(doc.run, doc.name, doc.type)
                    url = f'{self.base_url}/v1/document/get/{doc.id}'
                    base_name, ext = os.path.splitext(doc.name)
                    doc.name = f"{base_name}.docx"
                    data = (
                        '------WebKitFormBoundaryPBd18zhngU409CSz\r\n'
                        'Content-Disposition: form-data; name="kb_id"\r\n\r\n'
                        f'{self.dataset.id}\r\n'
                        '------WebKitFormBoundaryPBd18zhngU409CSz\r\n'
                        f'Content-Disposition: form-data; name="file"; filename={doc.name}\r\n'
                        'Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet\r\n\r\n'
                    )
                    # file_content = convert_doc_to_docx_from_url(url, '')
                    data = data.encode('utf-8') + file_content + b'\r\n------WebKitFormBoundaryPBd18zhngU409CSz--\r\n'
                    upload_url = f'{self.base_url}/v1/document/upload'
                    response = requests.post(upload_url, headers=headers, data=data, verify=False)
                    logger.info('响应内容:', response.text)
                    self.delete_documents([doc.id])





    def delete_dataset(self, id):
        self.rag_object.delete_datasets([id])

    @retry(max_retries=8, retry_delay=1)
    def download_file_from_url(self, url):
        """
        从URL下载文件, 一般是从OSS下载文件
        :param url: 文件URL
        :return: 文件内容
        """
        downloader = FileDownloader()
        ok, content = downloader.download_bytes(url)
        if not ok:
            raise Exception("下载失败")
        return content

    def process_filename(self, url):
        """
        :param url: 文件URL，用于提取扩展名和文件名
        :return: 处理后的文件名
        """
        filename = os.path.basename(urlparse(url).path)
        # 获取扩展名
        _, ext = os.path.splitext(url)
        if ext:
            return filename

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
            title = self.process_filename(url)
            data = self.dataset.upload_documents([{
                "display_name": title,
                "blob": content
            }])
            return data[0].id, data[0].dataset_id
        except Exception as e:
            logger.error(f"上传文件时出错: {e}")
            return False


    def process_documents(self, url, title):
        """
        处理文档
        :param url: 文档URL
        :param title: 文档标题
        :return: (doc_id, dataset_id) 元组或False
        """
        try:
            doc_id, dataset_id = self.upload_url_file(url, title)
            if doc_id:
                # self.dataset.async_parse_documents([doc_id])
                # logger.info(f"文档 {title} 上传成功，开始解析...")
                return doc_id, dataset_id
            else:
                logger.error(f"文件上传失败: {url}")
                return False
        except Exception as e:
            logger.error(f"处理文档 {title} 时出错: {str(e)}")
            # 仅在doc_id存在时删除
            if 'doc_id' in locals() and doc_id:
                self.delete_documents([doc_id])
            return False

    def upload_category_files(self, dataset, path):
        """上传整个目录中的文件"""
        total_files = 0
        success_files = 0

        # 遍历目录获取所有文件
        for root, _, files in os.walk(path):
            for filename in files:
                file_path = os.path.join(root, filename)
                total_files += 1

                try:
                    with open(file_path, 'rb') as file:
                        content = file.read()

                    display_name = filename

                    logger.info(f"正在上传文件: {display_name}")
                    dataset.upload_documents([{
                        "display_name": display_name,
                        "blob": content
                    }])

                    # if upload_results and len(upload_results) > 0:
                    #     # 解析单个文件
                    #     document_id = upload_results[0].id
                    #     logger.info(f"开始解析文件: {display_name} (ID: {document_id})")
                    #     self.dataset.async_parse_documents([document_id])
                    #     success_files += 1
                    #     logger.success(f"文件 {display_name} 上传并解析成功")
                    # else:
                    #     logger.error(f"文件 {display_name} 上传失败，无返回结果")

                except Exception as e:
                    logger.error(f"处理文件失败 {file_path}: {str(e)}")

        # 输出汇总结果
        logger.info(
            f"处理完成: 总共 {total_files} 个文件，成功 {success_files} 个，失败 {total_files - success_files} 个")


