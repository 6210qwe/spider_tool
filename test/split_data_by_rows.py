import pandas as pd
import uuid


def split_data_by_rows(data, rows_per_file=200, source_ext='.xlsx', title_prefix=None, sheet_name=None):
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
    # 1. 处理Excel返回的字典（键为工作表名，值为DataFrame）
    if isinstance(data, dict):
        # 检查是否是Excel工作表字典（所有值都是DataFrame）
        if all(isinstance(v, pd.DataFrame) for v in data.values()):
            # 确定要处理的工作表
            if sheet_name is not None:
                # 按指定工作表名/索引提取
                if isinstance(sheet_name, int):
                    # 按索引取（如0表示第一个工作表）
                    sheet_names = list(data.keys())
                    target_sheet = sheet_names[sheet_name] if sheet_name < len(sheet_names) else None
                else:
                    # 按名称取
                    target_sheet = sheet_name
                if target_sheet not in data:
                    raise ValueError(f"Excel中不存在工作表: {sheet_name}")
                data = data[target_sheet]
            else:
                # 默认取第一个工作表
                data = next(iter(data.values()))

    # 2. 统一转换为DataFrame（处理数据库返回的list of dict）
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


def dataframe_to_bytes(df, file_format='xlsx'):
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
        print(f"DataFrame转字节流失败: {e}")
        raise
    finally:
        buffer.close()


# 使用示例
if __name__ == "__main__":
    # 测试数据
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
        
        # 转换为字节流测试
        content_bytes = dataframe_to_bytes(result['content'])
        print(f"  字节流大小: {len(content_bytes)} bytes")




