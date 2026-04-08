#!/usr/bin/env python3
"""
8 小时持续模拟交易测试
实盘监控 + 本地记账 + 自动资金评估
每 5 分钟检查一次市场
"""

import subprocess
import re
import json
import time
from datetime import datetime, timedelta
from collections import defaultdict

# 测试配置
TEST_CONFIG = {
    "duration_hours": 8,
    "initial_capital": 1000,
    "currency": "USDC",
    "check_interval_minutes": 5,
    "arbitrage": {
        "surebet_threshold": 0.98,  # 价格和 < 0.98
        "cross_market_min_spread": 0.03,  # 价差 > 3%
        "cross_market_max_spread": 0.15,  # 价差 < 15%
        "min_liquidity": 5000,  # 最小流动性
        "max_profit_threshold": 0.50  # 最大利润阈值（排除异常事件）
    },
    "risk_management": {
        "high_profit_max_position": 0.15,  # 高利润（>50%）最多投入 15%
        "medium_profit_max_position": 0.20,  # 中等利润（10-50%）最多投入 20%
        "low_profit_max_position": 0.25,  # 低利润（<10%）最多投入 25%
        "min_trade_amount": 10,  # 最小交易金额
        "max_trade_per_cycle": 5  # 每个周期最多 5 笔交易
    }
}

class TradingAccount:
    """模拟交易账户"""
    def __init__(self, initial_capital=1000):
        self.initial_capital = initial_capital
        self.balance = initial_capital
        self.positions = []  # 持仓
        self.trade_history = []  # 交易历史
        self.realized_pnl = 0  # 已实现盈亏

    def get_total_value(self):
        """账户总价值"""
        return self.balance + sum(pos['invested'] for pos in self.positions)

    def can_trade(self, amount):
        """是否有足够资金"""
        return self.balance >= amount

    def execute_trade(self, opportunity, amount):
        """执行模拟交易"""
        if not self.can_trade(amount):
            return False, "Insufficient funds"

        # 扣除余额
        self.balance -= amount

        # 记录交易
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

    def close_all_positions(self, actual_profit_multiplier=0.0):
        """
        模拟平仓所有持仓
        actual_profit_multiplier: 实际利润乘数（1.0 = 按预期盈利，0.0 = 全亏）
        """
        for pos in self.positions[:]:  # 使用切片避免修改时遍历
            invested = pos["invested"]
            expected_pct = pos["opportunity"]["expected_profit"]
            expected_profit = invested * (expected_pct / 100)
            actual_profit = expected_profit * actual_profit_multiplier

            # 更新账户
            self.balance += (invested + actual_profit)
            self.realized_pnl += actual_profit

            # 更新交易历史
            for trade in self.trade_history:
                if trade["trade_id"] == pos["trade_id"]:
                    trade["status"] = "closed"
                    trade["actual_profit_pct"] = expected_pct * actual_profit_multiplier
                    trade["actual_profit"] = actual_profit
                    trade["closed_at"] = datetime.now().isoformat()
                    break

        self.positions = []
        return True


class ArbitrageDetector:
    """套利检测器"""
    def __init__(self, config):
        self.config = config
        self.risk_level_map = {
            "high": {"max_position": 0.15, "desc": "High profit - Small position"},
            "medium": {"max_position": 0.20, "desc": "Medium profit - Medium position"},
            "low": {"max_position": 0.25, "desc": "Low profit - Larger position"}
        }

    def evaluate_opportunity(self, opportunity, account):
        """
        评估套利机会并推荐投入金额
        """
        profit = opportunity["expected_profit"]
        liquidity = opportunity.get("liquidity", 0)

        # 风险分级（利润越高，风险越大）
        if profit > 50:
            risk_level = "high"
        elif profit > 10:
            risk_level = "medium"
        else:
            risk_level = "low"

        risk_config = self.risk_level_map[risk_level]

        # 基础投入
        base_amount = account.initial_capital * risk_config["max_position"]

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
        recommended = min(recommended, account.balance)
        recommended = max(recommended, self.config["risk_management"]["min_trade_amount"])

        return {
            "risk_level": risk_level,
            "risk_description": risk_config["desc"],
            "recommended_amount": recommended,
            "position_pct": (recommended / account.initial_capital) * 100,
            "liquidity_multiplier": liquidity_multiplier
        }

    def detect_opportunities(self, markets):
        """
        检测真实套利机会
        返回：Surebet + 跨市场套利
        """
        opportunities = []

        # 1. Surebet 检测
        for market in markets[:300]:  # 分析前 300 个
            prices_str = market["outcome_prices"]
            liquidity = market["liquidity"]

            try:
                prices = list(prices_str.values())

                if len(prices) >= 2:
                    total = sum(prices)

                    # Surebet 条件：价格和 < 0.98（考虑交易费）
                    if total < self.config["arbitrage"]["surebet_threshold"] and total > 0.90:
                        profit = (1 - total) * 100

                        # 排除异常（利润 > 50%）
                        if profit < self.config["arbitrage"]["max_profit_threshold"]:
                            if liquidity >= self.config["arbitrage"]["min_liquidity"]:
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
        # 检测相同主题但不同市场的价差
        keyword_markets = defaultdict(list)

        for market in markets[:200]:
            question = market["question"].lower()
            words = [w for w in question.split() if len(w) > 4]

            for word in words:
                keyword_markets[word].append(market)

        for keyword, related_markets in keyword_markets.items():
            if len(related_markets) >= 2:
                # 检查价差
                for i, m1 in enumerate(related_markets):
                    for m2 in related_markets[i+1:]:
                        try:
                            prices1 = list(m1["outcome_prices"].values())
                            prices2 = list(m2["outcome_prices"].values())

                            if len(prices1) >= 2 and len(prices2) >= 2:
                                spread = abs(prices1[0] - prices2[0])

                                # 跨市场条件：3-15% 价差
                                if (self.config["arbitrage"]["cross_market_min_spread"] <= spread <=
                                    self.config["arbitrage"]["cross_market_max_spread"]):

                                    profit = spread * 100
                                    liquidity = m1["liquidity"] + m2["liquidity"]

                                    if profit < self.config["arbitrage"]["max_profit_threshold"]:
                                        if liquidity >= self.config["arbitrage"]["min_liquidity"] * 2:
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

        # 按利润排序
        opportunities.sort(key=lambda x: x["expected_profit"], reverse=True)

        return opportunities


def fetch_and_parse_markets():
    """获取并解析市场数据"""
    try:
        result = subprocess.run(['curl', '-s', 'https://polymarket.com/'],
                              capture_output=True, text=True, timeout=30)
        html = result.stdout

        # 解析市场
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


def run_simulation():
    """运行 8 小时模拟测试"""
    # 初始化
    account = TradingAccount(TEST_CONFIG["initial_capital"])
    detector = ArbitrageDetector(TEST_CONFIG)

    start_time = datetime.now()
    end_time = start_time + timedelta(hours=TEST_CONFIG["duration_hours"])
    check_interval = TEST_CONFIG["check_interval_minutes"] * 60  # 秒

    print("""
╔════════════════════════════════════════════════════════════╗
║       Polymarket 8 小时模拟交易测试                      ║
║      📊 实盘监控 | 💰 1000u 资金 | 📋 本地记账        ║
║      🎯 真实套利检测（修正版）                        ║
╚═════════════════════════════════════════════════════════════╝
""")

    print(f"⏰ 开始时间: {start_time.strftime('%H:%M:%S')}")
    print(f"⏰ 结束时间: {end_time.strftime('%H:%M:%S')}")
    print(f"💰 初始资金: {account.initial_capital}u")
    print(f"📊 检测间隔: {TEST_CONFIG['check_interval_minutes']} 分钟")
    print(f"📝 报告文件: simulation_report.json\n")

    # 记录所有发现的套利机会
    all_opportunities = []
    cycle_count = 0

    try:
        while datetime.now() < end_time:
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
            opportunities = detector.detect_opportunities(markets)

            print(f"✅ 检测到 {len(opportunities)} 个套利机会")

            if opportunities:
                print(f"\n🚀 Top 5 机会:")
                print("-" * 70)
                for i, opp in enumerate(opportunities[:5], 1):
                    print(f"{i}. [{opp['type']}] {opp['expected_profit']:.2f}% 利润")
                    print(f"   市场: {opp['market'][:50]}")
                    print(f"   流动性: ${opp.get('liquidity', 0):,.0f}")

                # 保存机会
                all_opportunities.extend(opportunities)
            else:
                print("✅ 未发现符合条件的套利机会")

            # 步骤 3: 评估并执行交易
            print("\n💼 步骤 3/4: 评估并执行模拟交易...")
            trades_this_cycle = 0

            # 取前 5 个机会进行评估
            for opp in opportunities[:5]:
                if trades_this_cycle >= TEST_CONFIG["risk_management"]["max_trade_per_cycle"]:
                    print(f"\n   ⏭️  本周期已达到最大交易数 ({TEST_CONFIG['risk_management']['max_trade_per_cycle']})")
                    break

                # 评估机会
                evaluation = detector.evaluate_opportunity(opp, account)

                print(f"\n   💰 评估机会 {len(all_opportunities) - len(opportunities) + 1}/{len(all_opportunities)}")
                print(f"      类型: {opp['type']}")
                print(f"      利润: {opp['expected_profit']:.2f}%")
                print(f"      风险: {evaluation['risk_level']} ({evaluation['risk_description']})")
                print(f"      推荐投入: {evaluation['recommended_amount']:.1f}u ({evaluation['position_pct']:.1f}%)")

                # 执行交易
                success, message = account.execute_trade(opp, evaluation["recommended_amount"])

                if success:
                    trades_this_cycle += 1
                    print(f"      ✅ 已执行: {evaluation['recommended_amount']:.1f}u")
                else:
                    print(f"      ❌ 执行失败: {message}")

            # 步骤 4: 显示账户状态
            print("\n📋 步骤 4/4: 账户状态")
            print("-" * 70)
            print(f"   余额: {account.balance:.1f}u")
            print(f"   持仓数: {len(account.positions)}")
            print(f"   持仓价值: {sum(pos['invested'] for pos in account.positions):.1f}u")
            print(f"   总价值: {account.get_total_value():.1f}u")
            print(f"   已盈亏: {account.realized_pnl:+.1f}u")
            print(f"   已交易: {len(account.trade_history)} 笔")

            # 显示持仓列表
            if account.positions:
                print(f"\n   📦 当前持仓:")
                for i, pos in enumerate(account.positions[:5], 1):
                    print(f"      {i}. {pos['opportunity']['market'][:40]}...")
                    print(f"         投入: {pos['invested']:.1f}u | 预期: {pos['opportunity']['expected_profit']:.1f}%")

            # 保存周期报告
            save_cycle_report(cycle_count, account, opportunities, trades_this_cycle, now)

            # 等待下一次检查
            print(f"\n⏳ 等待 {TEST_CONFIG['check_interval_minutes']} 分钟后下次检查...")
            time.sleep(min(check_interval, remaining))

        # 测试结束
        print(f"\n\n⚠️  测试时间结束！")
        print(f"   总运行周期: {cycle_count}")
        print(f"   开始: {start_time.strftime('%H:%M:%S')}")
        print(f"   结束: {datetime.now().strftime('%H:%M:%S')}")
        print(f"   总耗时: {(datetime.now() - start_time).total_seconds() / 3600:.2f} 小时")

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


def save_cycle_report(cycle_num, account, opportunities, trades, now):
    """保存周期报告"""
    report = {
        "cycle": cycle_num,
        "timestamp": now.isoformat(),
        "account": {
            "balance": account.balance,
            "positions": len(account.positions),
            "total_value": account.get_total_value(),
            "realized_pnl": account.realized_pnl,
            "trade_count": len(account.trade_history)
        },
        "opportunities_found": len(opportunities),
        "trades_executed": trades,
        "opportunities_snapshot": opportunities[:10]
    }

    # 追加写入（简单实现，每次覆盖）
    with open("cycle_report.json", "w", encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)


def generate_final_report(account, all_opportunities, total_cycles, start_time, interrupted=False):
    """生成最终测试报告"""
    end_time = datetime.now()

    # 统计
    opp_by_type = defaultdict(int)
    for opp in all_opportunities:
        opp_by_type[opp["type"]] += 1

    total_invested = sum(t["invested"] for t in account.trade_history)
    final_value = account.get_total_value()
    total_return = (final_value / account.initial_capital - 1) * 100

    report = {
        "test_summary": {
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_hours": (end_time - start_time).total_seconds() / 3600,
            "interrupted": interrupted,
            "total_cycles": total_cycles
        },
        "financial_summary": {
            "initial_capital": account.initial_capital,
            "final_balance": account.balance,
            "positions_value": sum(pos['invested'] for pos in account.positions),
            "total_value": final_value,
            "realized_pnl": account.realized_pnl,
            "total_invested": total_invested,
            "total_return_pct": total_return,
            "win_rate": "N/A (simulated trades not settled)"
        },
        "opportunities": {
            "total_discovered": len(all_opportunities),
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
    with open("simulation_report.json", "w", encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    # 显示最终报告
    print("\n" + "=" * 70)
    print("📊 8 小时模拟测试最终报告")
    print("=" * 70)

    print(f"\n🕐 测试时长:")
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
    print(f"   占用率: {total_invested/account.initial_capital*100:.1f}%")

    print(f"\n📊 机会统计:")
    print(f"   总发现: {len(all_opportunities)} 个")
    print(f"   类型分布:")
    for opp_type, count in sorted(opp_by_type.items(), key=lambda x: x[1], reverse=True):
        print(f"      {opp_type}: {count} 个")

    print(f"\n💼 交易统计:")
    print(f"   总交易数: {len(account.trade_history)} 笔")

    if account.trade_history:
        invested = sum(t["invested"] for t in account.trade_history)
        print(f"   总投入: {invested:.1f}u")

        print(f"\n   交易明细:")
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
    top_opps = sorted(all_opportunities, key=lambda x: x["expected_profit"], reverse=True)[:10]
    for i, opp in enumerate(top_opps, 1):
        print(f"{i}. [{opp['type']}] {opp['expected_profit']:.2f}% 利润")
        print(f"   市场: {opp['market'][:50]}")
        print(f"   流动性: ${opp.get('liquidity', 0):,.0f}")

    print(f"\n💾 报告已保存: simulation_report.json")
    print(f"💾 周期报告: cycle_report.json")


if __name__ == "__main__":
    run_simulation()
