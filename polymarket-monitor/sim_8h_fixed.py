#!/usr/bin/env python3
"""
8 小时持续模拟交易测试（修正版）
确保程序持续运行，即使没有机会也继续检测
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
        "surebet_threshold": 0.99,  # 放宽到 0.99（更激进）
        "cross_market_min_spread": 0.01,  # 放宽到 1%
        "min_liquidity": 1000,
        "max_profit_threshold": 1.0  # 降低到 100%
    }
}

# 全局变量用于信号处理
running = True

def signal_handler(signum, frame):
    """处理 Ctrl+C"""
    global running
    print("\n\n⚠️  收到中断信号，准备退出...")
    running = False

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


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
        """执行模拟交易"""
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
    """检测套利机会"""
    opportunities = []

    # 1. Surebet 检测（放宽条件）
    for market in markets[:300]:
        prices = list(market["outcome_prices"].values())

        if len(prices) >= 2:
            total = sum(prices)

            # 放宽：价格和 < 0.99
            if total < config["arbitrage"]["surebet_threshold"] and total > 0.90:
                profit = (1 - total) * 100

                # 放宽：利润 < 100%，流动性 > 1000
                if profit < config["arbitrage"]["max_profit_threshold"]:
                    if market["liquidity"] >= config["arbitrage"]["min_liquidity"]:
                        opportunities.append({
                            "type": "surebet",
                            "market_id": market["id"],
                            "market": market["question"],
                            "expected_profit": profit,
                            "liquidity": market["liquidity"],
                            "total_price": total
                        })

    # 2. 价差检测（放宽条件）
    for market in markets[:200]:
        prices = list(market["outcome_prices"].values())

        if len(prices) >= 2:
            spread = abs(prices[0] - prices[1])

            # 放宽：价差 > 1%
            if spread > config["arbitrage"]["cross_market_min_spread"]:
                profit = spread * 100

                # 放宽：利润 < 100%，流动性 > 1000
                if profit < config["arbitrage"]["max_profit_threshold"]:
                    if market["liquidity"] >= config["arbitrage"]["min_liquidity"]:
                        opportunities.append({
                            "type": "price_spread",
                            "market_id": market["id"],
                            "market": market["question"],
                            "expected_profit": profit,
                            "liquidity": market["liquidity"],
                            "spread": spread
                        })

    opportunities.sort(key=lambda x: x["expected_profit"], reverse=True)
    return opportunities


def run_8h_simulation():
    """运行 8 小时模拟测试"""
    # 初始化
    account = TradingAccount(TEST_CONFIG["initial_capital"])
    start_time = datetime.now()
    end_time = start_time + timedelta(hours=TEST_CONFIG["duration_hours"])
    check_interval = TEST_CONFIG["check_interval_minutes"] * 60

    print("""
╔══════════════════════════════════════════════════════════╗
║       Polymarket 8 小时模拟交易测试                    ║
║      📊 实盘监控 | 💰 1000u 资金 | 📋 本地记账         ║
║      🔄 持续运行（即使无机会也继续检测）               ║
╚══════════════════════════════════════════════════════════╝
""")

    print(f"⏰ 开始时间: {start_time.strftime('%H:%M:%S')}")
    print(f"⏰ 结束时间: {end_time.strftime('%H:%M:%S')}")
    print(f"💰 初始资金: {account.initial_capital}u")
    print(f"📊 检测间隔: {TEST_CONFIG['check_interval_minutes']} 分钟\n")

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

            # 步骤 2: 检测套利机会
            print("\n🔍 步骤 2/4: 检测套利机会...")
            opportunities = detect_arbitrage_opportunities(markets, TEST_CONFIG)

            print(f"✅ 发现 {len(opportunities)} 个套利机会")

            # 保存所有机会
            all_opportunities.extend(opportunities)

            if opportunities:
                print(f"\n🚀 Top 5 机会:")
                print("-" * 70)
                for i, opp in enumerate(opportunities[:5], 1):
                    print(f"{i}. [{opp['type']}] {opp['expected_profit']:.2f}% 利润")
                    print(f"   市场: {opp['market'][:50]}")
                    print(f"   流动性: ${opp['liquidity']:,.0f}")
                    print()

                # 步骤 3: 评估并执行交易（简化版）
                print("\n💼 步骤 3/4: 评估并执行模拟交易...")

                for opp in opportunities[:3]:  # 只评估前 3 个
                    profit = opp["expected_profit"]
                    liquidity = opp["liquidity"]

                    # 简化风险评估
                    if profit > 20:
                        risk = "medium"
                        position_pct = 0.10
                    elif profit > 10:
                        risk = "medium"
                        position_pct = 0.15
                    else:
                        risk = "low"
                        position_pct = 0.20

                    # 流动性调整
                    liq_mult = 1.0
                    if liquidity > 50000:
                        liq_mult = 1.5
                    elif liquidity > 20000:
                        liq_mult = 1.3

                    # 推荐投入
                    recommended = account.balance * position_pct * liq_mult
                    recommended = min(recommended, account.balance * 0.5)
                    recommended = max(recommended, 10)  # 最少 10u

                    print(f"\n   评估机会 {opp['type']}:")
                    print(f"      利润: {profit:.2f}%")
                    print(f"      风险: {risk}")
                    print(f"      推荐投入: {recommended:.1f}u ({recommended/account.initial_capital*100:.1f}%)")

                    # 执行交易
                    success, msg = account.execute_trade(opp, recommended)
                    if success:
                        print(f"      ✅ 已执行: {recommended:.1f}u")
                    else:
                        print(f"      ❌ 执行失败: {msg}")

            else:
                print("❌ 本次检测未发现套利机会")
                print("   这是正常的，继续监控...")

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

            # 等待下次检查（确保持续运行）
            print(f"\n⏳ 等待 {TEST_CONFIG['check_interval_minutes']} 分钟后下次检查...")

            time_to_wait = min(check_interval, remaining)

            # 显示倒计时
            for i in range(60, 0, -1):
                time.sleep(1)
                if i % 10 == 0:
                    mins_left = int(time_to_wait / 60)
                    secs_left = int(time_to_wait % 60)
                    print(f"\r⏰ {i:2d}秒/60s | 剩余: {mins_left:02d}:{secs_left:02d}", end="", flush=True)

            time.sleep(time_to_wait - 60)  # 等待剩余时间

        # 测试结束
        print(f"\n\n⏰ 测试时间到！")
        print(f"   运行周期: {cycle_count}")
        print(f"   开始: {start_time.strftime('%H:%M:%S')}")
        print(f"   结束: {datetime.now().strftime('%H:%M:%S')}")
        print(f"   实际时长: {(datetime.now() - start_time).total_seconds() / 3600:.2f} 小时")

        # 生成最终报告
        generate_final_report(account, all_opportunities, cycle_count, start_time)

    except KeyboardInterrupt:
        print("\n\n⚠️ 测试被手动停止")
        generate_final_report(account, all_opportunities, cycle_count, start_time, interrupted=True)
        return

    except Exception as e:
        print(f"\n\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        return


def generate_final_report(account, all_opportunities, total_cycles, start_time, interrupted=False):
    """生成最终报告"""
    end_time = datetime.now()

    # 按类型统计
    opp_by_type = defaultdict(int)
    for opp in all_opportunities:
        opp_by_type[opp["type"]] += 1

    # 账户统计
    total_invested = sum(t["invested"] for t in account.trade_history)
    final_value = account.get_total_value()
    total_return = (final_value / account.initial_capital - 1) * 100

    report = {
        "test_summary": {
            "start": start_time.isoformat(),
            "end": end_time.isoformat(),
            "duration_hours": (end_time - start_time).total_seconds() / 3600,
            "interrupted": interrupted,
            "total_cycles": total_cycles
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

    # 保存完整报告
    with open("simulation_final_report.json", "w", encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    # 显示最终报告
    print("\n" + "=" * 70)
    print("📊 8 小时模拟测试最终报告")
    print("=" * 70)

    print(f"\n🕐 测试时间:")
    print(f"   开始: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   结束: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   时长: {report['test_summary']['duration_hours']:.2f} 小时")
    print(f"   中断: {'是' if interrupted else '否'}")

    print(f"\n💰 资金统计:")
    print(f"   初始: {account.initial_capital}u")
    print(f"   余额: {account.balance:.1f}u")
    print(f"   持仓: {len(account.positions)}")
    print(f"   持仓价值: {sum(pos['invested'] for pos in account.positions):.1f}u")
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
    print(f"   总交易: {len(account.trade_history)} 笔")
    print(f"   总投入: {total_invested:.1f}u")

    if account.trade_history:
        print(f"\n   交易明细 (前 10 笔):")
        print("-" * 70)
        for i, t in enumerate(account.trade_history[:10], 1):
            print(f"   {i}. [{t['opportunity_type']}] {t['invested']:.1f}u")
            print(f"      市场: {t['market'][:50]}")
            print(f"      预期利润: {t['expected_profit_pct']:.1f}%")
            print()

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
