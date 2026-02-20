#!/usr/bin/env python3
"""
Fluid 回购追踪 v2
追踪 Treasury 的资产支出 → Router → 买入 FLUID
"""

import json
import subprocess
from datetime import datetime, timezone, timedelta
from collections import defaultdict

ETHERSCAN_API_KEY = "BUWR46PIP7JVZK98IP7YRQARRSABIP3V92"
BASE = "https://api.etherscan.io/api"

TREASURY = "0x28849D2b63fA8D361e5fc15cB8aBB13019884d09".lower()

TOKENS = {
    "FLUID": "0x6f40d4a6237c257fff2db00fa0510deeedc303eb".lower(),
    "WETH": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2".lower(),
    "USDC": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48".lower(),
    "USDT": "0xdAC17F958D2ee523a2206206994597C13D831ec7".lower(),
    "DAI": "0x6B175474E89094C44Da98b954EedeAC495271d0F".lower(),
}

ROUTERS = {
    "0xE592427A0AEce92De3Edee1F18E0157C05861564".lower(),  # Uniswap V3
    "0xEf1c6E67703c7BD7107eed8303Fbe6EC2554BF6B".lower(),  # Uniswap Universal
    "0x1111111254EEB25477B68fb85Ed929f73A960582".lower(),  # 1inch V5
}

START_DATE = "2025-10-01"
START_TS = int(datetime.fromisoformat(START_DATE).replace(tzinfo=timezone.utc).timestamp())

def etherscan_get(params):
    """Etherscan API GET request"""
    params_str = "&".join([f"{k}={v}" for k, v in params.items()])
    result = subprocess.run(
        ["curl", "-s", "--max-time", "30", f"{BASE}?{params_str}"],
        capture_output=True, text=True
    )
    return json.loads(result.stdout)

def fetch_treasury_native_spends():
    """获取 Treasury 的原生代币支出（ETH/USDC/USDT）"""
    result = etherscan_get({
        "module": "account",
        "action": "txlist",
        "address": TREASURY,
        "page": 1,
        "offset": 0,
        "sort": "desc",
    })
    txs = result.get("result", [])

    # 筛选：支出给 Router
    spends = []
    for tx in txs:
        if not isinstance(tx, dict):
            continue

        ts = int(tx.get("timeStamp", "0"))
        if ts < START_TS:
            continue

        from_addr = tx.get("from", "").lower()
        to_addr = tx.get("to", "").lower()

        if from_addr != TREASURY:
            continue

        if to_addr in ROUTERS:
            value = int(tx.get("value", "0"))
            if value > 0:
                spends.append({
                    "date": datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d"),
                    "to": to_addr,
                    "value_wei": value,
                    "value_eth": value / 1e18,
                    "block": int(tx.get("blockNumber", "0")),
                    "hash": tx.get("hash", "")
                })

    return spends

def fetch_token_transfers_to_treasury():
    """获取所有 Token 转入 Treasury"""
    all_transfers = []

    for token_name, token_addr in TOKENS.items():
        if token_name == "FLUID":
            continue  # 我们只看支出代币，不看 FLUID

        result = etherscan_get({
            "module": "account",
            "action": "tokentx",
            "contractaddress": token_addr,
            "address": TREASURY,
            "page": 1,
            "offset": 0,
            "sort": "desc",
        })

        txs = result.get("result", [])
        for tx in txs:
            if not isinstance(tx, dict):
                continue

            ts = int(tx.get("timeStamp", "0"))
            if ts < START_TS:
                continue

            to_addr = tx.get("to", "").lower()
            if to_addr != TREASURY:
                continue

            value = int(tx.get("value", "0"))
            if value > 0:
                all_transfers.append({
                    "date": datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d"),
                    "token": token_name,
                    "value": value,
                    "block": int(tx.get("blockNumber", "0"))
                })

    return all_transfers

def main():
    print("[*] Fluid Buyback Tracker v2")
    print(f"[*] Start date: {START_DATE}")
    print()

    # 获取 Treasury 原生代币支出
    print("[*] 获取 Treasury 原生代币支出（ETH/USDC/USDT）...")
    spends = fetch_treasury_native_spends()
    print(f"[*] 获取到 {len(spends)} 笔 Router 交互")

    # 按日期汇总支出
    by_date = defaultdict(lambda: {"eth": 0, "usdc": 0, "usdt": 0, "dai": 0})
    for s in spends:
        date = s["date"]
        to_addr = s["to"]

        # 识别代币类型（简化）
        if to_addr == "0xe592427a0aece92de3edee1f18e0157c05861564":
            by_date[date]["eth"] += s["value_eth"]
        else:
            # 其他 Router 暂时算作 ETH（需要 Token Transfer API 进一步验证）
            by_date[date]["eth"] += s["value_eth"]

    print()
    print("按日期汇总 Treasury 支出（ETH）:")
    for date in sorted(by_date.keys())[:20]:
        info = by_date[date]
        eth = info["eth"]
        usd = eth * 2000
        print(f"  {date}: {eth:.4f} ETH (${usd:,.0f})")

    # 总计
    total_eth = sum(s["value_eth"] for s in spends)
    total_usd = total_eth * 2000

    print()
    print("总计:")
    print(f"  ETH: {total_eth:.4f}")
    print(f"  USD: ${total_usd:,.0f}")
    print(f"  笔数: {len(spends)}")

    # 输出 JSON
    output = {
        "protocol": "fluid",
        "ticker": "FLUID",
        "total_supply": 100000000,
        "updated_at": datetime.utcnow().isoformat() + "Z",
        "summary": {
            "total_buyback_usd": round(total_usd, 2),
            "total_days": len(by_date),
            "first_date": min(by_date.keys()) if by_date else None,
            "last_date": max(by_date.keys()) if by_date else None,
            "note": "Etherscan Treasury 原生代币支出（ETH → Router）"
        },
        "daily_buybacks": [
            {
                "date": date,
                "usd": round(by_date[date]["eth"] * 2000, 2),
                "stage": "onchain-treasury",
                "dataType": "onchain",
                "source": "Etherscan"
            }
            for date in sorted(by_date.keys())
        ]
    }

    with open("data/fluid-buybacks.json", "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n[*] 已保存: data/fluid-buybacks.json")

if __name__ == "__main__":
    main()
