import redis
import json
from datetime import datetime
from loguru import logger


class RedisManager:
    def __init__(self, host='localhost', port=6379, db=0, password=None):
        """初始化Redis连接"""
        self.redis_client = redis.Redis(
            host=host,
            port=port,
            db=db,
            password=password,
            decode_responses=True
        )

    def is_url_visited(self, url, spider_name):
        """检查URL是否已经访问过"""
        key = f"visited_urls:{spider_name}"
        return self.redis_client.sismember(key, url)

    def mark_url_visited(self, url, spider_name):
        """标记URL为已访问"""
        key = f"visited_urls:{spider_name}"
        self.redis_client.sadd(key, url)

    def is_content_duplicate(self, content_hash, spider_name):
        """检查内容是否重复"""
        key = f"content_hashes:{spider_name}"
        return self.redis_client.sismember(key, content_hash)

    def mark_content_processed(self, content_hash, spider_name):
        """标记内容为已处理"""
        key = f"content_hashes:{spider_name}"
        self.redis_client.sadd(key, content_hash)

    def save_crawl_state(self, spider_name, state_data):
        """保存爬虫状态，用于断点续爬"""
        key = f"crawl_state:{spider_name}"
        state_data['last_update'] = datetime.now().isoformat()
        self.redis_client.set(key, json.dumps(state_data))

    def get_crawl_state(self, spider_name):
        """获取爬虫状态"""
        key = f"crawl_state:{spider_name}"
        state_data = self.redis_client.get(key)
        return json.loads(state_data) if state_data else None

    def save_incremental_data(self, spider_name, data):
        """保存增量数据"""
        key = f"incremental_data:{spider_name}"
        self.redis_client.rpush(key, json.dumps(data))

    def get_incremental_data(self, spider_name, start=0, end=-1):
        """获取增量数据"""
        key = f"incremental_data:{spider_name}"
        data_list = self.redis_client.lrange(key, start, end)
        return [json.loads(item) for item in data_list]

    def clear_incremental_data(self, spider_name):
        """清除增量数据"""
        key = f"incremental_data:{spider_name}"
        self.redis_client.delete(key)

    def set_spider_status(self, spider_name, status):
        """设置爬虫状态"""
        key = f"spider_status:{spider_name}"
        self.redis_client.set(key, status)

    def get_spider_status(self, spider_name):
        """获取爬虫状态"""
        key = f"spider_status:{spider_name}"
        return self.redis_client.get(key)

    def add_to_queue(self, spider_name, url, priority=0):
        """添加URL到爬取队列"""
        key = f"crawl_queue:{spider_name}"
        self.redis_client.zadd(key, {url: priority})

    def get_next_url(self, spider_name):
        """获取下一个要爬取的URL"""
        key = f"crawl_queue:{spider_name}"
        result = self.redis_client.zpopmin(key)
        return result[0] if result else None
