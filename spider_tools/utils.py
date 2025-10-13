import base64
import json
from loguru import logger
import time
import hashlib
from datetime import date, datetime
from dateutil.relativedelta import relativedelta


def retry(max_retries=8, retry_delay=5):
    """重试装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            last_exception = None
            for retry_count in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if retry_count < max_retries - 1:
                        time.sleep(retry_delay)
                        continue
            if last_exception:
                logger.error(f"{func.__name__} 执行失败，{max_retries} 次重试后失败，原因: {last_exception}")
            return None
        return wrapper
    return decorator


def to_bs64(self, s):
    """将字符串转换为Base64编码（简化版）"""
    return base64.b64encode(s.encode('utf-8')).decode('utf-8')

# def calculate_md5(data):
#     """计算数据的 MD5 哈希值"""
#     try:
#         if isinstance(data, bytes):
#             md5_hash = hashlib.md5()
#             md5_hash.update(data)
#
#         elif isinstance(data, str):
#             md5_hash = hashlib.md5()
#             md5_hash.update(data.encode('utf-8'))
#
#         elif isinstance(data, dict):
#             class DateTimeDateEncoder(json.JSONEncoder):
#                 def default(self, obj):
#                     if isinstance(obj, (datetime, date)):
#                         return obj.isoformat()
#                     return super().default(obj)
#
#             data_string = json.dumps(
#                 data,
#                 sort_keys=True,
#                 cls=DateTimeDateEncoder,
#                 ensure_ascii=False
#             )
#             return hashlib.md5(data_string.encode('utf-8')).hexdigest()
#
#         else:
#             print(data)
#             raise ValueError("不支持的数据类型，支持字符串、字节对象和字典")
#         return md5_hash.hexdigest()
#     except Exception as e:
#         logger.error(f"计算 MD5 哈希值时出错: {e}")
#         return None

def get_md5(data):
    """
    计算输入字符串的MD5值
    """
    md5_hash = hashlib.md5()
    md5_hash.update(data.encode('utf-8'))
    return md5_hash.hexdigest()

def calculate_md5(data):
    """计算数据的 MD5 哈希值，支持 bytes、str、dict 类型"""
    try:
        md5_hash = hashlib.md5()
        if isinstance(data, bytes):
            md5_hash.update(data)
        elif isinstance(data, str):
            # 字符串统一按 utf-8 编码为 bytes
            md5_hash.update(data.encode('utf-8'))

        elif isinstance(data, dict):
            class ExtendedJSONEncoder(json.JSONEncoder):
                def default(self, obj):
                    # 处理日期时间类型
                    if isinstance(obj, (datetime, date)):
                        return obj.isoformat()
                    # 处理元组（转为列表，避免序列化失败）
                    elif isinstance(obj, tuple):
                        return list(obj)
                    # 处理集合（转为排序后的列表，确保一致性）
                    elif isinstance(obj, set):
                        return sorted(list(obj))
                    # 其他不可序列化类型，明确报错
                    return super().default(obj)
            # 序列化字典：排序键 + 统一编码处理 + 严格控制特殊类型
            data_str = json.dumps(
                data,
                sort_keys=True,  # 键排序，确保字典顺序不影响哈希
                cls=ExtendedJSONEncoder,
                ensure_ascii=False,  # 若需与数据库CONCAT一致，可改为True（视场景而定）
                separators=(',', ':')  # 去除空格，减少冗余字符影响
            )
            md5_hash.update(data_str.encode('utf-8'))
        else:
            # 不支持的类型，记录日志并报错
            logger.error(f"不支持的数据类型: {type(data)}，数据: {str(data)[:100]}")  # 限制日志长度
            raise ValueError(f"不支持的数据类型: {type(data)}，仅支持 bytes、str、dict")
        return md5_hash.hexdigest()
    # 捕获特定异常，避免掩盖关键错误
    except TypeError as e:
        logger.error(f"数据序列化失败（可能包含不可处理的类型）: {e}，数据: {str(data)[:100]}")
        return None
    except Exception as e:
        logger.error(f"计算 MD5 时发生意外错误: {e}，数据: {str(data)[:100]}")
        return None


def generate_date_intervals(start_date, end_date=None, interval_value=1, interval_type='days', format='date'):
    """
    生成从起始日期到结束日期的时间间隔列表

    参数:
        start_date (str/datetime/date): 起始日期，可以是字符串(YYYY-MM-DD)、datetime或date对象
        end_date (str/datetime/date, optional): 结束日期，默认为当前日期
        interval_value (int): 时间间隔的值
        interval_type (str): 时间间隔类型，可选 'months', 'days', 'years' 等

    返回:
        list: 包含每个时间间隔的元组列表，格式为 (start_str, end_str)
    """
    # 解析起始日期
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, '%Y-%m-%d')

    # 解析结束日期（如果未提供则使用当前日期）
    if end_date is None:
        end_date = datetime.now()
    elif isinstance(end_date, str):
        end_date = datetime.strptime(end_date, '%Y-%m-%d')

    # 确保类型一致
    is_datetime = isinstance(start_date, datetime)
    if is_datetime != isinstance(end_date, datetime):
        raise ValueError("start_date和end_date必须是相同的类型")

    current = start_date
    intervals = []
    delta_kwargs = {interval_type: interval_value}

    while current <= end_date:
        next_interval = current + relativedelta(**delta_kwargs)
        actual_end = min(next_interval, end_date)
        # 根据输入类型选择格式
        if format == 'date':
            start_str = current.strftime('%Y-%m-%d')
            end_str = actual_end.strftime('%Y-%m-%d')
        else:
            start_str = current.strftime('%Y-%m-%d 00:00:00')
            end_str = actual_end.strftime('%Y-%m-%d 23:59:59')
        intervals.append((start_str, end_str))
        current = next_interval
    return intervals