#!/usr/bin/env python3
"""
Aster Buyback Daily Update Script
每日更新 Aster 回购数据

数据源：BscScan API 或 BSC RPC
- 读取 Stage 6 回购钱包 ASTER 余额
- 计算今日新增回购
- 追加到 aster-buybacks.json

用法：
  python3 scripts/update-aster.py                    # 使用 BSC RPC
  python3 scripts/update-aster.py --apikey YOUR_KEY  # 使用 BscScan API
  BSCSCAN_API_KEY=xxx python3 scripts/update-aster.py
"""

import requests
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# BscScan API
BSCSCAN_API = "https://api.bscscan.com/api"
BSCSCAN_API_KEY = os.environ.get("BSCSCAN_API_KEY", "")

# BSC 公共 RPC
BSC_RPC = "https://bsc-dataseed.binance.org/"

# ASTER token contract on BSC
ASTER_CONTRACT = "0x000Ae314E2A2172a039B26378814C252734f556A"

# Stage 6 回购钱包 (当前活跃)
STAGE6_AUTO = "0x664827c71193018D7843f0D0F41A5D0D6dcEBE0F"

# 数据文件路径
SCRIPT_DIR = Path(__file__).parent
DATA_FILE = SCRIPT_DIR / "../data/aster-buybacks.json"


def get_token_balance_rpc(address: str, contract: str) -> float:
    """使用 BSC RPC 获取代币余额 (ERC20 balanceOf)"""
    # balanceOf(address) function signature: 0x70a08231
    # Pad address to 32 bytes
    padded_address = address.lower().replace("0x", "").zfill(64)
    data = f"0x70a08231{padded_address}"
    
    payload = {
        "jsonrpc": "2.0",
        "method": "eth_call",
        "params": [{"to": contract, "data": data}, "latest"],
        "id": 1
    }
    
    try:
        resp = requests.post(BSC_RPC, json=payload, timeout=15)
        result = resp.json()
        if "result" in result and result["result"] != "0x":
            balance_hex = result["result"]
            return int(balance_hex, 16) / 1e18
        else:
            print(f"⚠️ RPC error: {result.get('error', 'no result')}")
    except Exception as e:
        print(f"❌ RPC request failed: {e}")
    return 0


def get_token_balance_bscscan(address: str, contract: str, apikey: str = "") -> float:
    """使用 BscScan API 获取代币余额"""
    params = {
        "module": "account",
        "action": "tokenbalance",
        "address": address,
        "contractaddress": contract,
        "tag": "latest"
    }
    if apikey:
        params["apikey"] = apikey
        
    try:
        resp = requests.get(BSCSCAN_API, params=params, timeout=15)
        data = resp.json()
        if data.get("status") == "1":
            return int(data.get("result", 0)) / 1e18
        else:
            print(f"⚠️ BscScan API error: {data.get('message', 'unknown')}")
    except Exception as e:
        print(f"❌ BscScan request failed: {e}")
    return 0


def get_token_balance(address: str, contract: str) -> float:
    """获取地址的代币余额（优先 RPC，失败则用 BscScan）"""
    # 先尝试 RPC (免费无限制)
    balance = get_token_balance_rpc(address, contract)
    if balance > 0:
        return balance
    
    # 再尝试 BscScan API
    if BSCSCAN_API_KEY:
        print("   Trying BscScan API with key...")
        return get_token_balance_bscscan(address, contract, BSCSCAN_API_KEY)
    
    return 0


def get_aster_price() -> float:
    """获取 ASTER 当前价格 (USD)"""
    try:
        # CoinGecko API (免费)
        resp = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": "aster-defi", "vs_currencies": "usd"},
            timeout=10
        )
        data = resp.json()
        return data.get("aster-defi", {}).get("usd", 0.55)  # 默认 $0.55
    except Exception as e:
        print(f"⚠️ Price fetch failed, using default: {e}")
        return 0.55


def load_data() -> dict:
    """加载现有数据"""
    if DATA_FILE.exists():
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {
        "protocol": "aster",
        "ticker": "ASTER",
        "total_supply": 1_000_000_000,
        "daily_buybacks": [],
        "stages": []
    }


def save_data(data: dict):
    """保存数据"""
    data["updated_at"] = datetime.now().isoformat()
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"✅ Saved to {DATA_FILE}")


def get_last_balance(data: dict) -> tuple[str, float]:
    """获取最后一条记录的日期和累计余额"""
    daily = data.get("daily_buybacks", [])
    if not daily:
        return None, 0
    
    # 计算到最后日期的累计 ASTER
    last_date = daily[-1]["date"]
    cumulative = sum(d.get("aster", 0) for d in daily if d.get("stage") == "6")
    return last_date, cumulative


def sync_stage6_data(data: dict, current_balance: float, price: float) -> dict:
    """
    同步 Stage 6 数据：用实际余额校正估算数据
    Stage 6 开始日期: 2026-02-04
    """
    from datetime import datetime
    
    stage6_start = datetime(2026, 2, 4)
    today = datetime.now()
    today_str = today.strftime("%Y-%m-%d")
    
    # 计算 Stage 6 天数
    days_since_start = (today - stage6_start).days + 1
    
    # 每日平均回购
    daily_avg = current_balance / days_since_start
    daily_avg_usd = daily_avg * price
    
    print(f"\n🔄 Syncing Stage 6 data...")
    print(f"   Days: {days_since_start}")
    print(f"   Daily avg: {daily_avg:,.0f} ASTER (${daily_avg_usd:,.2f})")
    
    # 移除旧的 Stage 6 数据
    data["daily_buybacks"] = [d for d in data.get("daily_buybacks", []) if d.get("stage") != "6"]
    
    # 重新生成 Stage 6 每日数据
    for i in range(days_since_start):
        date = (stage6_start + timedelta(days=i)).strftime("%Y-%m-%d")
        data["daily_buybacks"].append({
            "date": date,
            "usd": round(daily_avg_usd, 2),
            "aster": round(daily_avg, 0),
            "stage": "6"
        })
    
    # 排序
    data["daily_buybacks"].sort(key=lambda x: x["date"])
    
    return data


def main():
    print("=" * 50)
    print("Aster Buyback Daily Update")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    # 检查命令行参数
    sync_mode = "--sync" in sys.argv
    
    # 加载现有数据
    data = load_data()
    today = datetime.now().strftime("%Y-%m-%d")
    
    # 获取当前钱包余额
    print(f"\n📊 Fetching Stage 6 wallet balance...")
    current_balance = get_token_balance(STAGE6_AUTO, ASTER_CONTRACT)
    print(f"   Current balance: {current_balance:,.0f} ASTER")
    
    if current_balance == 0:
        print("❌ Failed to fetch balance, aborting.")
        return
    
    # 获取价格
    print(f"\n💰 Fetching ASTER price...")
    price = get_aster_price()
    print(f"   Price: ${price:.4f}")
    
    # 检查 Stage 6 累计数据是否需要校正
    stage6_cumulative = sum(
        d.get("aster", 0) 
        for d in data.get("daily_buybacks", []) 
        if d.get("stage") == "6"
    )
    
    diff = current_balance - stage6_cumulative
    diff_pct = abs(diff / current_balance * 100) if current_balance else 0
    
    print(f"\n📋 Stage 6 data check:")
    print(f"   Recorded: {stage6_cumulative:,.0f} ASTER")
    print(f"   Actual: {current_balance:,.0f} ASTER")
    print(f"   Diff: {diff:,.0f} ({diff_pct:.1f}%)")
    
    # 如果偏差超过 5% 或首次运行，执行同步
    if diff_pct > 5 or sync_mode or stage6_cumulative == 0:
        print(f"\n⚠️ Data discrepancy detected, syncing...")
        data = sync_stage6_data(data, current_balance, price)
    elif diff > 10000:
        # 正常增量：有新回购
        print(f"\n✅ New buyback detected: {diff:,.0f} ASTER")
        
        # 检查今日是否已有数据
        today_exists = any(d["date"] == today and d.get("stage") == "6" for d in data["daily_buybacks"])
        
        if today_exists:
            # 更新今日数据
            for d in data["daily_buybacks"]:
                if d["date"] == today and d.get("stage") == "6":
                    d["aster"] = round(d["aster"] + diff, 0)
                    d["usd"] = round(d["aster"] * price, 2)
        else:
            # 添加今日数据
            data["daily_buybacks"].append({
                "date": today,
                "usd": round(diff * price, 2),
                "aster": round(diff, 0),
                "stage": "6"
            })
            data["daily_buybacks"].sort(key=lambda x: x["date"])
    else:
        print(f"\n✅ Data is up to date, no changes needed.")
        return
    
    # 更新汇总
    total_aster = sum(d.get("aster", 0) for d in data["daily_buybacks"])
    total_usd = sum(d.get("usd", 0) for d in data["daily_buybacks"])
    
    data["summary"] = {
        "total_buyback_usd": round(total_usd, 2),
        "total_buyback_aster": round(total_aster, 0),
        "total_days": len(data["daily_buybacks"]),
        "start_date": data["daily_buybacks"][0]["date"] if data["daily_buybacks"] else today,
        "end_date": today,
        "data_sources": ["BSC RPC", "CoinGecko"]
    }
    
    # 保存
    save_data(data)
    
    # 输出摘要
    print(f"\n📊 Total buybacks:")
    print(f"   ASTER: {total_aster:,.0f}")
    print(f"   USD: ${total_usd:,.2f}")
    print(f"   Days: {len(data['daily_buybacks'])}")
    
    progress = (total_aster / 1_000_000_000) * 100
    print(f"\n🎯 Progress: {progress:.2f}% of total supply")


if __name__ == "__main__":
    main()
