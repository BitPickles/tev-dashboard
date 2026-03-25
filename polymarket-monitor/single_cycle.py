#!/usr/bin/env python3
"""单周期测试：展示套利检测和模拟交易"""
import subprocess
import re
import json
import time
from datetime import datetime

print("""
╔════════════════════════════════════════════════════════════╗
║       Polymarket 模拟交易 - 单周期演示                 ║
║      📊 套利检测 | 💰 1000u 资金 | 🎯 自动评估          ║
╚═════════════════════════════════════════════════════════════╝
""")

print(f"🕐 开始时间: {datetime.now().strftime('%H:%M:%S')}")
print(f"💰 初始资金: 1000u\n")

# 1. 获取市场数据
print("=" * 70)
print("📡 步骤 1/4: 获取市场数据")
print("=" * 70)

result = subprocess.run(['curl', '-s', 'https://polymarket.com/'],
                      capture_output=True, text=True, timeout=30)
html = result.stdout

# 解析市场
market_pattern = r'\{"id":"(\d+)".*?"question":"([^"]+)".*?"outcomePrices":(\[[^\]]+\]).*?"liquidity":"(\d+(?:\.\d+)?)"'
matches = re.findall(market_pattern, html, re.DOTALL)

print(f"✅ 获取到 {len(html)} 字节 HTML")
print(f"✅ 解析到 {len(matches)} 个市场")

# 2. 检测套利机会
print("\n" + "=" * 70)
print("🔍 步骤 2/4: 检测套利机会")
print("=" * 70)

# Surebet 检测
surebets = []
for m in matches[:200]:  # 分析前 200 个
    prices_str = m[2]
    liquidity = float(m[3])
    
    try:
        prices = [float(p) for p in json.loads(prices_str)]
        if len(prices) >= 2:
            total = sum(prices)
            # 考虑交易成本后仍有利润
            if total < 0.97 and total > 0.90:
                profit = (1 - total) * 100
                if liquidity >= 1000:
                    surebets.append({
                        "type": "surebet",
                        "market_id": m[0],
                        "market": m[1][:60],
                        "expected_profit": profit,
                        "liquidity": liquidity,
                        "total_price": total
                    })
    except:
        pass

# 价格异常检测
anomalies = []
for m in matches[:100]:
    prices_str = m[2]
    liquidity = float(m[3])
    
    try:
        prices = [float(p) for p in json.loads(prices_str)]
        if len(prices) >= 2:
            spread = abs(prices[0] - prices[1])
            if spread > 0.08:  # 价差 > 8%
                anomalies.append({
                    "type": "price_spike",
                    "market_id": m[0],
                    "market": m[1][:60],
                    "expected_profit": spread * 100,
                    "liquidity": liquidity,
                    "spread": spread
                })
    except:
        pass

# 汇总机会
all_opportunities = surebets + anomalies
all_opportunities.sort(key=lambda x: x["expected_profit"], reverse=True)

print(f"✅ Surebet 机会: {len(surebets)} 个")
print(f"✅ 价格异常: {len(anomalies)} 个")
print(f"🎯 总机会: {len(all_opportunities)} 个")

if all_opportunities:
    print(f"\n🚀 Top 5 套利机会:")
    print("-" * 70)
    for i, opp in enumerate(all_opportunities[:5], 1):
        print(f"{i}. [{opp['type']}] {opp['expected_profit']:.2f}% 利润")
        print(f"   市场: {opp['market']}")
        print(f"   流动性: ${opp['liquidity']:,.0f}")

# 3. 模拟交易评估
print("\n" + "=" * 70)
print("💰 步骤 3/4: 模拟交易评估")
print("=" * 70)

account_balance = 1000.0
positions_value = 0.0
trades = []

# 自动评估每个机会
for opp in all_opportunities[:10]:  # 只评估前 10 个
    print(f"\n📊 评估机会 {len(trades) + 1}/10...")
    
    profit = opp["expected_profit"]
    liquidity = opp["liquidity"]
    
    # 风险分级
    if profit > 5:
        risk = "high"
        risk_pct = 0.15
    elif profit > 2:
        risk = "medium"
        risk_pct = 0.20
    else:
        risk = "low"
        risk_pct = 0.25
    
    # 流动性调整
    if liquidity > 100000:
        liq_mult = 1.5
    elif liquidity > 10000:
        liq_mult = 1.2
    else:
        liq_mult = 1.0
    
    # 推荐投入金额
    recommended = min(account_balance * risk_pct * liq_mult, account_balance * 0.5)
    recommended = max(recommended, 10)  # 最少 10u
    
    print(f"   类型: {opp['type']}")
    print(f"   利润: {profit:.2f}%")
    print(f"   风险: {risk}")
    print(f"   流动性倍数: {liq_mult}x")
    print(f"   推荐投入: {recommended:.1f}u")
    
    # 执行模拟交易
    if recommended <= account_balance:
        account_balance -= recommended
        positions_value += recommended
        
        trade = {
            "trade_id": len(trades) + 1,
            "opportunity": opp,
            "risk": risk,
            "invested": recommended,
            "expected_profit": profit
        }
        trades.append(trade)
        
        print(f"   ✅ 已执行: 投入 {recommended:.1f}u")
    else:
        print(f"   ⏭️  跳过: 资金不足")

# 4. 生成报告
print("\n" + "=" * 70)
print("📋 步骤 4/4: 生成报告")
print("=" * 70)

total_invested = sum(t["invested"] for t in trades)
total_expected_profit = sum(t["invested"] * t["expected_profit"] / 100 for t in trades)
final_value = account_balance + positions_value

print(f"\n💰 账户状态:")
print(f"   初始资金: 1000.0u")
print(f"   已执行交易: {len(trades)} 笔")
print(f"   总投入: {total_invested:.1f}u")
print(f"   剩余余额: {account_balance:.1f}u")
print(f"   持仓价值: {positions_value:.1f}u")
print(f"   账户总值: {final_value:.1f}u")
print(f"   预期利润: {total_expected_profit:.1f}u ({total_expected_profit/10:.1f}%)")

print(f"\n📊 交易详情:")
print("-" * 70)
for i, t in enumerate(trades[:5], 1):
    print(f"{i}. [{t['risk']}] {t['opportunity']['type']} - 投入 {t['invested']:.1f}u")
    print(f"   市场: {t['opportunity']['market'][:50]}")
    print(f"   利润: {t['expected_profit']:.2f}%")
    print()

# 保存报告
report = {
    "timestamp": datetime.now().isoformat(),
    "initial_balance": 1000.0,
    "final_balance": final_value,
    "trades_executed": len(trades),
    "total_invested": total_invested,
    "expected_profit": total_expected_profit,
    "return_pct": (final_value / 1000 - 1) * 100,
    "trades": trades
}

with open("single_cycle_report.json", "w", encoding='utf-8') as f:
    json.dump(report, f, indent=2, ensure_ascii=False)

print(f"💾 报告已保存: single_cycle_report.json")
print(f"\n✅ 单周期测试完成！")
print(f"⏰ 结束时间: {datetime.now().strftime('%H:%M:%S')}")
