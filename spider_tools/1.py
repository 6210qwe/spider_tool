# import oss2
# import pymysql
#
# conn = pymysql.Connect(
#     host="rm-2ze9f04i505y525i19o.mysql.rds.aliyuncs.com",
#     port=3306,
#     user="lucky2025",
#     password="80f4%d5fc",
#     db="patents",
#     charset="utf8mb4"
# )
# cur = conn.cursor()
# sql = "select * from oss_sts where id = 1"
# cur.execute(sql)
# oss_sts = cur.fetchone()
# taken = oss_sts[1]
# key_id = oss_sts[2]
# key_secret = oss_sts[3]
# print(taken, key_id, key_secret)
# auth = oss2.StsAuth(key_id, key_secret, taken)
# endpoit = 'http://oss-cn-beijing.aliyuncs.com'
# buckname = 'ytb-zhuanli'
# bucket = oss2.Bucket(auth, endpoit, buckname)
#
# object_name = 'AU1000201.pdf'
#
# url = bucket.sign_url('GET', object_name, 600, slash_safe=True)
# print('预签名URL的地址为：', url)


# 一行代码提取文档类型（仅保留主流文档后缀）
from purl import URL

def get_ext(url):
    return URL(url).path().split('.')[-1].lower() if (isinstance(url, str) and '.' in URL(url).path()) else ''

# 测试（一行调用）
print(get_ext("https://example.com/report.pdf?token=123"))  # pdf
print(get_ext("https://example.com/file.docx#fragment"))    # docx
print(type(get_ext("https://example.com/archive.tar.gz")))       # gz（多后缀取最后一个）
