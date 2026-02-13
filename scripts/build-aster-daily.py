#!/usr/bin/env python3
"""
构建 Aster 每日回购数据

数据来源：
- Stage 1-4: Cryptopolitan 报道总量，按天均分（估算）
- Stage 5: 钱包余额总量，按天均分（估算）
- Stage 6: 钱包余额总量，按天均分（估算）

TODO: 获取 BscScan API key 后替换为真实链上数据
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
import requests

SCRIPT_DIR = Path(__file__).parent
DATA_FILE = SCRIPT_DIR / "../data/aster-buybacks.json"

# 回购钱包地址
WALLETS = {
    "stage5": "0x4786927333c0bA8aB27CA41361ADF33148C5301E",
    "stage6": "0x664827c71193018D7843f0D0F41A5D0D6dcEBE0F"
}

# ASTER 合约
ASTER_CONTRACT = "0x000Ae314E2A2172a039B26378814C252734f556A"
BSC_RPC = "https://bsc-dataseed.binance.org/"


def get_token_balance(address: str) -> float:
    """用 BSC RPC 获取 ASTER 余额"""
    padded = address.lower().replace("0x", "").zfill(64)
    data = f"0x70a08231{padded}"
    
    try:
        resp = requests.post(BSC_RPC, json={
            "jsonrpc": "2.0",
            "method": "eth_call",
            "params": [{"to": ASTER_CONTRACT, "data": data}, "latest"],
            "id": 1
        }, timeout=10)
        result = resp.json().get("result", "0x0")
        return int(result, 16) / 1e18
    except:
        return 0


def generate_daily_data():
    """生成每日回购数据"""
    
    print("=" * 50)
    print("Building Aster Daily Buyback Data")
    print("=" * 50)
    
    daily_data = []
    
    # ========== Stage 1-4 (估算) ==========
    # 来源: Cryptopolitan 报道
    # 总量: 143,380,000 ASTER / $214M
    # 时间: 2025-10-28 ~ 2025-12-22 (56天)
    
    print("\n📊 Stage 1-4 (估算，来源: Cryptopolitan)")
    
    stage1_start = datetime(2025, 10, 28)
    stage1_end = datetime(2025, 12, 22)
    stage1_days = (stage1_end - stage1_start).days + 1
    stage1_total_aster = 143_380_000
    stage1_total_usd = 214_000_000
    
    stage1_daily_aster = stage1_total_aster / stage1_days
    stage1_daily_usd = stage1_total_usd / stage1_days
    
    print(f"   Period: {stage1_start.date()} ~ {stage1_end.date()} ({stage1_days} days)")
    print(f"   Total: {stage1_total_aster:,.0f} ASTER / ${stage1_total_usd:,.0f}")
    print(f"   Daily avg: {stage1_daily_aster:,.0f} ASTER / ${stage1_daily_usd:,.0f}")
    
    for i in range(stage1_days):
        date = stage1_start + timedelta(days=i)
        daily_data.append({
            "date": date.strftime("%Y-%m-%d"),
            "aster": round(stage1_daily_aster),
            "usd": round(stage1_daily_usd),
            "stage": "1-4",
            "data_type": "estimated",
            "source": "Cryptopolitan"
        })
    
    # ========== Stage 5 (估算) ==========
    # 钱包: 0x4786927333c0bA8aB27CA41361ADF33148C5301E
    # 时间: 2025-12-23 ~ 2026-02-03 (43天)
    
    print("\n📊 Stage 5 (估算，来源: 钱包余额)")
    
    stage5_start = datetime(2025, 12, 23)
    stage5_end = datetime(2026, 2, 3)
    stage5_days = (stage5_end - stage5_start).days + 1
    
    print(f"   Fetching wallet balance...")
    stage5_total_aster = get_token_balance(WALLETS["stage5"])
    
    if stage5_total_aster == 0:
        stage5_total_aster = 8_058_000  # 回退值
        print(f"   Using fallback: {stage5_total_aster:,.0f} ASTER")
    else:
        print(f"   Wallet balance: {stage5_total_aster:,.0f} ASTER")
    
    stage5_daily_aster = stage5_total_aster / stage5_days
    
    print(f"   Period: {stage5_start.date()} ~ {stage5_end.date()} ({stage5_days} days)")
    print(f"   Daily avg: {stage5_daily_aster:,.0f} ASTER")
    
    for i in range(stage5_days):
        date = stage5_start + timedelta(days=i)
        daily_data.append({
            "date": date.strftime("%Y-%m-%d"),
            "aster": round(stage5_daily_aster),
            "usd": None,
            "stage": "5",
            "data_type": "estimated",
            "source": "wallet_balance"
        })
    
    # ========== Stage 6 (估算) ==========
    # 钱包: 0x664827c71193018D7843f0D0F41A5D0D6dcEBE0F
    # 时间: 2026-02-04 ~ 今天
    
    print("\n📊 Stage 6 (估算，来源: 钱包余额)")
    
    stage6_start = datetime(2026, 2, 4)
    stage6_end = datetime.now()
    stage6_days = (stage6_end - stage6_start).days + 1
    
    print(f"   Fetching wallet balance...")
    stage6_total_aster = get_token_balance(WALLETS["stage6"])
    
    if stage6_total_aster == 0:
        stage6_total_aster = 7_604_000  # 回退值
        print(f"   Using fallback: {stage6_total_aster:,.0f} ASTER")
    else:
        print(f"   Wallet balance: {stage6_total_aster:,.0f} ASTER")
    
    stage6_daily_aster = stage6_total_aster / stage6_days
    
    print(f"   Period: {stage6_start.date()} ~ {stage6_end.date()} ({stage6_days} days)")
    print(f"   Daily avg: {stage6_daily_aster:,.0f} ASTER")
    
    for i in range(stage6_days):
        date = stage6_start + timedelta(days=i)
        daily_data.append({
            "date": date.strftime("%Y-%m-%d"),
            "aster": round(stage6_daily_aster),
            "usd": None,
            "stage": "6",
            "data_type": "estimated",
            "source": "wallet_balance"
        })
    
    # ========== 保存数据 ==========
    
    total_aster = sum(d["aster"] for d in daily_data)
    total_usd = sum(d["usd"] or 0 for d in daily_data)
    
    output = {
        "protocol": "aster",
        "ticker": "ASTER",
        "total_supply": 1_000_000_000,
        "updated_at": datetime.now().isoformat(),
        
        "summary": {
            "total_buyback_aster": total_aster,
            "total_buyback_usd": total_usd if total_usd > 0 else None,
            "total_days": len(daily_data),
            "start_date": daily_data[0]["date"],
            "end_date": daily_data[-1]["date"],
            "note": "Stage 1-4 来自报道，Stage 5-6 来自钱包余额，均为估算"
        },
        
        "stages": [
            {
                "stage": "1-4",
                "period": f"{stage1_start.date()} ~ {stage1_end.date()}",
                "days": stage1_days,
                "total_aster": stage1_total_aster,
                "total_usd": stage1_total_usd,
                "data_type": "reported",
                "source": "Cryptopolitan"
            },
            {
                "stage": "5",
                "period": f"{stage5_start.date()} ~ {stage5_end.date()}",
                "days": stage5_days,
                "total_aster": round(stage5_total_aster),
                "total_usd": None,
                "data_type": "onchain",
                "source": "wallet_balance",
                "wallet": WALLETS["stage5"]
            },
            {
                "stage": "6",
                "period": f"{stage6_start.date()} ~ {stage6_end.date()}",
                "days": stage6_days,
                "total_aster": round(stage6_total_aster),
                "total_usd": None,
                "data_type": "onchain",
                "source": "wallet_balance",
                "wallet": WALLETS["stage6"]
            }
        ],
        
        "daily_buybacks": daily_data
    }
    
    with open(DATA_FILE, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Saved to {DATA_FILE}")
    print(f"\n📊 Summary:")
    print(f"   Total ASTER: {total_aster:,.0f}")
    print(f"   Total Days: {len(daily_data)}")
    print(f"   Progress: {total_aster / 1e9 * 100:.2f}%")


if __name__ == "__main__":
    generate_daily_data()
