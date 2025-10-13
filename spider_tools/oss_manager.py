import html2text
import oss2
import pymysql
from spider_tools.file_utils import *
# from utils import calculate_md5
from fake_useragent import UserAgent
from urllib.parse import urljoin
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# OSS初始化和文件上传
class OSSManager:
    def __init__(self, endpoint, bucket_name, directory, 
                 db_config=None, oss_credentials=None):
        self.endpoint = endpoint
        self.bucket_name = bucket_name
        self.directory = directory
        
        # 优先使用传入的 OSS 凭证
        if oss_credentials:
            self.security_token = oss_credentials['security_token']
            self.access_key_id = oss_credentials['access_key_id']
            self.access_key_secret = oss_credentials['access_key_secret']
        else:
            # 从数据库获取（需要传入数据库配置）
            if not db_config:
                raise ValueError("必须提供 OSS 凭证或数据库配置")
            self.security_token, self.access_key_id, self.access_key_secret = \
                self.get_oss_credentials_from_db(db_config)
        
        self.bucket = self.initialize_oss_bucket(
            self.security_token, self.access_key_id, self.access_key_secret
        )
    def get_oss_credentials_from_db(self, db_config):
        conn = pymysql.connect(**db_config)
        # 获取到 oss_sts 表中的的数据
        sql_select = "select security_token,access_key_id, access_key_secret from oss_sts"
        cur = conn.cursor()
        cur.execute(sql_select)
        oss_sts = cur.fetchone()
        security_token = oss_sts[0]
        access_key_id = oss_sts[1]
        access_key_secret = oss_sts[2]
        conn.close()
        return security_token, access_key_id, access_key_secret

    def initialize_oss_bucket(self, security_token, access_key_id, access_key_secret):
        auth = oss2.StsAuth(access_key_id, access_key_secret, security_token)
        return oss2.Bucket(auth, self.endpoint, self.bucket_name)

    def upload_file_to_oss(self, file_content, oss_path):
        oss_path = self.directory + "/" + oss_path
        result = self.bucket.put_object(oss_path, file_content)
        if result.status == 200:
            file_url = self.get_file_url(oss_path)
            logger.info(f"文件 {oss_path} 上传到 OSS 成功，访问链接: {file_url}")
            return file_url
        else:
            logger.error(f"文件 {oss_path} 上传到 OSS 失败，状态码: {result.status}")

    def get_file_url(self, file_path):
        file_url = f"http://{self.bucket.bucket_name}.{self.bucket.endpoint.split('//')[1]}/{file_path}"
        return file_url

    def upload_html_to_oss(self, html, oss_object_name):
        file_url = self.get_file_url(oss_object_name)
        # exist = self.bucket.object_exists(oss_object_name)
        # if exist:
        #     logger.info(f"文件 {oss_object_name} 已存在，链接为{file_url}跳过上传")
        #     return file_url
        result = self.bucket.put_object(oss_object_name, html)
        if result.status == 200:
            logger.info(f"html文件上传成功！OSS对象名称: {oss_object_name}, 文件OSS地址为: {file_url}")
            return file_url
        else:
            logger.error(f"html文件上传失败，状态码: {result.status}")
            raise Exception("html上传失败")

    def get_new_name(self, filename, md5_hash):
        # 分割文件名和扩展名
        base_name, ext = os.path.splitext(filename)
        # 检查文件名中是否包含 + 或 =
        if '+' in base_name or '=' in base_name:
            new_filename = f"{md5_hash}{ext}"
        else:
            # 拼接新的文件名
            new_filename = f"{base_name}_{md5_hash}{ext}"
        return new_filename

    def detect_file_type(self, response, item_data):
        file_name = item_data['file_name']
        file_url = item_data['file_url']
        file_type = start_detect_file_type(file_url=file_url,file_name=file_name)
        if not file_type:
            file_name = get_filename_from_response(response)
            file_type = start_detect_file_type(file_url=file_url, file_name=file_name)
        supported_extensions = ('zip', 'tar', 'tar.gz', 'tgz', 'tar.bz2', 'tbz2', 'rar', 'gz')
        if file_type in supported_extensions:
            extracted_files = extract_archive(response.content, file_name, file_type)
            for content, new_name in extracted_files:
                item_data['md5_hash'] = calculate_md5(content)
                valid_oss_filename = validate_and_fix_filename(new_name)
                valid_oss_filename = self.get_new_name(valid_oss_filename, item_data['md5_hash'])
                file_oss_url = self.upload_file_to_oss(content, valid_oss_filename)
                file_new_type = start_detect_file_type(file_name=valid_oss_filename)
                file_size = len(content)
                item_data['file_name'] = file_name
                item_data['file_oss_name'] = valid_oss_filename
                item_data['file_oss_url'] = file_oss_url
                item_data['file_size'] = file_size
                item_data['file_type'] = file_type
                item_data['file_new_type'] = file_new_type
                return item_data
        else:
            name, ext = os.path.splitext(file_name)
            if not ext:
                file_name = file_name + "." + file_type
            valid_oss_filename = validate_and_fix_filename(file_name)
            item_data['md5_hash'] = calculate_md5(response.content)
            if file_type == 'md':
                item_data['file_oss_url'] = file_url
            else:
                valid_oss_filename = self.get_new_name(valid_oss_filename, item_data['md5_hash'])
                item_data['file_oss_url'] = self.upload_file_to_oss(response.content, valid_oss_filename)
            file_size = len(response.content)
            item_data['file_name'] = file_name
            item_data['file_oss_name'] = valid_oss_filename
            item_data['file_size'] = file_size
            item_data['file_type'] = file_type
            item_data['file_new_type'] = file_type
            return item_data



    def save_markdown(self, site_name, item_name, html_content, base_url=None):
        """将详情页保存为markdown上传到云端"""
        converter = html2text.HTML2Text()  # 创建 html2text 转换器实例
        converter.ignore_links = False  # 不忽略链接
        if base_url:
            html = self.extract_and_replace_img_links(html_content, base_url)
            markdown = converter.handle(html)
        else:
            markdown = converter.handle(html_content)
        md5_hash = calculate_md5(markdown)
        # name = site_name + "/" + item_name + "_" +md5_hash + ".md"
        # name = validate_and_fix_filename(name)
        new_name = site_name + "/" + md5_hash + ".md"
        file_url = self.upload_html_to_oss(markdown, new_name)
        return file_url

    def extract_and_replace_img_links(self, html_content, base_url):
        """
        从 HTML 文本中提取 img 标签的链接，与 base_url 拼接后替换原有链接, 解决md中图片为空的问题
        :param html_content: HTML 文本内容
        :param base_url: 基础 URL
        :return: 替换后的 HTML 文本
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        img_tags = soup.find_all('img')
        for img in img_tags:
            src = img.get('src')
            if src:
                full_url = urljoin(base_url, src)
                img['src'] = full_url
        return str(soup)

    def parse(self, file_info):
        item_data = {'file_url': file_info['href'], 'file_name': file_info['file_name']}
        response = self.get_response(item_data['file_url'])
        item_data = self.detect_file_type(response, item_data)
        return item_data

    @retry(max_retries=1, retry_delay=1)
    def get_response(self, url):
        # headers = {
        #     'Connection': 'keep-alive',
        #     'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0',
        # }
        response = requests.get(url, timeout=60, verify=False)
        response.raise_for_status()
        return response
