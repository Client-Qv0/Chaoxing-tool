"""超星学习通加密与签名工具模块。

提供 AES-CBC 加密、Cookie 解析、视频播放 enc 签名生成等功能。
"""

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import base64
import hashlib
import re


SECRET = "d_yHJ!$pdA~5"


def encrypt_by_AES(message: str, key: str) -> str:
    """使用 AES-CBC 模式加密明文，返回 Base64 编码的密文。

    Args:
        message: 待加密的明文字符串
        key: 加密密钥，同时作为 IV 使用

    Returns:
        Base64 编码后的密文字符串
    """
    key_bytes = key.encode('utf-8')
    iv_bytes = key_bytes

    block_size = 16
    padding_len = block_size - (len(message) % block_size)
    padded_msg = message + chr(padding_len) * padding_len

    cipher = Cipher(algorithms.AES(key_bytes), modes.CBC(iv_bytes), backend=default_backend())
    encryptor = cipher.encryptor()

    encrypted = encryptor.update(padded_msg.encode('utf-8')) + encryptor.finalize()

    return base64.b64encode(encrypted).decode('utf-8')


def parse_cookiejar_to_dict(cookiejar_str: str) -> dict[str, str]:
    """解析 RequestsCookieJar 字符串表示，提取为 name-value 字典。

    Args:
        cookiejar_str: requests.Session.cookies 的 str() 输出

    Returns:
        以 cookie name 为键、value 为值的字典
    """
    pattern = r'<Cookie\s+([^=]+)=([^\s]+)\s+for\s+([^>]+)>'
    matches = re.findall(pattern, cookiejar_str)

    _cookies = {}
    for name, value, _domain in matches:
        _cookies[name] = value

    return _cookies


def generate_enc(clazzId: str, userid: str, jobid: str, objectId: str,
                 playTime: int, attDuration: int, clipTime: str) -> str:
    """生成超星视频播放进度上报的 enc 签名。

    将各参数拼接后取 MD5 哈希值。

    Args:
        clazzId: 班级 ID
        userid: 用户 ID
        jobid: 任务 ID
        objectId: 视频对象 ID
        playTime: 当前播放时长（秒），内部会乘以 1000
        attDuration: 视频总时长（秒），内部会乘以 1000
        clipTime: 视频片段时间范围，格式如 "0_3600"

    Returns:
        32 位小写 MD5 哈希值
    """
    data = (
        f"[{clazzId}][{userid}][{jobid}][{objectId}]"
        f"[{playTime * 1000}][{SECRET}][{attDuration * 1000}][{clipTime}]"
    )
    return hashlib.md5(data.encode('utf-8')).hexdigest()