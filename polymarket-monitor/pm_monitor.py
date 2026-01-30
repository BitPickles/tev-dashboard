#!/usr/bin/env python3
"""
Polymarket 三级策略监控程序
专注于：
P0: 已确定事件 - 几乎100%确定，等待结算
P1: 高确定性分散 - >=98%确定性，分散投资
P2: 尾盘狙击 - >=95%确定性，6小时内结束
"""

import subprocess
import json
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
from dataclasses import dataclass
import time

from config_manager import get_config_manager
from logger import setup_logger
from notifier import TelegramNotifier
from pm_strategy import StrategyEngine, StrategyConfig

logger = setup_logger("pm_monitor")


@dataclass
class MarketOpportunity:
    """市场机会"""
    market_id: str
    question: str
    opportunity_type: str  # endgame, high_liquidity, extreme_price, price_move
    prices: Dict[str, float]
    liquidity: float
    volume: float
    hours_left: float
    score: float  # 综合评分
    reason: str


def fetch_markets(limit: int = 500) -> List[Dict]:
    """获取市场数据"""
    url = f"https://gamma-api.polymarket.com/markets?limit={limit}&active=true&closed=false"

    try:
        result = subprocess.run(
            ["curl", "-s", url],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            logger.error("Curl failed")
            return []

        data = json.loads(result.stdout)
        return data

    except Exception as e:
        logger.error(f"Fetch error: {e}")
        return []


def parse_market(m: Dict) -> Optional[Dict]:
    """解析单个市场"""
    if m.get("closed") or not m.get("active"):
        return None

    try:
        prices_str = m.get("outcomePrices", "[]")
        outcomes_str = m.get("outcomes", "[]")

        prices = json.loads(prices_str) if isinstance(prices_str, str) else prices_str
        outcomes = json.loads(outcomes_str) if isinstance(outcomes_str, str) else outcomes_str

        outcome_prices = {}
        for outcome, price in zip(outcomes, prices):
            outcome_prices[outcome] = float(price)

        # 解析结束时间
        end_date = m.get("endDate")
        if end_date:
            end_time = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
        else:
            end_time = datetime.now(timezone.utc) + timedelta(days=365)

        now = datetime.now(timezone.utc)
        hours_left = (end_time - now).total_seconds() / 3600

        return {
            "id": str(m["id"]),
            "question": m["question"],
            "outcome_prices": outcome_prices,
            "liquidity": float(m.get("liquidity", 0)),
            "volume": float(m.get("volumeNum", m.get("volume", 0))),
            "end_time": end_time,
            "hours_left": hours_left,
            "slug": m.get("slug", "")
        }

    except Exception as e:
        logger.debug(f"Parse error: {e}")
        return None


def find_endgame_markets(markets: List[Dict], hours: int = 24) -> List[MarketOpportunity]:
    """找到即将结束的市场"""
    opportunities = []

    for m in markets:
        if 0 < m["hours_left"] <= hours and m["liquidity"] > 1000:
            prices = m["outcome_prices"]

            # 计算评分：越快结束 + 越高流动性 = 越高分
            time_score = max(0, (hours - m["hours_left"]) / hours) * 50
            liq_score = min(50, m["liquidity"] / 10000)
            score = time_score + liq_score

            # 找出领先结果
            if prices:
                leading = max(prices.items(), key=lambda x: x[1])
                reason = f"领先: {leading[0]} @ {leading[1]:.1%}"
            else:
                reason = "即将结束"

            opportunities.append(MarketOpportunity(
                market_id=m["id"],
                question=m["question"],
                opportunity_type="endgame",
                prices=prices,
                liquidity=m["liquidity"],
                volume=m["volume"],
                hours_left=m["hours_left"],
                score=score,
                reason=reason
            ))

    return sorted(opportunities, key=lambda x: x.hours_left)


def find_high_liquidity_opportunities(markets: List[Dict], min_liq: float = 100000) -> List[MarketOpportunity]:
    """找到高流动性市场"""
    opportunities = []

    for m in markets:
        if m["liquidity"] >= min_liq:
            prices = m["outcome_prices"]

            # 计算价差
            if len(prices) >= 2:
                values = list(prices.values())
                spread = abs(values[0] - values[1])

                # 有意义的价差（20-80%区间）
                if 0.2 < min(values) < 0.8:
                    score = m["liquidity"] / 10000 + spread * 100

                    opportunities.append(MarketOpportunity(
                        market_id=m["id"],
                        question=m["question"],
                        opportunity_type="high_liquidity",
                        prices=prices,
                        liquidity=m["liquidity"],
                        volume=m["volume"],
                        hours_left=m["hours_left"],
                        score=score,
                        reason=f"价差: {spread:.1%} | 流动性: ${m['liquidity']:,.0f}"
                    ))

    return sorted(opportunities, key=lambda x: x.liquidity, reverse=True)


def find_high_certainty_politics(markets: List[Dict], threshold: float = 0.98) -> List[MarketOpportunity]:
    """找到高确定性的政治选举市场 (>98% 胜率)"""
    opportunities = []

    # 政治相关关键词 (必须匹配)
    political_keywords = [
        "president", "presidential", "election", "nominee",
        "democratic", "republican", "senate", "house", "governor",
        "trump", "biden", "vance", "harris", "newsom", "desantis",
        "vote", "primary", "nomination", "congress", "mayor",
        "political", "party control", "gop", "democrat"
    ]

    # 排除关键词 (体育等)
    exclude_keywords = [
        "nba", "nfl", "mlb", "nhl", "super bowl", "finals",
        "mvp", "coach", "stanley cup", "world series",
        "premier league", "champions league", "ufc", "boxing",
        "tennis", "golf", "f1", "formula", "olympics",
        "grizzlies", "lakers", "celtics", "warriors", "knicks",
        "patriots", "seahawks", "chiefs", "eagles", "cowboys"
    ]

    for m in markets:
        if m["liquidity"] < 5000:
            continue

        question_lower = m["question"].lower()

        # 排除体育市场
        if any(kw in question_lower for kw in exclude_keywords):
            continue

        # 检查是否是政治相关市场
        is_political = any(kw in question_lower for kw in political_keywords)

        if not is_political:
            continue

        prices = m["outcome_prices"]

        for outcome, price in prices.items():
            # 高确定性: >98%
            if price >= threshold:
                opportunities.append(MarketOpportunity(
                    market_id=m["id"],
                    question=m["question"],
                    opportunity_type="high_certainty_politics",
                    prices=prices,
                    liquidity=m["liquidity"],
                    volume=m["volume"],
                    hours_left=m["hours_left"],
                    score=price * 100,
                    reason=f"{outcome} @ {price:.1%} 确定性"
                ))
                break  # 每个市场只记录一次

    return sorted(opportunities, key=lambda x: (x.score, x.liquidity), reverse=True)


def find_extreme_prices(markets: List[Dict], threshold: float = 0.05) -> List[MarketOpportunity]:
    """找到极端价格的市场（接近确定但仍有交易）"""
    opportunities = []

    for m in markets:
        if m["liquidity"] < 5000:
            continue

        prices = m["outcome_prices"]

        for outcome, price in prices.items():
            # 极低价格 (<5%) 但有流动性
            if price < threshold:
                # 潜在回报 = 1/price - 1
                potential_return = (1 / price - 1) * 100 if price > 0 else 0

                opportunities.append(MarketOpportunity(
                    market_id=m["id"],
                    question=m["question"],
                    opportunity_type="extreme_low",
                    prices=prices,
                    liquidity=m["liquidity"],
                    volume=m["volume"],
                    hours_left=m["hours_left"],
                    score=potential_return,
                    reason=f"{outcome} @ {price:.1%} → 潜在 {potential_return:.0f}x"
                ))

            # 极高价格 (>95%) - 可以考虑做空对手方
            elif price > (1 - threshold):
                other_price = 1 - price
                if other_price > 0:
                    potential_return = (1 / other_price - 1) * 100
                    other_outcome = [k for k in prices.keys() if k != outcome][0] if len(prices) > 1 else "No"

                    opportunities.append(MarketOpportunity(
                        market_id=m["id"],
                        question=m["question"],
                        opportunity_type="extreme_high",
                        prices=prices,
                        liquidity=m["liquidity"],
                        volume=m["volume"],
                        hours_left=m["hours_left"],
                        score=potential_return,
                        reason=f"{other_outcome} @ {other_price:.1%} → 潜在 {potential_return:.0f}x"
                    ))

    return sorted(opportunities, key=lambda x: x.score, reverse=True)


def generate_report(
    endgame: List[MarketOpportunity],
    high_liq: List[MarketOpportunity],
    politics: List[MarketOpportunity],
    strategy_result: Dict
) -> Dict:
    """生成报告"""
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "endgame_count": len(endgame),
            "high_liquidity_count": len(high_liq),
            "high_certainty_politics_count": len(politics),
            "p0_count": strategy_result["summary"]["p0_count"],
            "p1_count": strategy_result["summary"]["p1_count"],
            "p2_count": strategy_result["summary"]["p2_count"],
        },
        # 三级策略
        "strategy": {
            "status": strategy_result["status"],
            "p0": strategy_result["p0"],
            "p1": strategy_result["p1"],
            "p2": strategy_result["p2"],
            "portfolio": strategy_result["portfolio"],
            "risk_status": strategy_result["risk_status"],
            "config": strategy_result["config"]
        },
        # 原有数据 (作为补充参考)
        "endgame_markets": [
            {
                "id": o.market_id,
                "question": o.question,
                "hours_left": o.hours_left,
                "liquidity": o.liquidity,
                "prices": o.prices,
                "reason": o.reason
            }
            for o in endgame[:10]
        ],
        "high_certainty_politics": [
            {
                "id": o.market_id,
                "question": o.question,
                "liquidity": o.liquidity,
                "prices": o.prices,
                "reason": o.reason,
                "certainty": o.score
            }
            for o in politics[:20]
        ],
        "high_liquidity_markets": [
            {
                "id": o.market_id,
                "question": o.question,
                "liquidity": o.liquidity,
                "prices": o.prices,
                "reason": o.reason
            }
            for o in high_liq[:10]
        ]
    }


def main(send_telegram: bool = True):
    """
    主函数

    Args:
        send_telegram: 是否发送 Telegram 通知
    """
    print("""
    ╔════════════════════════════════════════════════════════════╗
    ║           Polymarket 三级策略监控                          ║
    ║   P0 已确定 | P1 高确定性分散 | P2 尾盘狙击                 ║
    ╚════════════════════════════════════════════════════════════╝
    """)

    config = get_config_manager().load_config()

    # 初始化 Telegram 通知器
    notifier = TelegramNotifier() if send_telegram else None

    print("📊 获取市场数据...")
    raw_markets = fetch_markets(500)

    if not raw_markets:
        print("❌ 无法获取市场数据")
        return

    # 解析市场
    markets = []
    for m in raw_markets:
        parsed = parse_market(m)
        if parsed:
            markets.append(parsed)

    print(f"✅ 获取到 {len(markets)} 个活跃市场\n")

    # 初始化策略引擎
    strategy_engine = StrategyEngine()
    strategy_result = strategy_engine.analyze_markets(markets)

    # ========== 三级策略展示 ==========
    print("=" * 70)
    print("🎯 P0 - 已确定事件 (最高优先级, $300 配额)")
    print("=" * 70)

    p0_opps = strategy_result["p0"]
    if p0_opps:
        for i, o in enumerate(p0_opps[:5], 1):
            print(f"\n{i}. {o['question'][:55]}...")
            print(f"   买入: {o['outcome']} @ {o['price']:.2%}")
            print(f"   建议: ${o['suggested_amount']:.0f} | 流动性: ${o['liquidity']:,.0f}")
    else:
        print("   暂无 P0 机会 (需要 >=99.5% 确定性)")

    print("\n" + "=" * 70)
    print("📊 P1 - 高确定性分散 (中等优先级, $500 配额)")
    print("=" * 70)

    p1_opps = strategy_result["p1"]
    if p1_opps:
        for i, o in enumerate(p1_opps[:8], 1):
            print(f"\n{i}. [{o['category']}] {o['question'][:50]}...")
            print(f"   买入: {o['outcome']} @ {o['price']:.1%}")
            print(f"   建议: ${o['suggested_amount']:.0f} | 剩余: {o['hours_left']:.0f}h")
    else:
        print("   暂无 P1 机会 (需要 >=98% 确定性, >=50k 流动性)")

    print("\n" + "=" * 70)
    print("⚡ P2 - 尾盘狙击 (低优先级, $200 配额)")
    print("=" * 70)

    p2_opps = strategy_result["p2"]
    if p2_opps:
        for i, o in enumerate(p2_opps[:5], 1):
            print(f"\n{i}. [{o['hours_left']:.1f}h 剩余] {o['question'][:45]}...")
            print(f"   买入: {o['outcome']} @ {o['price']:.1%}")
            print(f"   建议: ${o['suggested_amount']:.0f} | 流动性: ${o['liquidity']:,.0f}")
    else:
        print("   暂无 P2 机会 (需要 >=95% 确定性, <=6h 剩余)")

    # ========== 补充信息 ==========
    # 1. 尾盘市场
    print("\n" + "=" * 70)
    print("🎯 尾盘市场参考 (24小时内结束)")
    print("=" * 70)

    endgame = find_endgame_markets(markets, hours=24)

    if endgame:
        for i, o in enumerate(endgame[:5], 1):
            print(f"\n{i}. [{o.hours_left:.1f}h 剩余] {o.question[:55]}...")
            print(f"   价格: {o.prices}")
            print(f"   流动性: ${o.liquidity:,.0f} | {o.reason}")
    else:
        print("   暂无即将结束的市场")

    # 高确定性政治市场
    politics = find_high_certainty_politics(markets, threshold=0.98)

    # 高流动性市场
    high_liq = find_high_liquidity_opportunities(markets, min_liq=100000)

    # ========== 风控状态 ==========
    risk_status = strategy_result["risk_status"]
    portfolio = strategy_result["portfolio"]

    print("\n" + "=" * 70)
    print("💼 投资组合 & 风控状态")
    print("=" * 70)
    print(f"   已投资: P0 ${portfolio['p0_invested']:.0f} | P1 ${portfolio['p1_invested']:.0f} | P2 ${portfolio['p2_invested']:.0f}")
    print(f"   日盈亏: ${portfolio['daily_pnl']:.0f} (限额: ${risk_status['daily_limit']:.0f})")
    print(f"   累计盈亏: ${portfolio['cumulative_pnl']:.0f} (暂停线: ${risk_status['cumulative_limit']:.0f})")
    if risk_status["paused"]:
        print(f"   ⚠️  状态: 暂停 - {risk_status['reason']}")
    else:
        print(f"   ✅ 状态: 正常运行")

    # 生成报告
    report = generate_report(endgame, high_liq, politics, strategy_result)

    with open("pm_opportunities.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)

    print(f"\n\n💾 详细报告已保存至 pm_opportunities.json")
    print(f"📊 策略汇总: P0 {len(p0_opps)} 个 | P1 {len(p1_opps)} 个 | P2 {len(p2_opps)} 个")
    print(f"📊 参考信息: {len(endgame)} 尾盘 | {len(politics)} 高确定性政治 | {len(high_liq)} 高流动性")

    # 发送 Telegram 通知
    if notifier and notifier.enabled:
        print("\n📤 发送 Telegram 通知...")

        # 转换为字典格式
        endgame_dicts = [
            {"question": o.question, "hours_left": o.hours_left,
             "prices": o.prices, "liquidity": o.liquidity, "reason": o.reason}
            for o in endgame
        ]

        # 发送策略机会告警
        sent = False

        # P0 告警 (最高优先级)
        if p0_opps:
            notifier.send_alert(
                "P0 已确定事件",
                [{"question": o["question"], "reason": o["reason"], "liquidity": o["liquidity"]}
                 for o in p0_opps],
                alert_type="urgent"
            )
            sent = True

        # P2 尾盘告警 (时间敏感)
        if p2_opps:
            notifier.send_endgame_alert([
                {"question": o["question"], "hours_left": o["hours_left"],
                 "prices": {o["outcome"]: o["price"]}, "liquidity": o["liquidity"]}
                for o in p2_opps
            ])
            sent = True

        # 如果没有紧急告警，发送汇总
        if not sent:
            notifier.send_summary(
                len(p2_opps), len(p1_opps), len(high_liq), len(p0_opps)
            )

        print("✅ Telegram 通知已发送")
    elif notifier and not notifier.enabled:
        print("\n⚠️  Telegram 未配置，跳过通知")


def run_loop(interval_minutes: int = 5, send_telegram: bool = True):
    """
    循环运行监控

    Args:
        interval_minutes: 扫描间隔（分钟）
        send_telegram: 是否发送 Telegram 通知
    """
    print(f"""
    ╔════════════════════════════════════════════════════════════╗
    ║           Polymarket 三级策略 - 循环监控模式               ║
    ║              每 {interval_minutes} 分钟自动扫描一次                       ║
    ╚════════════════════════════════════════════════════════════╝

    按 Ctrl+C 停止监控
    """)

    run_count = 0
    while True:
        try:
            run_count += 1
            print(f"\n{'='*70}")
            print(f"第 {run_count} 次扫描 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'='*70}\n")

            main(send_telegram=send_telegram)

            print(f"\n⏰ 下次扫描: {interval_minutes} 分钟后...")
            time.sleep(interval_minutes * 60)

        except KeyboardInterrupt:
            print("\n\n👋 监控已停止")
            break
        except Exception as e:
            print(f"\n❌ 扫描出错: {e}")
            print(f"⏰ {interval_minutes} 分钟后重试...")
            time.sleep(interval_minutes * 60)


if __name__ == "__main__":
    import sys

    # 解析命令行参数
    send_tg = "--no-telegram" not in sys.argv and "-q" not in sys.argv

    if "--test-telegram" in sys.argv:
        # 测试 Telegram 连接
        notifier = TelegramNotifier()
        if notifier.test_connection():
            print("✅ Telegram 测试成功")
        else:
            print("❌ Telegram 测试失败")
    elif "--loop" in sys.argv or "-l" in sys.argv:
        # 循环监控模式
        # 解析间隔参数 --interval=5 或 -i 5
        interval = 5  # 默认5分钟
        for i, arg in enumerate(sys.argv):
            if arg.startswith("--interval="):
                interval = int(arg.split("=")[1])
            elif arg in ("-i", "--interval") and i + 1 < len(sys.argv):
                interval = int(sys.argv[i + 1])

        run_loop(interval_minutes=interval, send_telegram=send_tg)
    else:
        main(send_telegram=send_tg)
