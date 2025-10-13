# -*- coding:utf-8 -*-
"""
@Author   : MindLullaby
@Website  : https://pypi.org/project/spider-tools-pro/
@Copyright: (c) 2020 by g1879, Inc. All Rights Reserved.

不允许任何人以个人身份使用或分发本项目源代码。
个人或组织如未获得版权持有人授权，不得将本项目以源代码或二进制形式用于商业行为。

使用本项目需满足以下条款，如使用过程中出现违反任意一项条款的情形，授权自动失效。
* 禁止应用到任何可能违反当地法律规定和道德约束的项目中
* 禁止用于任何可能有损他人利益的项目中
* 禁止用于攻击与骚扰行为
* 遵守Robots协议，禁止用于采集法律或系统Robots协议不允许的数据

使用期间发生的一切行为均由使用人自行负责。
因使用本工具进行任何行为所产生的一切纠纷及后果均与版权持有人无关，
版权持有人不承担任何工具使用带来的风险和损失。
版权持有人不对工具可能存在的缺陷导致的任何损失负任何责任。
"""



from spider_tools.oss_manager import OSSManager
from spider_tools import file_utils
from spider_tools import utils
# from spider_tools.redis_manager import RedisManager
from spider_tools.ragflow_manager import BaseProcessor
from spider_tools import time_utils
# from spider_tools.file_utils import FileUtils
# from spider_tools.user_agent_utils import UserAgentUtils
# from spider_tools.xpath_utils import XPathUtils
# from spider_tools.regex_utils import RegexUtils

__all__ = [
    'OSSManager',
    'file_utils',
    'utils',
    'BaseProcessor'
]
