import re
from datetime import datetime
from typing import Optional, Union
from dateutil import parser
from loguru import logger


class TimeUtils:
    @staticmethod
    def get_current_time() -> str:
        """获取当前时间"""
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    @staticmethod
    def parse_date_string(date_str: str) -> Optional[str]:
        """
        解析日期字符串，返回标准格式的日期字符串 (YYYY-MM-DD)
        
        Args:
            date_str: 输入的日期字符串，如 '发布时间：2022-12-28\r\n'
            
        Returns:
            str: 处理后的日期字符串，如 '2022-12-28'
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

    @staticmethod
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