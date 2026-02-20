#!/usr/bin/env python3
"""
Fluid 回购精准追踪
从 Etherscan API 追踪 Treasury 的 Buyback 交易
"""

import os
import time
import csv
import math
import json
import subprocess
from datetime import datetime, timezone, timedelta

# Etherscan API Key
ETHERSCAN_API_KEY = "BUWR46PIP7JVZK98IP7YRQARRSABIP3V92"
BASE = "https://api.etherscan.io/api"

# Config: addresses (official)
TREASURY = "0x28849D2b63fA8D361e5fc15cB8aBB13019884d09".lower()
TEAM_MULTISIG = "0x4F6F977aCDD1177DCD81aB83074855EcB9C2D49e".lower()
WATCH_WALLETS = {
    "treasury": TREASURY,
    "team_multisig": TEAM_MULTISIG,
}

# Token contracts (Ethereum mainnet)
TOKENS = {
    # FLUID token (Instadapp rebrand)
    "FLUID": "0x6f40d4a6237c257fff2db00fa0510deeedc303eb".lower(),
    # Common payment assets
    "WETH": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2".lower(),
    "USDC": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48".lower(),
    "USDT": "0xdAC17F958D2ee523a2206206994597C13D831ec7".lower(),
    "DAI": "0x6B175474E89094C44Da98b954EedeAC495271d0F".lower(),
}

PAY_TOKENS = {"WETH", "USDC", "USDT", "DAI"}  # tokens used to buy/sell FLUID

# ERC-20 Transfer topic0 keccak256("Transfer(address,address,uint256)")
TRANSFER_TOPIC0 = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"

# A small allowlist of typical routers/aggregators (optional signal)
ROUTERS = {
    "UniswapV3Router": "0xE592427A0AEce92De3Edee1F18E0157C05861564".lower(),
    "UniswapUniversalRouter": "0xEf1c6E67703c7BD7107eed8303Fbe6EC2554BF6B".lower(),
    "1inchV5": "0x1111111254EEB25477B68fb85Ed929f73A960582".lower(),
    "0xExchangeProxy": "0xdef1c0ded9bec7f1a1670819833240f027b25eff".lower(),
    "ParaswapV5": "0xDEF171Fe48CF0115B1d80b88dc8eAB59176FEe57".lower(),
}

# Time window
START_DATE = "2025-10-01"
START_TS = int(datetime.fromisoformat(START_DATE).replace(tzinfo=timezone.utc).timestamp())

# Helpers
def etherscan_get(params, max_retries=5, sleep_s=0.25):
    """Etherscan API GET request with retry"""
    params_str = "&".join([f"{k}={v}" for k, v in params.items()])
    result = subprocess.run(
        ["curl", "-s", "--max-time", "30", f"{BASE}?{params_str}"],
        capture_output=True, text=True
    )
    data = json.loads(result.stdout)
    return data

def fetch_fluid_transfers_to_treasury():
    """获取 FLUID 转入 Treasury 的交易"""
    result = etherscan_get({
        "module": "account",
        "action": "tokentx",
        "contractaddress": TOKENS["FLUID"],
        "address": TREASURY,
        "page": 1,
        "offset": 0,
        "sort": "desc",
    })
    return result.get("result", [])

def fetch_treasury_native_spends():
    """获取 Treasury 的 ETH 支出（用于 swap）"""
    result = etherscan_get({
        "module": "account",
        "action": "txlist",
        "address": TREASURY,
        "page": 1,
        "offset": 0,
        "sort": "desc",
    })
    return result.get("result", [])

def is_buyback(tx_fluid, native_txs):
    """
    判断是否为 Buyback:
    1. Treasury 收到 FLUID
    2. 同一区块内 Treasury 有 ETH 支出到 Router
    """
    # 跳过非字典对象
    if not isinstance(tx_fluid, dict):
        return False

    # 检查 FLUID 转入 Treasury
    to_addr = tx_fluid.get("to", "").lower()
    if to_addr != TREASURY:
        return False

    # 检查时间范围
    ts = int(tx_fluid.get("timeStamp", "0"))
    if ts < START_TS:
        return False

    # 查找同一区块内的 ETH 支出
    block = int(tx_fluid.get("blockNumber", "0"))
    fluid_tokens = int(tx_fluid.get("value", "0"))

    eth_spent = 0
    for tx in native_txs:
        if int(tx.get("blockNumber", "0")) == block:
            to_addr = tx.get("to", "").lower()
            from_addr = tx.get("from", "").lower()
            if from_addr == TREASURY and to_addr in ROUTERS.values():
                eth_spent += int(tx.get("value", "0"))

    # 判断：是否有 ETH 支出 + 收到 FLUID
    if eth_spent > 0 and fluid_tokens > 0:
        return {
            "is_buyback": True,
            "date": datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d"),
            "fluid_tokens": fluid_tokens / 1e18,
            "eth_spent": eth_spent / 1e18,
            "block": block
        }

    return None

def main():
    print("[*] Fluid Buyback Tracker")
    print(f"[*] Start date: {START_DATE}")
    print()

    # 获取 FLUID 转账
    print("[*] 获取 FLUID → Treasury 转账...")
    fluid_txs = fetch_fluid_transfers_to_treasury()
    print(f"[*] 获取到 {len(fluid_txs)} 笔 FLUID 转账")

    # 获取 Treasury ETH 支出
    print("[*] 获取 Treasury ETH 支出...")
    eth_txs = fetch_treasury_native_spends()
    print(f"[*] 获取到 {len(eth_txs)} 笔 ETH 交易")

    # 筛选 buyback
    print()
    print("[*] 识别 Buyback 交易...")
    buybacks = []

    for tx_fluid in fluid_txs:
        result = is_buyback(tx_fluid, eth_txs)
        if result and result["is_buyback"]:
            buybacks.append(result)

    print(f"[*] 找到 {len(buybacks)} 笔回购")

    if not buybacks:
        print("[!] 未找到 Buyback")
        return

    # 按日期汇总
    from collections import defaultdict
    by_date = defaultdict(list)
    for b in buybacks:
        by_date[b["date"]].append(b)

    print()
    print("按日期汇总:")
    for date in sorted(by_date.keys()):
        daily = by_date[date]
        total_fluid = sum(b["fluid_tokens"] for b in daily)
        total_eth = sum(b["eth_spent"] for b in daily)
        usd_value = total_eth * 2000  # 假设 ETH $2,000
        print(f"  {date}: {total_fluid:,.0f} FLUID, {total_eth:.4f} ETH, ${usd_value:,.0f}")

    # 总计
    total_fluid = sum(b["fluid_tokens"] for b in buybacks)
    total_eth = sum(b["eth_spent"] for b in buybacks)
    total_usd = total_eth * 2000

    print()
    print("总计:")
    print(f"  FLUID: {total_fluid:,.0f}")
    print(f"  ETH: {total_eth:.4f}")
    print(f"  USD: ${total_usd:,.0f}")

if __name__ == "__main__":
    main()
