# -*- coding: utf-8 -*-
"""
AI图像生成工具 - 简洁版
支持HTTP请求和SDK调用两种方式，通过传入API key进行认证
"""

import base64
import datetime
import json
import uuid
import os
import sys
import hashlib
import hmac
import requests
import traceback
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any

# 尝试导入volcengine SDK
try:
    from volcengine.visual.VisualService import VisualService

    VOLCENGINE_AVAILABLE = True
except ImportError:
    VOLCENGINE_AVAILABLE = False


@dataclass
class JimengT2IRequest:
    """请求参数类：jimeng_t2i_v40"""
    req_key: str = "jimeng_t2i_v40"
    prompt: str = ""
    image_urls: Optional[List[str]] = field(default_factory=list)
    size: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    scale: float = 0.5
    force_single: bool = False
    min_ratio: float = 1 / 3
    max_ratio: float = 3.0

    def to_dict(self) -> dict:
        """转换为API可直接使用的dict，自动去掉None的字段"""
        data = asdict(self)
        return {k: v for k, v in data.items() if v is not None and v != []}


@dataclass
class ImageResult:
    """图片结果类"""
    filename: str
    content: bytes
    base64_content: str
    size: int


class AIImageTool:
    """AI图像生成工具类"""

    def __init__(self, access_key: str, secret_key: str, save_dir: Optional[str] = None):
        """
        初始化工具
        :param access_key: 访问密钥
        :param secret_key: 秘密密钥
        :param save_dir: 图片保存目录，如果为None则不保存到本地
        """
        self.access_key = access_key
        self.secret_key = secret_key
        self.save_dir = save_dir
        self.visual_service = None

        # 只有在指定了保存目录时才创建
        if self.save_dir:
            os.makedirs(save_dir, exist_ok=True)

        # 初始化SDK服务
        if VOLCENGINE_AVAILABLE:
            self.visual_service = VisualService()
            self.visual_service.set_ak(access_key)
            self.visual_service.set_sk(secret_key)

    def _process_images(self, resp_str: str, save_to_local: bool = True) -> List[ImageResult]:
        """处理图片数据，可选择是否保存到本地"""
        resp = json.loads(resp_str)
        base64_list = resp["data"]["binary_data_base64"]

        results = []
        timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')

        for i, b64_str in enumerate(base64_list, start=1):
            # 生成文件名
            filename = f"{timestamp}_{uuid.uuid4().hex[:8]}.png"

            # 解码图片数据
            img_data = base64.b64decode(b64_str)

            # 如果指定了保存目录且需要保存到本地
            if save_to_local and self.save_dir:
                filepath = os.path.join(self.save_dir, filename)
                with open(filepath, "wb") as f:
                    f.write(img_data)
                print(f"图片已保存: {filepath}")
                filename = filepath  # 使用完整路径

            # 创建结果对象
            result = ImageResult(
                filename=filename,
                content=img_data,
                base64_content=b64_str,
                size=len(img_data)
            )
            results.append(result)

        return results

    def _sign(self, key, msg):
        """HMAC签名"""
        return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()

    def _get_signature_key(self, key, date_stamp, region_name, service_name):
        """获取签名密钥"""
        k_date = self._sign(key.encode('utf-8'), date_stamp)
        k_region = self._sign(k_date, region_name)
        k_service = self._sign(k_region, service_name)
        return self._sign(k_service, 'request')

    def _format_query(self, parameters):
        """格式化查询参数"""
        return '&'.join(f"{key}={parameters[key]}" for key in sorted(parameters))

    def _http_request(self, form_data: dict, save_to_local: bool = True):
        """执行HTTP签名请求"""
        method = 'POST'
        host = 'visual.volcengineapi.com'
        region = 'cn-north-1'
        endpoint = 'https://visual.volcengineapi.com'
        service = 'cv'

        # 构建请求参数
        query_params = {'Action': 'CVProcess', 'Version': '2022-08-31'}
        formatted_query = self._format_query(query_params)
        formatted_body = json.dumps(form_data)

        # 生成签名
        t = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
        current_date = t.strftime('%Y%m%dT%H%M%SZ')
        datestamp = t.strftime('%Y%m%d')

        payload_hash = hashlib.sha256(formatted_body.encode('utf-8')).hexdigest()
        signed_headers = 'content-type;host;x-content-sha256;x-date'

        canonical_headers = f"content-type:application/json\nhost:{host}\nx-content-sha256:{payload_hash}\nx-date:{current_date}\n"
        canonical_request = f"{method}\n/\n{formatted_query}\n{canonical_headers}\n{signed_headers}\n{payload_hash}"

        credential_scope = f"{datestamp}/{region}/{service}/request"
        string_to_sign = f"HMAC-SHA256\n{current_date}\n{credential_scope}\n{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"

        signing_key = self._get_signature_key(self.secret_key, datestamp, region, service)
        signature = hmac.new(signing_key, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()

        authorization_header = f"HMAC-SHA256 Credential={self.access_key}/{credential_scope}, SignedHeaders={signed_headers}, Signature={signature}"

        headers = {
            'X-Date': current_date,
            'Authorization': authorization_header,
            'X-Content-Sha256': payload_hash,
            'Content-Type': 'application/json'
        }

        # 发送请求
        request_url = f"{endpoint}?{formatted_query}"
        print(f"请求URL: {request_url}")

        try:
            response = requests.post(request_url, headers=headers, data=formatted_body)
            print(f"响应状态码: {response.status_code}")

            resp_str = response.text.replace("\\u0026", "&")
            # print(f"响应内容: {resp_str}")

            return self._process_images(resp_str, save_to_local)
        except Exception as err:
            print(f"请求错误: {err}")
            raise

    def generate_image(self, prompt: str, method: str = "http", save_to_local: bool = False, **kwargs) -> List[
        ImageResult]:
        """
        生成图像
        :param prompt: 提示词
        :param method: 请求方式 ("http" 或 "sdk")
        :param save_to_local: 是否保存到本地
        :param kwargs: 其他参数
        :return: 图片结果列表
        """
        form_data = {
            "req_key": "jimeng_t2i_v40",
            "prompt": prompt,
            **kwargs
        }

        if method == "http":
            return self._http_request(form_data, save_to_local)
        elif method == "sdk":
            if not VOLCENGINE_AVAILABLE:
                raise ImportError("volcengine SDK 未安装，请使用 method='http'")

            try:
                resp = self.visual_service.cv_process(form_data)
                print(resp)
                return self._process_images(json.dumps(resp), save_to_local)
            except Exception as e:
                traceback.print_exc()
                raise
        else:
            raise ValueError("method 必须是 'http' 或 'sdk'")

    def generate_image_content(self, prompt: str, method: str = "http", **kwargs) -> List[Dict[str, Any]]:
        """
        生成图像并返回内容信息（不保存到本地）
        :param prompt: 提示词
        :param method: 请求方式 ("http" 或 "sdk")
        :param kwargs: 其他参数
        :return: 包含图片信息的字典列表
        """
        results = self.generate_image(prompt, method, save_to_local=False, **kwargs)

        return [
            {
                "filename": result.filename,
                "content": result.content,
                "base64_content": result.base64_content,
                "size": result.size
            }
            for result in results
        ]

    def submit_async_task(self, prompt: str, method: str = "sync2async", **kwargs):
        """
        提交异步任务
        :param prompt: 提示词
        :param method: 提交方式 ("sync2async" 或 "async")
        :param kwargs: 其他参数
        :return: 任务ID
        """
        if not VOLCENGINE_AVAILABLE:
            raise ImportError("volcengine SDK 未安装，无法使用异步功能")

        form_data = {
            "req_key": "jimeng_t2i_v40",
            "prompt": prompt,
            **kwargs
        }

        if method == "sync2async":
            resp = self.visual_service.cv_sync2async_submit_task(form_data)
        elif method == "async":
            resp = self.visual_service.cv_submit_task(form_data)
        else:
            raise ValueError("method 必须是 'sync2async' 或 'async'")

        print(resp)
        return resp.get('task_id') if isinstance(resp, dict) else resp

    def get_async_result(self, task_id: str, method: str = "sync2async", save_to_local: bool = True):
        """
        获取异步任务结果
        :param task_id: 任务ID
        :param method: 查询方式 ("sync2async" 或 "async")
        :param save_to_local: 是否保存到本地
        :return: 图片结果列表
        """
        if not VOLCENGINE_AVAILABLE:
            raise ImportError("volcengine SDK 未安装，无法使用异步功能")

        form_data = {
            "req_key": "jimeng_t2i_v40",
            "task_id": task_id
        }

        if method == "sync2async":
            resp = self.visual_service.cv_sync2async_get_result(form_data)
        elif method == "async":
            resp = self.visual_service.cv_get_result(form_data)
        else:
            raise ValueError("method 必须是 'sync2async' 或 'async'")

        print(resp)
        return self._process_images(json.dumps(resp), save_to_local)


# 便捷函数，保持向后兼容
def json_load_img(resp_str: str, save_dir: str = "imgs"):
    """从JSON响应中提取base64图片数据并保存（兼容函数）"""
    tool = AIImageTool("", "", save_dir)
    return tool._process_images(resp_str, save_to_local=True)
