#!/usr/bin/env python3
"""
Fluid 回购数据更新脚本
追踪 FLUID 代币流入储备钱包 = 回购量
"""

import requests
import json
from datetime import datetime, timezone
from pathlib import Path

# 配置
FLUID_TOKEN = "0x6f40d4A6237C257fff2dB00FA0510DeEECd303eb"
RESERVE_WALLETS = [
    "0x3e6FeBd2b195e1Ef3e8e3F4AABB6772aada32353",
    "0x9Afb8C1798B93a8E04a18553eE65bAFa41a012F1"
]
ETHERSCAN_API_KEY = "BUWR46PIP7JVZK98IP7YRQARRSABIP3V92"
COINGECKO_ID = "instadapp"  # FLUID 在 CoinGecko 的 ID

# 路径
SCRIPT_DIR = Path(__file__).parent
DATA_FILE = SCRIPT_DIR.parent / "data" / "fluid-buybacks.json"


def get_fluid_transfers():
    """获取所有转入储备钱包的 FLUID 转账 (Etherscan V2 API)"""
    all_transfers = []
    
    for wallet in RESERVE_WALLETS:
        # Etherscan V2 API
        url = "https://api.etherscan.io/v2/api"
        params = {
            "chainid": 1,  # Ethereum mainnet
            "module": "account",
            "action": "tokentx",
            "contractaddress": FLUID_TOKEN,
            "address": wallet,
            "startblock": 0,
            "endblock": 99999999,
            "sort": "asc",
            "apikey": ETHERSCAN_API_KEY
        }
        
        print(f"获取钱包 {wallet[:10]}... 的 FLUID 转入记录")
        resp = requests.get(url, params=params, timeout=60)
        data = resp.json()
        
        if data.get("status") == "1" and data.get("result"):
            # 只保留转入（to = wallet）
            inflows = [tx for tx in data["result"] if tx["to"].lower() == wallet.lower()]
            print(f"  找到 {len(inflows)} 笔转入")
            all_transfers.extend(inflows)
        else:
            print(f"  API 返回: {data.get('message', 'Unknown error')}")
    
    return all_transfers


def get_fluid_price_history():
    """获取 FLUID 历史价格"""
    url = f"https://api.coingecko.com/api/v3/coins/{COINGECKO_ID}/market_chart"
    params = {
        "vs_currency": "usd",
        "days": "180"  # 6个月
    }
    
    print("获取 FLUID 价格历史...")
    resp = requests.get(url, params=params, timeout=30)
    data = resp.json()
    
    # 转换为 {date: price} 字典
    prices = {}
    for ts, price in data.get("prices", []):
        date = datetime.fromtimestamp(ts/1000, tz=timezone.utc).strftime("%Y-%m-%d")
        prices[date] = price
    
    print(f"  获取到 {len(prices)} 天的价格数据")
    return prices


def aggregate_daily(transfers, prices):
    """按天聚合转账数据"""
    daily = {}
    
    for tx in transfers:
        ts = int(tx["timeStamp"])
        date = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
        amount = int(tx["value"]) / 1e18
        
        if date not in daily:
            daily[date] = {"fluid": 0, "txs": 0}
        
        daily[date]["fluid"] += amount
        daily[date]["txs"] += 1
    
    # 添加价格和 USD 价值
    result = []
    for date in sorted(daily.keys()):
        d = daily[date]
        price = prices.get(date, 0)
        usd = d["fluid"] * price if price else 0
        
        result.append({
            "date": date,
            "fluid": round(d["fluid"], 2),
            "usd": round(usd, 2),
            "price": round(price, 4) if price else None,
            "txs": d["txs"],
            "dataType": "onchain",
            "source": "Etherscan"
        })
    
    return result


def main():
    print("=" * 50)
    print("Fluid 回购数据更新")
    print("=" * 50)
    
    # 获取链上转账
    transfers = get_fluid_transfers()
    print(f"\n总共 {len(transfers)} 笔转入记录")
    
    if not transfers:
        print("未找到转账记录，退出")
        return
    
    # 获取价格
    prices = get_fluid_price_history()
    
    # 按天聚合
    daily_buybacks = aggregate_daily(transfers, prices)
    
    # 计算汇总
    total_fluid = sum(d["fluid"] for d in daily_buybacks)
    total_usd = sum(d["usd"] for d in daily_buybacks)
    
    print(f"\n汇总:")
    print(f"  总回购: {total_fluid:,.0f} FLUID")
    print(f"  总价值: ${total_usd:,.0f}")
    print(f"  天数: {len(daily_buybacks)}")
    
    # 构建输出
    output = {
        "protocol": "fluid",
        "ticker": "FLUID",
        "total_supply": 100000000,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "data_type": "daily",
        "data_source": "onchain",
        "data_source_note": "追踪 FLUID 流入储备钱包 (Etherscan API)",
        "reserve_wallets": RESERVE_WALLETS,
        "summary": {
            "total_buyback_fluid": round(total_fluid, 2),
            "total_buyback_usd": round(total_usd, 2),
            "total_days": len(daily_buybacks),
            "first_date": daily_buybacks[0]["date"] if daily_buybacks else None,
            "last_date": daily_buybacks[-1]["date"] if daily_buybacks else None,
            "avg_daily_fluid": round(total_fluid / len(daily_buybacks), 2) if daily_buybacks else 0
        },
        "daily_buybacks": daily_buybacks
    }
    
    # 保存
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(DATA_FILE, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ 已保存到 {DATA_FILE}")


if __name__ == "__main__":
    main()
