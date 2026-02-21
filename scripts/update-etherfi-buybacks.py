#!/usr/bin/env python3
"""
ether.fi 回购数据更新脚本
基于官方 Dune 逻辑，从链上追踪 ETHFI 买入

数据来源：Etherscan API V2
"""

import requests
import json
from datetime import datetime, timezone
from pathlib import Path

# 配置
ETHFI_TOKEN = "0xFe0c30065B384F05761f15d0CC899D4F9F9Cc0eB"  # ETHFI token

# 回购相关地址（从 Dune 逻辑提取）
# 追踪 ETHFI 流入的地址（回购后的接收地址）
BUYBACK_RECEIVERS = [
    "0x0c83EAe1FE72c390A02E426572854931EefF93BA",  # 主收款地址
    "0x2f5301a3D59388c509C65f8698f521377D41Fd0F",  # 收款地址2
]

ETHERSCAN_API_KEY = "BUWR46PIP7JVZK98IP7YRQARRSABIP3V92"
COINGECKO_ID = "ether-fi"

# 路径
SCRIPT_DIR = Path(__file__).parent
DATA_FILE = SCRIPT_DIR.parent / "data" / "etherfi-buybacks.json"


def get_last_block():
    """获取已有数据的最后区块号"""
    if DATA_FILE.exists():
        try:
            with open(DATA_FILE) as f:
                data = json.load(f)
                return data.get("last_block", 0)
        except:
            pass
    return 0


def get_ethfi_transfers(start_block=0):
    """获取转入回购地址的 ETHFI 转账"""
    all_transfers = []
    
    for wallet in BUYBACK_RECEIVERS:
        url = "https://api.etherscan.io/v2/api"
        params = {
            "chainid": 1,
            "module": "account",
            "action": "tokentx",
            "contractaddress": ETHFI_TOKEN,
            "address": wallet,
            "startblock": start_block,
            "endblock": 99999999,
            "sort": "asc",
            "apikey": ETHERSCAN_API_KEY
        }
        
        print(f"获取钱包 {wallet[:10]}... 的 ETHFI 转入记录 (从区块 {start_block})")
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


def get_ethfi_price_history():
    """获取 ETHFI 历史价格"""
    url = f"https://api.coingecko.com/api/v3/coins/{COINGECKO_ID}/market_chart"
    params = {
        "vs_currency": "usd",
        "days": "365"
    }
    
    print("获取 ETHFI 价格历史...")
    resp = requests.get(url, params=params, timeout=30)
    data = resp.json()
    
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
            daily[date] = {"ethfi": 0, "txs": 0}
        
        daily[date]["ethfi"] += amount
        daily[date]["txs"] += 1
    
    result = []
    for date in sorted(daily.keys()):
        d = daily[date]
        price = prices.get(date, 0)
        usd = d["ethfi"] * price if price else 0
        
        result.append({
            "date": date,
            "ethfi": round(d["ethfi"], 2),
            "usd": round(usd, 2),
            "price": round(price, 4) if price else None,
            "txs": d["txs"],
            "dataType": "onchain",
            "source": "Etherscan"
        })
    
    return result


def load_existing_data():
    """加载已有数据"""
    if DATA_FILE.exists():
        try:
            with open(DATA_FILE) as f:
                return json.load(f)
        except:
            pass
    return None


def merge_daily_data(existing, new_data):
    """合并已有数据和新数据"""
    if not existing:
        return new_data
    
    # 用 date 作为 key 合并
    merged = {d["date"]: d for d in existing}
    for d in new_data:
        if d["date"] in merged:
            # 更新已有日期的数据
            merged[d["date"]]["ethfi"] += d["ethfi"]
            merged[d["date"]]["usd"] += d["usd"]
            merged[d["date"]]["txs"] += d["txs"]
        else:
            merged[d["date"]] = d
    
    return [merged[k] for k in sorted(merged.keys())]


def main():
    import sys
    full_sync = "--full" in sys.argv
    
    print("=" * 50)
    print("ether.fi 回购数据更新")
    print("=" * 50)
    
    # 检查是否增量更新
    existing_data = load_existing_data()
    if existing_data and not full_sync:
        last_block = existing_data.get("last_block", 0)
        print(f"增量更新模式，从区块 {last_block} 开始")
        transfers = get_ethfi_transfers(start_block=last_block + 1)
    else:
        print("完整同步模式")
        transfers = get_ethfi_transfers(start_block=0)
        existing_data = None
    
    print(f"\n获取到 {len(transfers)} 笔新转入记录")
    
    if not transfers and not existing_data:
        print("未找到转账记录，退出")
        return
    
    # 获取价格
    prices = get_ethfi_price_history()
    
    # 按天聚合新数据
    new_daily = aggregate_daily(transfers, prices) if transfers else []
    
    # 合并数据
    if existing_data and not full_sync:
        daily_buybacks = merge_daily_data(existing_data.get("daily_buybacks", []), new_daily)
    else:
        daily_buybacks = new_daily
    
    # 获取最新区块号
    last_block = max(int(tx["blockNumber"]) for tx in transfers) if transfers else (existing_data.get("last_block", 0) if existing_data else 0)
    
    # 计算汇总
    total_ethfi = sum(d["ethfi"] for d in daily_buybacks)
    total_usd = sum(d["usd"] for d in daily_buybacks)
    
    print(f"\n汇总:")
    print(f"  总回购: {total_ethfi:,.0f} ETHFI")
    print(f"  总价值: ${total_usd:,.0f}")
    print(f"  天数: {len(daily_buybacks)}")
    
    # 构建输出
    output = {
        "protocol": "etherfi",
        "ticker": "ETHFI",
        "total_supply": 1000000000,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "last_block": last_block,
        "data_type": "daily",
        "data_source": "onchain",
        "data_source_note": "追踪 ETHFI 流入回购地址 (Etherscan API)",
        "buyback_receivers": BUYBACK_RECEIVERS,
        "summary": {
            "total_buyback_ethfi": round(total_ethfi, 2),
            "total_buyback_usd": round(total_usd, 2),
            "total_days": len(daily_buybacks),
            "first_date": daily_buybacks[0]["date"] if daily_buybacks else None,
            "last_date": daily_buybacks[-1]["date"] if daily_buybacks else None,
            "avg_daily_ethfi": round(total_ethfi / len(daily_buybacks), 2) if daily_buybacks else 0
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
