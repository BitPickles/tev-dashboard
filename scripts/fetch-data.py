#!/usr/bin/env python3
"""
DeFi TEV Dashboard — 批量数据拉取脚本
从 DefiLlama + CoinGecko API 获取 16 个协议的真实数据

用法: python3 scripts/fetch-data.py [--dry-run] [--protocol compound]
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone

# ── 配置 ──────────────────────────────────────────────

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

# 协议映射: protocol_id → { coingecko_id, defillama_tvl_slug, fee_slugs }
PROTOCOLS = {
    "compound": {
        "coingecko_id": "compound-governance-token",
        "tvl_slugs": ["compound-v2", "compound-v3"],
        "fee_slugs": ["compound-v2", "compound-v3"],
    },
    "dydx": {
        "coingecko_id": "dydx",
        "tvl_slugs": ["dydx"],
        "fee_slugs": ["dydx-v4"],
    },
    "eigenlayer": {
        "coingecko_id": "eigenlayer",
        "tvl_slugs": ["eigenlayer"],
        "fee_slugs": [],  # EigenLayer 无传统费用
    },
    "ethena": {
        "coingecko_id": "ethena",
        "tvl_slugs": ["ethena-usde"],
        "fee_slugs": ["ethena-usde"],
    },
    "etherfi": {
        "coingecko_id": "ether-fi",
        "tvl_slugs": ["ether.fi"],
        "fee_slugs": ["ether.fi-liquid", "etherfi-borrowing-market", "etherfi-cash-liquid"],
    },
    "gmx": {
        "coingecko_id": "gmx",
        "tvl_slugs": ["gmx"],
        "fee_slugs": ["gmx-v2-perps"],
    },
    "jito": {
        "coingecko_id": "jito-governance-token",
        "tvl_slugs": ["jito"],
        "fee_slugs": ["jito-liquid-staking", "jito-mev-tips", "jito-dao"],
    },
    "justlend": {
        "coingecko_id": "just",
        "tvl_slugs": ["justlend"],
        "fee_slugs": ["justlend"],
    },
    "kamino": {
        "coingecko_id": "kamino",
        "tvl_slugs": ["kamino"],
        "fee_slugs": ["kamino-liquidity", "kamino-lend"],
    },
    "lido": {
        "coingecko_id": "lido-dao",
        "tvl_slugs": ["lido"],
        "fee_slugs": ["lido"],
    },
    "maple": {
        "coingecko_id": "syrup",
        "tvl_slugs": ["maple"],
        "fee_slugs": ["maple"],
    },
    "morpho": {
        "coingecko_id": "morpho",
        "tvl_slugs": ["morpho"],
        "fee_slugs": ["morpho-v1"],
    },
    "pancakeswap": {
        "coingecko_id": "pancakeswap-token",
        "tvl_slugs": ["pancakeswap"],
        "fee_slugs": ["pancakeswap-amm", "pancakeswap-amm-v3", "pancakeswap-stableswap",
                       "pancakeswap-infinity", "pancakeswap-prediction", "pancakeswap-lottery"],
    },
    "radiant": {
        "coingecko_id": "radiant-capital",
        "tvl_slugs": ["radiant"],
        "fee_slugs": ["radiant-v2"],
    },
    "spark": {
        "coingecko_id": "spark",
        "tvl_slugs": ["spark"],
        "fee_slugs": ["sparklend", "spark-liquidity-layer"],
    },
}

# TEV 比例 (从 config.json 读取或使用默认值)
TEV_RATIOS = {
    "compound": 0,       # Fee Switch OFF
    "dydx": 1.0,         # 100% 给 stakers
    "eigenlayer": 0,     # 无 TEV
    "ethena": 0,         # 待定 (sENA)
    "etherfi": 0,        # Partial
    "gmx": 0.30,         # 30% 给 GMX stakers
    "jito": 0,           # Fee Switch OFF
    "justlend": 0,       # Partial
    "kamino": 0,         # Partial
    "lido": 0,           # Fee Switch OFF
    "maple": 0.50,       # 50% 预估
    "morpho": 0,         # Fee Switch OFF
    "pancakeswap": 0.20, # CAKE burn
    "radiant": 0.60,     # 60% → dLP lockers
    "spark": 0,          # Fee Switch OFF (Sky ecosystem)
}


# ── HTTP 工具 ──────────────────────────────────────────

def fetch_json(url, retries=3, delay=2):
    """HTTP GET → JSON，带重试"""
    headers = {
        "User-Agent": "TEV-Dashboard/1.0",
        "Accept": "application/json",
    }
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = delay * (2 ** attempt)
                print(f"  ⏳ Rate limited, waiting {wait}s...")
                time.sleep(wait)
                continue
            elif e.code == 404:
                print(f"  ⚠️ 404 Not Found: {url}")
                return None
            else:
                print(f"  ❌ HTTP {e.code}: {url}")
                if attempt < retries - 1:
                    time.sleep(delay)
                    continue
                return None
        except Exception as e:
            print(f"  ❌ Error: {e}")
            if attempt < retries - 1:
                time.sleep(delay)
                continue
            return None
    return None


# ── DefiLlama API ─────────────────────────────────────

def fetch_defillama_tvl(tvl_slugs):
    """获取协议 TVL (合并多个版本)"""
    total_tvl = 0
    for slug in tvl_slugs:
        url = f"https://api.llama.fi/tvl/{slug}"
        data = fetch_json(url)
        if data is not None and isinstance(data, (int, float)):
            total_tvl += data
            print(f"    TVL [{slug}]: ${data:,.0f}")
        time.sleep(0.3)
    return total_tvl


def fetch_defillama_fees_bulk():
    """一次性获取所有协议费用数据"""
    print("\n📊 正在获取 DefiLlama 费用数据（全量）...")
    url = "https://api.llama.fi/overview/fees"
    data = fetch_json(url)
    if not data:
        print("  ❌ 无法获取费用数据")
        return {}

    protocols = data.get("protocols", [])
    fee_map = {}
    for p in protocols:
        slug = p.get("slug", "")
        fee_map[slug] = {
            "total24h": p.get("total24h"),
            "total7d": p.get("total7d"),
            "total30d": p.get("total30d"),
            "total1y": p.get("total1y"),
            "dailyRevenue": p.get("dailyRevenue"),
        }

    print(f"  ✅ 获取到 {len(protocols)} 个协议的费用数据")
    return fee_map


def aggregate_fees(fee_map, fee_slugs):
    """汇总多个版本的费用"""
    result = {"total24h": 0, "total30d": 0, "total1y": 0}
    for slug in fee_slugs:
        if slug in fee_map:
            entry = fee_map[slug]
            for key in result:
                val = entry.get(key)
                if val is not None:
                    result[key] += val
            print(f"    Fees [{slug}]: 30d=${entry.get('total30d', 0):,.0f}")
    return result


# ── CoinGecko API ─────────────────────────────────────

def fetch_coingecko(coingecko_id):
    """获取代币价格、市值、流通量"""
    url = (
        f"https://api.coingecko.com/api/v3/coins/{coingecko_id}"
        f"?localization=false&tickers=false&community_data=false&developer_data=false"
    )
    data = fetch_json(url)
    if not data:
        return None

    md = data.get("market_data", {})
    return {
        "price_usd": md.get("current_price", {}).get("usd"),
        "market_cap_usd": md.get("market_cap", {}).get("usd"),
        "circulating_supply": md.get("circulating_supply"),
        "total_supply": md.get("total_supply"),
        "fdv_usd": md.get("fully_diluted_valuation", {}).get("usd"),
        "price_change_24h_pct": md.get("price_change_percentage_24h"),
        "ath_usd": md.get("ath", {}).get("usd"),
    }


# ── 数据写入 ──────────────────────────────────────────

def write_latest_json(protocol_id, data):
    """写入 data/daily/{protocol}/latest.json"""
    dir_path = os.path.join(DATA_DIR, "daily", protocol_id)
    os.makedirs(dir_path, exist_ok=True)
    file_path = os.path.join(dir_path, "latest.json")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"  💾 写入 {file_path}")


def update_config_json(protocol_id, cg_data):
    """更新 config.json 中缺失的 token 字段"""
    config_path = os.path.join(DATA_DIR, "protocols", protocol_id, "config.json")
    if not os.path.exists(config_path):
        print(f"  ⚠️ config.json 不存在: {config_path}")
        return

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    token = config.get("token", {})
    updated = False

    if cg_data:
        if not token.get("circulating_supply") and cg_data.get("circulating_supply"):
            token["circulating_supply"] = cg_data["circulating_supply"]
            updated = True
        if not token.get("total_supply") and cg_data.get("total_supply"):
            token["total_supply"] = cg_data["total_supply"]
            updated = True

    if updated:
        config["token"] = token
        config["last_updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        print(f"  📝 更新 config.json (supply 数据)")


# ── 主逻辑 ────────────────────────────────────────────

def process_protocol(protocol_id, cfg, fee_map, dry_run=False):
    """处理单个协议"""
    print(f"\n{'='*60}")
    print(f"🔄 处理: {protocol_id}")
    print(f"{'='*60}")

    now = datetime.now(timezone.utc)
    tev_ratio = TEV_RATIOS.get(protocol_id, 0)

    # 1. DefiLlama TVL
    print("  📈 获取 TVL...")
    tvl = fetch_defillama_tvl(cfg["tvl_slugs"])
    print(f"  → 总 TVL: ${tvl:,.0f}")

    # 2. DefiLlama Fees (从预加载的数据中提取)
    print("  💰 提取费用数据...")
    fees = aggregate_fees(fee_map, cfg["fee_slugs"])
    print(f"  → 30d 费用: ${fees['total30d']:,.0f}")

    # 3. CoinGecko (价格/市值/供应量)
    print("  🪙 获取代币数据...")
    time.sleep(6)  # CoinGecko free tier: 10-30 req/min, 保守等待
    cg = fetch_coingecko(cfg["coingecko_id"])
    if cg:
        print(f"  → 价格: ${cg['price_usd']}")
        print(f"  → 市值: ${cg['market_cap_usd']:,.0f}" if cg['market_cap_usd'] else "  → 市值: N/A")
        print(f"  → 流通: {cg['circulating_supply']:,.0f}" if cg['circulating_supply'] else "  → 流通: N/A")
    else:
        print("  ⚠️ CoinGecko 数据获取失败")
        cg = {}

    # 4. 计算 TEV 指标
    daily_fees = fees.get("total24h", 0) or 0
    fees_30d = fees.get("total30d", 0) or 0
    daily_tev = daily_fees * tev_ratio
    tev_30d = fees_30d * tev_ratio
    tev_annualized = tev_30d * 12
    mcap = cg.get("market_cap_usd") or 0
    tev_yield = (tev_annualized / mcap) if mcap > 0 else 0

    # 5. 构造 latest.json
    latest = {
        "protocol": protocol_id,
        "updated_at": now.isoformat(),
        "data_sources": {
            "tvl": "DefiLlama",
            "fees": "DefiLlama",
            "market": "CoinGecko",
        },
        "latest_record": {
            "date": now.strftime("%Y-%m-%d"),
            "price_usd": cg.get("price_usd"),
            "market_cap_usd": cg.get("market_cap_usd"),
            "fdv_usd": cg.get("fdv_usd"),
            "circulating_supply": cg.get("circulating_supply"),
            "total_supply": cg.get("total_supply"),
            "tvl_usd": tvl,
            "daily_fees_usd": daily_fees,
            "daily_tev_usd": round(daily_tev, 2),
            "tev_ratio_used": tev_ratio,
        },
        "metrics": {
            "trailing_30d_fees_usd": fees_30d,
            "trailing_30d_tev_usd": round(tev_30d, 2),
            "annualized_fees_usd": round(fees_30d * 12, 2),
            "annualized_tev_usd": round(tev_annualized, 2),
            "current_market_cap_usd": mcap,
            "tev_yield": f"{tev_yield:.2%}" if mcap > 0 else "N/A",
            "tev_yield_decimal": round(tev_yield, 6) if mcap > 0 else 0,
            "tvl_usd": tvl,
            "mcap_tvl_ratio": round(mcap / tvl, 4) if tvl > 0 else None,
            "calculated_at": now.isoformat(),
        },
        "fees_breakdown": {
            slug: fee_map.get(slug, {}).get("total30d", 0)
            for slug in cfg["fee_slugs"]
            if slug in fee_map
        },
    }

    if dry_run:
        print(f"\n  [DRY RUN] 数据预览:")
        print(json.dumps(latest, indent=2))
    else:
        write_latest_json(protocol_id, latest)
        update_config_json(protocol_id, cg)

    return latest


def main():
    dry_run = "--dry-run" in sys.argv
    target = None
    for i, arg in enumerate(sys.argv):
        if arg == "--protocol" and i + 1 < len(sys.argv):
            target = sys.argv[i + 1]

    if dry_run:
        print("🏃 DRY RUN 模式 — 不写入文件")

    # 预加载 DefiLlama 费用数据
    fee_map = fetch_defillama_fees_bulk()
    if not fee_map:
        print("❌ 无法获取费用数据，退出")
        sys.exit(1)

    protocols_to_process = {target: PROTOCOLS[target]} if target and target in PROTOCOLS else PROTOCOLS
    results = {}
    total = len(protocols_to_process)

    print(f"\n🚀 开始处理 {total} 个协议...")

    for i, (pid, cfg) in enumerate(protocols_to_process.items(), 1):
        print(f"\n[{i}/{total}]", end="")
        try:
            result = process_protocol(pid, cfg, fee_map, dry_run)
            results[pid] = "✅"
        except Exception as e:
            print(f"  ❌ 失败: {e}")
            results[pid] = f"❌ {e}"

    # 汇总
    print(f"\n\n{'='*60}")
    print(f"📊 执行结果汇总")
    print(f"{'='*60}")
    for pid, status in results.items():
        print(f"  {pid:20s} {status}")

    print(f"\n⏰ 完成时间: {datetime.now(timezone.utc).isoformat()}")


if __name__ == "__main__":
    main()
