import os
import requests
from loguru import logger
from spider_tools.utils import retry, calculate_md5
import urllib.parse
import ftfy
import magic
from spider_tools.file_utils import (
    clean_name,
    get_filename_from_response,
    start_detect_file_type,
    extract_archive,
    # convert_doc_to_docx_from_url,
)

# 忽略SSL警告（如需强制关闭校验，可在实例化时传入 verify_ssl=False）
requests.packages.urllib3.disable_warnings()

    
class FileDownloader:
    """
    通用文件下载器：支持HEAD探测、分块下载、重试、最小大小校验、文件名推断、返回字节或文件
    """

    def __init__(
            self,
            headers=None,
            proxies=None,
            retry_times=3,
            retry_delay=1,
            chunk_size=1024 * 1024,
            min_valid_size=1024,
            timeout=60,
            verify_ssl=True,
            deny_extensions=None,
    ):
        self.default_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
            "Accept": "*/*"
        }
        self.headers = headers if headers else self.default_headers
        self.proxies = proxies if proxies else {}
        self.retry_times = retry_times
        self.retry_delay = retry_delay
        self.chunk_size = chunk_size
        self.min_valid_size = min_valid_size
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.PDF_MAGIC_NUMBER = b"%PDF-"
        # 不下载的后缀（可扩展）
        self.deny_extensions = set((deny_extensions or [
            '.html', '.htm', '.js', '.css'
        ]))

    def _head(self, url):
        try:
            resp = requests.head(
                url,
                headers=self.headers,
                proxies=self.proxies,
                verify=self.verify_ssl,
                timeout=min(15, self.timeout),
                allow_redirects=True
            )
            resp.raise_for_status()
            return resp
        except Exception as e:
            logger.warning(f"HEAD探测失败{url}")
            return None

    def infer_filename(self, url, response=None, fallback_name=None):
        if response is not None:
            try:
                name = get_filename_from_response(response)
                if name:
                    return clean_name(name)
            except Exception:
                pass
        # 从URL推断
        try:
            from urllib.parse import urlparse
            name = os.path.basename(urlparse(url).path)
            if name:
                return clean_name(name)
        except Exception:
            pass
        return clean_name(fallback_name or "download.bin")

    def check_file_exist(self, save_path):
        if not os.path.exists(save_path):
            return False, "文件不存在，需下载"
        file_size = os.path.getsize(save_path)
        if file_size < self.min_valid_size:
            size = file_size
            try:
                os.remove(save_path)
            finally:
                return False, f"文件过小（{size}字节 < {self.min_valid_size}字节），已删除并重新下载"
        return True, f"文件已存在且有效（{file_size}字节），跳过下载"

    @retry(max_retries=3, retry_delay=1)
    def _stream_download(self, url, save_path):
        try:
            with requests.get(
                url,
                headers=self.headers,
                proxies=self.proxies,
                verify=self.verify_ssl,
                timeout=self.timeout,
                stream=True
            ) as resp:
                resp.raise_for_status()
                with open(save_path, 'wb') as f:
                    for chunk in resp.iter_content(chunk_size=self.chunk_size):
                        if chunk:
                            f.write(chunk)
            size = os.path.getsize(save_path)
            if size < self.min_valid_size:
                os.remove(save_path)
                raise Exception(f"下载文件过小（{size}字节），判定为损坏")
            return True, f"下载成功（保存路径：{save_path}）"
        except Exception as e:
            if os.path.exists(save_path):
                os.remove(save_path)
            raise e

    @retry(max_retries=2, retry_delay=1)
    def _get_bytes(self, url):
        with requests.get(
            url,
            headers=self.headers,
            proxies=self.proxies,
            verify=self.verify_ssl,
            timeout=self.timeout,
            stream=True
        ) as resp:
            resp.raise_for_status()
            content = resp.content
            if len(content) < self.min_valid_size:
                raise Exception(f"下载内容过小（{len(content)}字节）")
            return content

    def probe(self, url):
        head_resp = self._head(url)
        info = {
            'status': None,
            'content_type': None,
            'content_length': None,
            'headers': {}
        }
        if head_resp is not None:
            info['status'] = head_resp.status_code
            info['content_type'] = (head_resp.headers.get('Content-Type') or '').lower()
            info['content_length'] = head_resp.headers.get('Content-Length')
            info['headers'] = dict(head_resp.headers)
        return info

    def is_downloadable_url(self, url):
        """基础URL校验：协议、片段、扩展名过滤"""
        try:
            if not url or '#' in url:
                return False
            from urllib.parse import urlparse
            parsed = urlparse(url)
            if parsed.scheme not in ('http', 'https'):
                return False
            ext = os.path.splitext(parsed.path)[1].lower()
            if ext and ext in self.deny_extensions:
                return False
            if not parsed.path or parsed.path.endswith('/'):
                # 目录链接通常不是直接下载资源
                return False
            return True
        except Exception:
            return False

    def is_valid_pdf(self, url):
        """PDF 合法性校验（HEAD + 文件头魔数）"""
        try:
            head_resp = self._head(url)
            if head_resp is not None:
                ctype = (head_resp.headers.get('Content-Type') or '').lower()
                if 'application/pdf' in ctype:
                    return True
            with requests.get(
                url,
                headers=self.headers,
                proxies=self.proxies,
                verify=self.verify_ssl,
                timeout=min(30, self.timeout),
                stream=True
            ) as resp:
                resp.raise_for_status()
                first5 = next(resp.iter_content(chunk_size=5), b'')
                return first5.startswith(self.PDF_MAGIC_NUMBER)
        except Exception as e:
            logger.error(f"PDF校验失败（{url}）：{e}")
            return False

    def download(self, url, save_to_disk=True, save_dir=None, file_name=None, require_pdf=False):
        """
        下载文件。
        强制默认执行 URL 合法性校验（协议/片段/后缀/目录链接过滤）。
        - save_to_disk=True（默认）：保存到磁盘，未指定 save_dir 时保存到当前工作目录，返回 (ok, save_path)
        - save_to_disk=False：不落盘，直接返回字节内容，返回 (ok, bytes)
        """
        try:
            # URL 合法性强制校验
            if not self.is_downloadable_url(url):
                raise Exception("不合法的下载链接或被过滤的后缀")
            if require_pdf and not self.is_valid_pdf(url):
                raise Exception("非PDF文件或PDF校验不通过")
            if not save_to_disk:
                content = self._get_bytes(url)
                if not content:
                    raise Exception("下载失败")
                return True, content

            # 保存到磁盘：默认保存到当前工作目录
            target_dir = save_dir or os.getcwd()
            os.makedirs(target_dir, exist_ok=True)
            name = file_name or self.infer_filename(url)
            save_path = os.path.abspath(os.path.join(target_dir, clean_name(name)))
            skip, msg = self.check_file_exist(save_path)
            if skip:
                logger.info(f"[{url}] {msg}")
                return True, save_path
            success, msg = self._stream_download(url, save_path)
            if success:
                logger.success(f"[{url}] {msg}")
                return True, save_path
            return False, save_path
        except Exception as e:
            logger.error(f"[{url}] 下载处理异常：{str(e)}")
            return False, None

    def download_bytes(self, url, require_pdf=False):
        """便捷方法：下载字节；同样强制执行 URL 合法性校验，可选 require_pdf"""
        return self.download(url, save_to_disk=False, require_pdf=require_pdf)

    # ================== 统一整合的下载相关高阶方法 ==================

    @retry(max_retries=3, retry_delay=1)
    def get_response(self, url):
        """统一的 GET 响应（沿用全局 headers/verify/timeout）"""
        headers = {
            'User-Agent': self.headers.get('User-Agent', 'Mozilla/5.0')
        }
        response = requests.get(url, headers=headers, timeout=min(self.timeout, 60), verify=self.verify_ssl)
        response.raise_for_status()
        return response

    def get_file_extension(self, url):
        """根据文件内容的 MIME 推断扩展名"""
        response = self.get_response(url)
        file_content = response.content
        MIME_TO_EXT = {
            "application/pdf": "pdf",
            "application/msword": "doc",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
            "application/vnd.ms-excel": "xls",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
            "application/vnd.ms-powerpoint": "ppt",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
            "text/plain": "md",
            "text/csv": "csv",
            "text/markdown": "md",
            "image/jpeg": "jpg",
            "image/png": "png",
            "image/gif": "gif",
            "image/svg+xml": "svg",
            "image/webp": "webp",
            "application/zip": "zip",
            "application/x-tar": "tar",
            "application/gzip": "gz",
            "application/x-bzip2": "bz2",
            "application/x-7z-compressed": "7z",
            "application/x-rar": "rar",
            "application/json": "json",
            "application/xml": "xml",
            "text/html": "html",
            "application/javascript": "js",
            "text/css": "css",
        }
        try:
            mime_type = magic.from_buffer(file_content, mime=True)
            if mime_type in MIME_TO_EXT:
                return MIME_TO_EXT[mime_type]
        except Exception as e:
            logger.error(f"错误: 判断文件类型失败 - {e}")
        return ""

    def check_file(self, title, url=None, content=None):
        """下载/或接收内容 → 识别类型 → doc→docx → md5 命名，返回 (content, ext, name)"""
        if content is None:
            ext = start_detect_file_type(url, title)
            ok, content = self.download_bytes(url)
            if not ok or not content:
                raise Exception("下载失败")
        else:
            ext = start_detect_file_type(file_url=None, file_name=title)

        if ext == "doc":
            content = convert_doc_to_docx_from_url(url or '', content)
            ext = "docx"

        md5 = calculate_md5(content)
        name = md5 + "." + ext
        return content, ext, name

    def get_file(self, url, title):
        """根据 url 获取文件；若为压缩包则展开并逐个规范化"""
        files = []
        content, ext, name = self.check_file(title=title, url=url)
        if ext in ["zip", "rar", "tar", "gz", "bz2", "7z"]:
            extracted_files = extract_archive(content, name, ext)
            for content, new_name in extracted_files:
                content, ext, name = self.check_file(title=new_name, content=content)
                logger.info(f"已提取文件新名字：{name}")
                files.append((content, name))
        else:
            files.append((content, name))
        return files
