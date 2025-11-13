from spider_tools import BaseProcessor


class RAGProcessor(BaseProcessor):
    def __init__(self):
        self.user_info = {'email': 'zhangyulong@yutumed.com', 'password': 'qq12345678'}
        self.ragflow_config = {'api_key': 'ragflow-U1YzM4Mzg4MjAzMjExZjA5NzljMDAxNj','base_url': 'https://www.yutubang.com/'}
        super().__init__(dataset_name="招投标", description="招投标数据", ragflow_config=self.ragflow_config, user_info=self.user_info)

    # @retry(max_retries=50, retry_delay=10)
    def start(self):
        self.dataset = self.get_or_create_dataset()
        print(self.dataset.id)
        print(self.rag_object.list_datasets())
        print(self.reprocess_all_files(self.dataset))
        # self.reprocess_all_files(self.dataset, time_sleep=2)


if __name__ == "__main__":
    processor = RAGProcessor()
    processor.start()

