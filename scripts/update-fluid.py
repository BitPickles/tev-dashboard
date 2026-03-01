#!/usr/bin/env python3
"""
Fluid TEV 更新脚本

主数据源：链上回购（Etherscan V2 追踪 FLUID 流入储备钱包）
交叉验证：DefiLlama holdersRevenue

输出：
  - data/protocols/fluid/tev-records.json（链上每日回购）
  - data/protocols/fluid/config.json（TEV Yield 等）

用法：
  python3 scripts/update-fluid.py           # 增量更新
  python3 scripts/update-fluid.py --full    # 全量重建
"""

import subprocess
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# === 配置 ===
FLUID_TOKEN = "0x6f40d4A6237C257fff2dB00FA0510DeEECd303eb"
RESERVE_WALLETS = [
    "0x3e6FeBd2b195e1Ef3e8e3F4AABB6772aada32353",
    "0x9Afb8C1798B93a8E04a18553eE65bAFa41a012F1"
]
ETHERSCAN_API_KEY = "BUWR46PIP7JVZK98IP7YRQARRSABIP3V92"

SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "data" / "protocols" / "fluid"
TEV_FILE = DATA_DIR / "tev-records.json"
CONFIG_FILE = DATA_DIR / "config.json"


def curl_json(url):
    r = subprocess.run(["curl", "-s", "--max-time", "30", url],
                       capture_output=True, text=True)
    try:
        return json.loads(r.stdout) if r.returncode == 0 else {}
    except:
        return {}


def load_tev_records():
    if TEV_FILE.exists():
        with open(TEV_FILE) as f:
            return json.load(f)
    return {
        "protocol": "fluid",
        "data_source": "Etherscan on-chain (FLUID transfers to reserve wallets)",
        "reserve_wallets": RESERVE_WALLETS,
        "last_block": 0,
        "summary": {},
        "records": []
    }


def get_fluid_transfers(start_block=0):
    """获取 FLUID 转入储备钱包的记录"""
    all_transfers = []
    for wallet in RESERVE_WALLETS:
        url = (
            f"https://api.etherscan.io/v2/api?chainid=1"
            f"&module=account&action=tokentx"
            f"&contractaddress={FLUID_TOKEN}"
            f"&address={wallet}"
            f"&startblock={start_block}&endblock=99999999"
            f"&sort=asc&apikey={ETHERSCAN_API_KEY}"
        )
        print(f"查询钱包 {wallet[:10]}... (from block {start_block})")
        data = curl_json(url)

        if data.get("status") == "1" and data.get("result"):
            inflows = [tx for tx in data["result"]
                       if tx["to"].lower() == wallet.lower()]
            print(f"  {len(inflows)} 笔转入")
            all_transfers.extend(inflows)
        else:
            print(f"  {data.get('message', 'No data')}")

    return all_transfers


def get_prices(days=180):
    """CoinGecko FLUID 历史价格"""
    print(f"获取 CoinGecko 价格 ({days} 天)...")
    data = curl_json(
        f"https://api.coingecko.com/api/v3/coins/instadapp/market_chart"
        f"?vs_currency=usd&days={days}&interval=daily"
    )
    prices = {}
    for ts_ms, price in data.get("prices", []):
        date = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
        prices[date] = price
    print(f"  {len(prices)} 天价格")
    return prices


def aggregate(transfers, prices, existing_dates):
    """按日聚合 + 过滤已有日期"""
    daily = {}
    for tx in transfers:
        ts = int(tx["timeStamp"])
        date = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
        amount = int(tx["value"]) / 1e18

        if date not in daily:
            daily[date] = {"fluid": 0, "tx_count": 0, "max_block": 0}
        daily[date]["fluid"] += amount
        daily[date]["tx_count"] += 1
        block = int(tx["blockNumber"])
        if block > daily[date]["max_block"]:
            daily[date]["max_block"] = block

    new_records = []
    for date in sorted(daily.keys()):
        if date in existing_dates:
            continue
        d = daily[date]
        price = prices.get(date, 0)
        usd = d["fluid"] * price if price else 0
        new_records.append({
            "date": date,
            "type": "buyback",
            "amount_fluid": round(d["fluid"], 2),
            "amount_usd": round(usd, 2),
            "avg_price": round(price, 4) if price else None,
            "tx_count": d["tx_count"],
            "block": d["max_block"],
            "source": {"type": "onchain", "provider": "Etherscan"}
        })
    return new_records


def cross_validate():
    """DefiLlama 交叉验证"""
    print("DefiLlama 交叉验证...")
    dl = curl_json("https://api.llama.fi/summary/fees/fluid?dataType=dailyHoldersRevenue")
    chart = dl.get("totalDataChart", [])
    if chart:
        dl_total = sum(v for _, v in chart if isinstance(v, (int, float)) and v > 0)
        return dl_total
    return None


def main():
    full_mode = "--full" in sys.argv
    data = load_tev_records()

    if full_mode:
        print("=== 全量重建模式 ===")
        data["records"] = []
        data["last_block"] = 0
        existing_dates = set()
    else:
        existing_dates = {r["date"] for r in data["records"]}
        print(f"=== 增量更新模式 (已有 {len(existing_dates)} 天) ===")

    start_block = data.get("last_block", 0)
    if start_block > 0 and not full_mode:
        start_block += 1

    # 1. 链上数据
    transfers = get_fluid_transfers(start_block)
    if not transfers and not full_mode:
        print("无新转账")
        # Still do cross-validation
        dl_total = cross_validate()
        if dl_total:
            onchain_total = sum(r["amount_usd"] for r in data["records"])
            diff_pct = abs(dl_total - onchain_total) / dl_total * 100 if dl_total else 0
            print(f"  链上: ${onchain_total:,.0f} vs DefiLlama: ${dl_total:,.0f} (差 {diff_pct:.1f}%)")
            if diff_pct > 10:
                print(f"  ⚠️ 差异超过 10%，建议 --full 重建")
        return

    # 2. 价格
    days_needed = 365 if full_mode else 180
    prices = get_prices(days_needed)
    if not prices:
        print("❌ 无法获取价格"); return

    # 3. 聚合
    new_records = aggregate(transfers, prices, existing_dates)
    print(f"新增 {len(new_records)} 天记录")

    if not new_records and not full_mode:
        print("无新增记录"); return

    # 4. 合并
    data["records"].extend(new_records)
    data["records"].sort(key=lambda r: r["date"])

    # 5. last_block
    max_block = max((r.get("block", 0) for r in data["records"]), default=0)
    if max_block > data.get("last_block", 0):
        data["last_block"] = max_block

    # 6. Summary
    records = data["records"]
    total_fluid = sum(r.get("amount_fluid", 0) for r in records)
    total_usd = sum(r["amount_usd"] for r in records)
    days = len(records)

    cutoff = (datetime.now(timezone.utc) - timedelta(days=365)).strftime("%Y-%m-%d")
    trailing_usd = sum(r["amount_usd"] for r in records if r["date"] >= cutoff)
    trailing_fluid = sum(r.get("amount_fluid", 0) for r in records if r["date"] >= cutoff)

    data["summary"] = {
        "total_fluid": round(total_fluid, 2),
        "total_usd": round(total_usd, 0),
        "days_with_buyback": days,
        "trailing_365d_usd": round(trailing_usd, 0),
        "trailing_365d_fluid": round(trailing_fluid, 2),
        "avg_daily_fluid": round(total_fluid / days, 2) if days else 0
    }
    data["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    data["data_source"] = "Etherscan on-chain (FLUID transfers to reserve wallets)"
    data["reserve_wallets"] = RESERVE_WALLETS

    # 7. 保存
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(TEV_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"✅ tev-records.json: {days} 条, 365d TEV ${trailing_usd:,.0f}")

    # 同步 fluid-buybacks.json（图表兼容）
    legacy = {
        "protocol": "fluid", "ticker": "FLUID", "total_supply": 1000000000,
        "updated_at": data["updated_at"],
        "data_type": "daily", "data_source": "onchain",
        "data_source_note": "链上追踪 FLUID 流入储备钱包 (Etherscan API)",
        "reserve_wallets": RESERVE_WALLETS,
        "summary": {
            "total_buyback_fluid": round(total_fluid, 2),
            "total_buyback_usd": round(total_usd, 2),
            "total_days": days,
            "first_date": records[0]["date"] if records else None,
            "last_date": records[-1]["date"] if records else None,
            "avg_daily_fluid": round(total_fluid / days, 2) if days else 0,
            "avg_price": round(total_usd / total_fluid, 4) if total_fluid else 0
        },
        "daily_buybacks": [
            {"date": r["date"], "fluid": r.get("amount_fluid", 0), "usd": r["amount_usd"],
             "price": r.get("avg_price"), "txs": r.get("tx_count", 0),
             "dataType": "onchain", "source": "Etherscan"}
            for r in records
        ]
    }
    legacy_file = SCRIPT_DIR.parent / "data" / "fluid-buybacks.json"
    with open(legacy_file, "w") as f:
        json.dump(legacy, f, indent=2, ensure_ascii=False)
    print("  fluid-buybacks.json 已同步（图表兼容）")

    # 8. 交叉验证
    dl_total = cross_validate()
    if dl_total:
        diff_pct = abs(dl_total - total_usd) / dl_total * 100 if dl_total else 0
        print(f"  链上: ${total_usd:,.0f} vs DefiLlama: ${dl_total:,.0f} (差 {diff_pct:.1f}%)")
        if diff_pct > 10:
            print(f"  ⚠️ 差异超过 10%")

    # 9. 更新 config.json
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            config = json.load(f)

        cg = curl_json(
            "https://api.coingecko.com/api/v3/simple/price"
            "?ids=instadapp&vs_currencies=usd&include_market_cap=true"
        )
        mcap = cg.get("instadapp", {}).get("usd_market_cap", 0)
        price = cg.get("instadapp", {}).get("usd", 0)
        tev_yield = round(trailing_usd / mcap * 100, 2) if mcap else 0

        if "tev_data" not in config:
            config["tev_data"] = {}
        td = config["tev_data"]
        td["has_tev"] = True
        td["trailing_365d_tev_usd"] = round(trailing_usd, 0)
        td["tev_yield_percent"] = tev_yield
        td["market_cap_usd"] = round(mcap, 0)
        td["price_usd"] = price
        td["last_updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        td["methodology"] = "链上回购追踪（Etherscan FLUID→储备钱包），DefiLlama 交叉验证"
        td["validation"] = {
            "onchain_total_usd": round(total_usd, 0),
            "defillama_total_usd": round(dl_total, 0) if dl_total else None,
            "diff_pct": round(diff_pct, 1) if dl_total else None
        }

        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        print(f"  config.json: Yield {tev_yield}%, 市值 ${mcap:,.0f}")

    print("=== 完成 ===")


if __name__ == "__main__":
    main()
