"""
简洁版 PDF/图片 -> Markdown 流程。
支持 PDF 路径/链接和单张图片路径/链接。
"""

import base64
import shutil
import tempfile
import time
from pathlib import Path
from typing import List, Tuple, Optional

import requests
from openai import OpenAI
from pdf2image import convert_from_path
from PIL import Image
import warnings
from collections import Counter
from pprint import pprint
import pandas as pd
from io import BytesIO
from spider_tools.utils import retry
# 核心：过滤openpyxl的页眉/页脚解析警告
warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl.worksheet.header_footer')

# 内置配置：合并自 conf.yaml
_DEFAULT_CONFIG = {
    "model": {
        "timeout": 60,
        "max_retries": 3,
    },
    "pdf2img": {
        "dpi": 200,
        "format": "jpeg",
        "quality": 95,
        "thread_count": 4,
        "poppler_path": None,
    },
    "img2markdown": {
        "batch_size": 10,
        "delay_between_requests": 0.5,  # seconds
    },
    "task_manager": {
        "tasks_dir": "tasks",
        "task_file_prefix": "task_",
        "status_update_interval": 5,  # seconds
    },
    "paths": {
        "pdf_input": "pdfs",
        "image_output": "images",
        "markdown_output": "markdowns",
        "logs": "logs",
    },
}

# 内置提示词：合并自 prompts.yaml
_DEFAULT_PROMPTS = {
    "img2markdown": {
        "system": "你是一个专业的文档转换助手，擅长将图像内容准确转换出纯文本格式。",
        "user_prompt": """请将图像内容转换为规范的纯文本格式文本。

要求：
1. 保持原文档的结构和格式
2. 保留表格、列表等格式
3. 识别代码块并使用正确的语法高亮
4. 如果是空白页，请输出"(空白页)"
5. 不要包含任何解释或额外说明，只输出转换后的内容
""",
        "error_prompt": "无法识别图像内容，请输出：[识别失败]",
    },
    "split_by_meaning": {
        "system": "你是一个专业的文档分析助手，擅长理解文档的语义结构。",
        "user_prompt": """请分析以下Markdown文档的语义结构，并根据内容的逻辑关系进行智能分段。

分段原则：
1. 每个段落应该包含完整的语义单元
2. 相关的内容应该保持在同一段
3. 不同主题或章节应该分开
4. 保持原有的标题层级结构

输出格式：
返回一个JSON数组，每个元素包含：
- section_id: 段落编号
- title: 段落标题（如果有）
- content: 段落内容
- start_line: 起始行号
- end_line: 结束行号
""",
    },
}


class SimplePDFPipeline:
    """最小依赖的 PDF 解析管道，封装图片生成与 Markdown 识别。"""

    def __init__(
        self,
        model_name: str,
        api_key: str,
        base_url: str,
        save_images: bool = False,
    ):
        """
        初始化管道。

        参数:
            model_name: 模型名称，如 "qwen-vl-max"（必填）
            api_key: API密钥（必填）
            base_url: API基础URL（必填）
            save_images: 是否在本地保存图片，默认为 False（不保存）
        """
        if not model_name:
            raise ValueError("model_name 参数不能为空")
        if not api_key:
            raise ValueError("api_key 参数不能为空")
        if not base_url:
            raise ValueError("base_url 参数不能为空")

        self._config = _DEFAULT_CONFIG.copy()
        self._prompts = _DEFAULT_PROMPTS.copy()

        # 使用传入的参数
        model_cfg = self._config.get("model", {}).copy()
        model_cfg["name"] = model_name
        model_cfg["apikey"] = api_key
        model_cfg["url"] = base_url
        # 更新配置字典
        self._config["model"] = model_cfg

        self._client = OpenAI(
            api_key=api_key,
            base_url=base_url,
        )
        self._model_name = model_name
        self._pdf_cfg = self._config.get("pdf2img", {})
        self._img_cfg = self._config.get("img2markdown", {})
        self._prompts_img = self._prompts.get("img2markdown", {})
        self._save_images = save_images
        self._temp_dirs: List[Path] = []  # 跟踪临时目录，用于后续清理

    # ------------------------------------------------------------------ #
    # 公共接口
    # ------------------------------------------------------------------ #
    def pdf_to_images(
        self,
        path_or_url: str,
        output_dir: Optional[str] = None,
    ) -> List[str]:
        """
        将 PDF 或单张图片统一转换为图片列表。
        PDF: 转成多页 JPG；图片：写入标准命名后返回。

        如果 save_images=False，图片将保存到临时目录，处理完后可调用 cleanup_temp_dirs() 清理。
        """
        input_kind = self._detect_input_type(path_or_url)
        file_path, cleanup_path = self._prepare_file(path_or_url)

        # 根据 save_images 参数决定使用临时目录还是配置的目录
        if self._save_images:
            output_root = Path(output_dir or Path(self._config.get("paths", {}).get("image_output", "images")))
            target_dir = output_root / file_path.stem
            target_dir.mkdir(parents=True, exist_ok=True)
            is_temp_dir = False
        else:
            # 使用临时目录
            target_dir = Path(tempfile.mkdtemp(prefix="spider_tools_images_"))
            self._temp_dirs.append(target_dir)
            is_temp_dir = True

        saved_paths: List[str] = []

        try:
            if input_kind == "pdf":
                self._assert_pdf_signature(file_path.read_bytes()[:8])
                images = convert_from_path(
                    str(file_path),
                    dpi=self._pdf_cfg.get("dpi", 200),
                    fmt=self._pdf_cfg.get("format", "jpeg"),
                    thread_count=self._pdf_cfg.get("thread_count", 4),
                    poppler_path=self._pdf_cfg.get("poppler_path"),
                )

                for idx, img in enumerate(images, start=1):
                    output_file = target_dir / f"page_{idx:03d}.jpg"
                    img.save(output_file, "JPEG", quality=self._pdf_cfg.get("quality", 95))
                    saved_paths.append(str(output_file))
            elif input_kind == "image":
                saved_paths.append(self._save_single_image(file_path, target_dir))
            else:
                raise ValueError("目前仅支持 PDF 或单张图片输入")
            return saved_paths
        finally:
            if cleanup_path and cleanup_path.exists():
                cleanup_path.unlink()

    def images_to_markdown(self, path_or_dir: str) -> str:
        """
        将指定目录或单张图片转成 Markdown 文本，返回合并后的字符串。
        """
        target = Path(path_or_dir)
        if not target.exists():
            raise FileNotFoundError(f"图片路径不存在: {target}")

        if target.is_dir():
            image_files = sorted(
                [p for p in target.glob("*") if p.suffix.lower() in {".jpg", ".jpeg", ".png"}],
                key=lambda p: int(p.stem.split("_")[-1]) if "_" in p.stem and p.stem.split("_")[-1].isdigit() else 0,
            )
        else:
            image_files = [target]

        if not image_files:
            raise ValueError(f"{target} 中找不到可识别的图片 (jpg/png)")

        delay = self._img_cfg.get("delay_between_requests", 0.5)
        pieces: List[str] = []
        for file in image_files:
            text = self._describe_image(str(file))
            if text:
                pieces.append(text)
            if delay > 0:
                time.sleep(delay)
        return "\n\n".join(pieces)

    def pdf_to_markdown(
        self,
        pdf_path_or_url: str,
        image_output_dir: Optional[str] = None,
    ) -> Tuple[List[str], str]:
        """
        一步执行：PDF -> 图片路径列表 -> Markdown 字符串。
        返回 (图片路径列表, Markdown 内容)。

        如果 save_images=False，处理完后会自动清理临时目录。
        """
        try:
            image_paths = self.pdf_to_images(pdf_path_or_url, image_output_dir)
            markdown_text = self.images_to_markdown(Path(image_paths[0]).parent if len(image_paths) > 1 else image_paths[0])
            return image_paths, markdown_text
        finally:
            # 如果 save_images=False，处理完后清理临时目录
            if not self._save_images:
                self.cleanup_temp_dirs()

    def cleanup_temp_dirs(self):
        """
        清理所有临时目录（仅在 save_images=False 时使用）。
        通常在处理完成后自动调用，也可手动调用。
        """
        for temp_dir in self._temp_dirs:
            if temp_dir.exists():
                try:
                    shutil.rmtree(temp_dir)
                except Exception:
                    # 忽略清理错误，避免影响主流程
                    pass
        self._temp_dirs.clear()

    # ------------------------------------------------------------------ #
    # 内部工具
    # ------------------------------------------------------------------ #
    def _describe_image(self, image_path: str) -> str:
        prompt_user = self._prompts_img.get(
            "user_prompt",
            "请将图像内容转换为规范的 Markdown 纯文本；若为空白页输出“(空白页)”。",
        )
        system_prompt = self._prompts_img.get("system", "")
        base64_image, mime_type = self._encode_image(image_path)

        completion = self._client.chat.completions.create(
            model=self._model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt_user},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime_type};base64,{base64_image}"},
                        },
                    ],
                },
            ],
        )
        return completion.choices[0].message.content.strip()

    @staticmethod
    def _encode_image(image_path: str) -> Tuple[str, str]:
        data = Path(image_path).read_bytes()
        mime_type = SimplePDFPipeline._guess_mime_type(image_path)
        return base64.b64encode(data).decode("utf-8"), mime_type


    # ------------------------------------------------------------------ #
    # URL & 文件支持
    # ------------------------------------------------------------------ #
    @retry(max_retries=3, retry_delay=1)
    def _prepare_file(self, path_or_url: str) -> Tuple[Path, Optional[Path]]:
        if self._is_url(path_or_url):
            suffix = self._extract_suffix(path_or_url)
            tmp_file = Path(tempfile.NamedTemporaryFile(delete=False, suffix=suffix or ".tmp").name)
            response = requests.get(path_or_url, timeout=self._config.get("download_timeout", 30))
            response.raise_for_status()
            tmp_file.write_bytes(response.content)
            return tmp_file, tmp_file

        local_path = Path(path_or_url)
        if not local_path.exists():
            raise FileNotFoundError(f"文件不存在: {local_path}")
        return local_path, None

    def _detect_input_type(self, path_or_url: str) -> str:
        suffix = self._extract_suffix(path_or_url).lower()
        if suffix == ".pdf":
            return "pdf"
        if suffix in {".jpg", ".jpeg", ".png"}:
            return "image"

        if not self._is_url(path_or_url):
            local_path = Path(path_or_url)
            if local_path.is_dir():
                return "image_dir"
            if local_path.suffix.lower() == ".pdf":
                return "pdf"
            if local_path.suffix.lower() in {".jpg", ".jpeg", ".png"}:
                return "image"

        return "pdf"

    def _save_single_image(self, source: Path, target_dir: Path) -> str:
        ext = source.suffix.lower()
        if ext not in {".jpg", ".jpeg", ".png"}:
            raise ValueError("仅支持 jpg/jpeg/png 图片")

        target_ext = ".jpg" if ext == ".jpeg" else ext
        target_file = target_dir / f"page_001{target_ext}"

        if ext == ".png":
            img = Image.open(source)
            rgb = img.convert("RGB")
            target_file = target_dir / "page_001.jpg"
            rgb.save(target_file, "JPEG", quality=self._pdf_cfg.get("quality", 95))
        else:
            shutil.copy2(source, target_file)

        return str(target_file)

    @staticmethod
    def _is_url(path: str) -> bool:
        return path.startswith("http://") or path.startswith("https://")

    @staticmethod
    def _assert_pdf_signature(head: bytes) -> None:
        if not head:
            raise ValueError("提供的文件为空，无法读取 PDF 内容")
        if not head.lstrip().startswith(b"%PDF"):
            raise ValueError("提供的路径或链接不是有效的 PDF 文件")

    @staticmethod
    def _extract_suffix(path_or_url: str) -> str:
        clean = path_or_url.split("?")[0].split("#")[0]
        return Path(clean).suffix

    @staticmethod
    def _guess_mime_type(image_path: str) -> str:
        ext = Path(image_path).suffix.lower()
        if ext == ".png":
            return "image/png"
        return "image/jpeg"


# 注意：由于需要传入 API 密钥等敏感信息，请直接使用 SimplePDFPipeline 类创建实例
# 示例：
# pipeline = SimplePDFPipeline(
#     model_name="qwen-vl-max",
#     api_key="your-api-key",
#     base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
#     save_images=False  # 默认为 False，不保存图片到本地；设置为 True 则保存到配置的目录
# )
# result = pipeline.pdf_to_markdown("document.pdf")


def download_and_parse_xlsx(url: str):
    """下载 XLSX 文件并解析所有 Sheet，返回 {sheet_name: rows_list} 结构"""
    # 1. 下载文件
    resp = requests.get(url)
    resp.raise_for_status()

    # 2. 使用 pandas 读取所有 Sheet
    excel_bytes = BytesIO(resp.content)
    sheets = pd.read_excel(excel_bytes, sheet_name=None,header=None)  # sheet_name=None → 全部 sheet

    # 3. 转成 sheet → 行列表
    result = {}
    for sheet_name, df in sheets.items():
        # 保留原始数据，不做类型转换
        rows = df.fillna("").astype(str).values.tolist()
        result[sheet_name] = rows

    return result

def most_common_length(list_of_lists):
    """
    获取列表-列表 子列表长度最多的子列表长度
    :param list_of_lists:
    :return:
    """
    # 1. 计算每个子数组的长度
    lengths = [len(arr) for arr in list_of_lists]

    # 2. 统计每个长度出现次数
    counter = Counter(lengths)

    # 3. 找到出现次数最多的长度
    most_common = counter.most_common(1)[0]  # (长度, 次数)

    return most_common

def deal_data(sheets_data:dict):
    sheets_deal_data = {}
    for sheet_name,sheet_data in sheets_data.items():
        deal_sheet_data = []
        for row in sheet_data:
            deal_sheet_data.append([r for r in row if r])
        sheets_deal_data[sheet_name] = deal_sheet_data
    return sheets_deal_data

def get_max_column_length(data):
    """获取所有列的长度"""
    return max([len(row) for row in data])

def get_data_header(data):
    max_row_length = get_max_column_length(data)
    for index,d in enumerate(data):
        if len([_ for _ in d if _]) == max_row_length:
            return d,index
    else:
        return None,None
def get_data_front_text(data,header_index):
    front_list = []
    for front_row in data[:header_index]:
        if rtrim_list(front_row):
            front_list.append(','.join([r for r in front_row if r]))
    front_text = ','.join(front_list)
    return front_text

def rtrim_list(lst):
    """
    去除列表后边的空内容
    :param lst:
    :return:
    """
    def is_empty(x):
        return x is None or (isinstance(x, str) and x.strip() == "")

    end = len(lst) - 1
    while end >= 0 and is_empty(lst[end]):
        end -= 1

    return lst[:end + 1]

def get_data_end_text(data,header_index):
    rtrim_list_data = [rtrim_list(d) for d in data[header_index:]]
    end_data = []
    end_index = 0
    for index,d in enumerate(rtrim_list_data[::-1]):
        if len(d)==1:
            end_data.append(d[0])
        else:
            end_index = -index
            return ','.join(end_data[::-1]),end_index
    return ','.join(end_data[::-1]),end_index

def parse_excel(url):
    sheets_data = download_and_parse_xlsx(url)
    result = {}
    for t, v in sheets_data.items():
        header, header_index = get_data_header(v)
        front_text = get_data_front_text(v, header_index)
        end_text, end_index = get_data_end_text(v, header_index)
        table_true_data = v[header_index + 1:end_index]
        process_sheet_data = []
        for row in table_true_data:
            temp_list = []
            for key, value in zip(header, row):
                temp_list.append(f"{key}:{value}")
            process_sheet_data.append(f"{front_text},{','.join(temp_list)},{end_text}")
        result[t] = process_sheet_data
    return result


