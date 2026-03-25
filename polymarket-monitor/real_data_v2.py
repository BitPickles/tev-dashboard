#!/usr/bin/env python3
"""
Polymarket 真实数据获取器 - 修改版
包含下午 2 点会议提醒
"""

import subprocess
import json
import re
from datetime import datetime, timedelta
import time

# 上午下午 2 点的提醒
MEETING_TIME_HOUR = 14
MEETING_TIME_MINUTE = 0
REMINDER_MESSAGE = "⏰ 会议提醒：下午 2 点有会！"

def check_meeting_reminder():
    """检查是否需要发送会议提醒"""
    now = datetime.now()

    # 检查是否在下午 2 点（允许 5 分钟的窗口）
    if (now.hour == MEETING_TIME_HOUR and
        0 <= now.minute < 5):
        print(f"\n{'='*60}")
        print(REMINDER_MESSAGE)
        print(f"当前时间: {now.strftime('%H:%M:%S')}")
        print(f"{'='*60}\n")
        return True
    return False


def parse_markets_from_html(html):
    """从 HTML 中解析市场数据 - 降低流动性要求"""
    print("🔍 Parsing markets from HTML (降低流动性要求)...")

    markets = []
    processed_ids = set()

    # 查找所有符合模式的市场对象
    pattern = r'\{[^{}]*"id"\s*:\s*"(\d+)"[^{}]*"question"\s*:\s*"([^"]+)"[^{}]*"outcomePrices"\s*:\s*(\[[^\]]+\])'

    matches = re.finditer(pattern, html)
    print(f"📊 Found {sum(1 for _ in matches)} market patterns")

    for match in matches:
        market_id = match.group(1)
        question = match.group(2)
        prices_str = match.group(3)

        # 避免重复
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

        # 从 HTML 中查找对应的市场数据
        id_context = html[match.end():match.end()+5000]

        # 查找 volume
        vol_pattern = rf'"id"\s*:\s*"{market_id}"[^{{}}]*"volume"\s*:\s*(\d+(?:\.\d+)?)'
        vol_match = re.search(vol_pattern, id_context)

        # 查找 liquidity
        liq_pattern = rf'"id"\s*:\s*"{market_id}"[^{{}}]*"liquidity"\s*:\s*(\d+(?:\.\d+)?)'
        liq_match = re.search(liq_pattern, id_context)

        # 查找 endDate
        end_pattern = rf'"id"\s*:\s*"{market_id}"[^{{}}]*"endDate"\s*:\s*"([^"]+)"'
        end_match = re.search(end_pattern, id_context)

        volume = 0
        liquidity = 0
        end_time = datetime.now() + timedelta(days=365)

        if vol_match:
            volume = float(vol_match.group(1))
        if liq_match:
            liquidity = float(liq_match.group(1))
        if end_match:
            try:
                end_time = datetime.fromisoformat(end_match.group(1).replace("Z", "+00:00"))
            except:
                pass

        # 降低流动性要求到 $1,000
        if liquidity < 1000:
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

    print(f"✅ Parsed {len(markets)} viable markets (liquidity >= $1,000)")
    return markets


def fetch_real_markets():
    """使用 curl 获取真实的 Polymarket 市场数据"""
    print("📡 Fetching real-time data from polymarket.com...")

    # 同时尝试 gamma-api（之前返回过 200 OK）
    # 备用方案
    urls_to_try = [
        "https://polymarket.com/",
        "https://gamma-api.polymarket.com/markets?limit=500"
    ]

    all_markets = []

    for url in urls_to_try:
        print(f"  🌐 Trying: {url}")
        curl_command = ["curl", "-s", url]

        try:
            result = subprocess.run(curl_command, capture_output=True, text=True, timeout=30)
            content = result.stdout

            if "polymarket.com" in url:
                # 从 HTML 解析
                markets = parse_markets_from_html(content)
            else:
                # 尝试解析 JSON
                try:
                    data = json.loads(content)
                    if isinstance(data, list):
                        # 直接是市场列表
                        for m in data[:100]:
                            if isinstance(m, dict) and not m.get("closed", True):
                                all_markets.append(m)
                except:
                    markets = []

            if markets:
                all_markets.extend(markets)
                break

        except Exception as e:
            print(f"  ❌ Error: {e}")

    # 去重
    seen = set()
    unique_markets = []
    for m in all_markets:
        if m.get("id") not in seen:
            seen.add(m["id"])
            unique_markets.append(m)

    return unique_markets


def find_arbitrage_opportunities(markets, threshold=0.02):
    """检测套利机会"""
    opportunities = []

    # 不再过滤流动性，使用所有解析到的市场
    print(f"🔍 Analyzing {len(markets)} markets for arbitrage...")

    # 多结果套利
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

    # 跨市场套利（相同关键词）
    question_keywords = {}
    for m in markets:
        words = m["question"].lower().split()
        keywords = [w for w in words if len(w) > 3]
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

            # 检查关键词相似度
            m1_words = set(w for w in m1["question"].lower().split() if len(w) > 3)
            m2_words = set(w for w in m2["question"].lower().split() if len(w) > 3)

            if len(m1_words & m2_words) >= 2:
                # 检查相同结果价格差
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
    ╔═══════════════════════════════════════════════════════╗
    ║       Polymarket Arbitrage & End-Game Monitor          ║
    ║              套利和尾盘监控程序 (真实数据)               ║
    ║      ⏰ 会议提醒：下午 2 点                                ║
    ╚═══════════════════════════════════════════════════════╝
    """)

    # 检查会议提醒
    meeting_alert = check_meeting_reminder()

    markets = fetch_real_markets()

    if not markets:
        print("❌ No markets found")
        # 继续监控
        print("⏳ 继续监控中...")
        return

    print(f"\n📊 Successfully fetched {len(markets)} REAL markets from polymarket.com")

    # 检查会议提醒
    check_meeting_reminder()

    # 显示顶部市场
    print(f"\n📈 Top 10 Markets by Volume:")
    print("=" * 60)
    sorted_markets = sorted(markets, key=lambda m: m["volume"], reverse=True)[:10]
    for i, m in enumerate(sorted_markets, 1):
        print(f"{i}. {m['question'][:55]}...")
        print(f"   Prices: {m['outcome_prices']}")
        print(f"   Volume: ${m['volume']:,.0f} | Liquidity: ${m['liquidity']:,.0f}")
        print(f"   Ends: {m['end_time'][:10]}")
        print()

    # 检测套利
    opportunities = find_arbitrage_opportunities(markets)

    if opportunities:
        print(f"\n🚨 Found {len(opportunities)} REAL Arbitrage Opportunities!")
        print("=" * 60)
        for i, opp in enumerate(opportunities[:10], 1):
            print(f"{i}. [{opp['type'].upper()}] {opp['expected_profit']:.2f}% profit")
            if opp['type'] == 'surebet':
                print(f"   Market: {opp['market'][:60]}...")
                print(f"   Total Price: {opp['total_price']:.4f} (profit: {opp['expected_profit']:.2f}%)")
            else:
                print(f"   Market 1: {opp['market1'][:55]}...")
                print(f"   Market 2: {opp['market2'][:55]}...")
                print(f"   Outcome: {opp['outcome']}")
                print(f"   Price Diff: {abs(opp['price1'] - opp['price2']):.3f}")
            print()
    else:
        print(f"\n✅ No arbitrage opportunities found (above {0.02*100:.0f}% threshold)")

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
            print(f"    Prices: {m['outcome_prices']}\n")
    else:
        print(f"\n✅ No markets closing in 24 hours")

    # 保存结果
    result = {
        "timestamp": datetime.now().isoformat(),
        "meeting_alert_sent": meeting_alert,
        "data_source": "https://polymarket.com/ (real-time HTML)",
        "total_markets_parsed": len(markets),
        "viable_markets": len(markets),
        "arbitrage_opportunities": len(opportunities),
        "end_game_markets": len(end_game),
        "top_markets": sorted_markets,
        "opportunities": opportunities,
        "end_game_markets": end_game
    }

    output_file = "arbitrage_report_real.json"
    with open(output_file, "w", encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\n💾 Report saved to {output_file}")
    print(f"📊 Markets analyzed: {len(markets)}")
    print(f"🚨 Arbitrage Opportunities: {len(opportunities)}")
    print(f"⏰ End-Game Markets: {len(end_game)}")


if __name__ == "__main__":
    main()
