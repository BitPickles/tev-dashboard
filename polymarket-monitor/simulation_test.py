#!/usr/bin/env python3
"""
模拟交易测试程序
实盘监控 + 本地记账 + 自动资金评估
"""

import subprocess
import json
import re
from datetime import datetime, timedelta
from collections import defaultdict

# 测试配置
TEST_CONFIG = {
    "duration_hours": 8,  # 测试时长 8 小时
    "initial_capital": 1000,  # 初始资金 1000u
    "currency": "USDC",
    "max_position_pct": 0.20,  # 单笔最大仓位 20%
    "min_profit_threshold": 0.01,  # 最小利润阈值 1%
}

class TradingAccount:
    """模拟交易账户"""
    def __init__(self, initial_capital=1000):
        self.initial_capital = initial_capital
        self.balance = initial_capital  # 可用余额
        self.positions = []  # 持仓（已占用资金）
        self.trade_history = []  # 交易历史
        self.realized_pnl = 0  # 已实现盈亏

    def get_total_value(self):
        """计算账户总价值"""
        return self.balance + self.positions_value()

    def positions_value(self):
        """计算持仓价值（简化为投入本金）"""
        return sum(pos['invested'] for pos in self.positions)

    def can_trade(self, amount):
        """检查是否有足够资金"""
        available = self.balance
        return available >= amount

    def execute_trade(self, trade_opportunity, amount):
        """执行模拟交易"""
        if not self.can_trade(amount):
            print(f"   ⚠️  资金不足！需要 {amount}u，可用 {self.balance}u")
            return False

        # 扣除余额
        self.balance -= amount

        # 记录交易
        trade = {
            "trade_id": len(self.trade_history) + 1,
            "timestamp": datetime.now().isoformat(),
            "opportunity_type": trade_opportunity["type"],
            "market_id": trade_opportunity.get("market_id"),
            "market": trade_opportunity.get("market", ""),
            "invested": amount,
            "expected_profit_pct": trade_opportunity["expected_profit"],
            "status": "open"  # 模拟开仓
        }

        self.trade_history.append(trade)

        # 添加到持仓
        self.positions.append({
            "trade_id": trade["trade_id"],
            "invested": amount,
            "opportunity": trade_opportunity
        })

        return True

    def close_position(self, trade_id, actual_profit_pct=0):
        """平仓"""
        for i, pos in enumerate(self.positions):
            if pos["trade_id"] == trade_id:
                invested = pos["invested"]
                expected = pos["opportunity"]["expected_profit"]

                # 计算实际盈亏
                actual_profit = invested * (actual_profit_pct / 100)
                self.realized_pnl += actual_profit
                self.balance += (invested + actual_profit)

                # 从持仓中移除
                self.positions.pop(i)

                # 更新交易历史
                for trade in self.trade_history:
                    if trade["trade_id"] == trade_id:
                        trade["status"] = "closed"
                        trade["actual_profit_pct"] = actual_profit_pct
                        trade["actual_profit"] = actual_profit
                        trade["closed_at"] = datetime.now().isoformat()
                        break

                return {
                    "success": True,
                    "invested": invested,
                    "expected_profit": expected,
                    "actual_profit": actual_profit
                }

        return {"success": False, "error": "Position not found"}


class OpportunityEvaluator:
    """套利机会评估器"""
    def __init__(self):
        self.risk_levels = {
            "low": {"max_position": 0.3, "description": "低风险 - 小仓位"},
            "medium": {"max_position": 0.2, "description": "中风险 - 中等仓位"},
            "high": {"max_position": 0.15, "description": "高风险 - 小仓位"},
        }

    def evaluate_opportunity(self, opportunity, account):
        """
        评估套利机会并推荐投入金额
        """
        # 基础风险评估
        profit = opportunity["expected_profit"]
        liquidity = opportunity.get("liquidity", 0)

        # 风险分级
        if profit < 0.5:
            risk_level = "high"
        elif profit < 2:
            risk_level = "medium"
        else:
            risk_level = "low"

        risk_config = self.risk_levels[risk_level]
        max_position = account.initial_capital * risk_config["max_position"]

        # 考虑风险后调整投入金额
        # 高利润可以用更多资金，低利润用更少资金
        risk_adjusted_amount = min(max_position, account.balance * 0.5)

        # 流动性调整（高流动性更安全）
        liquidity_multiplier = 1.0
        if liquidity > 10000:
            liquidity_multiplier = 1.2
        elif liquidity > 100000:
            liquidity_multiplier = 1.5

        final_amount = risk_adjusted_amount * liquidity_multiplier

        # 不超过可用余额
        final_amount = min(final_amount, account.balance)

        # 最小交易金额
        final_amount = max(final_amount, 10)  # 最少 10u

        return {
            "risk_level": risk_level,
            "risk_description": risk_config["description"],
            "recommended_amount": final_amount,
            "position_pct": (final_amount / account.initial_capital) * 100,
            "liquidity_multiplier": liquidity_multiplier
        }


class SimulationMonitor:
    """模拟交易监控器"""
    def __init__(self):
        self.account = TradingAccount(TEST_CONFIG["initial_capital"])
        self.evaluator = OpportunityEvaluator()

        self.detected_opportunities = []
        self.executed_trades = []
        self.start_time = None
        self.end_time = None

    def fetch_markets(self):
        """获取市场数据"""
        result = subprocess.run(['curl', '-s', 'https://polymarket.com/'],
                              capture_output=True, text=True, timeout=30)
        html = result.stdout

        # 解析市场
        market_pattern = r'\{"id":"(\d+)".*?"question":"([^"]+)".*?"outcomePrices":(\[[^\]]+\]).*?"liquidity":"(\d+(?:\.\d+)?)"'
        matches = re.findall(market_pattern, html, re.DOTALL)

        markets = []
        for match in matches:
            market_id, question, prices_str, liquidity = match
            try:
                prices = [float(p) for p in json.loads(prices_str)]
                if len(prices) >= 2:
                    outcome_prices = {f"Outcome{i+1}": p for i, p in enumerate(prices)}
                    markets.append({
                        "id": market_id,
                        "question": question,
                        "outcome_prices": outcome_prices,
                        "liquidity": float(liquidity)
                    })
            except:
                pass

        return markets

    def detect_surebets(self, markets, threshold=0.98):
        """检测 Surebet 机会"""
        surebets = []
        for market in markets:
            prices = list(market["outcome_prices"].values())
            if len(prices) >= 2:
                total = sum(prices)
                # 考虑交易成本后仍有利润
                if total < threshold and total > 0.90:
                    profit = (1 - total) * 100
                    if market["liquidity"] >= 1000:  # 流动性要求
                        surebets.append({
                            "type": "surebet",
                            "market_id": market["id"],
                            "market": market["question"],
                            "expected_profit": profit,
                            "liquidity": market["liquidity"],
                            "total_price": total
                        })
        return surebets

    def detect_high_liquidity_arbitrage(self, markets):
        """检测高流动性套利"""
        high_liq = [m for m in markets if m["liquidity"] > 100000]
        opportunities = []

        for market in high_liq[:20]:  # 只分析 Top 20
            prices = list(market["outcome_prices"].values())
            if len(prices) >= 2:
                spread = abs(prices[0] - prices[1])
                if spread > 0.03:  # 价差 > 3%
                    opportunities.append({
                        "type": "high_liquidity_spread",
                        "market_id": market["id"],
                        "market": market["question"],
                        "expected_profit": spread * 100,
                        "liquidity": market["liquidity"],
                        "spread": spread
                    })
        return opportunities

    def detect_price_anomalies(self, markets, change_threshold=0.20):
        """检测价格异常"""
        # 简化：检测价差特别大的市场
        anomalies = []

        for market in markets[:100]:
            prices = list(market["outcome_prices"].values())
            if len(prices) >= 2:
                spread = abs(prices[0] - prices[1])
                if spread > 0.1:  # 价差 > 10%
                    anomalies.append({
                        "type": "price_spike",
                        "market_id": market["id"],
                        "market": market["question"],
                        "expected_profit": spread * 100,
                        "liquidity": market["liquidity"],
                        "spread": spread
                    })
        return anomalies

    def evaluate_and_trade(self, opportunities):
        """评估机会并执行模拟交易"""
        print(f"\n💼 评估 {len(opportunities)} 个机会...")

        # 按利润排序
        opportunities.sort(key=lambda x: x["expected_profit"], reverse=True)

        # 取前 10 个机会
        top_opportunities = opportunities[:10]

        print(f"   分析 Top {len(top_opportunities)} 个机会")

        for opp in top_opportunities:
            # 评估风险和推荐金额
            evaluation = self.evaluator.evaluate_opportunity(opp, self.account)

            # 检查是否可以交易
            if evaluation["recommended_amount"] > self.account.balance:
                print(f"\n   ⏭️  跳过 {opp['type']}: 资金不足")
                print(f"      需要: {evaluation['recommended_amount']:.0f}u")
                print(f"      可用: {self.account.balance:.0f}u")
                continue

            # 执行模拟交易
            print(f"\n   💰 执行模拟交易:")
            print(f"      市场: {opp['market'][:40]}...")
            print(f"      类型: {opp['type']}")
            print(f"      预期利润: {opp['expected_profit']:.2f}%")
            print(f"      风险: {evaluation['risk_level']} ({evaluation['risk_description']})")
            print(f"      投入: {evaluation['recommended_amount']:.0f}u ({evaluation['position_pct']:.1f}%)")

            success = self.account.execute_trade(opp, evaluation["recommended_amount"])

            if success:
                self.executed_trades.append({
                    "opportunity": opp,
                    "evaluation": evaluation
                })
            else:
                print(f"      ❌ 交易失败")

    def run_test(self):
        """运行完整测试"""
        self.start_time = datetime.now()
        self.end_time = self.start_time + timedelta(hours=TEST_CONFIG["duration_hours"])

        print("""
    ╔════════════════════════════════════════════════════════════╗
    ║       模拟交易测试实盘监控                              ║
    ║      📊 8小时持续监控 | 💰 1000u 模拟资金          ║
    ║      📋 本地记账 | 🎯 自动资金评估                    ║
    ╚═════════════════════════════════════════════════════════════╝
    """)

        print(f"⏰ 开始时间: {self.start_time.strftime('%H:%M:%S')}")
        print(f"⏰ 结束时间: {self.end_time.strftime('%H:%M:%S')}")
        print(f"💰 初始资金: {self.account.initial_capital}u\n")

        iteration = 0
        check_interval = 300  # 每 5 分钟检查一次

        try:
            while datetime.now() < self.end_time:
                iteration += 1
                now = datetime.now()
                remaining = (self.end_time - now).total_seconds()

                print(f"\n{'='*70}")
                print(f"📊 检测周期 #{iteration} - {now.strftime('%H:%M:%S')}")
                print(f"⏳ 剩余时间: {remaining/60:.1f} 分钟")
                print(f"{'='*70}\n")

                # 1. 获取市场数据
                print("📡 获取市场数据...")
                markets = self.fetch_markets()
                print(f"✅ 解析到 {len(markets)} 个市场")

                # 2. 检测套利机会
                print("\n🔍 检测套利机会...")

                # Surebet
                surebets = self.detect_surebets(markets)
                print(f"   Surebet: {len(surebets)} 个")

                # 高流动性价差
                high_liq = self.detect_high_liquidity_arbitrage(markets)
                print(f"   高流动性价差: {len(high_liq)} 个")

                # 价格异常
                anomalies = self.detect_price_anomalies(markets)
                print(f"   价格异常: {len(anomalies)} 个")

                all_opportunities = surebets + high_liq + anomalies

                if all_opportunities:
                    print(f"\n✅ 发现 {len(all_opportunities)} 个套利机会")

                    # 按利润排序
                    all_opportunities.sort(key=lambda x: x["expected_profit"], reverse=True)

                    print(f"🎯 最高利润: {all_opportunities[0]['expected_profit']:.2f}%")

                    # 3. 评估并执行交易
                    self.evaluate_and_trade(all_opportunities)

                    # 显示当前账户状态
                    print(f"\n💼 账户状态:")
                    print(f"   余额: {self.account.balance:.0f}u")
                    print(f"   持仓价值: {self.account.positions_value():.0f}u")
                    print(f"   总价值: {self.account.get_total_value():.0f}u")
                    print(f"   已盈亏: {self.account.realized_pnl:+.0f}u")

                    # 显示持仓列表
                    if self.account.positions:
                        print(f"\n📋 当前持仓:")
                        for i, pos in enumerate(self.account.positions[:5], 1):
                            print(f"   {i}. {pos['opportunity']['market'][:30]}...")
                            print(f"      投入: {pos['invested']:.0f}u")
                            print(f"      预期: {pos['opportunity']['expected_profit']:.1f}%")

                else:
                    print("❌ 未发现套利机会")

                # 4. 保存机会
                self.detected_opportunities.extend(all_opportunities)

                # 等待下次检查
                print(f"\n⏳ 等待 {check_interval} 秒后下次检查...")
                import time
                time.sleep(min(check_interval, remaining))

            # 最后一次检查
            print(f"\n⚠️  测试结束！准备生成报告...")

        except KeyboardInterrupt:
            print("\n\n⚠️  测试被手动停止")
            self.generate_report()
            return

        # 时间到，生成报告
        print(f"\n⏰ 测试时间结束！")
        self.generate_report()

    def generate_report(self):
        """生成最终报告"""
        now = datetime.now()

        # 统计
        total_opportunities = len(self.detected_opportunities)
        total_trades = len(self.executed_trades)

        # 按类型统计
        opp_by_type = defaultdict(int)
        for opp in self.detected_opportunities:
            opp_by_type[opp["type"]] += 1

        # 盈亏统计
        realized_pnl = self.account.realized_pnl
        account_value = self.account.get_total_value()
        total_return = (account_value / self.account.initial_capital - 1) * 100

        print("\n" + "=" * 70)
        print("📊 模拟交易测试报告")
        print("=" * 70)

        print(f"\n🕐 测试时间:")
        print(f"   开始: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   结束: {now.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   时长: {(now - self.start_time).total_seconds() / 3600:.1f} 小时")

        print(f"\n💰 资金统计:")
        print(f"   初始: {self.account.initial_capital}u")
        print(f"   余额: {self.account.balance:.0f}u")
        print(f"   持仓: {self.account.positions_value():.0f}u")
        print(f"   总价值: {account_value:.0f}u")
        print(f"   已盈亏: {realized_pnl:+.0f}u ({realized_pnl/self.account.initial_capital*100:+.1f}%)")
        print(f"   总回报: {total_return:+.1f}%")

        print(f"\n📊 套利机会统计:")
        print(f"   总发现: {total_opportunities} 个")
        print(f"   类型分布:")
        for opp_type, count in sorted(opp_by_type.items(), key=lambda x: x[1], reverse=True):
            print(f"      {opp_type}: {count} 个")

        print(f"\n💼 交易统计:")
        print(f"   执行交易: {total_trades} 笔")
        print(f"   投入总额: {sum(t['evaluation']['recommended_amount'] for t in self.executed_trades):.0f}u")

        if self.executed_trades:
            invested = sum(t['evaluation']['recommended_amount'] for t in self.executed_trades)
            print(f"   占用率: {invested/self.account.initial_capital*100:.1f}%")

        print(f"\n🎯 Top 10 套利机会:")
        print("-" * 70)
        sorted_opps = sorted(self.detected_opportunities, key=lambda x: x["expected_profit"], reverse=True)
        for i, opp in enumerate(sorted_opps[:10], 1):
            print(f"{i}. [{opp['type']}] {opp['expected_profit']:.2f}% 利润")
            print(f"   市场: {opp['market'][:50]}")
            print(f"   流动性: {opp.get('liquidity', 0):,.0f}u")
            if opp.get('total_price'):
                print(f"   价格和: {opp['total_price']:.4f}")

        # 保存报告到文件
        report = {
            "test_config": TEST_CONFIG,
            "test_period": {
                "start": self.start_time.isoformat(),
                "end": now.isoformat(),
                "duration_hours": (now - self.start_time).total_seconds() / 3600
            },
            "capital": {
                "initial": self.account.initial_capital,
                "final_balance": self.account.balance,
                "positions_value": self.account.positions_value(),
                "total_value": account_value,
                "realized_pnl": realized_pnl,
                "total_return_pct": total_return
            },
            "opportunities": {
                "total": total_opportunities,
                "by_type": dict(opp_by_type),
                "top_10": sorted(self.detected_opportunities, key=lambda x: x["expected_profit"], reverse=True)[:10]
            },
            "trades": {
                "total": total_trades,
                "details": self.executed_trades
            }
        }

        with open("simulation_test_report.json", "w", encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"\n💾 报告已保存到 simulation_test_report.json")


def main():
    """主函数"""
    print("""
    ╔════════════════════════════════════════════════════════════╗
    ║       Polymarket 模拟交易测试                              ║
    ║      📊 实盘监控 | 💰 本地记账 | 🎯 自动评估          ║
    ╚═════════════════════════════════════════════════════════════╝
    """)

    monitor = SimulationMonitor()

    # 询问是否立即开始
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--now":
        print("🚀 立即开始测试...\n")
        monitor.run_test()
    else:
        print("\n⏰ 测试将 8 小时后开始")
        print("   模拟资金: 1000u")
        print("   模式: 本地记账，不实际下单\n")

        import time
        start_time = datetime.now()
        target_time = start_time + timedelta(hours=8)

        print(f"\n开始时间: {start_time.strftime('%H:%M:%S')}")
        print(f"目标时间: {target_time.strftime('%H:%M:%S')}")

        # 倒计时等待
        while datetime.now() < target_time:
            remaining = (target_time - datetime.now()).total_seconds()
            hours = int(remaining // 3600)
            minutes = int((remaining % 3600) // 60)
            secs = int(remaining % 60)

            print(f"\r⏳ 倒计时: {hours:02d}:{minutes:02d}:{secs:02d}", end="", flush=True)
            time.sleep(1)

        print("\n\n🚀 时间到！开始测试...\n")
        monitor.run_test()


if __name__ == "__main__":
    main()
