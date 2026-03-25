#!/usr/bin/env python3
"""
单市场解析器 - 解析特定 ID 的市场数据
"""

import subprocess
import re
from datetime import datetime, timedelta

def parse_single_market(html, market_id):
    """解析指定 ID 的市场"""
    print(f"🔍 Looking for market ID: {market_id}")

    # 查找该 ID 在 HTML 中的位置
    id_pattern = f'"id": "{market_id }"'
    id_match = re.search(id_pattern, html)

    if not id_match:
        print(f"❌ Market ID {market_id} not found in current HTML")
        return None

    # 获取该位置周围的大量上下文（前后各 10000 字符）
    context_start = max(0, id_match.start() - 10000)
    context_end = min(len(html), id_match.end() + 10000)
    context = html[context_start:context_end]

    print(f"✅ Found ID at position {id_match.start()}, extracting data...")

    # 解析价格
    price_pattern = rf'"id": "{market_id }"[\s\S]*? "outcomePrices"[\s\S]*?: "\s*\(\s*\[([^\]]+)\)\s*\)'
    price_match = re.search(price_pattern, context)
    outcome_prices = {}

    if price_match:
        try:
            prices = json.loads(price_match.group(1))
            if len(prices) >= 2:
                outcome_prices = {"Outcome1": float(prices[0]), "Outcome2": float(prices[1])}
            elif len(prices) >= 3:
                outcome_prices = {
                    "Outcome1": float(prices[0]),
                    "Outcome2": float(prices[1]),
                    "Outcome3": float(prices[2])
                }
        except:
            pass

    # 解析 volume
    vol_match = re.search(rf'"id": "{market_id }"[\s\S]*? "volume"[\s\S]*?: "\s*(\d+(?:\.\d+)?)', context)
    volume = float(vol_match.group(1)) if vol_match else 0

    # 解析 liquidity
    liq_match = re.search(rf'"id": "{market_id }"[\s\S]*? "liquidity"[\s\S]*?: "\s*(\d+(?:\.\d+)?)', context)
    liquidity = float(liq_match.group(1)) if liq_match else 0

    # 解析 endDate
    end_match = re.search(rf'"id": "{market_id }"[\s\S]*? "endDate"[\s\S]*?: "\s*"([^"]+)"', context)
    end_time = None
    if end_match:
        try:
            end_time = datetime.fromisoformat(end_match.group(1).replace("Z", "+00:00"))
        except:
            pass

    # 解析 question
    q_match = re.search(rf'"id": "{market_id }"[\s\S]*? "question"[\s\S]*?: "\s*"([^"]+)"', context)
    question = q_match.group(1) if q_match else "Unknown"

    # 如果找不到任何价格，尝试备用模式
    if not outcome_prices:
        # 查找该 ID 周围的任何价格数据
        price_search = re.search(rf'\[["id": "{market_id }".*?price', context)
        if price_search:
            print(f"Found alternative price format near market")

    market = {
        "id": market_id,
        "question": question,
        "outcome_prices": outcome_prices,
        "volume": volume,
        "liquidity": liquidity,
        "end_time": end_time.isoformat() if end_time else None,
        "tags": ["Real Market"]
    }

    print(f"✅ Parsed market:")
    print(f"   Question: {question[:60]}")
    print(f"   Prices: {outcome_prices}")
    print(f"   Volume: ${volume:,.0f}")
    print(f"   Liquidity: ${liquidity:,.0f}")
    print(f"   Ends: {end_time.isoformat() if end_time else 'N/A'}")

    return market


def main():
    print("""
    ╔═════════════════════════════════════════════════════╗
    ║       Single Market Parser (REAL DATA - 2026)             ║
    ╚═════════════════════════════════════════════════════╝
    """)

    # 获取 HTML
    print("📡 Fetching fresh HTML from polymarket.com...")
    curl_cmd = ["curl", "-s", "https://polymarket.com/"]
    result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=30)
    html = result.stdout
    print(f"✅ Fetched {len(html)} bytes\n")

    # 尝试解析特定的市场 ID
    target_ids = [
        "1199779",  # US Strike Somalia
        "100265",  # 从之前测试中发现的
        "78",
        "126"
    ]

    for mid in target_ids:
        market = parse_single_market(html, mid)

        if market and market["volume"] > 0:
            print("\n" + "=" * 70)
            print(f"📊 MARKET {market['id']} - REAL DATA")
            print("=" * 70)
            print(f"Question: {market['question']}")
            print(f"Prices: {market['outcome_prices']}")
            print(f"Volume: ${market['volume']:,.2f}")
            print(f"Liquidity: ${market['liquidity']:,.2f}")
            print(f"End Time: {market['end_time']}")
            print("=" * 70 + "\n")

    # 检查会议提醒
    now = datetime.now()
    if now.hour == 14 and now.minute < 5:
        print("\n" + "🔔" * 30)
        print("⏰  REMINDER: 下午 2 点有会！")
        print("🔔" * 30 + "\n")


if __name__ == "__main__":
    main()
