#!/usr/bin/env python3
"""
简化版本 - 使用模拟数据演示套利监控功能
包含人为制造的套利机会用于演示
"""

from datetime import datetime, timedelta
import random
import json

# 模拟实时市场数据（包含套利机会）
SIMULATED_MARKETS = [
    # 多结果套利机会 - 价格和 < 1
    {
        "id": "1",
        "question": "Will Bitcoin reach $100k by end of 2026?",
        "outcome_prices": {"Yes": 0.62, "No": 0.35},
        "liquidity": 150000,
        "volume": 2500000,
        "end_time": (datetime.now() + timedelta(days=350)).isoformat(),
        "tags": ["Crypto"]
    },
    # 另一个多结果套利
    {
        "id": "2",
        "question": "Bitcoin Halving 2028 - Price Range",
        "outcome_prices": {"$60k-$70k": 0.28, "$70k-$80k": 0.25, "$80k+": 0.30},
        "liquidity": 45000,
        "volume": 800000,
        "end_time": (datetime.now() + timedelta(days=800)).isoformat(),
        "tags": ["Crypto"]
    },
    # 跨市场套利 - T1 vs JDGaming 不同平台
    {
        "id": "3",
        "question": "LPL 2026: T1 vs JDGaming Match Winner (Platform A)",
        "outcome_prices": {"T1": 0.58, "JDGaming": 0.42},
        "liquidity": 120000,
        "volume": 3200000,
        "end_time": (datetime.now() + timedelta(days=2)).isoformat(),
        "tags": ["Esports"]
    },
    {
        "id": "4",
        "question": "LPL 2026: T1 vs JDGaming Match Winner (Platform B)",
        "outcome_prices": {"T1": 0.52, "JDGaming": 0.48},
        "liquidity": 95000,
        "volume": 2800000,
        "end_time": (datetime.now() + timedelta(days=2)).isoformat(),
        "tags": ["Esports"]
    },
    # 另一个跨市场套利 - 政治选举
    {
        "id": "5",
        "question": "Presidential Election 2024 - Democratic Winner (Prediction Market A)",
        "outcome_prices": {"Yes": 0.48, "No": 0.52},
        "liquidity": 200000,
        "volume": 5000000,
        "end_time": (datetime.now() + timedelta(days=700)).isoformat(),
        "tags": ["Politics"]
    },
    {
        "id": "6",
        "question": "Presidential Election 2024 - Democratic Winner (Prediction Market B)",
        "outcome_prices": {"Yes": 0.42, "No": 0.58},
        "liquidity": 180000,
        "volume": 4500000,
        "end_time": (datetime.now() + timedelta(days=700)).isoformat(),
        "tags": ["Politics"]
    },
    # 尾盘市场 - 即将关闭
    {
        "id": "7",
        "question": "NBA: Lakers vs Celtics Game Tonight (Closing in 1 hour)",
        "outcome_prices": {"Lakers": 0.45, "Celtics": 0.55},
        "liquidity": 85000,
        "volume": 1250000,
        "end_time": (datetime.now() + timedelta(minutes=55)).isoformat(),
        "tags": ["Sports", "NBA"]
    },
    {
        "id": "8",
        "question": "Premier League: Manchester vs Liverpool (Closing in 3 hours)",
        "outcome_prices": {"Man United": 0.38, "Liverpool": 0.62, "Draw": 0.20},
        "liquidity": 150000,
        "volume": 2100000,
        "end_time": (datetime.now() + timedelta(hours=3)).isoformat(),
        "tags": ["Sports", "Football"]
    },
    {
        "id": "9",
        "question": "CS: Major Tournament Winner (Closing in 6 hours)",
        "outcome_prices": {"Team A": 0.35, "Team B": 0.40, "Team C": 0.25},
        "liquidity": 250000,
        "volume": 5800000,
        "end_time": (datetime.now() + timedelta(hours=6)).isoformat(),
        "tags": ["Esports", "CS"]
    },
    {
        "id": "10",
        "question": "Valorant: Grand Final Today (Closing in 30 minutes)",
        "outcome_prices": {"Team 1": 0.49, "Team 2": 0.51},
        "liquidity": 450000,
        "volume": 3800000,
        "end_time": (datetime.now() + timedelta(minutes=25)).isoformat(),
        "tags": ["Esports", "Valorant"]
    },
    # 高流动性市场
    {
        "id": "11",
        "question": "Will Apple release iPhone 17 in 2026?",
        "outcome_prices": {"Yes": 0.75, "No": 0.25},
        "liquidity": 750000,
        "volume": 8500000,
        "end_time": (datetime.now() + timedelta(days=250)).isoformat(),
        "tags": ["Tech"]
    },
    {
        "id": "12",
        "question": "Will Tesla reach 200k deliveries in 2026?",
        "outcome_prices": {"Yes": 0.68, "No": 0.32},
        "liquidity": 500000,
        "volume": 6200000,
        "end_time": (datetime.now() + timedelta(days=365)).isoformat(),
        "tags": ["Auto"]
    }
]


def find_arbitrage_opportunities(markets, threshold=0.02):
    """检测套利机会"""
    opportunities = []

    # 过滤流动性充足的市场
    viable_markets = [m for m in markets if m["liquidity"] >= 50000]

    print(f"🔍 Analyzing {len(viable_markets)} markets for arbitrage...")

    # 1. 多结果套利（同一市场内不同结果的价格之和 < 1）
    print("  🔹 Checking surebet opportunities...")
    for market in viable_markets:
        prices = list(market["outcome_prices"].values())
        if len(prices) >= 2:
            total = sum(prices)
            if total < (1 - threshold) and total > 0:
                profit = (1 - total) * 100
                opportunities.append({
                    "type": "surebet",
                    "market": market["question"],
                    "expected_profit": profit,
                    "total_price": total,
                    "details": market
                })

    # 2. 跨市场套利（相同事件不同市场的价差）
    print("  🔹 Checking cross-market arbitrage...")
    # 简化版本：查找相同关键词的市场
    question_keywords = {}
    for m in markets:
        words = m["question"].lower().split()
        words = [w for w in words if len(w) > 4]
        for word in words:
            if word not in question_keywords:
                question_keywords[word] = []
            question_keywords[word].append(m)

    # 检查价差
    checked_pairs = set()
    for m1 in markets:
        for m2 in markets:
            if m1["id"] >= m2["id"]:
                break

            pair_id = f"{m1['id']}-{m2['id']}"
            if pair_id in checked_pairs:
                continue
            checked_pairs.add(pair_id)

            # 检查是否相似（相同关键词）
            m1_words = set(w for w in m1["question"].lower().split() if len(w) > 4)
            m2_words = set(w for w in m2["question"].lower().split() if len(w) > 4)

            if len(m1_words & m2_words) >= 2:  # 至少2个关键词相同
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
                                        "expected_profit": profit_pct,
                                        "outcome": outcome,
                                        "price1": price1,
                                        "price2": price2,
                                        "trades": [
                                            {"market": m1["id"], "outcome": outcome, "action": "sell" if price1 > price2 else "buy", "price": price1},
                                            {"market": m2["id"], "outcome": outcome, "action": "buy" if price1 > price2 else "sell", "price": price2}
                                        ]
                                    })

    opportunities.sort(key=lambda x: x["expected_profit"], reverse=True)
    return opportunities


def get_end_game_markets(markets, hours=24):
    """获取尾盘市场"""
    now = datetime.now()
    threshold = now + timedelta(hours=hours)

    end_game = [
        m for m in markets
        if datetime.fromisoformat(m["end_time"]) <= threshold
    ]

    return sorted(end_game, key=lambda m: m["end_time"])


def main():
    print("""
    ╔════════════════════════════════════════════════╗
    ║       Polymarket Arbitrage & End-Game Monitor              ║
    ║          套利和尾盘监控程序 (演示模式)                    ║
    ╚═════════════════════════════════════════════════╝
    """)

    markets = SIMULATED_MARKETS

    # 显示顶部市场
    print(f"\n📈 Top 10 Markets by Volume:")
    print("=" * 60)
    sorted_markets = sorted(markets, key=lambda m: m["volume"], reverse=True)[:10]
    for i, m in enumerate(sorted_markets, 1):
        print(f"{i}. {m['question'][:55]}...")
        print(f"   Prices: {m['outcome_prices']}")
        print(f"   Volume: ${m['volume']:,.0f} | Liquidity: ${m['liquidity']:,.0f}")
        print(f"   Tags: {', '.join(m['tags'])}\n")

    # 检测套利
    opportunities = find_arbitrage_opportunities(markets)

    if opportunities:
        print(f"\n🚨 Found {len(opportunities)} ARBITRAGE OPPORTUNITIES!")
        print("=" * 60)
        for i, opp in enumerate(opportunities[:8], 1):
            print(f"{i}. [{opp['type'].upper()}] {opp['expected_profit']:.2f}% profit")
            if opp['type'] == 'surebet':
                print(f"   Market: {opp['market'][:60]}...")
                print(f"   Total Price: {opp['total_price']:.4f} (below 1.00 by {(1-opp['total_price'])*100:.2f}%)")
            else:
                print(f"   Market 1: {opp['market1'][:50]}...")
                print(f"   Market 2: {opp['market2'][:50]}...")
                print(f"   Outcome: {opp['outcome']}")
                print(f"   Price 1: {opp['price1']:.3f} | Price 2: {opp['price2']:.3f} | Diff: {abs(opp['price1'] - opp['price2']):.3f}")
            print()
    else:
        print(f"\n✅ No arbitrage opportunities found (above {0.02*100:.0f}% threshold)")

    # 尾盘市场
    end_game = get_end_game_markets(markets, hours=24)
    if end_game:
        print(f"\n⏰ {len(end_game)} MARKETS CLOSING IN 24 HOURS:")
        print("=" * 60)
        for m in end_game[:6]:
            end = datetime.fromisoformat(m["end_time"])
            time_left = (end - datetime.now()).total_seconds()
            print(f"  - [{time_left//3600:.0f}h {time_left%3600//60:.0f}m left] {m['question'][:55]}...")
            print(f"    Volume: ${m['volume']:,.0f} | Liquidity: ${m['liquidity']:,.0f}")
            print(f"    Current Prices: {m['outcome_prices']}\n")
    else:
        print(f"\n✅ No markets closing in 24 hours")

    # 保存结果
    result = {
        "timestamp": datetime.now().isoformat(),
        "total_markets": len(markets),
        "active_markets": len([m for m in markets if m['liquidity'] > 0]),
        "arbitrage_opportunities": len(opportunities),
        "end_game_markets": len(end_game),
        "opportunities": opportunities
    }

    with open("arbitrage_report.json", "w") as f:
        json.dump(result, f, indent=2)

    print(f"\n💾 Report saved to arbitrage_report.json")


if __name__ == "__main__":
    main()
