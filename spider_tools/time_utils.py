# from datetime import datetime, timedelta
# import pytz
# from dateutil import parser
# from loguru import logger
#
#
# def get_current_time(timezone='Asia/Shanghai'):
#     """获取当前时间"""
#     tz = pytz.timezone(timezone)
#     return datetime.now(tz)
#
#
# def parse_time(time_str, timezone='Asia/Shanghai'):
#     """解析时间字符串"""
#     try:
#         tz = pytz.timezone(timezone)
#         dt = parser.parse(time_str)
#         if dt.tzinfo is None:
#             dt = tz.localize(dt)
#         return dt
#     except Exception as e:
#         logger.error(f"时间解析错误: {e}")
#         return None
#
#
# def format_time(dt, format_str='%Y-%m-%d %H:%M:%S'):
#     """格式化时间"""
#     if isinstance(dt, str):
#         dt = TimeUtils.parse_time(dt)
#     return dt.strftime(format_str)
#
#
# def get_time_range(days=7, timezone='Asia/Shanghai'):
#     """获取时间范围"""
#     tz = pytz.timezone(timezone)
#     end_time = datetime.now(tz)
#     start_time = end_time - timedelta(days=days)
#     return start_time, end_time
#
#
# def is_within_time_range(dt, start_time, end_time):
#     """检查时间是否在指定范围内"""
#     if isinstance(dt, str):
#         dt = TimeUtils.parse_time(dt)
#     if isinstance(start_time, str):
#         start_time = TimeUtils.parse_time(start_time)
#     if isinstance(end_time, str):
#         end_time = TimeUtils.parse_time(end_time)
#     return start_time <= dt <= end_time
#
#
# def get_timestamp(dt=None):
#     """获取时间戳"""
#     if dt is None:
#         dt = datetime.now()
#     return int(dt.timestamp())
#
#
# def add_time(dt, days=0, hours=0, minutes=0, seconds=0):
#     """时间加减"""
#     if isinstance(dt, str):
#         dt = TimeUtils.parse_time(dt)
#     return dt + timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)
#
#
# def get_time_diff(start_time, end_time):
#     """计算时间差"""
#     if isinstance(start_time, str):
#         start_time = TimeUtils.parse_time(start_time)
#     if isinstance(end_time, str):
#         end_time = TimeUtils.parse_time(end_time)
#     return end_time - start_time
#
#
# def is_working_time(dt=None, timezone='Asia/Shanghai'):
#     """判断是否为工作时间（9:00-18:00）"""
#     if dt is None:
#         dt = get_current_time(timezone)
#     return 9 <= dt.hour < 18
#
#
# def get_next_working_time(dt=None, timezone='Asia/Shanghai'):
#     """获取下一个工作时间"""
#     if dt is None:
#         dt = get_current_time(timezone)
#
#     # 如果当前时间在工作时间内，直接返回
#     if is_working_time(dt):
#         return dt
#
#     # 如果当前时间在工作时间之前
#     if dt.hour < 9:
#         next_time = dt.replace(hour=9, minute=0, second=0, microsecond=0)
#     # 如果当前时间在工作时间之后
#     else:
#         next_time = (dt + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
#
#     return next_time
import re
from datetime import datetime
from typing import Optional, Union
from dateutil import parser
from loguru import logger

def get_current_time() -> str:
    """获取当前时间"""
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def parse_date_string(date_str: str) -> Optional[str]:
    """
    解析日期字符串，返回标准格式的日期字符串 (YYYY-MM-DD)
    Args:date_str: 输入的日期字符串，如 '发布时间：2022-12-28\r\n'
    Returns:str: 处理后的日期字符串，如 '2022-12-28'
    """
    try:
        # 清理字符串，只保留数字、分隔符和中文年月日
        date_str = re.sub(r'[^\d\-/年月日]', '', date_str.strip())
        # 替换中文分隔符
        date_str = date_str.replace('年', '-').replace('月', '-').replace('日', '')
        # 使用dateutil解析日期
        parsed_date = parser.parse(date_str, fuzzy=True)
        return parsed_date.strftime('%Y-%m-%d')
    except Exception as e:
        logger.error(f"处理日期字符串时发生错误: {str(e)}")
        return None


def format_timestamp(timestamp: Union[int, float, str]) -> Optional[str]:
    """
    将时间戳转换为标准格式的日期字符串 (YYYY-MM-DD HH:MM:SS)

    Args:
        timestamp: 时间戳（秒或毫秒）

    Returns:
        str: 格式化后的日期字符串
    """
    try:
        # 将时间戳转换为整数
        if isinstance(timestamp, str):
            timestamp = float(timestamp)

        # 处理毫秒时间戳
        if timestamp > 1e10:
            timestamp = timestamp / 1000

        # 转换为datetime对象
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime('%Y-%m-%d %H:%M:%S')

    except Exception as e:
        logger.error(f"格式化时间戳时发生错误: {str(e)}")
        return None