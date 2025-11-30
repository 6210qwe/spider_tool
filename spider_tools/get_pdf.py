# -*- coding: utf-8 -*-

import os
import json
import sys
import json
import re
import shutil
from concurrent.futures import ThreadPoolExecutor
from pypdf import PdfWriter
import os
import struct
import zlib
import requests
import os
import json
import time
import os
import requests
import zipfile
from retrying import retry
from pathlib import Path
import shutil
import os
import json
import subprocess
import base64
from loguru import logger

key1 = "PJLKMNOI3xyz021wvrpqstouHCFBDEGAnhikjlmgfZbacedYRXTSUVQW!56789+4"
key2 = "PJKLMNOI3xyz012wvprqstuoHBCDEFGAnhijklmgfZabcdeYXRSTUVWQ!56789+4"
std_str = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"


def encode(data: str, key: str = key1) -> str:
    return (
        base64.b64encode(data.encode("utf-8"))
        .decode("utf-8")
        .translate(str.maketrans(std_str, key))
    )


def decode(data: str, key: str = key1) -> str:
    return base64.b64decode(data.translate(str.maketrans(key, std_str))).decode("utf-8")


class Config:
    def __init__(self, config_path="config.json"):
        # 配置直接整合到代码中，不依赖外部文件
        self.default_config = {
            "version": "1.8",
            "ffdec_version": "version24.1.0",
            "o_dir_path": "docs/",
            "o_swf_path": "swf/",
            "o_pdf_path": "pdf/",
            "o_svg_path": "svg/",
            "proxy_url": "https://ghproxy.cn/",
            "check_update": True,
            "swf2svg": False,
            "svgfontface": False,
            "clean": True,
            "get_more": False,
            "path_replace": True,
            "download_workers": 10,
            "convert_workers": 5,
            "auto_mode": True  # 默认启用自动模式
        }
        self.config_path = config_path
        # 直接使用默认配置，不读取文件
        self.load_from_default()

    def load_from_default(self):
        """直接从代码中的默认配置加载，不依赖文件"""
        config_data = self.default_config.copy()

        # 如果config.json存在，可以选择性地读取部分配置（可选功能）
        # 但主要使用代码中的默认配置
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    file_config = json.load(f)
                # 只读取version和ffdec_version，其他使用代码默认值
                if "version" in file_config:
                    config_data["version"] = file_config["version"]
                if "ffdec_version" in file_config:
                    config_data["ffdec_version"] = file_config["ffdec_version"]
            except:
                pass  # 如果文件读取失败，使用默认配置

        # 直接使用配置值
        self.version = config_data.get("version", "1.8")
        self.ffdec_version = config_data.get("ffdec_version", "version24.1.0")
        self.o_dir_path = config_data["o_dir_path"]
        self.o_swf_path = config_data["o_swf_path"]
        self.o_pdf_path = config_data["o_pdf_path"]
        self.o_svg_path = config_data["o_svg_path"]
        self.dir_path = ""
        self.swf_path = ""
        self.pdf_path = ""
        self.svg_path = ""
        self.proxy_url = config_data["proxy_url"]
        self.check_update = config_data["check_update"]
        self.swf2svg = config_data["swf2svg"]
        self.svgfontface = config_data["svgfontface"]
        self.clean = config_data["clean"]
        self.get_more = config_data["get_more"]
        self.path_replace = config_data["path_replace"]
        self.download_workers = config_data["download_workers"]
        self.convert_workers = config_data["convert_workers"]
        self.auto_mode = config_data["auto_mode"]

    def reload(self):
        self.load_from_default()

    def save(self):
        """保存配置到文件（可选功能，主要用于记录version和ffdec_version）"""
        config_data = {
            "version": self.version,
            "ffdec_version": self.ffdec_version,
            "o_dir_path": self.o_dir_path,
            "o_swf_path": self.o_swf_path,
            "o_pdf_path": self.o_pdf_path,
            "o_svg_path": self.o_svg_path,
            "proxy_url": self.proxy_url,
            "check_update": self.check_update,
            "swf2svg": self.swf2svg,
            "svgfontface": self.svgfontface,
            "clean": self.clean,
            "get_more": self.get_more,
            "path_replace": self.path_replace,
            "download_workers": self.download_workers,
            "convert_workers": self.convert_workers,
            "auto_mode": self.auto_mode
        }
        try:
            with open(self.config_path, 'w') as f:
                json.dump(config_data, f, indent=4)
        except:
            pass  # 如果保存失败，不影响程序运行


cfg2 = Config()


class gen_cfg:
    def __init__(self, config: dict) -> None:
        self.headerInfo = config['headerInfo']
        self.p_swf = config['p_swf']
        self.ebt_host = config['ebt_host']
        self.p_code = config['p_code']
        self.pageInfo = config['pageInfo']
        self.p_name = config["p_name"]
        self.p_date = config["p_upload_date"]
        self.p_countinfo = config['pageCount']
        self.p_download = config['p_download']
        self.p_doc_format = config['p_doc_format']
        self.p_pagecount = config['p_pagecount']
        self.pageids = decode(self.pageInfo).split(",")
        self.p_count = len(self.pageids)
        self.headnums = self.headerInfo.replace('"', "").split(',')

    def ph_nums(self) -> int:
        return len(self.headnums)

    def ph_num(self, page: int) -> int:
        pageid = self.pageids[page - 1].split("-")
        return int(pageid[0])

    def ph(self, level):
        return self.c_ph(self, level)

    def pk(self, page):
        return self.c_pk(self, page)

    class c_ph():
        def __init__(self, cfg, level: int) -> None:
            self.name = "getebt-" + encode(f"{level}-0-{cfg.headnums[level - 1]}-{cfg.p_swf}", key2) + ".ebt"
            self.url = f"{cfg.ebt_host}/{self.name}"

    class c_pk():
        def __init__(self, cfg, page: int) -> None:
            pageid = cfg.pageids[page - 1].split("-")
            level_num = int(pageid[0])
            self.name = "getebt-" + encode(f"{level_num}-{pageid[3]}-{pageid[4]}-{cfg.p_swf}-{page}-{cfg.p_code}",
                                           key2) + ".ebt"
            self.url = f"{cfg.ebt_host}/{self.name}"


class Update:
    def __init__(self, cfg2: Config) -> None:
        self.cfg2 = cfg2
        self.docs_dir = self.cfg2.o_dir_path[0:-1] if self.cfg2.o_dir_path.endswith("/") else self.cfg2.o_dir_path

    def download_ffdec(self):
        ffdec_info = github_release("jindrapetrik/jpexs-decompiler", 2)
        ffdec_url = cfg2.proxy_url + ffdec_info.download_url
        logger.info("开始下载 ffdec...")
        logger.info(
            "警告: 使用内置下载可能会非常慢，建议手动下载 ffdec 的压缩包，并将文件（确保包含 'ffdec.jar'）解压到 'ffdec' 目录中。"
        )
        logger.info("正在下载: " + ffdec_url)
        try:
            os.makedirs("ffdec")
        except FileExistsError:
            # 自动模式下，如果目录已存在，自动继续
            if cfg2.auto_mode or choose("exists"):
                shutil.rmtree("ffdec")
                os.makedirs("ffdec")
                logger.info("Continuing...")
            else:
                return False
        try:
            download(ffdec_url, "ffdec/ffdec.zip")
        except:
            logger.info(
                "下载出错! 请检查网络连接或修改配置中的 'proxy_url' 内容。如果仍然无法下载，请手动下载 ffdec 文件并提取到目录 ffdec 中。"
            )
            input()
            return False
        logger.info("下载完成! 开始解压...")
        try:
            extractzip("ffdec/ffdec.zip", "ffdec/")
            os.remove("ffdec/ffdec.zip")
            logger.info("解压完成!")
            return True
        except zipfile.BadZipFile:
            logger.info(
                "解压失败! 链接可能已失效? 请尝试修改函数 'download_ffdec' 中的 'ffdec_url' 内容。"
            )
            input()
            return False

    def check_java(self):
        text = "Java 不正常，请尝试重新安装 Java。"
        text2 = "Java 未找到! 请安装 Java 并将其添加到 PATH 或 JAVA_HOME 中。"
        try:
            output = subprocess.run(['java', '-version'], capture_output=True, text=True)
            if output.returncode != 0:
                logger.info(text)
                return False
            return True
        except FileNotFoundError:
            platform = os.name
            if platform == "nt":
                java_home = os.environ.get("JAVA_HOME", "")
                if java_home:
                    java_path = os.path.join(java_home, "bin", "java.exe")
                    if os.path.isfile(java_path):
                        os.environ["PATH"] = os.pathsep.join(
                            [os.path.join(java_home, "bin"), os.environ.get("PATH", "")])
                        try:
                            if subprocess.run(['java', '-version'], capture_output=True).returncode == 0:
                                logger.info(
                                    "警告: Java 未配置到 PATH 中，但在 JAVA_HOME 中找到了，建议将其添加到 PATH 中。")
                                return True
                            else:
                                logger.info(text)
                                return False
                        except FileNotFoundError:
                            logger.info(text2)
                            return False
                    else:
                        logger.info(text2)
                        return False
            else:
                logger.info(text2)
                return False

    def ffdec_update(self):
        if os.path.isfile("ffdec/ffdec.jar"):
            # 自动模式下，删除旧版本
            if cfg2.auto_mode or choose("是否删除旧版本ffdec，否则创建备份？ (Y: 删除, N: 备份): "):
                try:
                    shutil.rmtree("ffdec")
                except Exception as e:
                    logger.info(f"Error occurred while removing old version: {e}")
            else:
                try:
                    name = self.cfg2.ffdec_version
                    for i in range(1, 100):
                        if os.path.isdir(f"ffdec_{name}") or os.path.isdir(f"ffdec_{name}_{i}"):
                            name = f"{name}_{i + 1}"
                            break
                    shutil.move("ffdec", f"ffdec_{name}")
                except Exception as e:
                    logger.info(f"Error occurred while updating old version: {e}")
        return self.download_ffdec()

    def upgrade(self):
        if self.cfg2.version < "1.7":
            logger.info("检测到旧版本资源文件，正在更新...")
            self.resource_update()
        self.cfg2.version = self.cfg2.default_config["version"]
        self.cfg2.save()

    def resource_update(self):
        if not os.path.isdir(self.docs_dir):
            return
        for name in os.listdir(self.docs_dir):
            subdir = os.path.join(self.docs_dir, name)
            index_path = os.path.join(subdir, "index.json")
            if os.path.isdir(subdir) and os.path.isfile(index_path):
                try:
                    with open(index_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    p_code = data["p_code"]
                    new_dir = os.path.join(self.docs_dir, p_code)
                    if not os.path.exists(new_dir):
                        os.makedirs(new_dir)
                    for file in os.listdir(subdir):
                        shutil.move(os.path.join(subdir, file), os.path.join(new_dir, file))
                    shutil.rmtree(subdir)
                except Exception as e:
                    logger.info(f"资源文件迁移失败: {subdir} -> {e}")
        self.gen_indexs()

    def gen_indexs(self):
        indexs = {}
        for name in os.listdir(self.docs_dir):
            subdir = os.path.join(self.docs_dir, name)
            index_path = os.path.join(subdir, "index.json")
            if os.path.isdir(subdir) and os.path.isfile(index_path):
                try:
                    with open(index_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    indexs[data["p_code"]] = data["p_name"]
                except Exception as e:
                    logger.info(f"资源文件索引生成失败: {subdir} -> {e}")
        with open(os.path.join(self.docs_dir, "indexs.json"), "w", encoding="utf-8") as f:
            json.dump(indexs, f, ensure_ascii=False, indent=2)

    def check_update(self):
        try:
            main_info = github_release("cmy2008/doc88_extractor")
            if main_info.latest_version.lstrip("V") > self.cfg2.default_config["version"]:
                logger.info(f"主程序检测到新版本 {main_info.latest_version}，下载连接：\n{main_info.download_url}")
            return True
        except Exception as e:
            logger.info(f"Error occurred while checking for project updates: {e}")
            return False

    def check_ffdec_update(self):
        try:
            ffdec_info = github_release("jindrapetrik/jpexs-decompiler", 2)
            if ffdec_info.latest_version != self.cfg2.ffdec_version and os.path.isfile(
                    "ffdec/ffdec.jar") and self.cfg2.check_update:
                # 自动模式下，跳过ffdec更新（保持当前版本）
                if not cfg2.auto_mode and not choose(
                        f"当前 ffdec 版本 {self.cfg2.ffdec_version}, 检测到新版本(文件名：{ffdec_info.name})，是否更新？ (Y/n): "):
                    return False
            if ffdec_info.latest_version == self.cfg2.ffdec_version and os.path.isfile("ffdec/ffdec.jar"):
                return False
            if not self.ffdec_update() and not os.path.isfile("ffdec/ffdec.jar"):
                exit()
            self.cfg2.ffdec_version = ffdec_info.latest_version
            self.cfg2.save()
            return True
        except Exception as e:
            logger.info(f"Error occurred while checking ffdec updates: {e}")
            return False


def ospath(path):
    if os.name == "nt" and cfg2.path_replace:
        fullpath = Path(path)
        if len(str(fullpath.absolute())) >= 260:
            return "\\\\?\\" + str(fullpath.absolute())
        else:
            return fullpath
    else:
        return path


def special_path(path):
    char_list = ['*', '|', ':', '?', '/', '<', '>', '"', '\\']
    new_char_list = ['＊', '｜', '：', '？', '／', '＜', '＞', '＂', '＼']
    for i in range(len(char_list)):
        path = path.replace(char_list[i], new_char_list[i])
    return path


def choose(text=""):
    # 如果启用了自动模式，直接返回True，跳过所有确认
    if cfg2.auto_mode:
        return True

    if text == "exists":
        text = "The directory already exists!\nContinue? (Y/n): "
    elif text == "down":
        text = "是否下载，否则继续提取预览文档？ (Y/n): "
    elif text == "":
        text = "Continue? (Y/n): "
    try:
        user_input = input(text)
    except KeyboardInterrupt:
        exit()
    if user_input == "Y" or user_input == "y":
        return True
    else:
        return False


def logw(t: str):
    log = "[" + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + "]: " + t + "\n"
    log_dir = "logs/"
    dirc = log_dir + time.strftime("%Y-%m-%d", time.localtime()) + ".log"
    if not os.path.isdir(log_dir):
        os.mkdir(log_dir)
    with open(ospath(dirc), "a") as file:
        file.write(log)


def r(str):
    return '"' + str + '"'


def get_request(url: str):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36 Edg/112.0.1722.39",
        "Content-Type": "text/html; charset=utf-8",
        "Referer": "https://www.doc88.com/",
    }
    return requests.get(url, headers=headers)


def write_file(data, path):
    with open(ospath(path), "wb") as f:
        f.write(data)
        f.close()


def writes_file(data, path):
    with open(ospath(path), "w") as f:
        f.write(data)
        f.close()


def read_file(path):
    with open(ospath(path), "r") as file:
        read = file.read()
        return read


def load_file(path):
    with open(ospath(path), "rb") as file:
        read = file.read()
        return read


@retry(stop_max_attempt_number=3, wait_fixed=500)
def download(url: str, filepath: str):
    write_file(requests.get(url).content, filepath)


def extractzip(file_path: str, topath: str):
    with zipfile.ZipFile(file_path, "r") as f:
        f.extractall(topath)
        f.close


class github_release:
    def __init__(self, repo: str, n: int = 0) -> None:
        self.repo = repo
        self.latest_version = ""
        self.download_url = ""
        self.name = ""
        self.fetch_release_info(n)

    def fetch_release_info(self, n: int = 0):
        version_info = get_request(f"https://api.github.com/repos/{self.repo}/releases/latest").json()
        self.latest_version = version_info["tag_name"]
        self.download_url = version_info['assets'][n]['browser_download_url']
        self.name = version_info['assets'][n]['name']


# getebt-self.level_num-offset-filesize-p_swf-page-p_code
# ebt文件的编号，self.level_num为层数编号，offset为内容偏移量，filesize为获取的内容长度，文件排序如下：头文件1,页文件1...重置计数...头文件2,页文件51...
# get_more 尝试从隐藏文档中提取额外页

class get_more:
    def __init__(self, cfg: gen_cfg, level, filepath, page=0) -> None:
        self.cfg = cfg
        self.level = level
        self.chunk_size = 10240000
        self.header = bytearray()
        self.filepath = filepath
        self.newpageids = []
        self.pagecount = page
        self.PH_data = requests.get(self.cfg.ph(self.level).url).content
        self.progressfile = filepath + "progress.json"
        self.progress = {"pk": [], "ph": []}
        self.save_progress("ph", self.level)
        self.PK_data = bytearray()
        self.ids = []
        return None

    def read_progress(self):
        self.progress = json.loads(read_file(self.progressfile))

    def save_progress(self, type: str, page: int):
        self.progress[type].append(page)
        writes_file(json.dumps(self.progress), self.progressfile)

    def start(self):

        write_file(self.PH_data, f"{self.filepath}{self.cfg.ph(self.level).name}")
        if self.scan(self.level):
            return self.get_newpageids()

    def scan(self, scan_range=0):
        logger.info(f"level {self.level} start scannig...")
        headsize = int(self.cfg.headnums[self.level - 1])
        self.flags = [headsize]
        url = (
                self.cfg.ebt_host
                + "/getebt-"
                + encode(
            f"{self.level}-{headsize}-{self.chunk_size}-{self.cfg.p_swf}-1-{self.cfg.p_code}",
            key2,
        )
                + ".ebt"
        )
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            with open(ospath(f"{self.filepath}cache.ebt"), "wb") as file:
                size = 0
                offset = 0
                status = False
                try:
                    for chunk in response.iter_content(chunk_size=1):
                        if chunk:
                            self.PK_data.extend(chunk)
                            if 32 <= size <= 33:
                                self.header.extend(chunk)
                            elif size > 33:
                                if chunk == struct.pack("B", self.header[0]):
                                    status = True
                                elif chunk == struct.pack("B", self.header[1]):
                                    if status == True:
                                        if size - 33 - offset < scan_range:
                                            logger.info(f"pass:{size}-{size - 33 - offset}")
                                            status = False
                                            pass
                                        else:
                                            br = f"{headsize + offset}-{size - 33 - offset}"
                                            if self.test():
                                                write_file(
                                                    self.PK_data,
                                                    f"{self.filepath}getebt-{encode(f'{self.level}-{headsize + offset}-{size - offset - 33}-{self.cfg.p_swf}-{self.pagecount + len(self.ids) + 1}-{self.cfg.p_code}', key2)}.ebt",
                                                )
                                                self.save_progress(
                                                    "pk",
                                                    self.pagecount + len(self.ids) + 1,
                                                )
                                                self.PK_data = self.PK_data[
                                                               size - 33 - offset:
                                                               ]
                                                logger.info(f"found:{br}")
                                                self.ids.append(br)
                                                offset = size - 33
                                            else:
                                                logger.info(f"zpass:{br}")
                                                status = False
                                                pass
                                    else:
                                        status = False
                                else:
                                    status = False
                            size += file.write(chunk)
                except requests.exceptions.ChunkedEncodingError:
                    pass
                if self.test():
                    write_file(
                        self.PK_data,
                        f"{self.filepath}getebt-{encode(f'{self.level}-{headsize + offset}-{size - offset}-{self.cfg.p_swf}-{self.pagecount + len(self.ids) + 1}-{self.cfg.p_code}', key2)}.ebt",
                    )
                    self.save_progress("pk", self.pagecount + len(self.ids) + 1)
                    self.ids.append(f"{headsize + offset}-{size - offset}")
                    logger.info(f"finish:{headsize + offset}-{size - offset}")
                else:
                    logger.info("Except ending, is the file too big?")
                logger.info(f"total page:{len(self.ids)}")
                return True

    def test(self):
        comp = Compressor()
        pk = comp.decompressEBT_PK(self.PK_data)
        ph = comp.decompressEBT_PH(self.PH_data)
        if pk:
            write_file(
                comp.makeup(ph, pk),
                f"{self.filepath}swf/{self.pagecount + len(self.ids) + 1}.swf",
            )
            return True
        else:
            return False

    def get_newpageids(self):
        pid = f"{self.level}-{self.cfg.pageids[0].split('-')[1]}-{self.cfg.pageids[0].split('-')[2]}"
        for i in range(0, len(self.ids)):
            self.newpageids.append(f"{pid}-{self.ids[i]}")
        self.ids.clear()
        return self.newpageids


if cfg2.swf2svg:
    logger.info(
        "使用 SVG 转换功能建议同时关闭 font-face 功能，否则将会导致大量转换失败，若只需要 SVG 文件可关闭清理功能，文件将会生成到文档目录下的 svg 目录")
    if os.name == "nt":
        logger.warning(
            "警告：你正在使用 Windows 系统并使用 SVG 转换功能，虽然我们有意使其在多平台下工作，但需要使用 Cairo 库才能进行 SVG 的转换，建议你安装 GTK 运行库（需要 200MB 左右的安装空间）：\nhttps://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases\n如果安装后仍然无效，请尝试将安装目录下的 bin 目录添加到系统环境的 PATH 中然后重启终端或 Vscode\n")
        list = os.environ["Path"].split(";")
        pattern = re.compile(r"GTK.?-Runtime")
        matches = [item for item in list if pattern.search(item)]
        if matches:
            try:
                os.add_dll_directory(matches[0])
            except:
                logger.error("Error when setting environment.")
        else:
            logger.warning("GTK runtime not found, maybe not install?")
    import cairosvg


class Compressor:
    def __init__(self):
        return None

    def processSWF(self, file_EBT, file_EBT_PK, path):
        ph = self.decompressEBT_PH(load_file(file_EBT))
        pk = self.decompressEBT_PK(load_file(file_EBT_PK))
        swf = self.makeup(ph, pk)
        write_file(swf, path)

    def makeup(self, ebt_ph, ebt_pk):
        buff = bytearray()
        buff.extend(ebt_ph)
        buff.extend(ebt_pk)
        buff.extend(struct.pack("<BBBB", 64, 0, 0, 0))
        buff[4:8] = struct.pack("<I", len(buff))
        return buff

    def decompressEBT_PH(self, data):
        buff = bytearray()
        try:
            buff.extend(zlib.decompress(data[40:]))
            buff[4:8] = struct.pack("<I", len(buff))
        except zlib.error:
            return False
        return buff

    def decompressEBT_PK(self, data):
        try:
            return zlib.decompress(data[32:])
        except zlib.error:
            return False


def make_swf(file_EBT, file_EBT_PK, path):
    compressor = Compressor()
    compressor.processSWF(file_EBT, file_EBT_PK, path)


class get_cfg:
    def __init__(self, url: str) -> None:
        if url.find("doc88.com/p-") == -1 and url.find("doc88.piglin.eu.org/p-") == -1:
            raise Exception("Invalid URL!")
        self.url = url
        self.content = ""
        self.data = ""
        self.sta = 0
        if not self.get_main():
            # 自动模式下，如果主站失败，自动尝试CDN
            if cfg2.auto_mode or choose("Do you want to use CDN?(Y/n): "):
                self.__init__("https://doc88.piglin.eu.org" + url[url.find("doc88.com/") + 9:])
                return None
        return None

    def req(self):
        request = get_request(self.url)
        if request.status_code == 404:
            self.sta = 1
            raise Exception("404 Not found!")
        self.content = request.text

    def get_main(self):
        self.req()
        data = re.search(r"m_main.init\(\".*\"\);", self.content)
        if data == None:
            if re.search("网络环境安全验证", self.content):
                logger.warning("WAF detected!")
                return False
            raise Exception("Config data not found! May be deleted?")
        c = data.span()
        self.data = self.content[c[0] + 13: c[1] - 3]
        return True


def append_pdf(pdf: PdfWriter, file: str):
    pdf.append(ospath(file))
    return pdf


class init:
    def __init__(self, config: dict) -> None:
        cfg2.dir_path = cfg2.o_dir_path + config["p_code"] + "/"
        cfg2.swf_path = cfg2.dir_path + cfg2.o_swf_path
        cfg2.svg_path = cfg2.dir_path + cfg2.o_svg_path
        cfg2.pdf_path = cfg2.dir_path + cfg2.o_pdf_path
        try:
            os.makedirs(ospath(cfg2.dir_path))
        except FileExistsError:
            if choose("exists"):
                pass
            else:
                exit()
        if not os.path.exists(ospath(f"{cfg2.dir_path}index.json")):
            write_file(
                bytes(json.dumps(config), encoding="utf-8"),
                cfg2.dir_path + "index.json",
            )
        try:
            os.makedirs(ospath(cfg2.swf_path))
            os.makedirs(ospath(cfg2.svg_path))
            os.makedirs(ospath(cfg2.pdf_path))
        except:
            pass


def main(encoded_str, more=False):
    try:
        config = json.loads(decode(encoded_str))
    except json.decoder.JSONDecodeError:
        logger.error("Can't read!")
        return False
    except (ValueError, UnicodeDecodeError):
        logger.error("Can't read! Maybe keys were changed?")
        return False
    init(config)
    cfg = gen_cfg(config)
    if os.path.exists(ospath(f"{cfg2.dir_path}index.json")):
        cfg = gen_cfg(json.loads(read_file(f"{cfg2.dir_path}index.json")))
    logger.info(f"文档名：{cfg.p_name}")
    logger.info(f"文档 ID：{cfg.p_code}")
    logger.info(f"上传日期：{cfg.p_date}")
    logger.info(f"页数：{cfg.p_pagecount}")
    if int(cfg.p_pagecount) != cfg.p_count:
        more = True
        logger.info(f"可预览页数：{cfg.p_countinfo}")
        logger.info(f"可直接获取页数：{cfg.p_count}")
        logger.info(f"可能有额外页面（需扫描）！")
    # 自动模式下跳过确认，直接开始提取
    if not cfg2.auto_mode and not choose("开始提取？ (Y/n): "):
        return False
    if cfg.p_download == "1":
        logger.info("该文档为免费文档，可直接下载！")
        # 自动模式下，如果是免费文档，直接下载；否则继续提取预览
        if cfg2.auto_mode or choose("down"):
            try:
                if config["if_zip"] == 0:
                    doc_format = str.lower(cfg.p_doc_format)
                else:
                    doc_format = "zip"
                file_path = "docs/" + cfg.p_name + "." + doc_format
                download(
                    get_request("https://www.doc88.com/doc.php?act=download&pcode=" + cfg.p_code).text,
                    file_path,
                )
                logger.info("Saved file to " + file_path)
                return True
            except Exception as err:
                logger.error("Downlaod error: " + str(err))
                logw("Downlaod error: " + str(err))
        else:
            logger.info("Continuing...")
    if more:
        # 自动模式下，如果配置了get_more，则扫描；否则正常下载
        should_scan = cfg2.auto_mode and cfg2.get_more
        if should_scan or choose("即将通过扫描获取页面，是否继续（否则正常下载）？ (Y/n): "):
            logger.info("尝试通过扫描获取页面...")
            newpageids = []
            cfg.p_count = 0
            for i in range(1, cfg.ph_nums() + 1):
                get = get_more(cfg, i, cfg2.dir_path, cfg.p_count)
                get.start()
                newpageids += get.newpageids
                cfg.p_count += len(get.newpageids)
                del get
            cfg.pageids = newpageids
            config["pageInfo"] = encode(",".join(newpageids))
            config["p_count"] = cfg.p_count
            write_file(
                bytes(json.dumps(config), encoding="utf-8"),
                cfg2.dir_path + "index.json",
            )
            logger.info(f"成功扫描页数：{cfg.p_count}")
            del newpageids
            time.sleep(2)
        else:
            logger.info("普通下载模式...")
            more = False
    try:
        if not more:
            get_swf(cfg)
        convert(cfg)
        del cfg
        return True
    except Exception as err:
        logger.error(str(err))
        return False


class downloader:
    def __init__(self, cfg: gen_cfg) -> None:
        self.cfg = cfg
        self.downloaded = True
        self.progressfile = cfg2.dir_path + "progress.json"
        if os.path.isfile(ospath(self.progressfile)):
            self.read_progress()
        else:
            self.progress = {"pk": [], "ph": []}

    def read_progress(self):
        try:
            self.progress = json.loads(read_file(self.progressfile))
        except json.decoder.JSONDecodeError:
            self.progress = {}

    def save_progress(self, type: str, page: int):
        self.progress[type].append(page)
        writes_file(json.dumps(self.progress), self.progressfile)

    def ph(self, i: int):
        url = self.cfg.ph(i)
        logger.info(f"Downloading PH {i}: {url.url}")
        file_path = cfg2.dir_path + url.name
        if i in self.progress["ph"]:
            logger.info("Using Cache...")
            return None
        try:
            download(url.url, file_path)
            self.save_progress("ph", i)
        except Exception as e:
            logw(f"Download PH {i} error: {e}")
            self.downloaded = False

    def pk(self, i: int):
        url = self.cfg.pk(i)
        logger.info(f"Downloading page {i}: {url.url}")
        file_path = cfg2.dir_path + url.name
        if i in self.progress["pk"]:
            logger.info("Using Cache...")
            return None
        try:
            download(url.url, file_path)
            self.save_progress("pk", i)
        except Exception as e:
            logw(f"Download page {i} error: {e}")
            self.downloaded = False

    def makeswf(self, i: int):
        try:
            level_num = self.cfg.ph_num(i)
            make_swf(
                cfg2.dir_path + self.cfg.ph(level_num).name,
                cfg2.dir_path + self.cfg.pk(i).name,
                cfg2.swf_path + str(i) + ".swf",
            )
        except Exception as e:
            logger.info(f"Can't decompress page {i}! Skipping...")
            logw(str(e))
            self.cfg.p_count -= 1


def get_swf(cfg: gen_cfg):
    max_workers = cfg2.download_workers
    down = downloader(cfg)
    logger.info("Downloading PH...")
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for i in range(1, cfg.ph_nums() + 1):
            executor.submit(down.ph, i)
    logger.info("Downloading PK...")
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for i in range(1, cfg.p_count + 1):
            executor.submit(down.pk, i)
    if not down.downloaded:
        raise Exception("Downlaod error")
    logger.info("Making pages...")
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for i in range(1, cfg.p_count + 1):
            executor.submit(down.makeswf, i)
    logger.info("Donload done. (total page: " + str(cfg.p_count) + ")")


class converter:
    def __init__(self) -> None:
        self.pdf = PdfWriter()
        self.pdflist = set()
        try:
            if cfg2.svgfontface:
                log = os.popen(
                    "java -jar ffdec/ffdec.jar -config textExportExportFontFace=true"
                ).read()
            else:
                log = os.popen(
                    "java -jar ffdec/ffdec.jar -config textExportExportFontFace=flase"
                ).read()
        except Exception as err:
            logw(str(err))

    def set_swf(self, i: int):
        return os.popen(
            "java -jar ffdec/ffdec.jar -header -set frameCount 1 "
            + r(cfg2.swf_path + str(i) + ".swf")
            + " "
            + r(cfg2.swf_path + str(i) + ".swf")
        ).read()

    def swf2svg(self, i: int):
        def execute(num: int):
            dirpath = cfg2.svg_path + str(num) + "/"
            log = os.popen(
                "java -jar ffdec/ffdec.jar -format frame:svg -select 1 -export frame "
                + r(dirpath)
                + " "
                + r(cfg2.swf_path + str(num) + ".swf")
            ).read()
            shutil.move(
                ospath(dirpath + "1.svg"), ospath(cfg2.svg_path + str(i) + "_.svg")
            )
            shutil.rmtree(ospath(dirpath))

        logger.info("Converting page " + str(i) + " to svg...")
        try:
            execute(i)
        except FileNotFoundError:
            log = self.set_swf(i)
            try:
                execute(i)
            except FileNotFoundError:
                logger.info("Can't convert this page! Skipping...")
                logw("SVG converting error: " + log)

    def swf2pdf(self, i: int):
        def execute(num: int):
            dirpath = cfg2.pdf_path + str(num) + "/"
            log = os.popen(
                "java -jar ffdec/ffdec.jar -format frame:pdf -select 1 -export frame "
                + r(dirpath)
                + " "
                + r(cfg2.swf_path + str(num) + ".swf")
            ).read()
            shutil.move(
                ospath(dirpath + "frames.pdf"), ospath(cfg2.pdf_path + str(i) + "_.pdf")
            )
            shutil.rmtree(dirpath)
            shutil.move(
                ospath(cfg2.pdf_path + str(i) + "_.pdf"),
                ospath(cfg2.pdf_path + str(i) + ".pdf"),
            )
            self.pdflist.add(i)

        logger.info("Converting page " + str(i) + " to pdf...")
        try:
            execute(i)
        except FileNotFoundError:
            log = self.set_swf(i)
            try:
                execute(i)
            except FileNotFoundError:
                logger.info("Can't convert this page! Skipping...")
                logw("PDF converting error: " + log)

    def svg2pdf(self, i: int):
        try:
            logger.info(f"Converting page {i} to pdf...")
            cairosvg.svg2pdf(url=cfg2.svg_path + str(i) + "_.svg",
                             write_to=str(ospath(cfg2.pdf_path + str(i) + ".pdf")),
                             )
            self.pdflist.add(i)
        except FileNotFoundError:
            logger.info("Can't convert this page! Skipping...")

    def makepdf(self):
        for i in self.pdflist:
            self.pdf = append_pdf(self.pdf, str(ospath(cfg2.pdf_path + str(i) + ".pdf")))


def convert(cfg: gen_cfg):
    logger.info("开始转换...")
    max_workers = cfg2.convert_workers
    doc = converter()
    if not cfg2.swf2svg:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            for i in range(1, cfg.p_count + 1):
                executor.submit(doc.swf2pdf, i)
    else:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            for i in range(1, cfg.p_count + 1):
                executor.submit(doc.swf2svg, i)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            for i in range(1, cfg.p_count + 1):
                executor.submit(doc.svg2pdf, i)
    logger.info("Now start making pdf, please wait...")
    doc.makepdf()
    pdf_name = cfg2.o_dir_path + special_path(cfg.p_name) + ".pdf"
    doc.pdf.write(str(ospath(pdf_name)))
    logger.info("转换完成！")
    logger.info("已将文件保存至 " + pdf_name)


def clean(cfg2):
    logger.info("正在清理缓存...")
    shutil.rmtree(ospath(cfg2.swf_path))
    shutil.rmtree(ospath(cfg2.pdf_path))
    shutil.rmtree(ospath(cfg2.svg_path))
    for i in os.listdir(ospath(cfg2.dir_path)):
        if i.endswith(".ebt"):
            os.remove(ospath(cfg2.dir_path + i))
        elif i == "progress.json":
            os.remove(ospath(cfg2.dir_path + i))


class mode:
    def __init__(self) -> None:
        self.encode = ""

    def url(self):
        try:
            url = input("请输入网址：")
        except KeyboardInterrupt:
            exit()
        try:
            return main(get_cfg(url).data, cfg2.get_more)
        except Exception as Err:
            logger.info(Err)
            return False

    def pcode(self):
        try:
            p_code = input("请输入id：")
        except KeyboardInterrupt:
            exit()
        try:
            return main(get_cfg(f"https://www.doc88.com/p-{p_code}.html").data, cfg2.get_more)
        except Exception as Err:
            logger.info(Err)
            return False

    def data(self):
        try:
            data = input("请输入init_data：")
        except KeyboardInterrupt:
            exit()
        try:
            return main(data, cfg2.get_more)
        except Exception as Err:
            logger.info(Err)
            return False


def get_pdf(url=None):
    """
    下载 doc88 文档的主函数

    参数:
        url: doc88 文档的 URL，例如 "https://www.doc88.com/p-74787813372750.html"
            如果为 None，则进入交互模式
    """
    update = Update(cfg2)
    logger.info(f"update.check_java()的状态： update.check_java()")
    if not update.check_java():
        input()
        exit()
    update.check_ffdec_update()
    if cfg2.check_update:
        update.check_update()
    update.upgrade()

    # 如果传入了 URL，直接使用它
    if url:
        try:
            logger.info(f"开始处理 URL: {url}")
            result = main(get_cfg(url).data, cfg2.get_more)
            if result:
                update.gen_indexs()
                if cfg2.clean:
                    try:
                        clean(cfg2)
                    except NameError:
                        pass
            return result
        except Exception as Err:
            logger.error(f"处理 URL 时出错: {Err}")
            return False

    # 如果没有传入 URL，进入原有的交互模式
    a = sys.argv
    user = mode()
    if len(a) == 1:
        exe = user.url
    elif "-p" in a:
        exe = user.pcode
    elif "-d" in a:
        exe = user.data
    while True:
        if exe():
            update.gen_indexs()
            if cfg2.clean:
                try:
                    clean(cfg2)
                except NameError:
                    pass
            # 自动模式下，完成一个任务后继续下一个
            if cfg2.auto_mode:
                continue
            elif choose():
                pass
            else:
                exit()
        else:
            pass