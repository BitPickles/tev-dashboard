#!/usr/bin/env python3
"""
增强的持续监控和会议提醒程序
包含：
1. 持续数据更新
2. 下午 2 点会议提醒
3. 真实市场解析
4. 增强的套利检测
"""

import subprocess
import json
import re
import time
import sys
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional

from enhanced_arbitrage import EnhancedArbitrageDetector
from config_manager import get_config_manager
from logger import get_logger, setup_logger

# 设置日志
logger = setup_logger("continuous_monitor")

# 会议提醒状态
_reminder_sent = False


def get_meeting_config():
    """获取会议配置"""
    config = get_config_manager().load_config()
    return config.monitoring.meeting_hour, config.monitoring.meeting_minute


def send_meeting_reminder() -> bool:
    """发送会议提醒"""
    global _reminder_sent

    meeting_hour, meeting_minute = get_meeting_config()
    now = datetime.now()

    # 在会议时间前 5 分钟内触发
    if now.hour == meeting_hour and 0 <= now.minute < 5 and not _reminder_sent:
        _reminder_sent = True

        print("\n" + "=" * 70)
        print("⏰  会议提醒")
        print("=" * 70)
        print(f"⚠️  注意！下午 {meeting_hour}:00 有会议！")
        print(f"   当前时间: {now.strftime('%H:%M:%S')}")
        print("=" * 70 + "\n")

        logger.info(f"会议提醒已发送，会议时间: {meeting_hour}:00")
        return True

    # 重置标记（过了会议时间 30 分钟后）
    if now.hour == meeting_hour + 1 and now.minute >= 30:
        _reminder_sent = False

    return False


def parse_markets_from_html(html: str) -> List[Dict]:
    """
    解析 HTML 中的市场数据

    Args:
        html: HTML 内容

    Returns:
        List[Dict]: 市场列表
    """
    logger.info("解析 HTML 中的市场数据...")

    markets = []

    # 使用正则表达式提取市场数据
    market_pattern = r'\{"id":"(\d+)".*?"question":"([^"]+)".*?"outcomePrices":(\[[^\]]+\]).*?"liquidity":"(\d+(?:\.\d+)?)"'

    try:
        matches = re.findall(market_pattern, html, re.DOTALL)
        logger.info(f"找到 {len(matches)} 个市场候选")

        for match in matches:
            market_id, question, prices_str, liquidity = match

            try:
                prices = json.loads(prices_str)
                if len(prices) < 2:
                    continue

                outcome_prices = {}
                for i, p in enumerate(prices):
                    outcome_prices[f"Outcome{i+1}"] = float(p)

            except (json.JSONDecodeError, ValueError) as e:
                logger.debug(f"价格解析失败: {e}")
                continue

            try:
                liquidity_float = float(liquidity)
            except ValueError:
                continue

            # 只保留有流动性的市场
            if liquidity_float < 100:
                continue

            market_obj = {
                "id": market_id,
                "question": question,
                "outcome_prices": outcome_prices,
                "liquidity": liquidity_float,
                "volume": 0,
                "end_time": (datetime.now(timezone.utc) + timedelta(days=365)).isoformat(),
                "tags": ["Real Market"]
            }
            markets.append(market_obj)

        logger.info(f"成功解析 {len(markets)} 个有效市场（流动性 >= $100）")

    except re.error as e:
        logger.error(f"正则表达式错误: {e}")

    return markets


def find_arbitrage_opportunities(
    markets: List[Dict],
    threshold: float = 0.02
) -> List[Dict]:
    """
    检测套利机会

    Args:
        markets: 市场列表
        threshold: 套利阈值

    Returns:
        List[Dict]: 套利机会列表
    """
    opportunities = []

    logger.info(f"分析 {len(markets)} 个市场的套利机会...")

    # 1. Surebet 检测
    for market in markets:
        prices = list(market.get("outcome_prices", {}).values())
        if len(prices) >= 2:
            total = sum(prices)
            if 0 < total < (1 - threshold):
                profit = (1 - total) * 100
                opportunities.append({
                    "type": "surebet",
                    "market": market["question"],
                    "market_id": market["id"],
                    "expected_profit": profit,
                    "total_price": total
                })
                logger.info(f"Surebet: {market['question'][:50]}... - {profit:.2f}%")

    # 2. 跨市场套利检测（使用关键词索引优化）
    keyword_index: Dict[str, List[Dict]] = {}
    for m in markets:
        words = m["question"].lower().split()
        keywords = [w for w in words if len(w) > 3]
        for kw in keywords:
            if kw not in keyword_index:
                keyword_index[kw] = []
            keyword_index[kw].append(m)

    # 检查相似市场
    checked_pairs = set()
    for m1 in markets:
        m1_words = set(w for w in m1["question"].lower().split() if len(w) > 3)

        for m2 in markets:
            if m1["id"] >= m2["id"]:
                continue

            pair_id = f"{m1['id']}-{m2['id']}"
            if pair_id in checked_pairs:
                continue
            checked_pairs.add(pair_id)

            m2_words = set(w for w in m2["question"].lower().split() if len(w) > 3)

            # 至少 2 个关键词相同
            if len(m1_words & m2_words) >= 2:
                for outcome in m1["outcome_prices"]:
                    if outcome in m2["outcome_prices"]:
                        price1 = m1["outcome_prices"][outcome]
                        price2 = m2["outcome_prices"][outcome]

                        if price1 > 0 and price2 > 0:
                            price_diff = abs(price1 - price2)
                            min_price = min(price1, price2)

                            if min_price > 0:
                                profit_pct = (price_diff / min_price) * 100

                                if profit_pct >= threshold * 100:
                                    opportunities.append({
                                        "type": "cross_market",
                                        "market1": m1["question"],
                                        "market2": m2["question"],
                                        "market1_id": m1["id"],
                                        "market2_id": m2["id"],
                                        "expected_profit": profit_pct,
                                        "outcome": outcome,
                                        "price1": price1,
                                        "price2": price2
                                    })

    opportunities.sort(key=lambda x: x["expected_profit"], reverse=True)
    return opportunities


def generate_report(
    markets: List[Dict],
    opportunities: List[Dict],
    enhanced_detection: Optional[Dict] = None
) -> Dict:
    """
    生成状态报告

    Args:
        markets: 市场列表
        opportunities: 套利机会列表
        enhanced_detection: 增强检测结果

    Returns:
        Dict: 报告字典
    """
    meeting_hour, _ = get_meeting_config()
    now = datetime.now()

    total_liquidity = sum(m.get("liquidity", 0) for m in markets)
    total_volume = sum(m.get("volume", 0) for m in markets)

    report = {
        "timestamp": now.isoformat(),
        "status": "running",
        "meeting_time": f"{meeting_hour}:00",
        "meeting_reminder_sent": _reminder_sent,
        "next_meeting": f"今天下午 {meeting_hour} 点",
        "current_time": now.strftime('%H:%M'),
        "data_fetch": {
            "source": "polymarket.com",
            "status": "active"
        },
        "market_analysis": {
            "total_markets": len(markets),
            "total_liquidity": total_liquidity,
            "total_volume": total_volume,
            "avg_liquidity": total_liquidity / len(markets) if markets else 0,
            "avg_volume": total_volume / len(markets) if markets else 0
        },
        "arbitrage": {
            "opportunities_found": len(opportunities),
            "top_opportunities": opportunities[:5],
            "threshold": "2%"
        },
        "enhanced_detection": enhanced_detection,
        "markets": sorted(markets, key=lambda x: x.get("liquidity", 0), reverse=True)[:10]
    }

    return report


def fetch_real_markets() -> List[Dict]:
    """
    获取真实市场数据

    Returns:
        List[Dict]: 市场列表
    """
    logger.info("从 polymarket.com 获取数据...")

    try:
        result = subprocess.run(
            ["curl", "-s", "https://polymarket.com/"],
            capture_output=True,
            text=True,
            timeout=30
        )

        html = result.stdout
        logger.info(f"获取到 {len(html)} 字节数据")

        return parse_markets_from_html(html)

    except subprocess.TimeoutExpired:
        logger.error("请求超时")
        return []
    except subprocess.SubprocessError as e:
        logger.error(f"子进程错误: {e}")
        return []
    except Exception as e:
        logger.error(f"获取数据失败: {e}")
        return []


def main():
    """主监控循环"""
    print("""
    ╔════════════════════════════════════════════════════════════╗
    ║       Polymarket 持续监控程序 (增强版)                     ║
    ║      📊 实时套利检测 | 🎯 增强检测 | ⏰ 会议提醒          ║
    ╚════════════════════════════════════════════════════════════╝
    """)

    # 加载配置
    config_manager = get_config_manager()
    config = config_manager.load_config()

    # 初始化增强检测器
    detector = EnhancedArbitrageDetector()

    # 持续监控循环
    iteration = 0
    max_iterations = config.monitoring.max_iterations

    try:
        while iteration < max_iterations:
            iteration += 1
            print(f"\n{'='*70}")
            print(f"📊 监控周期 #{iteration} - {datetime.now().strftime('%H:%M:%S')}")
            print(f"{'='*70}\n")

            # 1. 检查会议提醒
            if send_meeting_reminder():
                print("⏰ 会议提醒已发送")

            # 2. 获取市场数据
            markets = fetch_real_markets()

            if markets:
                print(f"✅ 成功解析 {len(markets)} 个真实市场")
                print(f"   总流动性: ${sum(m.get('liquidity', 0) for m in markets):,.0f}")
                print(f"   总交易量: ${sum(m.get('volume', 0) for m in markets):,.0f}\n")

                # 3. 基础套利检测
                opportunities = find_arbitrage_opportunities(markets)

                if opportunities:
                    print(f"🚨 发现 {len(opportunities)} 个基础套利机会！")
                    print(f"   最高利润: {opportunities[0]['expected_profit']:.2f}%")
                else:
                    print(f"✅ 未发现基础套利机会（阈值: 2%）")

                # 4. 增强检测
                print("\n🎯 运行增强检测...")
                enhanced_report = detector.generate_enhanced_report(markets)

                # 显示增强检测结果
                enhanced = enhanced_report["enhanced_detection"]

                print(f"\n【增强检测结果】")

                if enhanced["surebets"]:
                    print(f"\n✅ Surebet 机会: {len(enhanced['surebets'])} 个")
                    for i, sb in enumerate(enhanced["surebets"][:5], 1):
                        print(f"   {i}. 利润 {sb['expected_profit']:.2f}% | {sb['market'][:50]}")

                if enhanced["high_liquidity_opportunities"]:
                    print(f"\n💰 高流动性机会: {len(enhanced['high_liquidity_opportunities'])} 个")
                    for i, hl in enumerate(enhanced["high_liquidity_opportunities"][:3], 1):
                        print(f"   {i}. 价差 {hl['spread_pct']:.2f}% | {hl['market'][:50]}")

                if enhanced["price_anomalies"]:
                    print(f"\n📈 价格异常: {len(enhanced['price_anomalies'])} 个")
                    for i, pa in enumerate(enhanced["price_anomalies"][:3], 1):
                        print(f"   {i}. 变化 {pa['change_pct']:.1f}% | {pa['market'][:50]}")

                if enhanced["expiring_markets"]:
                    print(f"\n⏰ 即将到期: {len(enhanced['expiring_markets'])} 个 (2小时内)")
                    for i, ex in enumerate(enhanced["expiring_markets"][:3], 1):
                        print(f"   {i}. {ex['hours_left']:.1f}h 剩余 | {ex['market'][:50]}")

                if enhanced["hot_events"]:
                    print(f"\n🔥 热门事件: {len(enhanced['hot_events'])} 个")
                    for i, he in enumerate(enhanced["hot_events"][:3], 1):
                        print(f"   {i}. {he['keyword']} | {he['market_count']} 个市场")

                print(f"\n📊 增强检测汇总:")
                print(f"   总机会数: {enhanced_report['summary']['total_opportunities']}")

                # 5. 生成报告
                report = generate_report(markets, opportunities, enhanced_report)

                # 显示顶部市场
                print(f"\n📈 流动性 Top 5:")
                print("-" * 70)
                for i, m in enumerate(report['markets'][:5], 1):
                    print(f"{i}. {m['question'][:55]}")
                    print(f"   流动性: ${m['liquidity']:,.0f}")

                # 保存报告
                try:
                    with open("monitor_report.json", "w", encoding='utf-8') as f:
                        json.dump(report, f, indent=2, ensure_ascii=False, default=str)
                    print(f"\n💾 报告已更新 (monitor_report.json)")
                except IOError as e:
                    logger.error(f"保存报告失败: {e}")

            else:
                logger.warning("无法解析市场数据，将在 30 秒后重试...")

            # 显示下次检查时间
            interval = config.monitoring.interval_seconds
            next_check = datetime.now() + timedelta(seconds=interval)

            print(f"\n⏳ 下次检查: {next_check.strftime('%H:%M:%S')} (等待 {interval} 秒)")

            time.sleep(interval)

    except KeyboardInterrupt:
        print("\n\n⚠️  监控程序已手动停止")
        logger.info("监控程序已手动停止")
        sys.exit(0)
    except Exception as e:
        logger.error(f"监控出错: {e}", exc_info=True)
        print(f"\n\n❌ 发生错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
