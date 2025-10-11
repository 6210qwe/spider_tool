from loguru import logger
import time
import hashlib

def get_proxy():
    tunnel = "g184.kdltps.com:15818"
    username = "t13632437348639"
    password = "10cc7lx7"
    proxies = {
        "http": f"http://{username}:{password}@{tunnel}",
        "https": f"http://{username}:{password}@{tunnel}"
    }
    return proxies


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


def calculate_md5(data):
    """计算数据的 MD5 哈希值"""
    try:
        md5_hash = hashlib.md5()
        if isinstance(data, bytes):
            md5_hash.update(data)
        elif isinstance(data, str):
            md5_hash.update(data.encode('utf-8'))
        else:
            raise ValueError("不支持的数据类型，支持字符串和字节对象")
        return md5_hash.hexdigest()
    except Exception as e:
        logger.error(f"计算 MD5 哈希值时出错: {e}")
        return None
