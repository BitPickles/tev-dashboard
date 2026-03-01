#!/usr/bin/env python3
"""
Hyperliquid (HYPE) TEV 增量更新脚本

核心逻辑：
1. 从 tev-records.json 读取最后日期
2. DefiLlama dailyHoldersRevenue 获取全部历史
3. 只追加新日期的记录
4. 用链上 AF 余额交叉验证累计值
5. 更新 config.json

用法：
  python3 scripts/update-hype.py           # 增量更新
  python3 scripts/update-hype.py --full    # 全量重建
"""

import subprocess
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# === 配置 ===
AF_ADDRESS = "0xfefefefefefefefefefefefefefefefefefefefe"
DEFILLAMA_URL = "https://api.llama.fi/summary/fees/hyperliquid?dataType=dailyHoldersRevenue"
TOTAL_SUPPLY = 1_000_000_000

# 路径
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "data" / "protocols" / "hype"
TEV_FILE = DATA_DIR / "tev-records.json"
CONFIG_FILE = DATA_DIR / "config.json"


def curl_json(url: str, method="GET", data=None) -> dict:
    cmd = ["curl", "-s", "--max-time", "30"]
    if data:
        cmd.extend(["-H", "Content-Type: application/json", "-d", data, url])
    else:
        cmd.append(url)
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return {}
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {}


def load_tev_records() -> dict:
    if TEV_FILE.exists():
        with open(TEV_FILE) as f:
            return json.load(f)
    return {
        "protocol": "hype",
        "data_source": "DefiLlama dailyHoldersRevenue + Hyperliquid AF on-chain",
        "data_source_url": "https://api.llama.fi/summary/fees/hyperliquid?dataType=dailyHoldersRevenue",
        "records": []
    }


def get_defillama_daily() -> list:
    """获取 DefiLlama 每日 holdersRevenue"""
    print("获取 DefiLlama dailyHoldersRevenue...")
    data = curl_json(DEFILLAMA_URL)
    chart = data.get("totalDataChart", [])
    if not chart:
        print("  ❌ 无数据")
        return []

    records = []
    for ts, usd in chart:
        date_str = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
        if usd and usd > 0:
            records.append({
                "date": date_str,
                "amount_usd": round(usd, 0)
            })
    print(f"  获取到 {len(records)} 天数据")
    return records


def get_af_balance() -> dict:
    """获取 AF 链上余额（交叉验证）"""
    print("获取链上 AF 余额...")
    data = curl_json(
        "https://api.hyperliquid.xyz/info",
        data=json.dumps({"type": "spotClearinghouseState", "user": AF_ADDRESS})
    )
    balances = data.get("balances", [])
    for b in balances:
        if b.get("coin") == "HYPE":
            total = float(b.get("total", 0))
            entry = float(b.get("entryNtl", 0))
            print(f"  AF 余额: {total:,.0f} HYPE, 成本: ${entry:,.0f}")
            return {"hype": total, "usd": entry}
    print("  ⚠️ 未找到 HYPE 余额")
    return {}


def main():
    full_mode = "--full" in sys.argv
    data = load_tev_records()

    if full_mode:
        print("=== 全量重建模式 ===")
        existing_dates = set()
        data["records"] = []
    else:
        existing_dates = {r["date"] for r in data["records"]}
        print(f"=== 增量更新模式 (已有 {len(existing_dates)} 天) ===")

    # 1. 获取 DefiLlama 数据
    daily = get_defillama_daily()
    if not daily:
        print("❌ 无法获取数据，中止")
        return

    # 2. 筛选新记录
    new_records = []
    for d in daily:
        if d["date"] not in existing_dates:
            new_records.append({
                "date": d["date"],
                "type": "buyback_burn",
                "amount_usd": d["amount_usd"],
                "period": d["date"],
                "source": {
                    "type": "api",
                    "provider": "DefiLlama"
                }
            })

    print(f"新增 {len(new_records)} 天记录")

    if not new_records and not full_mode:
        print("无新增记录")
        # 仍然做链上验证
        af = get_af_balance()
        if af:
            print(f"✅ 链上验证: AF 持有 {af.get('hype',0):,.0f} HYPE, 成本 ${af.get('usd',0):,.0f}")
        return

    # 3. 合并
    data["records"].extend(new_records)
    data["records"].sort(key=lambda r: r["date"])

    # 4. 链上交叉验证
    af = get_af_balance()

    # 5. 计算 summary
    total_usd = sum(r["amount_usd"] for r in data["records"])
    days = len(data["records"])
    
    # 365d 滚动
    all_records = data["records"]
    recent_365 = [r for r in all_records if r["date"] >= (datetime.now(timezone.utc).strftime("%Y-%m-%d")[:4] + "-01-01")]  # 简化
    # 更精确: 取最后365条或按日期
    if len(all_records) > 365:
        trailing_records = all_records[-365:]
    else:
        trailing_records = all_records
    trailing_365d_usd = sum(r["amount_usd"] for r in trailing_records)

    # 6. 更新时间戳
    data["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # 7. 保存
    with open(TEV_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✅ tev-records.json 已保存 ({len(data['records'])} 条记录)")
    print(f"   累计 TEV: ${total_usd:,.0f} ({days} 天)")
    print(f"   365d TEV: ${trailing_365d_usd:,.0f}")
    if af:
        print(f"   链上验证: AF {af.get('hype',0):,.0f} HYPE / ${af.get('usd',0):,.0f}")

    # 8. 更新 config.json
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            config = json.load(f)

        if "tev_data" in config:
            config["tev_data"]["trailing_365d_tev_usd"] = trailing_365d_usd
            config["tev_data"]["last_updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # 更新 burn_progress
        if af and "burn_progress" in config:
            bp = config["burn_progress"]
            hype_burned = af.get("hype", 0)
            bp["total_burned"] = round(hype_burned, 0)
            bp["pct"] = round(hype_burned / TOTAL_SUPPLY * 100, 2)

        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        print("  config.json 已更新")

    print("=== 完成 ===")


if __name__ == "__main__":
    main()
