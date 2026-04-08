#!/usr/bin/env python3
"""
直接从 Polymarket HTML 获取实时市场数据
"""

import aiohttp
import asyncio
import json
import re
from datetime import datetime
from bs4 import BeautifulSoup
from typing import Dict, List

async def fetch_live_markets():
    """从 Polymarket 主页获取实时市场数据"""

    url = "https://polymarket.com/"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            html = await resp.text()

            # 提取 embedded JSON 数据
            match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.+?)</script>', html)
            if not match:
                print("No embedded data found")
                return []

            try:
                data = json.loads(match.group(1))
            except json.JSONDecodeError as e:
                print(f"JSON decode error: {e}")
                return []

            props = data.get("props", {}).get("pageProps", {})

            # 提取 markets 数据
            dehydrated = props.get("dehydrated", {}).get("state", {}).get("data", {})
            markets_data = dehydrated.get("markets", [])

            if not markets_data:
                print("No markets found")
                return []

            # 处理市场数据
            markets = []
            for event in markets_data[:50]:  # 取前50个
                for market in event.get("markets", []):
                    # 跳过已关闭的市场
                    if market.get("closed", False):
                        continue

                    if not market.get("active", False):
                        continue

                    # 提取价格
                    outcomes = market.get("outcomes", [])
                    outcome_prices = {}

                    # 检查不同格式的价格数据
                    if isinstance(market.get("outcomePrices"), str):
                        # 字符串格式 "[\"0.47\", \"0.53\"]"
                        try:
                            outcome_prices_str = market.get("outcomePrices", "[]")
                            outcomes_list = json.loads(outcomes_list)
                            prices_list = json.loads(outcome_prices_str)
                            for outcome, price in zip(outcomes_list, prices_list):
                                outcome_prices[outcome] = float(price)
                        except:
                            pass
                    elif isinstance(market.get("outcomePrices"), list):
                        for outcome, price in zip(outcomes, market.get("outcomePrices", [])):
                            outcome_prices[outcome] = float(price) if price else 0.0
                    else:
                        # 从 tokens 或其他字段获取
                        tokens = market.get("tokens", [])
                        for token in tokens:
                            outcome = token.get("outcome", "")
                            outcome_prices[outcome] = float(token.get("price", 0))

                    # 解析结束时间
                    end_date = market.get("endDate")
                    if end_date:
                        try:
                            end_time = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
                        except:
                            end_time = datetime.now()
                    else:
                        end_time = datetime.now()

                    # 标签
                    tags = [tag.get("label", "") for tag in market.get("tags", [])]

                    market_obj = {
                        "id": str(market.get("id", "")),
                        "question": market.get("question", ""),
                        "outcome_prices": outcome_prices,
                        "liquidity": float(market.get("liquidity", 0)),
                        "volume": float(market.get("volume", 0)),
                        "end_time": end_time.isoformat(),
                        "slug": market.get("slug", ""),
                        "tags": tags
                    }
                    markets.append(market_obj)

            print(f"✅ Fetched {len(markets)} active markets")
            return markets


def find_arbitrage_opportunities(markets, threshold=0.02):
    """检测套利机会"""
    opportunities = []

    # 过滤流动性充足的市场
    viable_markets = [m for m in markets if m["liquidity"] >= 1000]

    print(f"🔍 Analyzing {len(viable_markets)} markets for arbitrage...")

    # 多结果套利检测
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
                    "details": m
                })

    # 跨市场套利 (相似问题)
    # 简化版本: 查找相似标题的市场
    question_keywords = {}
    for m in markets:
        words = m["question"].lower().split()
        words = [w for w in words if len(w) > 4]
        for word in words:
            if word not in question_keywords:
                question_keywords[word] = []
            question_keywords[word].append(m)

    opportunities.sort(key=lambda x: x["expected_profit"], reverse=True)
    return opportunities


def get_end_game_markets(markets, hours=1):
    """获取尾盘市场"""
    from datetime import timedelta
    now = datetime.now()
    threshold = now + timedelta(hours=hours)

    end_game = [
        m for m in markets
        if datetime.fromisoformat(m["end_time"]) <= threshold
    ]

    return sorted(end_game, key=lambda m: m["end_time"])


async def main():
    print("""
    ╔════════════════════════════════════════════════════╗
    ║     Polymarket Arbitrage & End-Game Monitor          ║
    ║              套利和尾盘监控程序 (实时数据)              ║
    ╚═══════════════════════════════════════════════════════╝
    """)

    markets = await fetch_live_markets()

    if not markets:
        print("❌ No active markets found")
        return

    # 显示顶部市场
    print(f"\n📈 Top 10 Active Markets by Volume:")
    print("=" * 60)
    sorted_markets = sorted(markets, key=lambda m: m["volume"], reverse=True)[:10]
    for i, m in enumerate(sorted_markets, 1):
        print(f"{i}. {m['question'][:55]}...")
        print(f"   Prices: {m['outcome_prices']}")
        print(f"   Volume: ${m['volume']:,.0f} | Liquidity: ${m['liquidity']:,.0f}\n")

    # 检测套利
    opportunities = find_arbitrage_opportunities(markets)

    if opportunities:
        print(f"\n🚨 Found {len(opportunities)} Arbitrage Opportunities!")
        print("=" * 60)
        for i, opp in enumerate(opportunities[:5], 1):
            print(f"{i}. [{opp['type'].upper()}] {opp['expected_profit']:.2f}% profit")
            print(f"   Market: {opp['market'][:60]}...")
            print(f"   Total Price: {opp['total_price']:.4f}\n")
    else:
        print("\n✅ No arbitrage opportunities found (above 2% threshold)")

    # 尾盘市场
    end_game = get_end_game_markets(markets, hours=24)
    if end_game:
        print(f"\n⏰ {len(end_game)} Markets Closing in 24 Hours:")
        print("=" * 60)
        for m in end_game[:5]:
            from datetime import timedelta
            end = datetime.fromisoformat(m["end_time"])
            time_left = (end - datetime.now()).total_seconds()
            print(f"  - [{time_left//3600:.0f}h {time_left%3600//60:.0f}m] {m['question'][:55]}...")
    else:
        print("\n✅ No markets closing in 24 hours")


if __name__ == "__main__":
    asyncio.run(main())
