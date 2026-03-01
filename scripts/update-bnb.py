#!/usr/bin/env python3
"""
BNB TEV 自动更新脚本

更新内容：
1. 查询链上 0xdead 余额（BSC RPC）
2. 获取 BNB 价格/市值/流通量（CoinGecko）
3. 计算 Burn APY + asBNB APY = 总 TEV Yield
4. 更新 config.json
5. 检测新季度销毁（0xdead 余额大幅变化时提醒）

注意：tev-records.json 为季度数据，需手动维护

用法：
  python3 scripts/update-bnb.py
"""

import subprocess
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

DEAD_ADDR = "0x000000000000000000000000000000000000dEaD"
BSC_RPC = "https://bsc-dataseed.binance.org/"
INITIAL_SUPPLY = 200_000_000

SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "data" / "protocols" / "bnb"
TEV_FILE = DATA_DIR / "tev-records.json"
CONFIG_FILE = DATA_DIR / "config.json"


def curl_json(url, data=None):
    cmd = ["curl", "-s", "--max-time", "30"]
    if data:
        cmd.extend(["-H", "Content-Type: application/json", "-d", data])
    cmd.append(url)
    r = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return json.loads(r.stdout) if r.returncode == 0 else {}
    except:
        return {}


def get_dead_balance():
    print("查询 BSC 0xdead BNB 余额...")
    d = curl_json(BSC_RPC, json.dumps({
        "jsonrpc": "2.0", "method": "eth_getBalance",
        "params": [DEAD_ADDR, "latest"], "id": 1
    }))
    if "result" in d:
        bal = int(d["result"], 16) / 1e18
        print(f"  余额: {bal:,.2f} BNB")
        return bal
    print("  ❌ 失败")
    return 0


def get_bnb_data():
    print("获取 BNB 价格/市值/流通量...")
    d = curl_json("https://api.coingecko.com/api/v3/coins/binancecoin")
    md = d.get("market_data", {})
    price = md.get("current_price", {}).get("usd", 0)
    mcap = md.get("market_cap", {}).get("usd", 0)
    circ = md.get("circulating_supply", 0)
    print(f"  价格: ${price:,.2f}, 市值: ${mcap:,.0f}, 流通量: {circ:,.0f}")
    return {"price": price, "market_cap": mcap, "circulating": circ}


def main():
    print("=== BNB TEV 数据更新 ===")

    dead_balance = get_dead_balance()
    if not dead_balance:
        print("❌ 无法获取链上数据"); return

    bd = get_bnb_data()
    price, mcap, circulating = bd["price"], bd["market_cap"], bd["circulating"]
    if not price:
        print("❌ 无法获取价格"); return
    if not circulating:
        circulating = INITIAL_SUPPLY - dead_balance

    if not CONFIG_FILE.exists():
        print("❌ config.json 不存在"); return

    with open(CONFIG_FILE) as f:
        config = json.load(f)

    tev = config.get("tev_data", {})
    validation = tev.get("validation", {})
    old_dead = validation.get("dead_address_balance_bnb", 0)

    # 近4季 Auto-Burn from tev-records
    annual_burn_bnb = 0
    total_autoburn_bnb = 0
    bep95_total = 0
    if TEV_FILE.exists():
        with open(TEV_FILE) as f:
            tr = json.load(f)
        burns = [r for r in tr["records"] if r["type"] == "burn"]
        total_autoburn_bnb = sum(r.get("amount_bnb", 0) for r in burns)
        recent_4q = burns[-4:] if len(burns) >= 4 else burns
        annual_burn_bnb = sum(r.get("amount_bnb", 0) for r in recent_4q)
        print(f"  近4季 Auto-Burn: {annual_burn_bnb:,.0f} BNB")

    # BEP-95 估算
    bep95_total = dead_balance - total_autoburn_bnb
    bep95_years = (datetime.now(timezone.utc) - datetime(2021, 11, 30, tzinfo=timezone.utc)).days / 365
    bep95_annual = round(bep95_total / bep95_years) if bep95_years > 0 and bep95_total > 0 else 16327
    print(f"  BEP-95 年化: {bep95_annual:,.0f} BNB")

    # Burn APY
    total_annual_burn = annual_burn_bnb + bep95_annual
    burn_apy = round(total_annual_burn / circulating * 100, 2)

    # asBNB APY (保留上次值)
    asbnb_apy = validation.get("asbnb_apy_percent", 6.87)
    total_apy = round(burn_apy + asbnb_apy, 2)
    annual_tev = round(total_apy / 100 * mcap)

    print(f"\n  Burn APY: {burn_apy}%")
    print(f"  asBNB APY: {asbnb_apy}%")
    print(f"  总 TEV Yield: {total_apy}%")
    print(f"  年化 TEV: ${annual_tev:,.0f}")

    # 更新 config
    tev["tev_yield_percent"] = total_apy
    tev["annual_tev_usd"] = annual_tev
    tev["calculation_date"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    validation["burn_apy_percent"] = burn_apy
    validation["asbnb_apy_percent"] = asbnb_apy
    validation["dead_address_balance_bnb"] = round(dead_balance, 2)
    validation["total_annual_burn_bnb"] = total_annual_burn
    validation["bep95_annual_bnb"] = bep95_annual
    validation["bnb_price_usd"] = price
    validation["market_cap_usd"] = mcap
    validation["circulating_supply"] = circulating
    tev["validation"] = validation
    config["tev_data"] = tev

    # burn_progress
    if "burn_progress" in config:
        bp = config["burn_progress"]
        bp["total_burned"] = round(dead_balance, 0)
        if "segments" in bp:
            for seg in bp["segments"]:
                if "Auto-Burn" in seg.get("label", ""):
                    seg["amount"] = round(total_autoburn_bnb, 0)
                elif "BEP-95" in seg.get("label", ""):
                    seg["amount"] = round(bep95_total, 0)

    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    # 检测新季度销毁
    if old_dead > 0:
        diff = dead_balance - old_dead
        if diff > 100_000:
            print(f"\n  ⚠️ 检测到大额销毁: +{diff:,.0f} BNB，可能有新季度 Auto-Burn")
            print(f"    请手动添加 tev-records.json 记录")
        elif diff > 0:
            print(f"\n  BEP-95 增量: +{diff:,.2f} BNB")

    print("\n✅ config.json 已更新")
    print("=== 完成 ===")


if __name__ == "__main__":
    main()
