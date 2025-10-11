import os
import re
import hashlib
from urllib.parse import urlparse
from loguru import logger
# import requests
from curl_cffi import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import os
import tempfile
import zipfile
import tarfile
import rarfile
import gzip
import shutil
import urllib
import ftfy
import hashlib
import re
from spider_tools.utils import *



def validate_and_fix_filename(filename):
    """
    校验文件名是否包含非法字符，若包含则进行修正
    :param filename: 待校验的文件名
    :return: 合法的文件名
    """
    # 定义非法字符的正则表达式
    illegal_char_regex = re.compile(r'[\\*?:"<>|]')
    replacement_char = '_'
    if illegal_char_regex.search(filename):
        # 若包含非法字符，将非法字符替换为指定的替换字符
        new_filename = illegal_char_regex.sub(replacement_char, filename)
        # logger.info(f"原文件名 {filename} 包含非法字符，已修正为 {new_filename}")
        return new_filename.replace("&nbsp", '')
    return filename


def extract_file_names(html_content, class_name=None, base_url=None):
    """只用于解析文档中的文件url地址"""
    # 创建 BeautifulSoup 对象，用于解析 HTML 内容
    soup = BeautifulSoup(html_content, 'html.parser')
    # 定义要查找的标签列表
    target_tags = ['a', 'iframe']
    # target_tags = ['a', 'iframe', 'img']
    # 定义要过滤的文件名关键词
    filtered_keywords = {'原文链接地址', '原文链接', '请到原网址下载附件', '详情请见原网站'}
    # 存储提取的文件信息
    files = []

    # 根据 class_name 筛选标签
    if class_name:
        target_elements = soup.find_all(class_=class_name)
        # all_tags = soup.find_all(target_tags, class_=class_name)
        if not target_elements:
            return []
        # 创建一个新的 BeautifulSoup 对象，只包含目标元素
        new_soup = BeautifulSoup(''.join(str(element) for element in target_elements), 'html.parser')
        all_tags = new_soup.find_all(target_tags)
    else:
        all_tags = soup.find_all(target_tags)

    # 遍历查找的标签
    for tag in all_tags:
        # 根据标签类型确定链接属性
        # link_attr = 'href' if tag.name == 'a' else 'src' if tag.name == 'iframe' else None
        # if not link_attr:
        #     continue
        # 根据标签类型确定链接属性
        if tag.name == 'a':
            link_attr = 'href'
        elif tag.name == 'iframe':
            link_attr = 'src'
        elif tag.name == 'img':
            link_attr = 'src'
        else:
            continue

        # 获取链接地址
        href = tag.get(link_attr)
        if not href:
            continue

        # 处理相对链接
        if base_url and not href.startswith(('http:', 'https:')):
            href = base_url.rstrip('/') + '/' + href.lstrip('/')

        # 过滤以 .html 或 .htm 结尾的链接
        if href.lower().endswith(('.html', '.htm')):
            continue

        # 解析链接地址
        parsed_url = urlparse(href)
        # 检查链接是否为有效的 URL
        if not (parsed_url.scheme and parsed_url.netloc):
            continue

        # 根据标签类型提取文件名
        if tag.name == 'a':
            # file_name = tag.get_text(strip=True)
            # 优先使用title属性
            file_name = tag.get('title', '').strip()
            if not file_name:
                # 如果没有title，使用text内容
                file_name = tag.get_text(strip=True)
        elif tag.name == 'iframe':
            file_name = href.split('/')[-1]
        elif tag.name == 'img':
            # 优先使用title属性
            file_name = tag.get('title', '').strip()
            if not file_name:
                # 如果没有title，使用alt属性
                file_name = tag.get('alt', '').strip()
            if not file_name:
                # 如果都没有，使用链接的最后一部分
                file_name = href.split('/')[-1]

        # 过滤包含特定关键词的文件名
        if any(keyword in file_name for keyword in {'http', 'https', 'www', '.cn'}):
            continue

        file_name = file_name.strip()
        # 检查文件名是否不在过滤列表中
        if file_name and file_name not in filtered_keywords:
            file_name = validate_and_fix_filename(file_name)
            ext = start_detect_file_type(href, file_name)
            if ext:
                SUPPORTED_FILE_TYPES = {
                    # 文档类
                    'doc', 'docx', 'wps', 'pdf', 'txt', 'rtf',
                    # 表格类
                    'xls', 'xlsx', 'et', 'csv',
                    # 演示类
                    'ppt', 'pptx',
                    # 图片类
                    'jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff',
                    # 压缩类
                    'zip', 'rar', '7z','tar', 'gz', 'tgz', 'tar.gz', 'bz2',
                    # 扫描类
                    'pdf', 'tiff',
                    # # 其他专业文件
                    # 'xml', 'json',
                    # # 视频类
                    # 'mp4', 'avi', 'mov',
                    # # 音频类
                    # 'mp3', 'wav'
                }
                if ext in SUPPORTED_FILE_TYPES:
                    # 有后缀名，直接添加到结果列表
                    files.append({
                        'file_name': file_name,
                        'href': href,
                    })
            else:
                try:
                    # 使用 requests.head 进行请求，只获取头部信息
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
                    response = requests.head(href, timeout=30, headers=headers)
                    response.raise_for_status()
                    # 获取 Content-Type
                    content_type = response.headers.get('Content-Type', '')
                    if content_type:
                        # 处理可能的编码问题
                        if isinstance(content_type, bytes):
                            content_type = content_type.decode('utf-8')
                        # 获取 MIME 类型
                        mime_type = content_type.split(';')[0].strip().lower()
                        # 检查是否为 HTML 类型
                        if 'text/html' not in mime_type:
                            files.append({
                                'file_name': file_name,
                                'href': href,
                            })
                except Exception as e:
                    logger.info(f"请求失败: {href}, 错误: {str(e)}")
                    continue
    return files


def set_unrar_path():
    # 获取当前文件所在目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    unrar_path = os.path.join(current_dir, "UnRAR.exe")

    # 检查UnRAR.exe是否存在
    if os.path.exists(unrar_path):
        rarfile.UNRAR_TOOL = unrar_path
        return True
    else:
        logger.error(f"未找到UnRAR.exe，请确保文件位于: {unrar_path}")
        return False
def extract_archive(archive_content, archive_name):
    # 设置UnRAR.exe路径
    if not set_unrar_path():
        logger.error("无法设置UnRAR.exe路径，RAR文件解压可能失败")

    temp_dir = tempfile.mkdtemp(prefix=f"extract_{archive_name}_")
    try:
        archive_path = os.path.join(temp_dir, archive_name)
        with open(archive_path, 'wb') as f:
            f.write(archive_content)
        archive_base_name = os.path.splitext(archive_name)[0]
        results = []
        if archive_name.endswith('.zip'):
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                for info in zip_ref.infolist():
                    if not info.is_dir():
                        content = zip_ref.read(info.filename)
                        try:
                            filename = info.filename.encode('cp437').decode('gbk')
                        except (UnicodeEncodeError, UnicodeDecodeError):
                            filename = info.filename
                        new_filename = f"{archive_base_name}/{filename}"
                        results.append((content, new_filename))
        elif archive_name.endswith(('.tar', '.tar.gz', '.tgz', '.tar.bz2', '.tbz2')):
            if archive_name.endswith('.tar'):
                mode = 'r'
            elif archive_name.endswith(('.tar.gz', '.tgz')):
                mode = 'r:gz'
            elif archive_name.endswith(('.tar.bz2', '.tbz2')):
                mode = 'r:bz2'
            with tarfile.open(archive_path, mode) as tar_ref:
                for member in tar_ref.getmembers():
                    if member.isfile():
                        content = tar_ref.extractfile(member).read()
                        try:
                            filename = member.name.encode('cp437').decode('gbk')
                        except (UnicodeEncodeError, UnicodeDecodeError):
                            filename = member.name
                        new_filename = f"{archive_base_name}/{filename}"
                        results.append((content, new_filename))
        elif archive_name.endswith('.rar'):
            with rarfile.RarFile(archive_path, 'r') as rar_ref:
                for file in rar_ref.infolist():
                    if not file.isdir():
                        content = rar_ref.read(file.filename)
                        try:
                            filename = file.filename.encode('cp437').decode('gbk')
                        except (UnicodeEncodeError, UnicodeDecodeError):
                            filename = file.filename
                        new_filename = f"{archive_base_name}/{filename}"
                        results.append((content, new_filename))
        elif archive_name.endswith('.gz'):
            try:
                with gzip.open(archive_path, 'rb') as f_in:
                    content = f_in.read()
                    out_file_name = os.path.splitext(archive_name)[0]
                    try:
                        filename = out_file_name.encode('cp437').decode('gbk')
                    except (UnicodeEncodeError, UnicodeDecodeError):
                        filename = out_file_name
                    new_filename = f"{archive_base_name}/{filename}"
                    results.append((content, new_filename))
            except Exception as e:
                logger.error(f"解压缩 GZ 文件 {archive_name} 时出错: {e}")
        else:
            logger.error(f"不支持的压缩包类型: {archive_name}")
        return results
    except Exception as e:
        logger.error(f"处理压缩包 {archive_name} 时出错: {e}")
        return []
    finally:
        shutil.rmtree(temp_dir)

def get_filename_from_response(response):
    cd = response.headers.get('Content-Disposition')
    if isinstance(cd, bytes):
        cd = cd.decode('utf-8')

    filename = None
    if cd:
        # 先尝试处理 filename*=
        if 'filename*=' in cd:
            parts = cd.split('filename*=')
            if len(parts) > 1:
                sub_parts = parts[1].split("''")
                if len(sub_parts) == 2:
                    encoded_filename = sub_parts[1]
                    filename = urllib.parse.unquote(encoded_filename)
        # 若 filename*= 未找到，再尝试处理 filename=
        elif 'filename=' in cd:
            parts = cd.split('filename=')
            if len(parts) > 1:
                filename_part = parts[1]
                # 处理可能的引号包裹
                if filename_part.startswith('"') and filename_part.endswith('"'):
                    filename = filename_part[1:-1]
                else:
                    # 若没有引号，直接使用
                    filename = filename_part
                try:
                    filename = urllib.parse.unquote(filename)
                except ValueError:
                    # 处理 URL 解码异常
                    logger.info(f"URL 解码异常: {filename_part}")
                    filename = None
    # 若前面都没提取到文件名，从 URL 中提取
    if not filename:
        filename = urllib.parse.urlparse(response.url).path.split('/')[-1]

    # 使用 ftfy 修复文件名
    return ftfy.fix_text(filename) if filename else None


def start_detect_file_type(file_url=None, file_name=None):
    sources = []
    if file_url is not None:
        sources.append(urlparse(file_url).path)
    if file_name is not None:
        sources.append(file_name)

    for source in sources:
        # 使用正则表达式匹配文件后缀名
        match = re.search(r'\.([a-zA-Z]+)$', source)
        if match:
            return match.group(1).lower()
    return ''

def get_html(html, class_name=None, id=None):
    if class_name is None:
        return html
    soup = BeautifulSoup(html, 'html.parser')
    detail_elements = soup.find_all(class_=class_name, id=id)
    # 修正：如果列表不为空，将列表元素的文本内容拼接成字符串
    if detail_elements:
        result = ''.join([str(element) for element in detail_elements])
        return result
    return ''


def extract_item_content(html):
    soup = BeautifulSoup(html, 'html.parser')
    item_content = soup.get_text().replace("\xa0", '').replace("\n", '')
    # 进一步去除可能残留的方括号
    item_content = item_content.strip('[]')
    return item_content

def extract_and_clean_title(title):
    """
    从 HTML 中提取标题并进行清理
    :param html: 包含 HTML 内容的对象
    :return: 清理后的标题字符串，如果未找到标题则返回空字符串
    """
    if title:
        # 去除换行符、制表符、回车符和空格
        cleaned_title = title.replace("\n", "").replace("\t", "").replace("\r", "").replace(" ", "")
        return cleaned_title
    return ""
