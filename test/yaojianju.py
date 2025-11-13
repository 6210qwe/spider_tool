import base64
import json
from io import BytesIO
from spider_tools.file_utils import *
import pandas as pd
from get_mysqldb import DatabasePool
from spider_tools import BaseProcessor
from loguru import logger


class RAGProcessor(BaseProcessor):
    def __init__(self):
        self.ragflow_config = {'api_key': 'ragflow-U1YzM4Mzg4MjAzMjExZjA5NzljMDAxNj','base_url': 'https://www.yutubang.com/'}
        # super().__init__(dataset_name="境内医疗器械", description="产品数据",ragflow_config=self.ragflow_config)
        self.mysql_db = DatabasePool(logger=logger, DB_HOST="rm-2ze9f04i505y525i19o.mysql.rds.aliyuncs.com",DB_PORT=3306, DB_DATABASE="yaojianju", DB_USER="zhangyanzhen", DB_PASSWORD="yutu#2025")
        self.knowledge = {
            "境内医疗器械": {
                "dataset_description": "产品数据-境内医疗器械",  # 知识库描述
                "tables": {
                    "境内医疗器械（注册）": "domestic_medical_devices_registration",
                    # "境内医疗器械（注册历史数据）": "domestic_medical_devices_registration_history_data",
                    # "境内医疗器械（备案）": "domestic_medical_devices_filing",
                    # "境内医疗器械（备案历史数据）": "domestic_medical_devices_filing_history_data",
                    # "一次性使用医疗器械产品": "disposable_medical_device_products"
                }
            },
            # "进口医疗器械": {
            #     "dataset_description": "产品数据-进口医疗器械",
            #     "tables": {
            #         "进口医疗器械（注册）": "imported_medical_devices_registration",
            #         "进口医疗器械（注册历史数据）": "imported_medical_devices_registration_history_data",
            #         "进口医疗器械（备案）": "imported_medical_devices_filing",
            #         "进口医疗器械（备案历史数据）": "imported_medical_devices_filing_history_data",
            #     }
            # },
            # "医疗器械生产企业": {
            #     "dataset_description": "企业数据-医疗器械生产企业",
            #     "tables": {
            #         "医疗器械生产企业（许可）": "medical_device_production_enterprises_licensing",
            #         "医疗器械生产企业（备案）": "medical_device_production_enterprises_filing",
            #     }
            # },
            # "医疗器械经营企业": {
            #     "dataset_description": "企业数据-医疗器械经营企业",
            #     "tables": {
            #         "医疗器械经营企业（许可）": "medical_device_operating_enterprises_licensing",
            #         "医疗器械经营企业（备案）": "medical_device_operating_enterprises_filing",
            #     }
            # }
        }

    @retry(max_retries=4, retry_delay=1)
    def upload_files(self, all_files_info):
        """批量上传所有文件，仅调用一次upload_documents, 并上传后自动解析"""
        self.dataset = self.get_or_create_dataset()
        doc_list = self.dataset.upload_documents(all_files_info)
        doc_ids = [doc.id for doc in doc_list]
        self.dataset.async_parse_documents(doc_ids)
        logger.info(f"成功批量上传并触发解析 {len(doc_ids)} 个文件")

    def init_knowledge(self, kb_name: str, description: str) -> BaseProcessor:
        """
        按需初始化单个知识库
        :param kb_name: 知识库名称（如“境内医疗器械”“进口医疗器械”）
        :return: 该知识库的BaseProcessor实例
        """
        # 初始化知识库
        kb_processor = BaseProcessor(dataset_name=kb_name,description=description,ragflow_config=self.ragflow_config)
        # 获取知识库数据集
        dataset = kb_processor.get_or_create_dataset()
        logger.info(f"知识库[{kb_name}]初始化成功，数据集ID：{dataset.id}")
        return dataset



    def get_data(self, table, dataset):
        sql = f"""select * from {table} where is_synced = 0"""
        results = self.mysql_db.execute_many_or_loop('', sql, [], operation='query')
        logger.info(f"获取到 {len(results)} 条记录")
        datas = []
        for result in results:
            result.pop('is_synced')
            result.pop('created_at')
            result.pop('updated_at')
            result.pop('md5_hash')
            item_id = result.pop('item_id')
            detail_id = result.pop('detail_id')
            detail_url = result['detail_url']
            if detail_url is None:
                detail_url =  "https://www.nmpa.gov.cn/datasearch/search-info.html?nmpa=" + self.str_to_base64(f"id={detail_id}&itemId={item_id}")
                item_data = {"detail_url": detail_url}
                self.mysql_db.update(table=table,condition={'detail_id': detail_id},data_dict=item_data)
                result['detail_url'] = detail_url
            # # 删除无需上传的字段（数据库维护字段）
            # for field in ['is_synced', 'created_at', 'updated_at', 'md5_hash', 'item_id', 'detail_id']:
            #     result.pop(field, None)
            datas.append(result)
        results = split_data_by_rows(results, rows_per_file=200, title_prefix=table)
        for result in results:
            title = result['title']
            content = dataframe_to_bytes(result['content'])
            doc = dataset.upload_documents([{
                "display_name": title,
                "blob": content,
            }])
            print(doc[0])

    # @retry(max_retries=50, retry_delay=1)
    def start(self):
        for kb_name, kb_config in self.knowledge.items():
            # 获取当前知识库的描述
            kb_desc = kb_config.get("dataset_description", "无描述")
            # 获取当前知识库下的表配置（内层字典）
            kb_tables = kb_config.get("tables", {})
            dataset = self.init_knowledge(kb_name, kb_desc)
            # 删除所有文件
            # dataset.delete_documents()
            logger.info(dataset)
            # # 第二层循环：遍历当前知识库下的“表名-数据库表名”
            for table_alias, db_table_name in kb_tables.items():
                logger.info(f"  - 表别名：{table_alias} → 数据库表名：{db_table_name}")
                self.get_data(db_table_name, dataset)



if __name__ == "__main__":
    processor = RAGProcessor()
    processor.start()


# 1、将所有数据转换为excel文件
# 2、将文件上传到知识库
# 3、获取到上传到知识库的文档的ID, 和每个文档对应的数据库的数据
# 4、批量更新数据库的doc_id, 有doc_id的数据视为已同步
# 5、检查数据库是否有注册证已过期数据, 有的话需要从知识库中去除掉