#!/usr/bin/env python3
"""
Polymarket 真实数据分析器 - 专门解析活跃市场
使用已验证的活跃市场 ID 进行精确解析
"""

import subprocess
import json
import re
from datetime import datetime, timedelta

# 已知的活跃市场 ID（从之前测试中发现的）
ACTIVE_MARKET_IDS = {
    "1199779": "US Strike Somalia",
    "601699": "Fed Rates - No Change",
    "601698": "Fed Rates - Decrease 25 bps",
    "601697": "Fed Rates - Decrease 50+ bps",
    "601700": "Fed Rates - Increase 25+ bps"
}

def parse_market_by_id(html, market_id, market_name=""):
    """解析指定 ID 的市场数据"""
    print(f"  🔍 Parsing market {market_id}: {market_name}")

    # 查找该 ID 在 HTML 中的位置
    id_pattern = f'"id": "{market_id }"'
    id_match = re.search(id_pattern, html)

    if not id_match:
        print(f"    ❌ Market ID {market_id} not found in HTML")
        return None

    # 获取该市场周围的上下文（前后各 3000 个字符）
    context_start = max(0, id_match.start() - 3000)
    context_end = min(len(html), id_match.end() + 3000)
    context = html[context_start:context_end]

    # 解析价格
    prices_pattern = rf'"id": "{market_id }"[\s\S]*? "outcomePrices"[\s\S]*?: "(\[[^\]]+\])'
    prices_match = re.search(prices_pattern, context, re.DOTALL)

    outcome_prices = {}
    if prices_match:
        try:
            prices = json.loads(prices_match.group(1))
            # 简化的价格映射（根据位置）
            outcomes_map = ["Yes", "No"]
            if len(prices) >= 2:
                outcome_prices = {
                    outcomes_map[0]: float(prices[0]),
                    outcomes_map[1]: float(prices[1])
                }
        except:
            pass

    # 解析 volume
    vol_match = re.search(rf'"id": "{market_id }"[\s\S]*? "volume"[\s\S]*?: "(\d+(?:\.\d+)?)', context)
    volume = float(vol_match.group(1)) if vol_match else 0

    # 解析 liquidity
    liq_match = re.search(rf'"id": "{market_id }"[\s\S]*? "liquidity"[\s\S]*?: "(\d+(?:\.\d+)?)', context)
    liquidity = float(liq_match.group(1)) if liq_match else 0

    # 解析 endDate
    end_match = re.search(rf'"id": "{market_id }"[\s\S]*? "endDate"[\s\S]*?: "([^"]+)"', context)
    end_time = None
    if end_match:
        try:
            end_time = datetime.fromisoformat(end_match.group(1).replace("Z", "+00:00"))
        except:
            end_time = datetime.now() + timedelta(days=365)

    # 解析 question
    q_match = re.search(rf'"id": "{market_id }"[\s\S]*? "question"[\s\S]*?: "([^"]+)"', context)
    question = q_match.group(1) if q_match else "Unknown"

    return {
        "id": market_id,
        "question": question,
        "outcome_prices": outcome_prices,
        "volume": volume,
        "liquidity": liquidity,
        "end_time": end_time.isoformat() if end_time else None,
        "tags": [market_name]
    }


def fetch_and_parse_markets():
    """获取并解析所有活跃市场"""
    print("📡 Fetching and parsing REAL markets from polymarket.com...\n")

    curl_command = ["curl", "-s", "https://polymarket.com/"]

    try:
        result = subprocess.run(curl_command, capture_output=True, text=True, timeout=30)
        html = result.stdout
        print(f"✅ Fetched {len(html)} bytes\n")

    except Exception as e:
        print(f"❌ Error fetching: {e}")
        return []

    markets = []

    # 解析所有已知的活跃市场
    for market_id, market_name in ACTIVE_MARKET_IDS.items():
        market = parse_market_by_id(html, market_id, market_name)
        if market and market["volume"] > 0:
            markets.append(market)

    print(f"\n✅ Successfully parsed {len(markets)} real active markets")
    return markets


def find_arbitrage_opportunities(markets, threshold=0.02):
    """检测套利机会"""
    opportunities = []

    print(f"🔍 Analyzing {len(markets)} markets for arbitrage...")

    # 1. Surebet - 单个市场内价格和 < 1
    for market in markets:
        prices = list(market["outcome_prices"].values())
        if len(prices) >= 2:
            total = sum(prices)

            if total < (1 - threshold) and total > 0:
                profit = (1 - total) * 100
                opportunities.append({
                    "type": "surebet",
                    "market": market["question"],
                    "market_id": market["id"],
                    "expected_profit": profit,
                    "total_price": total,
                    "details": market
                })
                print(f"  🎯 Found SUREBET: {market['question'][:50]}... - {profit:.2f}% profit")

    # 2. 跨市场套利 - 相同关键词的市场
    question_keywords = {}
    for m in markets:
        words = m["question"].lower().split()
        keywords = [w for w in words if len(w) > 4]
        for kw in keywords:
            if kw not in question_keywords:
                question_keywords[kw] = []
            question_keywords[kw].append(m)

    checked_pairs = set()
    for m1 in markets:
        for m2 in markets:
            if m1["id"] >= m2["id"]:
                continue

            pair_key = f"{m1['id']}-{m2['id']}"
            if pair_key in checked_pairs:
                continue
            checked_pairs.add(pair_key)

            # 检查关键词相似度（至少 3 个相同关键词）
            m1_words = set(w for w in m1["question"].lower().split() if len(w) > 4)
            m2_words = set(w for w in m2["question"].lower().split() if len(w) > 4)

            if len(m1_words & m2_words) >= 3:
                # 检查相同结果的价格差
                for outcome in m1["outcome_prices"]:
                    if outcome in m2["outcome_prices"]:
                        price1 = m1["outcome_prices"][outcome]
                        price2 = m2["outcome_prices"][outcome]

                        if price1 > 0 and price2 > 0:
                            price_diff = abs(price1 - price2)
                            min_price = min(price1, price2)

                            if min_price > 0:
                                profit_pct = (price_diff / min_price) * 100

                                if profit_pct >= threshold:
                                    opportunities.append({
                                        "type": "cross_market",
                                        "market1": m1["question"],
                                        "market2": m2["question"],
                                        "market1_id": m1["id"],
                                        "market2_id": m2["id"],
                                        "expected_profit": profit_pct,
                                        "outcome": outcome,
                                        "price1": price1,
                                        "price2": price2
                                    })
                                    print(f"  🎯 Found CROSS-MARKET: {m1['id']} vs {m2['id']} - {profit_pct:.2f}% profit")

    return opportunities


def get_end_game_markets(markets, hours=24):
    """获取尾盘市场"""
    now = datetime.now()
    threshold = now + timedelta(hours=hours)

    end_game = [
        m for m in markets
        if m["end_time"] and datetime.fromisoformat(m["end_time"]) <= threshold
    ]

    return sorted(end_game, key=lambda m: m["end_time"])


def check_meeting_reminder():
    """检查并显示会议提醒"""
    now = datetime.now()
    hour = now.hour
    minute = now.minute

    if hour == 14 and minute < 5:  # 下午 2 点，前 5 分钟
        print("\n" + "=" * 60)
        print("⏰  会议提醒")
        print("⏰  下午 2 点有会！")
        print("=" * 60 + "\n")
        return True
    return False


def main():
    print("""
    ╔═════════════════════════════════════════════════════════════╗
    ║        Polymarket Arbitrage Monitor (REAL DATA - 2026)            ║
    ║              套利监控程序 - 2026 年真实市场数据            ║
    ╚═════════════════════════════════════════════════════════════╝
    """)

    # 检查会议提醒
    meeting_triggered = check_meeting_reminder()

    # 获取并解析真实市场
    markets = fetch_and_parse_markets()

    if not markets:
        print("❌ No active markets found")
        return

    # 显示所有解析到的市场
    print(f"\n📊 PARSED {len(markets)} REAL ACTIVE MARKETS:\n")
    print("=" * 80)

    for i, m in enumerate(markets, 1):
        time_str = ""
        if m["end_time"]:
            end = datetime.fromisoformat(m["end_time"])
            time_left = (end - datetime.now()).total_seconds()
            if time_left > 0:
                days = int(time_left // 86400)
                hours = int((time_left % 86400) // 3600)
                time_str = f" | Ends in {days}d {hours}h" if days > 0 else f" | Ends in {hours}h"

        print(f"{i}. [{m['id']}] {m['question'][:60]}")
        print(f"   Prices: {m['outcome_prices']}")
        print(f"   Volume: ${m['volume']:,.0f} | Liquidity: ${m['liquidity']:,.0f}{time_str}")
        print()

    # 检测套利机会
    print("\n🔍 SCANNING FOR ARBITRAGE OPPORTUNITIES...\n")
    opportunities = find_arbitrage_opportunities(markets)

    if opportunities:
        print(f"\n🚨 FOUND {len(opportunities)} ARBITRAGE OPPORTUNITIES!")
        print("=" * 80)

        for i, opp in enumerate(opportunities, 1):
            print(f"{i}. [{opp['type'].upper()}] {opp['expected_profit']:.2f}% profit")

            if opp['type'] == 'surebet':
                print(f"   Market: {opp['market'][:65]}")
                print(f"   Total Price: {opp['total_price']:.4f} (below 1.00 by {(1-opp['total_price'])*100:.2f}%)")
                print(f"   Strategy: Buy all outcomes - Guaranteed {opp['expected_profit']:.2f}% return")

            elif opp['type'] == 'cross_market':
                print(f"   Market 1 [{opp['market1_id']}]: {opp['market1'][:55]}")
                print(f"   Market 2 [{opp['market2_id']}]: {opp['market2'][:55]}")
                print(f"   Outcome: {opp['outcome']}")
                print(f"   Price 1: {opp['price1']:.4f} | Price 2: {opp['price2']:.4f}")
                print(f"   Diff: {abs(opp['price1'] - opp['price2']):.4f} ({(abs(opp['price1'] - opp['price2'])/opp['price1']*100):.1f}%)")
                print(f"   Strategy: Buy at {min(opp['price1'], opp['price2']):.4f}, Sell at {max(opp['price1'], opp['price2']):.4f}")

            print()

    else:
        print("✅ No arbitrage opportunities found (above 2% threshold)")

    # 尾盘市场
    end_game = get_end_game_markets(markets, hours=24)

    if end_game:
        print(f"\n⏰ {len(end_game)} MARKETS CLOSING IN 24 HOURS:")
        print("=" * 80)

        for m in end_game:
            end = datetime.fromisoformat(m["end_time"])
            time_left = (end - datetime.now()).total_seconds()

            days = int(time_left // 86400)
            hours = int((time_left % 86400) // 3600)
            mins = int((time_left % 3600) // 60)

            time_str = f"{days}d " if days > 0 else ""
            time_str += f"{hours}h " if hours > 0 or days > 0 else ""
            time_str += f"{mins}m"

            print(f"  - [{time_str} left] {m['question'][:60]}")
            print(f"    Volume: ${m['volume']:,.0f} | Liquidity: ${m['liquidity']:,.0f}")
            print(f"    Prices: {m['outcome_prices']}\n")
    else:
        print("\n✅ No markets closing in 24 hours")

    # 保存报告
    result = {
        "timestamp": datetime.now().isoformat(),
        "data_source": "polymarket.com (real-time HTML 2026)",
        "meeting_alert_triggered": meeting_triggered,
        "total_markets": len(markets),
        "arbitrage_opportunities": len(opportunities),
        "end_game_markets": len(end_game),
        "markets": markets,
        "opportunities": opportunities,
        "end_game_markets": end_game
    }

    with open("arbitrage_report.json", "w", encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\n💾 Report saved to arbitrage_report.json")
    print(f"📊 Markets: {len(markets)}")
    print(f"🚨 Arbitrage: {len(opportunities)}")
    print(f"⏰ End-Game: {len(end_game)}")


if __name__ == "__main__":
    main()
