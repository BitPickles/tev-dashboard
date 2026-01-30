#!/usr/bin/env python3
"""
共享工具模块
统一管理钱包生成、认证等公共功能
"""

import secrets
import time
import hashlib
from typing import Tuple, Dict, Optional
from eth_account import Account
from eth_account.messages import encode_defunct


def generate_wallet() -> Tuple[str, str]:
    """
    生成新的 EVM 钱包

    Returns:
        Tuple[str, str]: (private_key, address)
    """
    priv = secrets.token_hex(32)
    private_key = "0x" + priv
    account = Account.from_key(private_key)
    return private_key, account.address


def sign_message(private_key: str, message: str) -> Tuple[str, str]:
    """
    签名消息

    Args:
        private_key: EVM 私钥
        message: 要签名的消息

    Returns:
        Tuple[str, str]: (signature, address)
    """
    account = Account.from_key(private_key)
    message_encoded = encode_defunct(text=message)
    signed_message = account.sign_message(message_encoded)
    return signed_message.signature.hex(), account.address


def get_auth_headers(private_key: str, use_milliseconds: bool = False) -> Dict[str, str]:
    """
    生成认证请求头

    Args:
        private_key: EVM 私钥
        use_milliseconds: 是否使用毫秒时间戳

    Returns:
        Dict[str, str]: 认证请求头
    """
    timestamp = int(time.time() * 1000) if use_milliseconds else int(time.time())
    message = f"Polymarket API Authentication\nTimestamp: {timestamp}"

    signature, address = sign_message(private_key, message)

    return {
        "x-poly-address": address,
        "x-poly-signature": signature,
        "x-poly-timestamp": str(timestamp),
        "Content-Type": "application/json"
    }


def get_eip712_auth_headers(private_key: str) -> Dict[str, str]:
    """
    使用 EIP-712 生成认证请求头

    Args:
        private_key: EVM 私钥

    Returns:
        Dict[str, str]: 认证请求头
    """
    account = Account.from_key(private_key)
    timestamp = int(time.time() * 1000)
    nonce = secrets.token_hex(16)

    # 构造签名消息
    message_str = f"Polymarket Authentication\nTimestamp: {timestamp}\nNonce: {nonce}"
    message_hash = hashlib.sha256(message_str.encode()).hexdigest()
    message_encoded = encode_defunct(hexstr=message_hash)
    signed = account.sign_message(message_encoded)

    return {
        "x-poly-address": account.address,
        "x-poly-signature": signed.signature.hex(),
        "x-poly-nonce": nonce,
        "x-poly-timestamp": str(timestamp),
        "Content-Type": "application/json"
    }


def validate_private_key(private_key: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    验证私钥有效性

    Args:
        private_key: EVM 私钥

    Returns:
        Tuple[bool, Optional[str], Optional[str]]: (is_valid, address, error_message)
    """
    try:
        if not private_key.startswith("0x"):
            private_key = "0x" + private_key

        if len(private_key) != 66:  # 0x + 64 hex chars
            return False, None, "私钥长度不正确（应为 64 个十六进制字符）"

        account = Account.from_key(private_key)
        return True, account.address, None
    except Exception as e:
        return False, None, str(e)


def validate_price(price: float) -> Tuple[bool, Optional[str]]:
    """
    验证价格有效性

    Args:
        price: 价格值

    Returns:
        Tuple[bool, Optional[str]]: (is_valid, error_message)
    """
    if not isinstance(price, (int, float)):
        return False, "价格必须是数字"
    if price < 0 or price > 1:
        return False, "价格必须在 0-1 之间"
    return True, None


def validate_amount(amount: float, min_amount: float = 0.01) -> Tuple[bool, Optional[str]]:
    """
    验证金额有效性

    Args:
        amount: 金额
        min_amount: 最小金额

    Returns:
        Tuple[bool, Optional[str]]: (is_valid, error_message)
    """
    if not isinstance(amount, (int, float)):
        return False, "金额必须是数字"
    if amount < min_amount:
        return False, f"金额必须大于 ${min_amount}"
    return True, None


if __name__ == "__main__":
    # 测试钱包生成
    pk, addr = generate_wallet()
    print(f"Private Key: {pk}")
    print(f"Address: {addr}")

    # 测试认证头
    headers = get_auth_headers(pk)
    print(f"\nAuth Headers:")
    for k, v in headers.items():
        print(f"  {k}: {v}")
