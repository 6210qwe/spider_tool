import warnings
from collections import Counter
from pprint import pprint

import requests
import pandas as pd
from io import BytesIO
# 核心：过滤openpyxl的页眉/页脚解析警告
warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl.worksheet.header_footer')
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


if __name__ == "__main__":
    url = "https://www.nmpa.gov.cn/directory/web/nmpa/images/ufq80tKpxre84La9udzA7b7WMjAxOMTqtdo5NLrFzai45ri9vP4yLnhsc3g=.xlsx"
    pprint(parse_excel(url))