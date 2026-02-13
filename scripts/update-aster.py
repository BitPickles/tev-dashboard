#!/usr/bin/env python3
"""
Aster Buyback 增量更新脚本

核心逻辑：
1. 读取上次同步状态 (last-sync.json)
2. 只查询新数据 (Moralis API)
3. 合并到历史数据
4. 保存并更新同步状态

用法：
  python3 scripts/update-aster.py          # 增量更新
  python3 scripts/update-aster.py --sync   # 强制全量同步
"""

import subprocess
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# API Keys
MORALIS_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJub25jZSI6IjdmYWFmNTdkLTNiOWQtNGNhNS1hNGY3LTExZGI4Y2YyYzBlNiIsIm9yZ0lkIjoiNTAwNDkyIiwidXNlcklkIjoiNTE0OTg0IiwidHlwZUlkIjoiMjA4MzcyMWEtZmJjMC00NzQzLWEzNGItNGEyYmFlY2ExNTNlIiwidHlwZSI6IlBST0pFQ1QiLCJpYXQiOjE3NzA5OTIwNTMsImV4cCI6NDkyNjc1MjA1M30.Ef1yoypuIgSdnMMFnB9aFaDX6ILinqWuchJ8npxEZrA"

# Token and Wallets
ASTER_TOKEN = "0x000ae314e2a2172a039b26378814c252734f556a"
STAGE5_WALLET = "0x4786927333c0ba8ab27ca41361adf33148c5301e"
STAGE6_WALLET = "0x664827c71193018d7843f0d0f41a5d0d6dcebe0f"

# Paths
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR / "../data"
BUYBACKS_FILE = DATA_DIR / "aster-buybacks.json"
ONCHAIN_FILE = DATA_DIR / "aster-onchain.json"
SYNC_STATE_FILE = DATA_DIR / "aster-last-sync.json"

# Stage 1-4 constants (historical, not changing)
STAGE14_TOTAL_ASTER = 143000000
STAGE14_TOTAL_USD = 214000000
STAGE14_DAYS = 56
STAGE14_START = "2025-10-28"
STAGE14_END = "2025-12-22"


def run_curl(url: str, headers: dict = None) -> dict:
    """使用 curl 发送请求（避免 Python SSL 问题）"""
    cmd = ["curl", "-s", url]
    if headers:
        for k, v in headers.items():
            cmd.extend(["-H", f"{k}: {v}"])
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        return json.loads(result.stdout)
    return {}


def load_sync_state() -> dict:
    """加载同步状态"""
    if SYNC_STATE_FILE.exists():
        with open(SYNC_STATE_FILE) as f:
            return json.load(f)
    return {"last_date": None, "last_block": None}


def save_sync_state(state: dict):
    """保存同步状态"""
    state["updated_at"] = datetime.now().isoformat()
    with open(SYNC_STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def load_onchain_data() -> list:
    """加载链上数据"""
    if ONCHAIN_FILE.exists():
        with open(ONCHAIN_FILE) as f:
            return json.load(f)
    return []


def save_onchain_data(data: list):
    """保存链上数据"""
    with open(ONCHAIN_FILE, "w") as f:
        json.dump(data, f, indent=2)


def fetch_transfers_since(wallet: str, stage: str, from_date: str = None, from_block: int = None) -> list:
    """获取指定日期/区块后的新转入"""
    print(f"   Fetching {stage} transfers since {from_date or from_block}...")
    
    transfers = []
    cursor = None
    page = 0
    
    while True:
        page += 1
        url = f"https://deep-index.moralis.io/api/v2.2/{wallet}/erc20/transfers?chain=bsc&contract_addresses%5B0%5D={ASTER_TOKEN}&limit=100"
        if cursor:
            url += f"&cursor={cursor}"
        if from_block:
            url += f"&from_block={from_block}"
        
        headers = {"X-API-Key": MORALIS_API_KEY}
        data = run_curl(url, headers)
        
        if "result" not in data:
            print(f"   ⚠️ API error: {data}")
            break
        
        # 筛选转入（to_address == wallet）
        for tx in data["result"]:
            if tx["to_address"].lower() == wallet.lower():
                tx_date = tx["block_timestamp"][:10]
                
                # 如果指定了 from_date，跳过更早的数据
                if from_date and tx_date < from_date:
                    continue
                
                amount = float(tx.get("value_decimal", 0) or 0)
                if amount > 0:
                    transfers.append({
                        "date": tx_date,
                        "amount": amount,
                        "block": int(tx["block_number"]),
                        "tx_hash": tx["transaction_hash"],
                        "stage": stage
                    })
        
        print(f"   Page {page}: {len(data['result'])} records")
        
        cursor = data.get("cursor")
        if not cursor:
            break
        if page >= 50:
            print("   Reached page limit")
            break
    
    return transfers


def aggregate_by_date(transfers: list, existing: list = None) -> list:
    """按日期聚合，合并到现有数据"""
    from collections import defaultdict
    
    # 现有数据转为字典
    existing_dict = {}
    if existing:
        for r in existing:
            existing_dict[r["date"]] = r
    
    # 聚合新数据
    daily = defaultdict(lambda: {"aster": 0.0, "txs": 0, "stage": None, "max_block": 0})
    for tx in transfers:
        date = tx["date"]
        daily[date]["aster"] += tx["amount"]
        daily[date]["txs"] += 1
        daily[date]["stage"] = tx["stage"]
        daily[date]["max_block"] = max(daily[date]["max_block"], tx["block"])
    
    # 合并到现有
    for date, d in daily.items():
        if date in existing_dict:
            # 更新现有（可能有新交易）
            existing_dict[date]["aster"] = round(d["aster"], 2)
            existing_dict[date]["txs"] = d["txs"]
        else:
            # 添加新日期
            existing_dict[date] = {
                "date": date,
                "aster": round(d["aster"], 2),
                "txs": d["txs"],
                "stage": d["stage"],
                "data_type": "onchain",
                "source": "moralis"
            }
    
    # 转回列表并排序
    result = list(existing_dict.values())
    result.sort(key=lambda x: x["date"])
    return result


def generate_stage14_data() -> list:
    """生成 Stage 1-4 估算数据"""
    from datetime import date, timedelta
    
    daily_aster = STAGE14_TOTAL_ASTER / STAGE14_DAYS
    daily_usd = STAGE14_TOTAL_USD / STAGE14_DAYS
    
    start = date.fromisoformat(STAGE14_START)
    result = []
    
    for i in range(STAGE14_DAYS):
        d = start + timedelta(days=i)
        result.append({
            "date": d.isoformat(),
            "aster": round(daily_aster),
            "usd": round(daily_usd),
            "stage": "1-4",
            "data_type": "estimated",
            "source": "Cryptopolitan"
        })
    
    return result


def merge_all_data(stage14: list, onchain: list) -> dict:
    """合并所有数据到主文件"""
    all_data = stage14 + onchain
    
    # 计算汇总
    stage14_sum = sum(r["aster"] for r in all_data if r.get("stage") == "1-4")
    stage5_sum = sum(r["aster"] for r in all_data if r.get("stage") == "stage5")
    stage6_sum = sum(r["aster"] for r in all_data if r.get("stage") == "stage6")
    
    return {
        "protocol": "aster",
        "ticker": "ASTER",
        "total_supply": 1000000000,
        "updated_at": datetime.now().isoformat(),
        "summary": {
            "total_buyback_aster": round(stage14_sum + stage5_sum + stage6_sum),
            "stage14_aster": round(stage14_sum),
            "stage14_usd": STAGE14_TOTAL_USD,
            "stage5_aster": round(stage5_sum),
            "stage6_aster": round(stage6_sum),
            "total_days": len(all_data),
            "note": "Stage 1-4 为估算 (Cryptopolitan), Stage 5-6 为链上真实数据 (Moralis API)"
        },
        "daily_buybacks": all_data
    }


def main():
    print("=" * 50)
    print("Aster Buyback 增量更新")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    full_sync = "--sync" in sys.argv
    
    # 加载同步状态
    state = load_sync_state()
    print(f"\n📋 上次同步: {state.get('last_date', '无')}")
    
    # 加载现有链上数据
    onchain = load_onchain_data()
    print(f"   现有数据: {len(onchain)} 天")
    
    if full_sync or not state.get("last_date"):
        print("\n🔄 执行全量同步...")
        
        # Stage 5
        print("\n📊 Stage 5:")
        s5_transfers = fetch_transfers_since(STAGE5_WALLET, "stage5")
        print(f"   获取 {len(s5_transfers)} 笔交易")
        
        # Stage 6
        print("\n📊 Stage 6:")
        s6_transfers = fetch_transfers_since(STAGE6_WALLET, "stage6")
        print(f"   获取 {len(s6_transfers)} 笔交易")
        
        all_transfers = s5_transfers + s6_transfers
        onchain = aggregate_by_date(all_transfers)
        
    else:
        print("\n📊 增量更新...")
        
        # 只获取最新日期之后的数据
        from_date = state["last_date"]
        
        # Stage 5 (如果还在活跃)
        s5_transfers = fetch_transfers_since(STAGE5_WALLET, "stage5", from_date=from_date)
        
        # Stage 6
        s6_transfers = fetch_transfers_since(STAGE6_WALLET, "stage6", from_date=from_date)
        
        new_transfers = s5_transfers + s6_transfers
        print(f"\n   新增 {len(new_transfers)} 笔交易")
        
        if new_transfers:
            onchain = aggregate_by_date(new_transfers, onchain)
    
    # 保存链上数据
    save_onchain_data(onchain)
    
    # 更新同步状态
    if onchain:
        latest_date = max(r["date"] for r in onchain)
        save_sync_state({"last_date": latest_date})
        print(f"\n✅ 同步状态已更新: {latest_date}")
    
    # 生成 Stage 1-4 数据
    stage14 = generate_stage14_data()
    
    # 合并并保存主文件
    result = merge_all_data(stage14, onchain)
    with open(BUYBACKS_FILE, "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    # 输出汇总
    print(f"\n📊 汇总:")
    print(f"   Stage 1-4: {result['summary']['stage14_aster']:,} ASTER (估算)")
    print(f"   Stage 5: {result['summary']['stage5_aster']:,} ASTER (链上)")
    print(f"   Stage 6: {result['summary']['stage6_aster']:,} ASTER (链上)")
    print(f"   总计: {result['summary']['total_buyback_aster']:,} ASTER")
    print(f"   占比: {result['summary']['total_buyback_aster'] / 1e9 * 100:.2f}%")
    print(f"\n✅ 已保存到 {BUYBACKS_FILE}")


if __name__ == "__main__":
    main()
