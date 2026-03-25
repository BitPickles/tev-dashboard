#!/usr/bin/env python3
"""
分析 Polymarket 市场的套利机会
"""
import subprocess
import re
import json
from collections import defaultdict

def analyze_polymarket_markets():
    """分析 Polymarket 市场的套利机会"""
    result = subprocess.run(['curl', '-s', 'https://polymarket.com/'],
                              capture_output=True, text=True, timeout=30)
    html = result.stdout

    print("=" * 70)
    print("Polymarket 市场套利机会分析")
    print("=" * 70)

    # 匹配所有市场
    market_pattern = r'\{"id":"(\d+)".*?"question":"([^"]+)".*?"outcomePrices":(\[[^\]]+\]).*?"liquidity":"(\d+(?:\.\d+)?)"'
    matches = re.findall(market_pattern, html, re.DOTALL)

    print(f"\n总市场数: {len(matches)}")

    # 分析 1: Surebet 机会（所有结果价格和 < 1）
    print("\n" + "-" * 70)
    print("【分析 1】Surebet 机会（包赚）")
    print("-" * 70)

    surebets = []
    for m in matches[:200]:  # 分析前 200 个
        market_id = m[0]
        question = m[1]
        prices_str = m[2]
        liquidity = float(m[3])

        try:
            prices = [float(p) for p in json.loads(prices_str)]

            if len(prices) >= 2:
                total = sum(prices)

                # 价格和明显小于 1（考虑交易费用前）
                if total < 0.98:
                    profit = (1 - total) * 100
                    surebets.append({
                        'id': market_id,
                        'question': question[:50],
                        'total': total,
                        'profit': profit,
                        'liquidity': liquidity
                    })
        except:
            pass

    print(f"发现 Surebet 机会: {len(surebets)} 个")

    if surebets:
        # 按利润排序
        surebets_sorted = sorted(surebets, key=lambda x: x['profit'], reverse=True)

        print("\n🎯 Top 10 Surebet 机会:")
        print("-" * 70)
        for i, sb in enumerate(surebets_sorted[:10], 1):
            print(f"{i}. 利润 {sb['profit']:.2f}% | 价格和 {sb['total']:.4f} | {sb['question']}...")
            print(f"   流动性: ${sb['liquidity']:,.0f}")

    # 分析 2: 价格分布统计
    print("\n" + "-" * 70)
    print("【分析 2】价格分布统计")
    print("-" * 70)

    spreads = []
    price_stats = []

    for m in matches[:100]:
        prices_str = m[2]

        try:
            prices = [float(p) for p in json.loads(prices_str)]

            if len(prices) >= 2:
                spread = abs(prices[0] - prices[1])
                avg_price = sum(prices) / len(prices)
                spreads.append(spread)
                price_stats.append(avg_price)
        except:
            pass

    if spreads:
        avg_spread = sum(spreads) / len(spreads)
        max_spread = max(spreads)
        min_spread = min(spreads)

        print(f"平均价差: {avg_spread:.4f}")
        print(f"最大价差: {max_spread:.4f}")
        print(f"最小价差: {min_spread:.4f}")

        # 计算潜在的套利机会（价差 > 5%）
        high_spread_count = sum(1 for s in spreads if s > 0.05)
        print(f"价差 > 5% 的市场: {high_spread_count} 个 ({high_spread_count/len(spreads)*100:.1f}%)")

    # 分析 3: 市场类型分类
    print("\n" + "-" * 70)
    print("【分析 3】市场类型分布")
    print("-" * 70)

    market_categories = defaultdict(int)

    for m in matches:
        question = m[1].lower()

        if 'winner' in question or 'wins' in question:
            market_categories['胜负类'] += 1
        elif ('over' in question or 'under' in question) and 'point' in question:
            market_categories['让分类'] += 1
        elif ('over' in question or 'under' in question):
            market_categories['大小球类'] += 1
        elif 'by' in question and ('jan' in question or 'feb' in question or 'dec' in question):
            market_categories['时间类'] += 1
        elif ('reaches' in question or 'above' in question):
            market_categories['数字预测类'] += 1
        else:
            market_categories['其他'] += 1

    for category, count in sorted(market_categories.items(), key=lambda x: x[1], reverse=True):
        print(f"{category}: {count} 个市场")

    # 分析 4: 高流动性市场（适合大额交易）
    print("\n" + "-" * 70)
    print("【分析 4】高流动性市场（流动性 > $100,000）")
    print("-" * 70)

    high_liquidity = []

    for m in matches:
        market_id = m[0]
        question = m[1]
        liquidity = float(m[3])
        prices_str = m[2]

        if liquidity > 100000:
            try:
                prices = [float(p) for p in json.loads(prices_str)]
                if len(prices) >= 2:
                    high_liquidity.append({
                        'id': market_id,
                        'question': question[:50],
                        'liquidity': liquidity,
                        'prices': prices
                    })
            except:
                pass

    print(f"高流动性市场数: {len(high_liquidity)}")

    if high_liquidity:
        sorted_liq = sorted(high_liquidity, key=lambda x: x['liquidity'], reverse=True)

        print("\n💰 流动性 Top 10:")
        print("-" * 70)
        for i, m in enumerate(sorted_liq[:10], 1):
            prices_str = ', '.join([f"{p:.3f}" for p in m['prices']])
            print(f"{i}. 流动性 ${m['liquidity']:,.0f} | {m['question']}...")
            print(f"   价格: [{prices_str}]")

    # 分析 5: 潜在跨市场套利（相同主题市场）
    print("\n" + "-" * 70)
    print("【分析 5】潜在跨市场套利（相同主题）")
    print("-" * 70)

    # 提取关键词
    market_keywords = {}

    for m in matches[:200]:
        market_id = m[0]
        question = m[1].lower()

        # 提取关键词（4 个字符以上）
        words = [w for w in question.split() if len(w) > 4]

        for word in words:
            if word not in market_keywords:
                market_keywords[word] = []

            prices_str = m[2]
            try:
                prices = [float(p) for p in json.loads(prices_str)]
                if len(prices) >= 2:
                    market_keywords[word].append({
                        'id': market_id,
                        'question': question,
                        'prices': prices
                    })
            except:
                pass

    # 找出有多个市场共享的关键词
    cross_market_opportunities = []

    for keyword, markets in market_keywords.items():
        if len(markets) >= 3:  # 至少 3 个市场共享同一关键词
            # 检查价格差异
            for i, m1 in enumerate(markets):
                for m2 in markets[i+1:]:
                    # 比较相同结果的价格
                    prices1 = m1['prices']
                    prices2 = m2['prices']

                    # 简化：假设第一个结果相同
                    if prices1[0] > 0 and prices2[0] > 0:
                        price_diff = abs(prices1[0] - prices2[0])
                        min_price = min(prices1[0], prices2[0])

                        if min_price > 0 and price_diff / min_price > 0.05:  # 价差 > 5%
                            cross_market_opportunities.append({
                                'keyword': keyword,
                                'market1': m1['question'][:40],
                                'market2': m2['question'][:40],
                                'price1': prices1[0],
                                'price2': prices2[0],
                                'spread_pct': price_diff / min_price * 100
                            })

    print(f"发现潜在跨市场机会: {len(cross_market_opportunities)} 个")

    if cross_market_opportunities:
        # 按价差排序
        sorted_cross = sorted(cross_market_opportunities,
                             key=lambda x: x['spread_pct'], reverse=True)

        print("\n🔀 Top 10 跨市场套利机会:")
        print("-" * 70)
        for i, opp in enumerate(sorted_cross[:10], 1):
            print(f"{i}. 关键词: {opp['keyword']}")
            print(f"   市场 1: {opp['market1']}...")
            print(f"   市场 2: {opp['market2']}...")
            print(f"   价差: {opp['price1']:.3f} vs {opp['price2']:.3f} ({opp['spread_pct']:.2f}%)")

    # 总结
    print("\n" + "=" * 70)
    print("【总结】套利机会")
    print("=" * 70)

    opportunities_summary = {
        "surebet_count": len(surebets),
        "cross_market_count": len(cross_market_opportunities),
        "high_liquidity_count": len(high_liquidity),
    }

    print(f"Surebet 机会: {opportunities_summary['surebet_count']} 个")
    print(f"跨市场套利机会: {opportunities_summary['cross_market_count']} 个")
    print(f"高流动性市场: {opportunities_summary['high_liquidity_count']} 个")

    # 建议监控重点
    print("\n🎯 建议监控重点:")
    print("-" * 70)

    if opportunities_summary['surebet_count'] > 0:
        print("1. 重点监控 Surebet 市场（包赚机会）")
        print("   - 优先级: 高")
        print("   - 风险: 低")

    if opportunities_summary['cross_market_count'] > 0:
        print("2. 监控跨市场价差（需要快速执行）")
        print("   - 优先级: 高")
        print("   - 风险: 中（价差可能快速消失）")

    if opportunities_summary['high_liquidity_count'] > 0:
        print("3. 高流动性市场适合大额交易")
        print("   - 优先级: 中")
        print("   - 风险: 低")

    # 基于分析结果，建议新增的监控功能
    print("\n" + "=" * 70)
    print("【建议新增的套利监控功能】")
    print("=" * 70)

    print("\n1. 价格异常监控")
    print("   监控价格突然变化，套利机会")

    print("\n2. 流动性波动监控")
    print("   检测流动性突然增加，可能是套利机会")

    print("\n3. 市场到期时间监控")
    print("   临近到期的市场容易出现价格偏差")

    print("\n4. 多结果市场监控")
    print("   3 个及以上结果的市场，套利空间更大")

    print("\n5. 特定事件集中监控")
    print("   对热门事件（如电竞比赛、重大新闻）集中监控")

    print("\n6. 尾盘加速监控")
    print("   市场关闭前 1 小时，每 30 秒检查一次")

    print("\n" + "=" * 70)

    return {
        'surebets': surebets,
        'cross_markets': cross_market_opportunities,
        'high_liquidity': high_liquidity,
        'market_types': market_categories,
        'summary': opportunities_summary
    }


if __name__ == "__main__":
    analyze_polymarket_markets()
