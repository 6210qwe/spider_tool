import time
from urllib.parse import urlparse
import html2text
from curl_cffi import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import zipfile
import tarfile
import rarfile
import gzip
import shutil
import urllib
import ftfy
import re
from spider_tools.utils import *
import os
import tempfile
import requests
from pathlib import Path
import magic
import os
import pandas as pd
from loguru import logger
import uuid

from pathvalidate import sanitize_filename
from pathvalidate.handler import ReservedNameHandler

def clean_name(filename):
    """基于pathvalidate的文件名清理函数，适配Windows系统"""
    # 1. 用pathvalidate清理非法字符（替换为下划线），处理保留名
    legal_name = sanitize_filename(
        filename,
        replacement_text="_",  # 非法字符替换为下划线
        platform="windows",  # 强制按Windows规则处理（即使在Linux环境）
        reserved_name_handler=ReservedNameHandler.add_trailing_underscore  # 保留名后加下划线（如"con"→"con_"）
    )
    # 2. 额外移除&nbsp（根据你的业务需求）
    legal_name = legal_name.replace("&nbsp", "")
    return legal_name


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
    if isinstance(file_url, bytes):
        file_url = file_url.decode('utf-8', errors='replace')

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
        else:
            ext = get_file_extension(file_url)
            if ext:
                supported_file_types = {
                    'doc', 'docx', 'wps', 'pdf', 'txt', 'rtf',
                    'xls', 'xlsx', 'et', 'csv',
                    'ppt', 'pptx',
                    'jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff',
                    'zip', 'rar', '7z', 'tar', 'gz', 'tgz', 'tar.gz', 'bz2',
                }
                if ext in supported_file_types:
                    return ext.lower()
    logger.info(f"未识别文件类型, url地址为{file_url}, 名称为{file_name}")
    return ''

def extract_archive(archive_content, archive_name, file_type):
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
        if file_type == "zip":
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
        elif file_type in ('tar', 'tar.gz', 'tgz', 'tar.bz2', 'tbz2'):
            if file_type == '.tar':
                mode = 'r'
            elif file_type in ('tar.gz', 'tgz'):
                mode = 'r:gz'
            elif file_type in ('tar.bz2', 'tbz2'):
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
        elif file_type == 'rar':
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
        elif file_type == 'gz':
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
            logger.error(f"不支持的压缩包类型: {archive_name}, {file_type}")
        return results
    except Exception as e:
        logger.error(f"处理压缩包 {archive_name} 时出错: {e}")
        return []
    finally:
        shutil.rmtree(temp_dir)


@retry(max_retries=2, retry_delay=1)
def convert_doc_to_docx_from_url(url, content=None):
    # 需要提前在win上安装
    # https://mirror-hk.koddos.net/tdf/libreoffice/stable/25.8.1/win/x86_64/LibreOffice_25.8.1_Win_x86-64.msi
    # 从URL下载doc文件并转换为docx格式，返回转换后的内容, 用来解决ragflow不能解析doc格式的问题
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir_path = Path(temp_dir)
            temp_doc = temp_dir_path / "temp.doc"
            temp_docx = temp_dir_path / "temp.docx"

            # 1. 处理内容（下载/复用）
            if not content:
                response = requests.get(url, timeout=120, verify=False)
                response.raise_for_status()
                content = response.content

            # 2. 新增：校验DOC文件头（判断是否为有效DOC文件）
            doc_header = b"\xD0\xCF\x11\xE0"  # 所有正常DOC文件的开头标识
            if not content.startswith(doc_header):
                logger.error(f"不是有效DOC文件（文件头不匹配）：{url}")
                return None
            if len(content) < 1024:
                logger.error(f"DOC文件过小（{len(content)}字节）：{url}")
                return None

            # 3. 写入临时文件
            temp_doc.write_bytes(content)

            # 4. 执行转换命令
            soffice_path = r"D:\software\Libre\program\soffice.exe"
            result = subprocess.run(
                [soffice_path, "--headless", "--convert-to", "docx", "--outdir", str(temp_dir_path), str(temp_doc)],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", timeout=30
            )

            # 5. 打印soffice的详细日志（定位错误原因）
            if result.returncode != 0:
                logger.error(f"soffice stdout：{result.stdout}")  # 打印soffice的标准输出
                logger.error(f"soffice stderr：{result.stderr}")  # 打印soffice的错误输出
                raise Exception(f"转换失败（代码：{result.returncode}）")

            # 6. 等待文件生成
            for _ in range(10):
                if temp_docx.exists():
                    break
                time.sleep(0.5)
            else:
                raise Exception("转换后文件未生成")
            # 7. 读取返回
            with open(temp_docx, "rb") as f:
                logger.success(f"转换成功：{url}")
                return f.read()

    except Exception as e:
        logger.error(f"转换失败（{url}）：{str(e)}")
        return None

def extract_file_names(html_content, class_name=None, base_url=None):
    """只用于解析文档中的文件url地址和获取文件名"""
    soup = BeautifulSoup(html_content, 'html.parser')
    target_tags = ['a', 'iframe', 'img']
    filtered_keywords = {'原文链接地址', '原文链接', '请到原网址下载附件', '详情请见原网站'}
    files = []
    if class_name:
        target_elements = soup.find_all(class_=class_name)
        if not target_elements:
            return []
        new_soup = BeautifulSoup(''.join(str(element) for element in target_elements), 'html.parser')
        all_tags = new_soup.find_all(target_tags)
    else:
        all_tags = soup.find_all(target_tags)

    # 遍历查找的标签
    for tag in all_tags:
        if tag.name == 'a':
            link_attr = 'href'
        elif tag.name == 'iframe':
            link_attr = 'src'
        elif tag.name == 'img':
            link_attr = 'src'
        else:
            continue

        href = tag.get(link_attr)
        if not href:
            continue

        if base_url and not href.startswith(('http:', 'https:')):
            href = base_url.rstrip('/') + '/' + href.lstrip('/')

        if href.lower().endswith(('.html', '.htm')):
            continue

        parsed_url = urlparse(href)
        if not (parsed_url.scheme and parsed_url.netloc):
            continue

        if tag.name == 'a':
            file_name = tag.get('title', '').strip()
            if not file_name:
                file_name = tag.get_text(strip=True)
        elif tag.name == 'iframe':
            file_name = href.split('/')[-1]
        elif tag.name == 'img':
            file_name = tag.get('title', '').strip()
            if not file_name:
                file_name = tag.get('alt', '').strip()
            if not file_name:
                file_name = href.split('/')[-1]

        if any(keyword in file_name for keyword in {'http', 'https', 'www', '.cn'}):
            continue

        file_name = file_name.strip()
        if file_name and file_name not in filtered_keywords:
            file_name = clean_name(file_name)
            ext = start_detect_file_type(href, file_name)
            if ext:
                files.append({'file_name': file_name,'href': href})
            else:
                try:
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
                    response = requests.head(href, timeout=30, headers=headers)
                    response.raise_for_status()
                    content_type = response.headers.get('Content-Type', '')
                    if content_type:
                        if isinstance(content_type, bytes):
                            content_type = content_type.decode('utf-8')
                        mime_type = content_type.split(';')[0].strip().lower()
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
    item_content = soup.get_text().replace("\xa0", '').replace("\n", '').replace("\r", '').replace("\t", '').replace(
        "\u3000", '')
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





def split_excel_by_rows(input_path, output_dir, rows_per_file=200):
    """
    将一个Excel文件按行数拆分为多个Excel文件

    参数:
    input_path (str): 输入Excel文件路径
    output_dir (str): 输出目录路径
    rows_per_file (int): 每个文件包含的行数，默认200行
    """
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    excel_data = pd.read_excel(input_path, sheet_name=None)

    for sheet_name, df in excel_data.items():
        total_rows = len(df)
        total_parts = (total_rows + rows_per_file - 1) // rows_per_file  # 计算拆分份数

        for part in range(total_parts):
            start_row = part * rows_per_file
            end_row = min((part + 1) * rows_per_file, total_rows)
            sub_df = df.iloc[start_row:end_row, :]

            # 生成输出文件名
            file_base = os.path.splitext(os.path.basename(input_path))[0]
            output_filename = f"{file_base}_{part + 1}.xlsx"
            output_path = os.path.join(output_dir, output_filename)

            # 保存子文件（保留原格式，需要openpyxl库）
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                sub_df.to_excel(writer, sheet_name=sheet_name, index=False)

            logger.info(f"已生成文件：{output_path}，包含第{start_row + 1}-{end_row}行数据")

    logger.info(f"文件 {input_path} 拆分完成！共生成{total_parts}个文件")


def batch_split_excel_files(input_dir, output_parent_dir, rows_per_file=200, file_extensions=('xlsx', 'xls', 'csv')):
    """
    批量处理文件夹中的所有Excel文件

    参数:
    input_dir (str): 输入文件夹路径
    output_parent_dir (str): 输出父目录路径
    rows_per_file (int): 每个子文件包含的行数
    file_extensions (tuple): 支持的文件扩展名
    """
    # 确保输出父目录存在
    os.makedirs(output_parent_dir, exist_ok=True)

    # 获取所有Excel文件
    excel_files = [f for f in os.listdir(input_dir)
                   if f.lower().endswith(file_extensions)
                   and os.path.isfile(os.path.join(input_dir, f))]

    if not excel_files:
        logger.info(f"在目录 {input_dir} 中未找到Excel文件！")
        return

    total_files = len(excel_files)
    logger.info(f"找到 {total_files} 个Excel文件，开始处理...")

    for i, filename in enumerate(excel_files, 1):
        file_path = os.path.join(input_dir, filename)
        # 为每个输入文件创建单独的输出子目录
        # file_base = os.path.splitext(filename)[0]
        file_base = 'xlsx'
        output_sub_dir = os.path.join(output_parent_dir, file_base)

        logger.info(f"\n处理文件 {i}/{total_files}: {filename}")
        split_excel_by_rows(file_path, output_sub_dir, rows_per_file)

    logger.info(f"\n全部处理完成！所有拆分后的文件保存在: {output_parent_dir}")


import io
import pandas as pd


def dataframe_to_bytes(df, file_format='xlsx'):
    """将DataFrame转换为指定格式的字节流"""
    if file_format == 'xlsx':
        # 转换为Excel字节流
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        return buffer.getvalue()

    elif file_format == 'csv':
        # 转换为CSV字节流
        return df.to_csv(sep=',', na_rep='nan', index=False).encode('utf-8')

    else:
        raise ValueError(f"不支持的文件格式: {file_format}")


def split_file_by_rows(input_path, rows_per_file=200):
    """自动识别文件类型并拆分"""
    ext = os.path.splitext(input_path)[1].lower()

    if ext == '.csv':
        # 处理CSV文件
        df = pd.read_csv(input_path)
        sheet_name = "默认表"
    else:
        # 处理Excel文件（保留原逻辑）
        try:
            excel_data = pd.read_excel(input_path, sheet_name=None, engine='openpyxl')
            # 假设只有一个sheet
            sheet_name, df = next(iter(excel_data.items()))
        except:
            excel_data = pd.read_excel(input_path, sheet_name=None, engine='xlrd')
            sheet_name, df = next(iter(excel_data.items()))

    # 拆分逻辑（与原函数一致）
    result = []
    total_rows = len(df)
    total_parts = (total_rows + rows_per_file - 1) // rows_per_file

    file_base = os.path.splitext(os.path.basename(input_path))[0]
    for part in range(total_parts):
        start_row = part * rows_per_file
        end_row = min((part + 1) * rows_per_file, total_rows)
        sub_df = df.iloc[start_row:end_row, :]

        title = f"{file_base}_{part + 1}{ext}"
        result.append({'title': title, 'content': sub_df})

    logger.info(f"文件 {input_path} 拆分完成！共生成{len(result)}个数据块")
    return result


import os
import pandas as pd
import io


# def split_data_by_rows(data, rows_per_file=200, source_ext='.xlsx', title_prefix=None):
#     """
#     拆分数据库查询结果（DataFrame或列表）为多个数据块
#
#     参数:
#     data: 数据库查询结果（支持DataFrame或列表 of dict）
#     rows_per_file (int): 每个数据块的行数
#     source_ext (str): 生成标题的文件扩展名（默认.xlsx）
#     title_prefix (str): 输出文件的标题前缀（默认使用'database_data'）
#
#     返回:
#     list: 包含字典的列表，每个字典含'title'（数据块标题）和'content'（DataFrame）
#     """
#     # 统一转换为DataFrame
#     if not isinstance(data, pd.DataFrame):
#         try:
#             data = pd.DataFrame(data)
#         except Exception as e:
#             raise ValueError(f"无法将数据转换为DataFrame: {e}")
#
#     result = []
#     total_rows = len(data)
#     total_parts = (total_rows + rows_per_file - 1) // rows_per_file
#
#     # 使用用户指定的标题前缀或默认值
#     file_base = title_prefix if title_prefix else "database_data"
#
#     for part in range(total_parts):
#         start_row = part * rows_per_file
#         end_row = min((part + 1) * rows_per_file, total_rows)
#         sub_df = data.iloc[start_row:end_row, :]
#
#         title = f"{file_base}_{part + 1}{source_ext}"
#         result.append({
#             'title': title,
#             'content': sub_df
#         })
#
#     logger.info(f"数据拆分完成！共生成{len(result)}个数据块")
#     return result

# def split_data_by_rows(data, rows_per_file=200, source_ext='.xlsx', title_prefix=None):
#     """
#     拆分数据库查询结果（DataFrame或列表）为多个数据块，文件名包含UUID确保唯一
#
#     参数:
#     data: 数据库查询结果（支持DataFrame或列表 of dict）
#     rows_per_file (int): 每个数据块的行数
#     source_ext (str): 生成标题的文件扩展名（默认.xlsx）
#     title_prefix (str): 输出文件的标题前缀（默认使用'database_data'）
#
#     返回:
#     list: 包含字典的列表，每个字典含'title'（数据块标题）和'content'（DataFrame）
#     """
#     # 统一转换为DataFrame
#     if not isinstance(data, pd.DataFrame):
#         try:
#             data = pd.DataFrame(data)
#         except Exception as e:
#             raise ValueError(f"无法将数据转换为DataFrame: {e}")
#
#     result = []
#     total_rows = len(data)
#     total_parts = (total_rows + rows_per_file - 1) // rows_per_file  # 计算总分片数
#
#     # 生成UUID（取前8位简化，确保唯一性同时避免文件名过长）
#     # unique_uuid = str(uuid.uuid4()).split('-')[0]  # 例如：'a1b2c3d4'
#
#
#     # 确定文件基础前缀
#     file_base = title_prefix if title_prefix else "database_data"
#
#
#     for part in range(total_parts):
#         unique_uuid = str(uuid.uuid4()).replace('-', '')
#         # 拼接UUID作为唯一标识（格式：前缀_UUID）
#         base_with_uuid = f"{file_base}_{unique_uuid}"
#         start_row = part * rows_per_file
#         end_row = min((part + 1) * rows_per_file, total_rows)
#         sub_df = data.iloc[start_row:end_row, :]
#
#         # 生成文件名（格式：前缀_UUID_分片序号.扩展名）
#         title = f"{base_with_uuid}{source_ext}"
#         result.append({
#             'title': title,
#             'content': sub_df
#         })
#
#     # logger.info(f"数据拆分完成！共生成{len(result)}个数据块，UUID标识：{unique_uuid}")
#     return result


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
    list: 包含字典的列表，每个字典含'title'和'content'（DataFrame）
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
        result.append({
            'title': title,
            'content': sub_df
        })

    return result


def split_file_by_rows_return_bytes(input_path, rows_per_file=200, file_format='xlsx'):
    """
    自动识别文件类型并拆分，返回每个数据块的二进制流

    参数:
    input_path (str): 输入文件路径
    rows_per_file (int): 每个部分的行数
    file_format (str): 输出文件格式，支持'xlsx'或'csv'

    返回:
    list: 包含字典元素的列表，每个字典包含:
          - 'title': 子文件标题
          - 'content': 二进制流数据
    """
    result = []
    file_base = os.path.splitext(os.path.basename(input_path))[0]
    ext = os.path.splitext(input_path)[1].lower()

    # 处理CSV文件
    if ext == '.csv':
        try:
            df = pd.read_csv(input_path)
            sheet_name = "默认表"
        except Exception as e:
            logger.info(f"读取CSV失败: {e}")
            return result

    # 处理Excel文件
    else:
        try:
            # 先尝试openpyxl（适用于xlsx）
            excel_data = pd.read_excel(input_path, sheet_name=None, engine='openpyxl')
            sheet_name, df = next(iter(excel_data.items()))
        except Exception as e:
            logger.info(f"openpyxl读取失败，尝试xlrd: {e}")
            try:
                # 再尝试xlrd（适用于xls）
                excel_data = pd.read_excel(input_path, sheet_name=None, engine='xlrd')
                sheet_name, df = next(iter(excel_data.items()))
            except Exception as e:
                logger.info(f"xlrd读取失败: {e}")
                return result

    # 执行拆分
    total_rows = len(df)
    total_parts = (total_rows + rows_per_file - 1) // rows_per_file

    for part in range(total_parts):
        start_row = part * rows_per_file
        end_row = min((part + 1) * rows_per_file, total_rows)
        sub_df = df.iloc[start_row:end_row, :]

        # 生成子文件标题
        title = f"{file_base}_{part + 1}.{file_format}"

        # 将DataFrame转换为二进制流
        if file_format == 'xlsx':
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                sub_df.to_excel(writer, sheet_name=sheet_name, index=False)
            content = buffer.getvalue()

        elif file_format == 'csv':
            content = sub_df.to_csv(sep=',', na_rep='nan', index=False).encode('utf-8')

        else:
            raise ValueError(f"不支持的格式: {file_format}")

        result.append({'title': title, 'content': content})

    logger.info(f"文件 {input_path} 拆分完成！共生成{len(result)}个二进制数据块")
    return result


def batch_split_excel_files_return_info(input_dir, output_parent_dir, rows_per_file=200,
                                        file_extensions=('xlsx', 'xls', 'csv')):
    """
    批量处理文件夹中的所有 Excel 文件，拆分后返回所有子文件的文件名和对应内容

    参数:
    input_dir (str): 输入文件夹路径
    output_parent_dir (str): 输出父目录路径
    rows_per_file (int): 每个子文件包含的行数
    file_extensions (tuple): 支持的文件扩展名

    返回:
    list: 包含字典元素的列表，每个字典包含 'filename'（子文件名）和 'content'（子文件内容 DataFrame），
          外层列表按处理的文件顺序，内层列表是每个原文件拆分后的子文件信息
    """
    # 确保输出父目录存在
    os.makedirs(output_parent_dir, exist_ok=True)

    # 获取所有 Excel 文件
    excel_files = [f for f in os.listdir(input_dir)
                   if f.lower().endswith(file_extensions)
                   and os.path.isfile(os.path.join(input_dir, f))]

    if not excel_files:
        logger.info(f"在目录 {input_dir} 中未找到 Excel 文件！")
        return []

    total_files = len(excel_files)
    logger.info(f"找到 {total_files} 个 Excel 文件，开始处理...")
    all_results = []
    for i, filename in enumerate(excel_files, 1):
        file_path = os.path.join(input_dir, filename)
        # 为每个输入文件创建单独的输出子目录
        file_base = os.path.splitext(filename)[0]
        output_sub_dir = os.path.join(output_parent_dir, file_base)

        logger.info(f"\n处理文件 {i}/{total_files}: {filename}")
        file_result = split_excel_by_rows_return_info(file_path, output_sub_dir, rows_per_file)
        all_results.append(file_result)

    logger.info(f"\n全部处理完成！所有拆分后的文件保存在: {output_parent_dir}")
    return all_results


def get_markdown(item_name, html):
    """将详情页保存为markdown上传到ragflow"""
    new_name = clean_name(item_name)
    converter = html2text.HTML2Text()  # 创建 html2text 转换器实例
    converter.ignore_links = False  # 不忽略链接
    markdown = converter.handle(html)
    md5_hash = calculate_md5(markdown)
    new_name = md5_hash + ".md"
    return markdown, new_name


def get_file_extension(url):
    response = requests.get(
        url,
        timeout=60)
    file_content = response.content
    # MIME 类型到后缀名的映射表（常见类型）
    MIME_TO_EXT = {
        # 文档类
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

        # 图片类
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/gif": "gif",
        "image/svg+xml": "svg",
        "image/webp": "webp",

        # 压缩类
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
    """根据文件内容获取真实后缀名"""
    try:
        mime_type = magic.from_buffer(file_content, mime=True)
        if mime_type in MIME_TO_EXT:
            return MIME_TO_EXT[mime_type]
    except Exception as e:
        logger.error(f"错误: 判断文件类型失败 - {e}")
        return ""


@retry(max_retries=2, retry_delay=1)
def get_response(url):
    """获取响应"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return response


def check_file(title, url=None, content=None):
    """
    统一校验并规范化文件：
    - 当提供 url 时：下载内容并基于 (url, title) 判定扩展名
    - 当提供 content 时：基于 title 判定扩展名
    返回 (content_bytes, ext, normalized_name_by_md5)
    """
    # 1、确定内容与扩展名
    if content is None:
        # 从 URL 获取内容
        ext = start_detect_file_type(url, title)
        content = get_response(url).content
    else:
        # 已有内容，基于标题推断扩展名
        ext = start_detect_file_type(file_url=None, file_name=title)

    # 2、处理 doc → docx
    if ext == "doc":
        content = convert_doc_to_docx_from_url(url or '', content)
        ext = "docx"

    # 3、统一使用 MD5 作为文件名
    md5 = calculate_md5(content)
    name = md5 + "." + ext
    return content, ext, name


def get_file(url, title):
    """根据url获取文件名"""
    files = []
    content, ext, name = check_file(title=title, url=url)
    if ext in ["zip", "rar", "tar", "gz", "bz2", "7z"]:
        extracted_files = extract_archive(content, name, ext)
        for content, new_name in extracted_files:
            content, ext, name = check_file(title=new_name, content=content)
            logger.info(f"已提取文件新名字：{name}")
            files.append((content, name))
    else:
        files.append((content, name))
    return files


def get_detail_data(item_data, html):
    """获取详情页数据"""
    # item_data['item_content'] = extract_item_content(html)
    item_data['md5_hash'] = calculate_md5(html)
    item_data['item_html_text'] = html
    file_infos = extract_file_names(html)
    if file_infos:
        item_data['file_infos'] = json.dumps(file_infos)
        item_data['has_attachment'] = 1
    return item_data
