#!/usr/bin/env python3
"""
Uniswap TEV 增量更新脚本

核心逻辑：
1. 从 tev-records.json 读取 last_block
2. Etherscan V2 查询新的 UNI → 0xdead 转账
3. 过滤 fee switch 后（≥2025-12-28）的记录
4. 排除 100M 国库一次性销毁
5. 按日聚合，用 CoinGecko 价格折算 USD
6. 追加到 tev-records.json，更新 last_block
7. 更新 config.json 的 tev_data 和 burn_progress

用法：
  python3 scripts/update-uniswap.py           # 增量更新
  python3 scripts/update-uniswap.py --full     # 全量重建
"""

import subprocess
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# === 配置 ===
ETHERSCAN_API_KEY = "BUWR46PIP7JVZK98IP7YRQARRSABIP3V92"
UNI_TOKEN = "0x1f9840a85d5af5bf1d1762f925bdaddc4201f984"
DEAD_ADDR = "0x000000000000000000000000000000000000dEaD"
FEE_SWITCH_DATE = "2025-12-28"
RETROACTIVE_TX = "0x091f0083242a777d55821c1189e568d6d033d9da501b75087dc736fa143d2c1e"
UNI_DECIMALS = 18
TOTAL_SUPPLY = 1_000_000_000

# 路径
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "data" / "protocols" / "uniswap"
TEV_FILE = DATA_DIR / "tev-records.json"
CONFIG_FILE = DATA_DIR / "config.json"


def curl_json(url: str) -> dict:
    """用 curl 请求避免 Python SSL 问题"""
    result = subprocess.run(
        ["curl", "-s", "--max-time", "30", url],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"  curl 失败: {result.stderr}")
        return {}
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        print(f"  JSON 解析失败: {result.stdout[:200]}")
        return {}


def load_tev_records() -> dict:
    if TEV_FILE.exists():
        with open(TEV_FILE) as f:
            return json.load(f)
    return {
        "protocol": "uniswap",
        "data_source": "Etherscan on-chain (UNI transfers to 0xdead)",
        "fee_switch_date": FEE_SWITCH_DATE,
        "last_block": 0,
        "retroactive_burn": {
            "tx": RETROACTIVE_TX,
            "date": "2025-12-27",
            "amount_uni": 100000000,
            "note": "一次性国库销毁，不计入持续 TEV"
        },
        "summary": {},
        "records": []
    }


def get_uni_burns(start_block: int = 0) -> list:
    """获取 UNI → 0xdead 的所有转账记录"""
    url = (
        f"https://api.etherscan.io/v2/api?chainid=1"
        f"&module=account&action=tokentx"
        f"&contractaddress={UNI_TOKEN}"
        f"&address={DEAD_ADDR}"
        f"&startblock={start_block}&endblock=99999999"
        f"&sort=asc&apikey={ETHERSCAN_API_KEY}"
    )
    print(f"查询 Etherscan V2 (from block {start_block})...")
    data = curl_json(url)

    if data.get("status") != "1" or not data.get("result"):
        msg = data.get("message", "Unknown")
        print(f"  API 返回: {msg}")
        return []

    transfers = [
        tx for tx in data["result"]
        if tx["to"].lower() == DEAD_ADDR.lower()
    ]
    print(f"  获取到 {len(transfers)} 笔 UNI → 0xdead 转账")
    return transfers


def get_coingecko_prices(days: int = 90) -> dict:
    """获取 UNI 历史价格，返回 {date_str: price}"""
    url = (
        f"https://api.coingecko.com/api/v3/coins/uniswap/market_chart"
        f"?vs_currency=usd&days={days}&interval=daily"
    )
    print(f"获取 CoinGecko UNI 价格 ({days} 天)...")
    data = curl_json(url)
    prices = {}
    for ts_ms, price in data.get("prices", []):
        date_str = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
        prices[date_str] = price
    print(f"  获取到 {len(prices)} 天价格数据")
    return prices


def filter_and_aggregate(transfers: list, prices: dict, existing_dates: set) -> list:
    """过滤 + 按日聚合"""
    daily = {}

    for tx in transfers:
        ts = int(tx["timeStamp"])
        date_str = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")

        if date_str < FEE_SWITCH_DATE:
            continue

        if tx["hash"].lower() == RETROACTIVE_TX.lower():
            continue

        amount = int(tx["value"]) / (10 ** UNI_DECIMALS)

        if amount > 1_000_000:
            print(f"  跳过异常大额: {amount:.0f} UNI @ {date_str} tx={tx['hash'][:16]}...")
            continue

        if date_str not in daily:
            daily[date_str] = {"amount_uni": 0, "tx_count": 0, "max_block": 0}

        daily[date_str]["amount_uni"] += amount
        daily[date_str]["tx_count"] += 1
        block = int(tx["blockNumber"])
        if block > daily[date_str]["max_block"]:
            daily[date_str]["max_block"] = block

    new_records = []
    for date_str in sorted(daily.keys()):
        if date_str in existing_dates:
            continue
        d = daily[date_str]
        price = prices.get(date_str, 0)
        amount_usd = d["amount_uni"] * price if price else 0

        new_records.append({
            "id": f"uni-burn-{date_str}",
            "date": date_str,
            "type": "buyback_burn",
            "amount_uni": round(d["amount_uni"], 2),
            "amount_usd": round(amount_usd, 2),
            "avg_price": round(price, 4) if price else None,
            "tx_count": d["tx_count"],
            "block": d["max_block"]
        })

    return new_records


def update_summary(data: dict):
    """重算 summary"""
    records = data["records"]
    if not records:
        return

    total_uni = sum(r["amount_uni"] for r in records)
    total_usd = sum(r["amount_usd"] for r in records)
    days = len(records)
    avg_daily = total_uni / days if days else 0

    data["summary"] = {
        "total_uni_burned": round(total_uni, 2),
        "total_usd_burned": round(total_usd, 2),
        "days": days,
        "avg_daily_uni": round(avg_daily, 2),
        "annualized_uni": round(avg_daily * 365, 0),
        "annualized_usd": round((total_usd / days * 365) if days else 0, 0)
    }


def find_max_block(records: list) -> int:
    max_b = 0
    for r in records:
        b = r.get("block", 0)
        if b > max_b:
            max_b = b
    return max_b


def update_config(summary: dict, records: list):
    """更新 config.json 的 tev_data 和 burn_progress"""
    if not CONFIG_FILE.exists():
        print("  config.json 不存在，跳过")
        return

    with open(CONFIG_FILE) as f:
        config = json.load(f)

    if "tev_data" in config:
        td = config["tev_data"]
        td["trailing_365d_tev_usd"] = summary.get("annualized_usd", 0)
        td["last_updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    total_burned_uni = summary.get("total_uni_burned", 0) + 100_000_000
    firepit_burned = summary.get("total_uni_burned", 0)

    if "burn_progress" in config:
        bp = config["burn_progress"]
        bp["total_burned"] = round(total_burned_uni, 0)
        bp["pct"] = round(total_burned_uni / TOTAL_SUPPLY * 100, 2)
        if "segments" in bp:
            for seg in bp["segments"]:
                if seg.get("id") == "firepit" or seg.get("label", "").startswith("Firepit"):
                    seg["value"] = round(firepit_burned, 0)
                    seg["pct"] = round(firepit_burned / TOTAL_SUPPLY * 100, 2)

    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    print("  config.json 已更新")


def main():
    full_mode = "--full" in sys.argv

    data = load_tev_records()
    existing_dates = {r["date"] for r in data["records"]}

    if full_mode:
        print("=== 全量重建模式 ===")
        start_block = 0
        data["records"] = []
        existing_dates = set()
    else:
        start_block = data.get("last_block", 0)
        if start_block > 0:
            start_block += 1
        print(f"=== 增量更新模式 (from block {start_block}) ===")

    # 1. 获取链上数据
    transfers = get_uni_burns(start_block)
    if not transfers and not full_mode:
        print("无新数据")
        return

    # 2. 获取价格
    days_needed = 120 if full_mode else 30
    prices = get_coingecko_prices(days_needed)
    if not prices:
        print("❌ 无法获取价格数据，中止")
        return

    # 3. 过滤聚合
    new_records = filter_and_aggregate(transfers, prices, existing_dates)
    print(f"新增 {len(new_records)} 天记录")

    if not new_records and not full_mode:
        print("无新增记录")
        return

    # 4. 合并
    data["records"].extend(new_records)
    data["records"].sort(key=lambda r: r["date"])

    # 5. 更新 last_block
    max_block = find_max_block(data["records"])
    if max_block > data.get("last_block", 0):
        data["last_block"] = max_block

    # 6. 重算 summary
    update_summary(data)

    # 7. 时间戳
    data["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # 8. 保存
    with open(TEV_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"✅ tev-records.json 已保存 ({len(data['records'])} 条记录)")

    s = data["summary"]
    print(f"   累计销毁: {s['total_uni_burned']:,.0f} UNI (${s['total_usd_burned']:,.0f})")
    print(f"   年化销毁: {s['annualized_uni']:,.0f} UNI (${s['annualized_usd']:,.0f})")

    # 9. 更新 config.json
    update_config(data["summary"], data["records"])
    print("=== 完成 ===")


if __name__ == "__main__":
    main()
