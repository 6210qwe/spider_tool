from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend


def rsa_encrypt(public_key_pem, plaintext):
    """
    RSA加密：已知公钥（PEM格式）和明文，返回密文（十六进制字符串）
    :param public_key_pem: 公钥（PEM格式字符串）
    :param plaintext: 明文（字符串）
    :return: 加密后的密文（十六进制字符串）
    """
    # 1. 加载公钥（PEM格式字符串 → 公钥对象）
    public_key = serialization.load_pem_public_key(public_key_pem.encode("utf-8"), backend=default_backend())
    # 2. 明文转换为字节（RSA加密处理字节数据）
    plaintext_bytes = plaintext.encode("utf-8")
    # 3. 加密（使用PKCS1v15填充，RSA必须指定填充方式）
    ciphertext_bytes = public_key.encrypt(plaintext_bytes,padding.PKCS1v15())
    # 4. 密文转为十六进制（方便存储/传输，也可转为Base64）
    ciphertext_hex = ciphertext_bytes.hex()
    return ciphertext_hex

