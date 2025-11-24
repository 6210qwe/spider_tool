import os
import io
import requests
import tempfile
from typing import Union
from rapidocr_onnxruntime import RapidOCR
from langchain_community.document_loaders import (PyPDFLoader, PDFPlumberLoader, Docx2txtLoader,UnstructuredExcelLoader, UnstructuredFileLoader, TextLoader)
from langchain_unstructured import UnstructuredLoader


class DocumentParser:
    def __init__(self):
        self.ocr = RapidOCR()
        # 模拟浏览器请求头（避免403）
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        # 指定Loader映射（优先使用用户列举的Loader）
        self.loader_mapping = {
            "pdf": PyPDFLoader,  # 用户指定PDF加载器
            "doc": Docx2txtLoader,  # 用户指定DOC加载器（兼容DOC/DOCX）
            "docx": Docx2txtLoader,  # 统一用Docx2txtLoader处理Word文件
            "xlsx": UnstructuredExcelLoader,  # 用户指定Excel加载器
            "xls": UnstructuredExcelLoader,  # 补充XLS格式支持
            "md": UnstructuredFileLoader,  # 用户指定Markdown加载器
            "txt": TextLoader,  # 用户指定文本加载器
            "jpg": self._parse_image,  # 图片映射OCR解析方法
            "png": self._parse_image  # 图片映射OCR解析方法
        }

    def parse(self, input_data: Union[str, bytes]) -> str:
        """统一解析入口：优先后缀识别，魔数兜底"""
        if isinstance(input_data, bytes):
            # 二进制数据：直接用魔数识别（无后缀可提取）
            ext = self._get_extension_by_magic(input_data)
            return self._parse_by_ext(ext, content=input_data)

        # 本地文件或URL：优先提取后缀
        ext = self._extract_extension(input_data)
        if ext not in self.loader_mapping or ext == 'unknown':
            # 后缀未识别/不支持，用魔数兜底
            content = self._get_content(input_data)
            ext = self._get_extension_by_magic(content)

        return self._parse_by_ext(ext, input_data=input_data)

    def _extract_extension(self, path_or_url: str) -> str:
        """从本地路径或URL中提取文件后缀"""
        # 切割URL参数/锚点或本地路径
        clean_str = path_or_url.split('?')[0].split('#')[0]
        # 提取后缀（去除.）
        ext = os.path.splitext(clean_str)[-1].lstrip('.').lower()
        return ext if ext else 'unknown'

    def _get_content(self, path_or_url: str) -> bytes:
        """获取本地文件或URL的二进制内容"""
        if os.path.exists(path_or_url):
            # 本地文件：读取二进制
            with open(path_or_url, 'rb') as f:
                return f.read()
        elif path_or_url.startswith(('http://', 'https://')):
            # URL：下载二进制
            resp = requests.get(path_or_url, timeout=30, headers=self.headers)
            resp.raise_for_status()
            return resp.content
        raise ValueError("输入既不是本地文件也不是有效URL")

    def _parse_by_ext(self, ext: str, input_data: str = None, content: bytes = None) -> str:
        """根据文件类型选择对应Loader或方法解析"""
        # 图片格式（OCR解析）
        if ext in ['jpg', 'png']:
            return self._parse_image(content or self._get_content(input_data))

        # 文档/文本格式（使用指定Loader）
        if ext in self.loader_mapping and callable(self.loader_mapping[ext]):
            try:
                if content:
                    # 二进制内容：生成临时文件供Loader读取
                    with tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False) as tmp:
                        tmp.write(content)
                        tmp_path = tmp.name
                    try:
                        loader = self.loader_mapping[ext](tmp_path)
                        docs = loader.load()
                    finally:
                        os.unlink(tmp_path)  # 清理临时文件
                else:
                    # 本地路径/URL：直接用Loader读取（URL需先下载为临时文件）
                    if input_data.startswith(('http://', 'https://')):
                        content = self._get_content(input_data)
                        with tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False) as tmp:
                            tmp.write(content)
                            tmp_path = tmp.name
                        loader = self.loader_mapping[ext](tmp_path)
                        docs = loader.load()
                        os.unlink(tmp_path)
                    else:
                        loader = self.loader_mapping[ext](input_data)
                        docs = loader.load()

                return '\n'.join([doc.page_content.strip() for doc in docs]) if docs else f"{ext}文件无有效文本"
            except Exception as e:
                return f"{ext}解析失败: {str(e)}"

        # 未识别/不支持的格式
        return f"不支持的文件类型（识别为{ext}）"

    def _parse_image(self, content: bytes) -> str:
        """OCR解析图片内容"""
        try:
            from PIL import Image
            img = Image.open(io.BytesIO(content))
            result, _ = self.ocr(img)
            return '\n'.join([line[1].strip() for line in result]) if result else "图片中未识别到文本"
        except Exception as e:
            return f"图片解析失败: {str(e)}"

    def _get_extension_by_magic(self, content: bytes) -> str:
        """魔数识别（后缀识别失败时兜底）"""
        if not content:
            return 'unknown'
        # PDF
        if content.startswith(b'%PDF'):
            return 'pdf'
        # ZIP格式（DOCX/XLSX/PPTX）
        if content.startswith(b'PK\x03\x04'):
            return 'docx' if b'word/' in content[:1024] else 'xlsx' if b'xl/' in content[:1024] else 'zip'
        # OLE复合文档（DOC/XLS）
        if content.startswith(b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'):
            return 'doc' if b'WordDocument' in content[:4096] else 'xls' if b'Workbook' in content[:4096] else 'ole'
        # 图片
        if content.startswith(b'\xff\xd8\xff'):
            return 'jpg'
        if content.startswith(b'\x89PNG'):
            return 'png'
        # 文本
        try:
            content.decode('utf-8')
            return 'txt'
        except UnicodeDecodeError:
            pass
        return 'unknown'


# if __name__ == "__main__":
#     parser = DocumentParser()
    # document = parser.parse("5b1d2ae212dc4081a38141e6e357ba8e.pdf")
    # print(document)
    # document = parser.parse("864933e9f246ca17256173df9c2812f6.png")
    # print(document)
    # document = parser.parse("1.md")
    # print(document)
    # document = parser.parse("https://zjjcmspublicnew.oss-cn-hangzhou-zwynet-d01-a.internet.cloud.zj.gov.cn/cms_files/jcms1/web1934/site/attach/0/5b1d2ae212dc4081a38141e6e357ba8e.pdf")
    # print(document)
    # document = parser.parse("https://kw.beijing.gov.cn/zwgk/zcwj/202506/W020250618597479728478.docx")
    # print(document)
    # document = parser.parse("https://www.nmpa.gov.cn/wbpp/formationDocument?homeUrl=https://www.nmpa.gov.cn/xxgk/fgwj/gzwj/gzwjylqx&pageSize=1&pageName=20250926145725125&title=%25E5%259B%25BD%25E5%25AE%25B6%25E8%258D%25AF%25E7%259B%2591%25E5%25B1%2580%25E5%2585%25B3%25E4%25BA%258E%25E5%258D%25B0%25E5%258F%2591%25E5%258C%25BB%25E7%2596%2597%25E5%2599%25A8%25E6%25A2%25B0%25E7%25BD%2591%25E7%25BB%259C%25E9%2594%2580%25E5%2594%25AE%25E8%25B4%25A8%25E9%2587%258F%25E7%25AE%25A1%25E7%2590%2586%25E8%25A7%2584%25E8%258C%2583%25E7%258E%25B0%25E5%259C%25BA%25E6%25A3%2580%25E6%259F%25A5%25E6%258C%2587%25E5%25AF%25BC%25E5%258E%259F%25E5%2588%2599%25E7%259A%2584%25E9%2580%259A%25E7%259F%25A5")
    # print(document)