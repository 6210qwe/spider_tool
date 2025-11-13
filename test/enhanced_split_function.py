import pandas as pd
import uuid
from typing import List, Dict, Any, Union, Tuple
from loguru import logger


def split_data_by_rows(
    data, 
    rows_per_file=200, 
    source_ext='.xlsx', 
    title_prefix=None, 
    sheet_name=None
):
    """
    拆分数据（支持数据库查询结果、Excel文件数据）为多个数据块

    参数:
    data: 输入数据，支持：
          - 数据库查询结果（list of dict 或 pd.DataFrame）
          - Excel读取结果（pd.read_excel(sheet_name=None)返回的字典）
    rows_per_file (int): 每个数据块的行数
    source_ext (str): 生成标题的文件扩展名
    title_prefix (str): 输出文件的标题前缀
    sheet_name (str/int, 可选): 当data是Excel字典时，指定要处理的工作表名/索引
                               不指定则默认处理第一个工作表

    返回:
    list: 包含字典的列表，每个字典含'title'、'content'（DataFrame）和'mapping_info'（映射信息）
    """
    # 1. 处理Excel返回的字典
    if isinstance(data, dict):
        if all(isinstance(v, pd.DataFrame) for v in data.values()):
            if sheet_name is not None:
                if isinstance(sheet_name, int):
                    sheet_names = list(data.keys())
                    target_sheet = sheet_names[sheet_name] if sheet_name < len(sheet_names) else None
                else:
                    target_sheet = sheet_name
                if target_sheet not in data:
                    raise ValueError(f"Excel中不存在工作表: {sheet_name}")
                data = data[target_sheet]
            else:
                data = next(iter(data.values()))

    # 2. 统一转换为DataFrame
    if not isinstance(data, pd.DataFrame):
        try:
            data = pd.DataFrame(data)
        except Exception as e:
            raise ValueError(f"无法将数据转换为DataFrame: {e}")

    # 3. 处理空数据
    if data.empty:
        return []

    # 4. 拆分数据
    result = []
    total_rows = len(data)
    total_parts = (total_rows + rows_per_file - 1) // rows_per_file
    file_base = title_prefix if title_prefix else "database_data"

    for part in range(total_parts):
        unique_uuid = str(uuid.uuid4()).replace('-', '')
        base_with_uuid = f"{file_base}_{unique_uuid}"
        start_row = part * rows_per_file
        end_row = min((part + 1) * rows_per_file, total_rows)
        sub_df = data.iloc[start_row:end_row, :]

        title = f"{base_with_uuid}{source_ext}"
        
        # 构建映射信息
        mapping_info = {
            'part_index': part,
            'start_row': start_row,
            'end_row': end_row,
            'row_count': len(sub_df),
            'original_indices': sub_df.index.tolist()  # 原始DataFrame的索引
        }
        
        # 如果有detail_id列，保存detail_id列表
        if 'detail_id' in sub_df.columns:
            mapping_info['detail_ids'] = sub_df['detail_id'].tolist()
        
        result.append({
            'title': title,
            'content': sub_df,
            'mapping_info': mapping_info
        })

    return result


def dataframe_to_bytes(df: pd.DataFrame, file_format: str = 'xlsx') -> bytes:
    """
    将DataFrame转换为字节流
    
    参数:
    df: DataFrame对象
    file_format: 文件格式 ('xlsx', 'csv', 'json')
    
    返回:
    bytes: 文件内容的字节流
    """
    from io import BytesIO
    
    buffer = BytesIO()
    
    try:
        if file_format.lower() == 'xlsx':
            df.to_excel(buffer, index=False, engine='openpyxl')
        elif file_format.lower() == 'csv':
            df.to_csv(buffer, index=False, encoding='utf-8-sig')
        elif file_format.lower() == 'json':
            df.to_json(buffer, orient='records', force_ascii=False, indent=2)
        else:
            raise ValueError(f"不支持的文件格式: {file_format}")
        
        buffer.seek(0)
        return buffer.getvalue()
    
    except Exception as e:
        logger.error(f"DataFrame转字节流失败: {e}")
        raise
    finally:
        buffer.close()


class DocumentMappingManager:
    """文档映射管理器"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.mapping_cache = {}
    
    def upload_and_map_documents(
        self, 
        dataset, 
        split_results: List[Dict], 
        mapping_info: Dict,
        table_name: str
    ) -> Dict[str, str]:
        """
        上传文档并建立映射关系
        
        参数:
        dataset: RAGFlow数据集对象
        split_results: 拆分结果列表
        mapping_info: 映射信息
        table_name: 数据库表名
        
        返回:
        Dict[str, str]: 文档名称 -> 文档ID的映射
        """
        doc_name_to_id = {}
        
        # 1. 准备上传文件
        upload_files = []
        for result in split_results:
            content_bytes = dataframe_to_bytes(result['content'])
            upload_files.append({
                'display_name': result['title'],
                'blob': content_bytes
            })
        
        # 2. 批量上传
        uploaded_docs = dataset.upload_documents(upload_files)
        
        # 3. 建立文档名称到ID的映射
        for i, doc in enumerate(uploaded_docs):
            doc_name = split_results[i]['title']
            doc_name_to_id[doc_name] = doc.id
            logger.info(f"文档上传成功: {doc_name} -> ID: {doc.id}")
        
        # 4. 触发解析
        doc_ids = [doc.id for doc in uploaded_docs]
        dataset.async_parse_documents(doc_ids)
        
        # 5. 更新数据库doc_id
        self.update_database_doc_ids(doc_name_to_id, mapping_info, table_name)
        
        return doc_name_to_id
    
    def update_database_doc_ids(
        self, 
        doc_name_to_id: Dict[str, str], 
        mapping_info: Dict, 
        table_name: str
    ):
        """
        根据文档名称更新数据库的doc_id
        
        参数:
        doc_name_to_id: 文档名称到ID的映射
        mapping_info: 映射信息
        table_name: 数据库表名
        """
        for doc_name, doc_id in doc_name_to_id.items():
            if doc_name in mapping_info['documents']:
                doc_info = mapping_info['documents'][doc_name]
                
                # 如果有detail_ids，批量更新
                if 'detail_ids' in doc_info:
                    detail_ids = doc_info['detail_ids']
                    for detail_id in detail_ids:
                        try:
                            self.db_manager.update(
                                table=table_name,
                                condition={'detail_id': detail_id},
                                data_dict={'doc_id': doc_id, 'is_synced': 1}
                            )
                            logger.info(f"更新成功: detail_id={detail_id} -> doc_id={doc_id}")
                        except Exception as e:
                            logger.error(f"更新失败: detail_id={detail_id}, 错误: {e}")
                else:
                    logger.warning(f"文档 {doc_name} 没有detail_ids信息，无法更新数据库")
    
    def get_document_data_by_name(self, doc_name: str, mapping_info: Dict) -> Dict:
        """根据文档名称获取对应的数据信息"""
        return mapping_info['documents'].get(doc_name, {})
    
    def cleanup_expired_documents(self, table_name: str, dataset):
        """
        清理过期的注册证数据
        
        参数:
        table_name: 数据库表名
        dataset: RAGFlow数据集对象
        """
        # 1. 查询过期的注册证数据
        expired_sql = """
        SELECT doc_id FROM {} 
        WHERE doc_id IS NOT NULL 
        AND (expiry_date < CURDATE() OR status = 'expired')
        """.format(table_name)
        
        expired_records = self.db_manager.execute_many_or_loop(
            '', expired_sql, [], operation='query'
        )
        
        if not expired_records:
            logger.info("没有找到过期的注册证数据")
            return
        
        # 2. 获取需要删除的文档ID
        doc_ids_to_delete = [record['doc_id'] for record in expired_records]
        
        # 3. 从知识库中删除文档
        try:
            dataset.delete_documents(doc_ids_to_delete)
            logger.info(f"成功从知识库删除 {len(doc_ids_to_delete)} 个过期文档")
            
            # 4. 更新数据库状态
            for doc_id in doc_ids_to_delete:
                self.db_manager.update(
                    table=table_name,
                    condition={'doc_id': doc_id},
                    data_dict={'doc_id': None, 'is_synced': 0}
                )
            
            logger.info("数据库状态更新完成")
            
        except Exception as e:
            logger.error(f"删除过期文档失败: {e}")


# 使用示例
def example_usage():
    """使用示例"""
    # 假设你有数据库查询结果
    db_data = [
        {'detail_id': 1, 'name': '产品A', 'status': 'active'},
        {'detail_id': 2, 'name': '产品B', 'status': 'active'},
        {'detail_id': 3, 'name': '产品C', 'status': 'active'},
        {'detail_id': 4, 'name': '产品D', 'status': 'active'},
        {'detail_id': 5, 'name': '产品E', 'status': 'active'},
    ]
    
    # 拆分数据（每2行一个文件，便于测试）
    split_results = split_data_by_rows(
        data=db_data,
        rows_per_file=2,
        title_prefix="医疗器械注册证",
        source_ext='.xlsx'
    )
    
    print(f"拆分完成，共 {len(split_results)} 个文件")
    
    # 查看每个文件的映射信息
    for i, result in enumerate(split_results):
        print(f"\n文件 {i+1}: {result['title']}")
        print(f"  内容行数: {len(result['content'])}")
        print(f"  映射信息: {result['mapping_info']}")
        print(f"  detail_ids: {result['mapping_info'].get('detail_ids', 'N/A')}")
    
    return split_results


if __name__ == "__main__":
    example_usage()
