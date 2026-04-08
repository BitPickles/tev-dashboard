#!/usr/bin/env python3
"""
Polymarket EVM Authentication Module
使用 EVM 钱包签名进行 API 认证

注意：此模块现在是对 utils.py 的封装，保持向后兼容
"""

from utils import (
    generate_wallet,
    sign_message,
    get_auth_headers,
    get_eip712_auth_headers,
    validate_private_key,
)

# EIP-712 域配置（供参考）
POLYMARKET_DOMAIN = {
    "name": "Polymarket",
    "version": "1",
    "chainId": 137,  # Polygon
}

# 重新导出所有函数以保持向后兼容
__all__ = [
    "generate_wallet",
    "sign_message",
    "get_auth_headers",
    "get_eip712_auth_headers",
    "validate_private_key",
    "POLYMARKET_DOMAIN",
]


if __name__ == "__main__":
    # 生成钱包并显示
    pk, addr = generate_wallet()
    print(f"Private Key: {pk}")
    print(f"Address: {addr}")

    # 生成认证头
    headers = get_auth_headers(pk)
    print(f"\nAuth Headers:")
    for k, v in headers.items():
        print(f"  {k}: {v}")

    # 测试 EIP-712 认证头
    eip712_headers = get_eip712_auth_headers(pk)
    print(f"\nEIP-712 Auth Headers:")
    for k, v in eip712_headers.items():
        print(f"  {k}: {v}")
