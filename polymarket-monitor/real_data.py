#!/usr/bin/env python3
"""
Polymarket 真实数据获取器 - 最终修正版
使用正确的字段名解析 HTML
"""

import subprocess
import json
import re
from datetime import datetime, timedelta

def parse_markets_from_html(html):
    """从 HTML 中解析市场数据"""
    print("🔍 Parsing markets from HTML...")

    markets = []
    processed_ids = set()

    # 查找所有完整的市场 JSON 对象
    # 模式: "id":"xxx", "question":"xxx", "outcomePrices":[...]
    pattern = r'\{[^{}]*"id"\s*:\s*"(\d+)"[^{}]*"question"\s*:\s*"([^"]+)"[^{}]*"outcomePrices"\s*:\s*(\[[^\]]+\])'

    matches = re.finditer(pattern, html)
    print(f"📊 Found {sum(1 for _ in matches)} market patterns")

    for match in matches:
        market_id = match.group(1)
        question = match.group(2)
        prices_str = match.group(3)

        if market_id in processed_ids:
            continue
        processed_ids.add(market_id)

        # 解析价格
        try:
            prices = json.loads(prices_str)
            if len(prices) < 2:
                continue
            outcome_prices = {f"Outcome{i+1}": float(p) for i, p in enumerate(prices)}
        except json.JSONDecodeError:
            continue

        # 在 HTML 中查找对应的市场数据
        # 搜索 ID 后面的数据
        id_context = html[match.end():match.end()+5000]

        # 查找 volume (字段名: "volume")
        vol_pattern = rf'"id"\s*:\s*"{market_id}"[^{{}}]*"volume"\s*:\s*(\d+(?:\.\d+)?)'
        vol_match = re.search(vol_pattern, id_context)

        # 查找 liquidity (字段名: "liquidity")
        liq_pattern = rf'"id"\s*:\s*"{market_id}"[^{{}}]*"liquidity"\s*:\s*(\d+(?:\.\d+)?)'
        liq_match = re.search(liq_pattern, id_context)

        # 查找 endDate
        end_pattern = rf'"id"\s*:\s*"{market_id}"[^{{}}]*"endDate"\s*:\s*"([^"]+)"'
        end_match = re.search(end_pattern, id_context)

        volume = 0
        liquidity = 0
        end_time = datetime.now() + timedelta(days=365)  # 默认

        if vol_match:
            volume = float(vol_match.group(1))
        if liq_match:
            liquidity = float(liq_match.group(1))
        if end_match:
            try:
                end_time = datetime.fromisoformat(end_match.group(1).replace("Z", "+00:00"))
            except:
                pass

        # 只保留流动性充足的市场
        if liquidity < 10000:  # 至少 $10,000
            continue

        market_obj = {
            "id": market_id,
            "question": question,
            "outcome_prices": outcome_prices,
            "liquidity": liquidity,
            "volume": volume,
            "end_time": end_time.isoformat(),
            "tags": ["Unknown"]
        }
        markets.append(market_obj)

    print(f"✅ Parsed {len(markets)} viable markets")
    return markets


def fetch_real_markets():
    """使用 curl 获取真实的 Polymarket 市场数据"""
    print("📡 Fetching real-time data from polymarket.com...")

    curl_command = [
        "curl",
        "-s",
        "https://polymarket.com/"
    ]

    try:
        result = subprocess.run(curl_command, capture_output=True, text=True, timeout=30)
        html = result.stdout
        print(f"✅ Fetched {len(html)} bytes of HTML")

        return parse_markets_from_html(html)

    except Exception as e:
        print(f"❌ Error fetching data: {e}")
        return []


def find_arbitrage_opportunities(markets, threshold=0.02):
    """检测套利机会"""
    opportunities = []

    print(f"🔍 Analyzing {len(markets)} markets for arbitrage...")

    # 多结果套利（所有结果价格之和 < 1）
    for market in markets:
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

    # 跨市场套利（相同关键词的市场）
    question_keywords = {}
    for m in markets:
        words = m["question"].lower().split()
        keywords = [w for w in words if len(w) > 4]
        for kw in keywords:
            if kw not in question_keywords:
                question_keywords[kw] = []
            question_keywords[kw].append(m)

    # 检查相似市场
    checked_pairs = set()
    for m1 in markets:
        for m2 in markets:
            if m1["id"] >= m2["id"]:
                continue

            pair_key = f"{m1['id']}-{m2['id']}"
            if pair_key in checked_pairs:
                continue
            checked_pairs.add(pair_key)

            # 检查关键词相似度
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
    ╔═══════════════════════════════════════════════════╗
    ║       Polymarket Arbitrage & End-Game Monitor    ║
    ║            套利和尾盘监控程序 (真实数据)        ║
    ╚═════════════════════════════════════════════════════╝
    """)

    markets = fetch_real_markets()

    if not markets:
        print("❌ No markets found")
        return

    print(f"\n📊 Successfully parsed {len(markets)} REAL markets from polymarket.com")

    # 显示顶部市场
    print(f"\n📈 Top 10 Markets by Volume:")
    print("=" * 60)
    sorted_markets = sorted(markets, key=lambda m: m["volume"], reverse=True)[:10]
    for i, m in enumerate(sorted_markets, 1):
        print(f"{i}. {m['question'][:55]}...")
        print(f"   Prices: {m['outcome_prices']}")
        print(f"   Volume: ${m['volume']:,.0f} | Liquidity: ${m['liquidity']:,.0f}")
        print(f"   End Time: {m['end_time'][:10]}\n")

    # 检测套利
    opportunities = find_arbitrage_opportunities(markets)

    if opportunities:
        print(f"\n🚨 Found {len(opportunities)} REAL Arbitrage Opportunities!")
        print("=" * 60)
        for i, opp in enumerate(opportunities[:10], 1):
            print(f"{i}. [{opp['type'].upper()}] {opp['expected_profit']:.2f}% profit")
            if opp['type'] == 'surebet':
                print(f"   Market: {opp['market'][:60]}...")
                print(f"   Total Price: {opp['total_price']:.4f}")
                print(f"   Expected Profit: {opp['expected_profit']:.2f}%")
            else:
                print(f"   Market 1: {opp['market1'][:50]}...")
                print(f"   Market 2: {opp['market2'][:50]}...")
                print(f"   Outcome: {opp['outcome']}")
                print(f"   Price Diff: {abs(opp['price1'] - opp['price2']):.3f} ({(opp['price1']-opp['price2'])/opp['price1']*100:.1f}%)")
            print()
    else:
        print(f"\n✅ No arbitrage opportunities found (above {threshold*100:.0f}% threshold)")

    # 尾盘市场
    end_game = get_end_game_markets(markets, hours=24)
    if end_game:
        print(f"\n⏰ {len(end_game)} Markets Closing in 24 Hours:")
        print("=" * 60)
        for m in end_game[:10]:
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
        "data_source": "https://polymarket.com/ (real-time HTML)",
        "total_markets_parsed": len(markets),
        "viable_markets": len(markets),
        "arbitrage_opportunities": len(opportunities),
        "end_game_markets": len(end_game),
        "opportunities": opportunities,
        "end_game_markets": end_game
    }

    output_file = "arbitrage_report.json"
    with open(output_file, "w", encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\n💾 Report saved to {output_file}")
    print(f"📊 Total Markets Analyzed: {len(markets)}")
    print(f"🚨 Arbitrage Opportunities: {len(opportunities)}")
    print(f"⏰ Markets Closing Soon: {len(end_game)}")


if __name__ == "__main__":
    main()
