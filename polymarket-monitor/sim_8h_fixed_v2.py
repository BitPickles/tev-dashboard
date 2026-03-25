#!/usr/bin/env python3
"""
8 小时持续模拟交易测试（修复版）
修复套利检测过滤逻辑
"""

import subprocess
import re
import json
import time
import signal
import sys
from datetime import datetime, timedelta
from collections import defaultdict

# 测试配置
TEST_CONFIG = {
    "duration_hours": 8,
    "initial_capital": 1000,
    "check_interval_minutes": 5,
    "arbitrage": {
        "surebet_threshold": 0.99,
        "cross_market_min_spread": 0.03,  # 恢复到 3%
        "cross_market_max_spread": 0.20,  # 提高到 20%
        "min_liquidity": 5000,
        # 修复：移除 max_profit_threshold
        # 改为过滤不可能事件的价格阈值
        "min_impossible_price": 0.01,  # 价格 < 1% 认为不可能事件
        "max_impossible_price": 0.99   # 价格 > 99% 认为不可能事件
    },
    "risk_management": {
        "high_profit_max_position": 0.15,
        "medium_profit_max_position": 0.20,
        "low_profit_max_position": 0.25,
        "min_trade_amount": 10,
        "max_trade_per_cycle": 5
    }
}

# 全局变量
running = True

def signal_handler(signum, frame):
    global running
    print("\n\n⚠️  收到中断信号，准备退出...")
    running = False

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def is_impossible_event(prices):
    """检查是否为不可能事件"""
    if len(prices) < 2:
        return False
    
    min_price = min(prices)
    max_price = max(prices)
    
    # 如果价格极其偏斜（如 [0.0005, 0.9995]），认为是极端事件
    if min_price < TEST_CONFIG["arbitrage"]["min_impossible_price"]:
        return True
    
    if max_price > TEST_CONFIG["arbitrage"]["max_impossible_price"]:
        return True
    
    # 价格偏斜度过大
    spread = max_price - min_price
    if spread > 0.95:  # 偏斜 > 95%
        return True
    
    return False


class TradingAccount:
    """模拟交易账户"""
    def __init__(self, initial_capital=1000):
        self.initial_capital = initial_capital
        self.balance = initial_capital
        self.positions = []
        self.trade_history = []
        self.realized_pnl = 0

    def get_total_value(self):
        return self.balance + sum(pos['invested'] for pos in self.positions)

    def execute_trade(self, opportunity, amount):
        if amount > self.balance:
            return False, "Insufficient funds"

        self.balance -= amount

        trade = {
            "trade_id": len(self.trade_history) + 1,
            "timestamp": datetime.now().isoformat(),
            "opportunity_type": opportunity["type"],
            "market_id": opportunity["market_id"],
            "market": opportunity["market"],
            "invested": amount,
            "expected_profit_pct": opportunity["expected_profit"],
            "status": "open"
        }

        self.trade_history.append(trade)
        self.positions.append({
            "trade_id": trade["trade_id"],
            "invested": amount,
            "opportunity": opportunity
        })

        return True, "Trade executed"


def fetch_and_parse_markets():
    """获取并解析市场数据"""
    try:
        result = subprocess.run(['curl', '-s', 'https://polymarket.com/'],
                              capture_output=True, text=True, timeout=30)
        html = result.stdout

        market_pattern = r'\{"id":"(\d+)".*?"question":"([^"]+)".*?"outcomePrices":(\[[^\]]+\]).*?"liquidity":"(\d+(?:\.\d+)?)\"'
        matches = re.findall(market_pattern, html, re.DOTALL)

        markets = []
        for match in matches:
            try:
                prices_str = match[2]
                prices = json.loads(prices_str)

                if len(prices) >= 2:
                    outcome_prices = {f"Outcome{i+1}": float(p) for i, p in enumerate(prices)}
                    markets.append({
                        "id": match[0],
                        "question": match[1],
                        "outcome_prices": outcome_prices,
                        "liquidity": float(match[3])
                    })
            except:
                pass

        return markets, len(html)

    except Exception as e:
        print(f"❌ Error fetching markets: {e}")
        return [], 0


def detect_arbitrage_opportunities(markets, config):
    """检测套利机会（修复过滤逻辑）"""
    opportunities = []

    # 1. Surebet 检测（过滤不可能事件）
    for market in markets[:300]:
        prices = list(market["outcome_prices"].values())
        liquidity = market["liquidity"]

        try:
            # 过滤不可能事件
            if is_impossible_event(prices):
                continue

            if len(prices) >= 2:
                total = sum(prices)

                if total < config["arbitrage"]["surebet_threshold"] and total > 0.90:
                    profit = (1 - total) * 100

                    if liquidity >= config["arbitrage"]["min_liquidity"]:
                        opportunities.append({
                            "type": "surebet",
                            "market_id": market["id"],
                            "market": market["question"],
                            "expected_profit": profit,
                            "liquidity": liquidity,
                            "total_price": total,
                            "prices": prices
                        })

        except:
            pass

    # 2. 跨市场套利检测（简化版）
    keyword_markets = defaultdict(list)

    for market in markets[:200]:
        question = market["question"].lower()
        words = [w for w in question.split() if len(w) > 4]

        for word in words:
            keyword_markets[word].append(market)

    for keyword, related_markets in keyword_markets.items():
        if len(related_markets) >= 2:
            for i, m1 in enumerate(related_markets):
                for m2 in related_markets[i+1:]:
                    try:
                        prices1 = list(m1["outcome_prices"].values())
                        prices2 = list(m2["outcome_prices"].values())

                        # 过滤不可能事件
                        if is_impossible_event(prices1) or is_impossible_event(prices2):
                            continue

                        if len(prices1) >= 2 and len(prices2) >= 2:
                            spread = abs(prices1[0] - prices2[0])

                            if (config["arbitrage"]["cross_market_min_spread"] <= spread <=
                                config["arbitrage"]["cross_market_max_spread"]):

                                profit = spread * 100
                                liquidity = m1["liquidity"] + m2["liquidity"]

                                if liquidity >= config["arbitrage"]["min_liquidity"] * 2:
                                    opportunities.append({
                                        "type": "cross_market",
                                        "market_id": m1["id"],
                                        "market": m1["question"][:60],
                                        "expected_profit": profit,
                                        "liquidity": liquidity,
                                        "spread": spread
                                    })

                    except:
                        pass

    opportunities.sort(key=lambda x: x["expected_profit"], reverse=True)
    return opportunities


def evaluate_opportunity(opportunity, account, config):
    """评估套利机会并推荐投入金额"""
    profit = opportunity["expected_profit"]
    liquidity = opportunity.get("liquidity", 0)

    # 风险分级（修复：3-15% 为中等风险）
    if profit > 15:
        risk_level = "high"
        risk_pct = 0.15
    elif profit >= 5:
        risk_level = "medium"
        risk_pct = 0.20
    else:
        risk_level = "low"
        risk_pct = 0.25

    risk_desc = {
        "high": "High profit - Small position (15%+)",
        "medium": "Medium profit - Medium position (5-15%)",
        "low": "Low profit - Larger position (<5%)"
    }

    # 基础投入
    base_amount = account.initial_capital * risk_pct

    # 流动性调整
    liquidity_multiplier = 1.0
    if liquidity > 100000:
        liquidity_multiplier = 1.5
    elif liquidity > 50000:
        liquidity_multiplier = 1.3
    elif liquidity > 20000:
        liquidity_multiplier = 1.2

    # 最终推荐金额
    recommended = base_amount * liquidity_multiplier
    recommended = min(recommended, account.balance * 0.5)
    recommended = max(recommended, config["risk_management"]["min_trade_amount"])

    return {
        "risk_level": risk_level,
        "risk_description": risk_desc[risk_level],
        "recommended_amount": recommended,
        "position_pct": (recommended / account.initial_capital) * 100,
        "liquidity_multiplier": liquidity_multiplier
    }


def run_8h_simulation():
    """运行 8 小时模拟测试"""
    account = TradingAccount(TEST_CONFIG["initial_capital"])
    start_time = datetime.now()
    end_time = start_time + timedelta(hours=TEST_CONFIG["duration_hours"])
    check_interval = TEST_CONFIG["check_interval_minutes"] * 60

    print("""
╔══════════════════════════════════════════════════════════╗
║       Polymarket 8 小时模拟交易测试（修复版）        ║
║      📊 实盘监控 | 💰 1000u 资金 | 📋 本地记账         ║
║      🛠️ 修复：正确的套利过滤逻辑                     ║
╚═══════════════════════════════════════════════════════════╝
""")

    print(f"⏰ 开始时间: {start_time.strftime('%H:%M:%S')}")
    print(f"⏰ 结束时间: {end_time.strftime('%H:%M:%S')}")
    print(f"💰 初始资金: {account.initial_capital}u")
    print(f"📊 检测间隔: {TEST_CONFIG['check_interval_minutes']} 分钟")
    print(f"🛠️ 修复: 不可能事件过滤已启用\n")

    cycle_count = 0
    all_opportunities = []

    try:
        while running and datetime.now() < end_time:
            cycle_count += 1
            now = datetime.now()
            remaining = (end_time - now).total_seconds()

            print(f"\n{'='*70}")
            print(f"📊 监控周期 #{cycle_count} - {now.strftime('%H:%M:%S')}")
            print(f"⏳ 剩余时间: {remaining/3600:.1f} 小时 ({remaining/60:.0f} 分钟)")
            print(f"{'='*70}\n")

            # 步骤 1: 获取市场数据
            print("📡 步骤 1/4: 获取市场数据...")
            markets, html_size = fetch_and_parse_markets()

            if not markets:
                print("❌ 无法获取市场数据，30 秒后重试...")
                time.sleep(30)
                continue

            print(f"✅ 获取到 {len(markets)} 个市场 ({html_size:,} 字节)")

            # 步骤 2: 检测套利机会（修复版）
            print("\n🔍 步骤 2/4: 检测套利机会（修复版）...")
            print("   策略:")
            print("   1. Surebet: 价格和 < 0.99")
            print("   2. 跨市场: 价差 3-20%")
            print("   3. 过滤: 排除价格偏斜 > 95% 的不可能事件\n")

            opportunities = detect_arbitrage_opportunities(markets, TEST_CONFIG)

            print(f"✅ 发现 {len(opportunities)} 个套利机会")

            # 保存机会
            all_opportunities.extend(opportunities)

            if opportunities:
                print(f"\n🚀 Top 5 机会:")
                print("-" * 70)
                for i, opp in enumerate(opportunities[:5], 1):
                    print(f"{i}. [{opp['type']}] {opp['expected_profit']:.2f}% 利润")
                    print(f"   市场: {opp['market'][:50]}")
                    print(f"   流动性: ${opp['liquidity']:,.0f}")
                    print()

                # 步骤 3: 评估并执行交易
                print("\n💼 步骤 3/4: 评估并执行模拟交易...")
                trades_this_cycle = 0

                for opp in opportunities[:5]:
                    if trades_this_cycle >= TEST_CONFIG["risk_management"]["max_trade_per_cycle"]:
                        print(f"\n   ⏭️  本周期已达到最大交易数 ({TEST_CONFIG['risk_management']['max_trade_per_cycle']})")
                        break

                    evaluation = evaluate_opportunity(opp, account, TEST_CONFIG)

                    print(f"\n   💰 评估机会:")
                    print(f"      类型: {opp['type']}")
                    print(f"      利润: {opp['expected_profit']:.2f}%")
                    print(f"      风险: {evaluation['risk_level']} ({evaluation['risk_description']})")
                    print(f"      推荐投入: {evaluation['recommended_amount']:.1f}u ({evaluation['position_pct']:.1f}%)")

                    # 执行交易
                    success, msg = account.execute_trade(opp, evaluation["recommended_amount"])

                    if success:
                        trades_this_cycle += 1
                        print(f"      ✅ 已执行: {evaluation['recommended_amount']:.1f}u")
                    else:
                        print(f"      ❌ 执行失败: {msg}")

            else:
                print("❌ 本次检测未发现套利机会")

            # 步骤 4: 显示账户状态
            print("\n📋 步骤 4/4: 账户状态")
            print("-" * 70)
            print(f"   余额: {account.balance:.1f}u")
            print(f"   持仓: {len(account.positions)}")
            print(f"   持仓价值: {sum(pos['invested'] for pos in account.positions):.1f}u")
            print(f"   总价值: {account.get_total_value():.1f}u")
            print(f"   已盈亏: {account.realized_pnl:+.1f}u")

            # 保存周期报告
            cycle_report = {
                "cycle": cycle_count,
                "timestamp": now.isoformat(),
                "account": {
                    "balance": account.balance,
                    "positions": len(account.positions),
                    "total_value": account.get_total_value(),
                    "realized_pnl": account.realized_pnl,
                    "trade_count": len(account.trade_history)
                },
                "opportunities": {
                    "found": len(opportunities),
                    "top_3": opportunities[:3]
                }
            }

            with open("cycle_report.json", "w", encoding='utf-8') as f:
                json.dump(cycle_report, f, indent=2, ensure_ascii=False)

            print(f"\n💾 周期报告已更新: cycle_report.json")

            # 等待下次检查
            print(f"\n⏳ 等待 {TEST_CONFIG['check_interval_minutes']} 分钟后下次检查...")

            time_to_wait = min(check_interval, remaining)

            # 显示倒计时
            for i in range(60, 0, -1):
                time.sleep(1)
                if i % 10 == 0:
                    mins_left = int(time_to_wait / 60)
                    secs_left = int(time_to_wait % 60)
                    print(f"\r⏰ {i:2d}秒/60s | 剩余: {mins_left:02d}:{secs_left:02d}", end="", flush=True)

            time.sleep(time_to_wait - 60)

        # 测试结束
        print(f"\n\n⏰ 测试时间到！")
        print(f"   运行周期: {cycle_count}")
        print(f"   开始: {start_time.strftime('%H:%M:%S')}")
        print(f"   结束: {datetime.now().strftime('%H:%M:%S')}")
        print(f"   实际时长: {(datetime.now() - start_time).total_seconds() / 3600:.2f} 小时")

        # 生成最终报告
        generate_final_report(account, all_opportunities, cycle_count, start_time)

    except KeyboardInterrupt:
        print("\n\n⚠️  测试被手动停止")
        generate_final_report(account, all_opportunities, cycle_count, start_time, interrupted=True)
        return

    except Exception as e:
        print(f"\n\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        return


def generate_final_report(account, all_opportunities, total_cycles, start_time, interrupted=False):
    """生成最终测试报告"""
    end_time = datetime.now()

    opp_by_type = defaultdict(int)
    for opp in all_opportunities:
        opp_by_type[opp["type"]] += 1

    total_invested = sum(t["invested"] for t in account.trade_history)
    final_value = account.get_total_value()
    total_return = (final_value / account.initial_capital - 1) * 100

    report = {
        "test_summary": {
            "start": start_time.isoformat(),
            "end": end_time.isoformat(),
            "duration_hours": (end_time - start_time).total_seconds() / 3600,
            "interrupted": interrupted,
            "total_cycles": total_cycles,
            "fix_applied": "修复：不可能事件过滤已启用"
        },
        "financial_summary": {
            "initial_capital": account.initial_capital,
            "final_balance": account.balance,
            "positions": len(account.positions),
            "positions_value": sum(pos['invested'] for pos in account.positions),
            "total_value": final_value,
            "realized_pnl": account.realized_pnl,
            "total_invested": total_invested,
            "total_return_pct": total_return,
            "win_rate": "N/A (simulated)"
        },
        "opportunities": {
            "total": len(all_opportunities),
            "by_type": dict(opp_by_type),
            "top_20": sorted(all_opportunities, key=lambda x: x["expected_profit"], reverse=True)[:20]
        },
        "trades": {
            "total": len(account.trade_history),
            "details": account.trade_history,
            "positions": account.positions
        },
        "config": TEST_CONFIG
    }

    with open("simulation_final_report.json", "w", encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    # 显示最终报告
    print("\n" + "=" * 70)
    print("📊 8 小时模拟测试最终报告")
    print("=" * 70)

    print(f"\n🕐 测试时间:")
    print(f"   开始: {start_time.strftime('%H:%M:%S')}")
    print(f"   结束: {end_time.strftime('%H:%M:%S')}")
    print(f"   时长: {report['test_summary']['duration_hours']:.2f} 小时")
    print(f"   中断: {'是' if interrupted else '否'}")

    print(f"\n💰 资金汇总:")
    print(f"   初始资金: {account.initial_capital}u")
    print(f"   余额: {account.balance:.1f}u")
    print(f"   持仓: {sum(pos['invested'] for pos in account.positions):.1f}u")
    print(f"   总价值: {final_value:.1f}u")
    print(f"   已盈亏: {account.realized_pnl:+.1f}u")
    print(f"   总回报: {total_return:+.1f}%")
    print(f"   总投入: {total_invested:.1f}u")

    print(f"\n📊 机会统计:")
    print(f"   总发现: {len(all_opportunities)} 个")
    print(f"   类型分布:")
    for opp_type, count in sorted(opp_by_type.items(), key=lambda x: x[1], reverse=True):
        print(f"      {opp_type}: {count} 个")

    print(f"\n💼 交易统计:")
    print(f"   总交易数: {len(account.trade_history)} 笔")

    if account.trade_history:
        print(f"\n   交易明细 (前 10 笔):")
        print("-" * 70)
        for i, t in enumerate(account.trade_history[:10], 1):
            print(f"   {i}. [{t['opportunity_type']}] {t['invested']:.1f}u")
            print(f"      市场: {t['market'][:50]}")
            print(f"      预期利润: {t['expected_profit_pct']:.1f}%")

    if account.positions:
        print(f"\n   未平持仓: {len(account.positions)} 笔")
        print(f"   总价值: {sum(pos['invested'] for pos in account.positions):.1f}u")

    print(f"\n🎯 Top 10 套利机会:")
    print("-" * 70)
    top_10 = sorted(all_opportunities, key=lambda x: x["expected_profit"], reverse=True)[:10]
    for i, opp in enumerate(top_10, 1):
        print(f"{i}. [{opp['type']}] {opp['expected_profit']:.2f}% 利润")
        print(f"   市场: {opp['market'][:50]}")
        print(f"   流动性: ${opp.get('liquidity', 0):,.0f}")

    print(f"\n💾 报告已保存:")
    print(f"   simulation_final_report.json (完整报告)")
    print(f"   cycle_report.json (最后一次周期)")


if __name__ == "__main__":
    run_8h_simulation()
