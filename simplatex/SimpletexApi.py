import datetime
import json
import requests
from random import Random
import hashlib
import os
import configparser
import sys

# 获取当前工作目录
pwd = os.getcwd()

# 创建配置解析器对象
config = configparser.ConfigParser()

# 配置文件路径
config_file = os.path.join(pwd, ".ini")

# 读取 .ini 文件
if os.path.exists(config_file):
    try:
        config.read(config_file, encoding="utf-8")
        # 获取配置信息
        SIMPLETEX_APP_ID = config.get("Simpletex", "APP_ID")
        SIMPLETEX_APP_SECRET = config.get("Simpletex", "APP_SECRET")
        
        # 检查配置是否为空或占位符
        if (not SIMPLETEX_APP_ID or SIMPLETEX_APP_ID == "your_app_id_here" or
            not SIMPLETEX_APP_SECRET or SIMPLETEX_APP_SECRET == "your_app_secret_here"):
            print("错误：配置文件中的 API 凭据无效或仍为占位符")
            print("请检查 .ini 文件并填入正确的 API 凭据")
            sys.exit(1)
            
    except Exception as e:
        print(f"读取配置文件失败: {e}")
        print("请确保 .ini 文件存在且包含正确的配置信息")
        sys.exit(1)
else:
    print(f"配置文件 {config_file} 不存在")
    print("请创建 .ini 文件并包含以下配置:")
    print("[Simpletex]")
    print("APP_ID = your_app_id_here")
    print("APP_SECRET = your_app_secret_here")
    sys.exit(1)

def random_str(randomlength=16):
    str = ''
    chars = 'AaBbCcDdEeFfGgHhIiJjKkLlMmNnOoPpQqRrSsTtUuVvWwXxYyZz0123456789'
    length = len(chars) - 1
    random = Random()
    for i in range(randomlength):
        str += chars[random.randint(0, length)]
    return str


def get_req_data(req_data, appid, secret):
    header = {}
    header["timestamp"] = str(int(datetime.datetime.now().timestamp()))
    header["random-str"] = random_str(16)
    header["app-id"] = appid
    pre_sign_string = ""
    sorted_keys = list(req_data.keys()) + list(header)
    sorted_keys.sort()
    for key in sorted_keys:
        if pre_sign_string:
            pre_sign_string += "&"
        if key in header:
            pre_sign_string += key + "=" + str(header[key])
        else:
            pre_sign_string += key + "=" + str(req_data[key])

    pre_sign_string += "&secret=" + secret
    header["sign"] = hashlib.md5(pre_sign_string.encode()).hexdigest()
    return header, req_data

if __name__ == "__main__":
    pwd = os.getcwd()
    work_dir = pwd + "/tex-ocr/"
    img_file = {"file": open(work_dir + "image/1.png", 'rb')}
    data = {

    } # 请求参数数据（非文件型参数），视情况填入，可以参考各个接口的参数说明
    header, data = get_req_data(data, SIMPLETEX_APP_ID, SIMPLETEX_APP_SECRET)
    res = requests.post("https://server.simpletex.cn/api/latex_ocr_turbo", files=img_file, data=data, headers=header)

    print(json.loads(res.text))