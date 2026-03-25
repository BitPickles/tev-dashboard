#!/usr/bin/env python3
"""
增强的套利检测模块
基于调研结果新增的监控功能
"""
import json
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from typing import Dict, List, Any, Optional

from config_manager import get_config_manager, AppConfig
from logger import get_logger

logger = get_logger("enhanced_arbitrage")


class EnhancedArbitrageDetector:
    """增强套利检测器"""

    def __init__(self, config: Optional[Dict] = None):
        """
        初始化增强套利检测器

        Args:
            config: 配置字典（可选，兼容旧接口）
        """
        # 加载配置
        app_config = get_config_manager().load_config()

        # 从配置加载阈值
        self.arbitrage_threshold = app_config.arbitrage.threshold
        self.surebet_threshold = app_config.arbitrage.surebet_threshold
        self.high_liquidity_min = app_config.arbitrage.high_liquidity_min
        self.price_anomaly_threshold = app_config.arbitrage.price_anomaly_threshold
        self.liquidity_change_threshold = app_config.arbitrage.liquidity_change_threshold

        # 从嵌套配置或默认值
        if config and "arbitrage" in config:
            arb_config = config["arbitrage"]
            self.keyword_threshold = arb_config.get("keyword_threshold", 5)
            self.min_outcomes = arb_config.get("min_outcomes", 3)
        else:
            self.keyword_threshold = 5
            self.min_outcomes = 3

        # 历史数据存储
        self.price_history: Dict[str, Dict] = {}
        self.liquidity_history: Dict[str, Dict] = {}
        self.current_markets: Dict[str, Any] = {}

        logger.info(f"增强套利检测器初始化完成，Surebet阈值: {self.surebet_threshold}")

    def detect_surebets_improved(
        self,
        markets: List[Dict],
        threshold: Optional[float] = None
    ) -> List[Dict]:
        """
        改进的 Surebet 检测

        Args:
            markets: 市场列表
            threshold: 价格和阈值（可选）

        Returns:
            List[Dict]: Surebet 机会列表
        """
        if threshold is None:
            threshold = self.surebet_threshold

        surebets = []

        for market in markets:
            prices = list(market.get("outcome_prices", {}).values())

            if len(prices) < 2:
                continue

            total = sum(prices)

            # 考虑交易费用后仍有利可图 (0.90 < 总价和 < threshold)
            if 0.90 < total < threshold:
                profit = (1 - total) * 100
                liquidity = market.get("liquidity", 0)

                if liquidity >= 1000:
                    surebets.append({
                        "type": "surebet",
                        "market_id": market.get("id"),
                        "market": market.get("question", ""),
                        "total_price": total,
                        "expected_profit": profit,
                        "liquidity": liquidity,
                        "confidence": "high" if liquidity > 10000 else "medium"
                    })

        surebets.sort(key=lambda x: x["expected_profit"], reverse=True)
        return surebets

    def detect_high_liquidity_opportunities(
        self,
        markets: List[Dict],
        min_liquidity: Optional[float] = None
    ) -> List[Dict]:
        """
        检测高流动性市场的套利机会

        Args:
            markets: 市场列表
            min_liquidity: 最小流动性阈值

        Returns:
            List[Dict]: 高流动性机会列表
        """
        if min_liquidity is None:
            min_liquidity = self.high_liquidity_min

        high_liq_markets = [
            m for m in markets
            if m.get("liquidity", 0) >= min_liquidity
        ]

        logger.info(f"发现 {len(high_liq_markets)} 个高流动性市场（> ${min_liquidity:,.0f}）")

        opportunities = []

        for market in high_liq_markets[:20]:
            prices = list(market.get("outcome_prices", {}).values())

            if len(prices) >= 2:
                spread = abs(prices[0] - prices[1])

                if spread > 0.02:
                    opportunities.append({
                        "type": "high_liquidity_spread",
                        "market_id": market.get("id"),
                        "market": market.get("question", ""),
                        "spread_pct": spread * 100,
                        "liquidity": market.get("liquidity", 0),
                        "prices": prices
                    })

        opportunities.sort(key=lambda x: x["liquidity"], reverse=True)
        return opportunities

    def detect_price_anomalies(self, markets: List[Dict]) -> List[Dict]:
        """
        检测价格异常

        Args:
            markets: 市场列表

        Returns:
            List[Dict]: 价格异常列表
        """
        anomalies = []

        for market in markets:
            market_id = market.get("id")
            prices = list(market.get("outcome_prices", {}).values())

            if not market_id or len(prices) < 2:
                continue

            avg_price = sum(prices) / len(prices)
            spread = abs(prices[0] - prices[1])

            if market_id in self.price_history:
                last_avg = self.price_history[market_id].get("avg", avg_price)

                if last_avg > 0:
                    price_change = abs(avg_price - last_avg) / last_avg

                    if price_change > self.price_anomaly_threshold:
                        anomalies.append({
                            "type": "price_spike",
                            "market_id": market_id,
                            "market": market.get("question", ""),
                            "previous_avg": last_avg,
                            "current_avg": avg_price,
                            "change_pct": price_change * 100
                        })

            self.price_history[market_id] = {
                "avg": avg_price,
                "spread": spread,
                "timestamp": datetime.now().isoformat()
            }

        anomalies.sort(key=lambda x: x["change_pct"], reverse=True)
        return anomalies

    def detect_liquidity_changes(self, markets: List[Dict]) -> List[Dict]:
        """
        检测流动性变化

        Args:
            markets: 市场列表

        Returns:
            List[Dict]: 流动性变化列表
        """
        changes = []

        for market in markets:
            market_id = market.get("id")
            liquidity = market.get("liquidity", 0)

            if not market_id:
                continue

            if market_id in self.liquidity_history:
                last_liq = self.liquidity_history[market_id].get("liquidity", 0)

                if last_liq > 0:
                    liq_change = (liquidity - last_liq) / last_liq

                    if liq_change > self.liquidity_change_threshold:
                        changes.append({
                            "type": "liquidity_surge",
                            "market_id": market_id,
                            "market": market.get("question", ""),
                            "previous_liquidity": last_liq,
                            "current_liquidity": liquidity,
                            "change_pct": liq_change * 100
                        })

            self.liquidity_history[market_id] = {
                "liquidity": liquidity,
                "timestamp": datetime.now().isoformat()
            }

        changes.sort(key=lambda x: x["change_pct"], reverse=True)
        return changes

    def detect_expiring_markets(
        self,
        markets: List[Dict],
        hours_before: int = 1
    ) -> List[Dict]:
        """
        检测即将到期的市场

        Args:
            markets: 市场列表
            hours_before: 到期前小时数

        Returns:
            List[Dict]: 即将到期的市场列表
        """
        expiring = []
        now = datetime.now(timezone.utc)
        cutoff_time = now + timedelta(hours=hours_before)

        for market in markets:
            try:
                end_time_str = market.get("end_time", "")
                if not end_time_str:
                    continue

                end_time = datetime.fromisoformat(end_time_str.replace("Z", "+00:00"))

                if now < end_time <= cutoff_time:
                    hours_left = (end_time - now).total_seconds() / 3600

                    expiring.append({
                        "market_id": market.get("id"),
                        "market": market.get("question", ""),
                        "end_time": end_time_str,
                        "hours_left": hours_left,
                        "liquidity": market.get("liquidity", 0)
                    })
            except (ValueError, TypeError) as e:
                logger.debug(f"解析到期时间失败: {e}")
                continue

        expiring.sort(key=lambda x: x["hours_left"])
        return expiring

    def detect_multi_outcome_arbitrage(
        self,
        markets: List[Dict],
        min_outcomes: Optional[int] = None
    ) -> List[Dict]:
        """
        检测多结果市场的套利机会

        Args:
            markets: 市场列表
            min_outcomes: 最小结果数

        Returns:
            List[Dict]: 多结果套利机会列表
        """
        if min_outcomes is None:
            min_outcomes = self.min_outcomes

        multi_outcome = []

        for market in markets:
            prices = list(market.get("outcome_prices", {}).values())

            if len(prices) >= min_outcomes:
                total = sum(prices)

                if total < 0.95:
                    profit = (1 - total) * 100

                    multi_outcome.append({
                        "type": "multi_outcome_surebet",
                        "market_id": market.get("id"),
                        "market": market.get("question", ""),
                        "outcome_count": len(prices),
                        "total_price": total,
                        "expected_profit": profit,
                        "prices": prices
                    })

        multi_outcome.sort(key=lambda x: x["expected_profit"], reverse=True)
        return multi_outcome

    def detect_hot_events(
        self,
        markets: List[Dict],
        keyword_threshold: Optional[int] = None
    ) -> List[Dict]:
        """
        检测热门事件

        Args:
            markets: 市场列表
            keyword_threshold: 关键词阈值

        Returns:
            List[Dict]: 热门事件列表
        """
        if keyword_threshold is None:
            keyword_threshold = self.keyword_threshold

        keyword_index = defaultdict(list)

        for market in markets:
            question = market.get("question", "").lower()
            words = [w for w in question.split() if len(w) > 4]

            for word in words:
                keyword_index[word].append(market)

        hot_keywords = {
            word: mkts
            for word, mkts in keyword_index.items()
            if len(mkts) >= keyword_threshold
        }

        logger.info(f"发现 {len(hot_keywords)} 个热门关键词")

        hot_events = []

        for keyword, related_markets in hot_keywords.items():
            price_spreads = []

            for m in related_markets:
                prices = list(m.get("outcome_prices", {}).values())

                if len(prices) >= 2:
                    spread = abs(prices[0] - prices[1])
                    price_spreads.append(spread)

            if price_spreads:
                avg_spread = sum(price_spreads) / len(price_spreads)

                if avg_spread > 0.05:
                    hot_events.append({
                        "type": "hot_event_arbitrage",
                        "keyword": keyword,
                        "market_count": len(related_markets),
                        "avg_spread_pct": avg_spread * 100,
                        "top_markets": [
                            {
                                "market_id": m.get("id"),
                                "market": m.get("question", "")[:40],
                                "prices": list(m.get("outcome_prices", {}).values())
                            }
                            for m in sorted(
                                related_markets,
                                key=lambda x: x.get("liquidity", 0),
                                reverse=True
                            )[:3]
                        ]
                    })

        hot_events.sort(key=lambda x: x["avg_spread_pct"], reverse=True)
        return hot_events

    def generate_enhanced_report(self, markets: List[Dict]) -> Dict:
        """
        生成增强的套利报告

        Args:
            markets: 市场列表

        Returns:
            Dict: 增强报告
        """
        now = datetime.now()

        logger.info("执行增强套利检测...")

        # 1. 改进的 Surebet
        surebets = self.detect_surebets_improved(markets)
        logger.info(f"Surebet 机会: {len(surebets)} 个")

        # 2. 高流动性市场
        high_liq = self.detect_high_liquidity_opportunities(markets)

        # 3. 价格异常
        price_anomalies = self.detect_price_anomalies(markets)
        logger.info(f"价格异常: {len(price_anomalies)} 个")

        # 4. 流动性变化
        liq_changes = self.detect_liquidity_changes(markets)
        logger.info(f"流动性变化: {len(liq_changes)} 个")

        # 5. 即将到期市场
        expiring = self.detect_expiring_markets(markets, hours_before=2)
        logger.info(f"即将到期市场（2小时内）: {len(expiring)} 个")

        # 6. 多结果市场
        multi_outcome = self.detect_multi_outcome_arbitrage(markets)
        logger.info(f"多结果套利: {len(multi_outcome)} 个")

        # 7. 热门事件
        hot_events = self.detect_hot_events(markets)
        logger.info(f"热门事件套利: {len(hot_events)} 个")

        report = {
            "timestamp": now.isoformat(),
            "enhanced_detection": {
                "surebets": surebets[:10],
                "high_liquidity_opportunities": high_liq[:10],
                "price_anomalies": price_anomalies[:10],
                "liquidity_changes": liq_changes[:10],
                "expiring_markets": expiring[:10],
                "multi_outcome_arbitrage": multi_outcome[:10],
                "hot_events": hot_events[:10]
            },
            "summary": {
                "total_opportunities": (
                    len(surebets) +
                    len(high_liq) +
                    len(price_anomalies) +
                    len(liq_changes) +
                    len(multi_outcome) +
                    len(hot_events)
                ),
                "surebets": len(surebets),
                "high_liquidity": len(high_liq),
                "price_anomalies": len(price_anomalies),
                "liquidity_changes": len(liq_changes),
                "multi_outcome": len(multi_outcome),
                "hot_events": len(hot_events)
            }
        }

        return report
