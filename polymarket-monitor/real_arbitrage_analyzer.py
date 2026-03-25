#!/usr/bin/env python3
"""
修正的套利检测模块
过滤掉不可能事件，只保留真正的套利机会
"""
import subprocess
import re
import json
from datetime import datetime

def analyze_polymarket_real_arbitrage():
    """分析 Polymarket 真正的套利机会"""
    print("""
╔════════════════════════════════════════════════════════════╗
║       Polymarket 真实套利分析                           ║
║      🔍 过滤异常事件 | 🎯 专注真正机会                ║
╚═════════════════════════════════════════════════════════════╝
""")

    # 获取市场数据
    print("📡 获取市场数据...")
    result = subprocess.run(['curl', '-s', 'https://polymarket.com/'],
                              capture_output=True, text=True, timeout=30)
    html = result.stdout
    print(f"✅ 获取到 {len(html)} 字节")

    # 解析市场
    market_pattern = r'\{"id":"(\d+)".*?"question":"([^"]+)".*?"outcomePrices":(\[[^\]]+\]).*?"liquidity":"(\d+(?:\.\d+)?)"'
    matches = re.findall(market_pattern, html, re.DOTALL)

    print(f"✅ 解析到 {len(matches)} 个市场\n")

    # 真正的套利检测
    print("=" * 70)
    print("🎯 检测策略")
    print("=" * 70)
    print("1. Surebet: 价格和 < 0.98（考虑 2% 交易费）")
    print("2. 跨市场: 相同事件的价差（3-15%）")
    print("3. 过滤: 排除利润 > 50%（异常事件）")

    real_opportunities = []

    for m in matches[:300]:  # 分析前 300 个市场
        market_id = m[0]
        question = m[1]
        prices_str = m[2]
        liquidity = float(m[3])

        try:
            prices = [float(p) for p in json.loads(prices_str)]

            if len(prices) >= 2:
                # 策略 1: Surebet
                total = sum(prices)
                if total < 0.98 and total > 0.90:  # 合理范围
                    profit = (1 - total) * 100
                    if liquidity >= 1000:  # 流动性要求
                        real_opportunities.append({
                            "type": "surebet",
                            "market_id": market_id,
                            "market": question[:60],
                            "total_price": total,
                            "expected_profit": profit,
                            "liquidity": liquidity,
                            "prices": prices
                        })

                # 策略 2: 跨市场套利（简化版）
                # 只检测明显的价差（3-15%）
                if len(prices) == 2:
                    spread = abs(prices[0] - prices[1])
                    if 0.03 <= spread <= 0.15:  # 3-15%
                        if liquidity >= 5000:  # 流动性要求
                            real_opportunities.append({
                                "type": "cross_market",
                                "market_id": market_id,
                                "market": question[:60],
                                "expected_profit": spread * 100,
                                "liquidity": liquidity,
                                "prices": prices,
                                "spread": spread
                            })

        except:
            pass

    # 按利润排序
    real_opportunities.sort(key=lambda x: x["expected_profit"], reverse=True)

    # 显示结果
    print(f"\n✅ 检测到 {len(real_opportunities)} 个真实套利机会\n")

    if real_opportunities:
        print("🚀 Top 10 真实套利机会:")
        print("-" * 70)

        for i, opp in enumerate(real_opportunities[:10], 1):
            print(f"{i}. [{opp['type']}] {opp['expected_profit']:.2f}% 利润")
            print(f"   市场: {opp['market']}")
            print(f"   流动性: ${opp['liquidity']:,.0f}")
            print(f"   价格: {opp['prices']}")
            print(f"   {'价差' if opp['type'] == 'cross_market' else '价格和'}: {opp.get('spread', opp.get('total_price', 0)):.4f}")
            print()

    else:
        print("❌ 未检测到真实的套利机会")
        print("   这可能表示市场效率高，没有明显的套利空间")

    # 保存结果
    report = {
        "timestamp": datetime.now().isoformat(),
        "total_markets_analyzed": len(matches),
        "real_opportunities_count": len(real_opportunities),
        "opportunities": real_opportunities[:20]
    }

    with open("real_arbitrage_report.json", "w", encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\n💾 报告已保存: real_arbitrage_report.json")

    return report


if __name__ == "__main__":
    analyze_polymarket_real_arbitrage()
