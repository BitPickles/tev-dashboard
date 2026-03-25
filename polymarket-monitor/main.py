#!/usr/bin/env python3
"""
Polymarket Arbitrage & End-Game Monitor
套利和尾盘监控程序 (使用 CDM API)
"""

import asyncio
import aiohttp
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from dataclasses import dataclass
import json
import os

from config_manager import get_config_manager, AppConfig
from logger import get_logger, setup_logger

# 设置日志
logger = setup_logger("polymarket", log_file="polymarket.log")


@dataclass
class Market:
    """市场数据结构"""
    id: str
    question: str
    outcome_prices: Dict[str, float]
    liquidity: float
    volume: float
    end_time: datetime
    slug: str
    tags: List[str]
    condition_id: str


@dataclass
class ArbitrageOpportunity:
    """套利机会"""
    market1_id: str
    market2_id: str
    question1: str
    question2: str
    strategy: str
    expected_profit: float
    trades: List[dict]
    confidence: float


class PolymarketMonitor:
    """Polymarket 监控器"""

    def __init__(self, config: Optional[AppConfig] = None):
        """
        初始化监控器

        Args:
            config: 应用配置（可选，不提供则自动加载）
        """
        if config is None:
            config = get_config_manager().load_config()

        self.config = config
        self.api_url = config.api_url
        self.session: Optional[aiohttp.ClientSession] = None
        self.markets: Dict[str, Market] = {}

        # 从配置加载阈值
        self.arbitrage_threshold = config.arbitrage.threshold
        self.liquidity_threshold = config.arbitrage.liquidity_threshold
        self.end_game_window = config.monitoring.end_game_window

        # 使用系统代理（如果配置了）
        self.proxy = os.environ.get("HTTPS_PROXY", os.environ.get("https_proxy"))

        logger.info(f"监控器初始化完成，API: {self.api_url}")
        logger.info(f"套利阈值: {self.arbitrage_threshold * 100}%, 流动性阈值: ${self.liquidity_threshold}")

    async def __aenter__(self):
        timeout = aiohttp.ClientTimeout(total=60)
        self.session = aiohttp.ClientSession(timeout=timeout)
        return self

    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()

    async def fetch_markets(self, limit: int = 200) -> List[Market]:
        """获取活跃市场列表"""
        url = f"{self.api_url}/markets"
        params = {
            "limit": limit,
            "active": "true",
            "closed": "false"
        }

        try:
            kwargs = {"url": url, "params": params}
            if self.proxy:
                kwargs["proxy"] = self.proxy

            async with self.session.get(**kwargs) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    logger.error(f"HTTP {resp.status}: {text[:200]}")
                    return []

                data = await resp.json()
                markets = []

                for m in data:
                    market = self._parse_market(m)
                    if market:
                        markets.append(market)
                        self.markets[market.id] = market

                logger.info(f"获取到 {len(markets)} 个活跃市场")
                return markets

        except aiohttp.ClientError as e:
            logger.error(f"网络请求失败: {e}")
            return []
        except asyncio.TimeoutError:
            logger.error("请求超时")
            return []
        except Exception as e:
            logger.error(f"获取市场数据失败: {e}")
            return []

    def _parse_market(self, m: dict) -> Optional[Market]:
        """
        解析市场数据

        Args:
            m: 原始市场数据

        Returns:
            Market 对象或 None
        """
        # 跳过已关闭的市场
        if m.get("closed") or not m.get("active"):
            return None

        # 解析价格
        outcome_prices_str = m.get("outcomePrices", "[]")
        outcomes_str = m.get("outcomes", "[]")

        try:
            outcomes = json.loads(outcomes_str) if isinstance(outcomes_str, str) else outcomes_str
            prices_str = json.loads(outcome_prices_str) if isinstance(outcome_prices_str, str) else outcome_prices_str

            outcome_prices = {}
            for outcome, price in zip(outcomes, prices_str):
                try:
                    outcome_prices[outcome] = float(price)
                except (ValueError, TypeError):
                    # 记录警告但不中断，使用默认值
                    logger.warning(f"市场 {m.get('id')} 价格解析失败: {price}")
                    outcome_prices[outcome] = 0.5  # 使用中性值而非 0

        except json.JSONDecodeError as e:
            logger.warning(f"市场 {m.get('id')} JSON 解析失败: {e}")
            return None

        # 解析结束时间
        end_date = m.get("endDate")
        if end_date:
            try:
                end_time = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
            except ValueError:
                end_time = datetime.now() + timedelta(days=365)
        else:
            return None

        # 解析标签
        tags = [m.get("category", "")] if m.get("category") else []

        return Market(
            id=str(m["id"]),
            question=m["question"],
            outcome_prices=outcome_prices,
            liquidity=float(m.get("liquidity", 0)),
            volume=float(m.get("volumeNum", m.get("volume", 0))),
            end_time=end_time,
            slug=m["slug"],
            tags=tags,
            condition_id=m.get("conditionId", "")
        )

    def find_related_markets(self, market: Market) -> List[Market]:
        """查找相关市场（基于标签和关键词）"""
        related = []
        market_keywords = self._extract_keywords(market.question)

        for m in self.markets.values():
            if m.id == market.id:
                continue

            # 检查标签重叠
            if any(tag in m.tags for tag in market.tags if tag):
                related.append(m)
                continue

            # 检查关键词重叠
            other_keywords = self._extract_keywords(m.question)
            if len(set(market_keywords) & set(other_keywords)) >= 2:
                related.append(m)

        return related

    def _extract_keywords(self, text: str) -> List[str]:
        """从问题中提取关键词"""
        stop_words = {
            "will", "the", "to", "in", "by", "for", "of", "and", "or",
            "before", "after", "with", "from", "this", "that", "be",
            "are", "were", "was", "been", "have", "has", "had", "do", "does", "did"
        }
        words = text.lower().replace("?", "").replace(",", "").split()
        return [w for w in words if len(w) > 3 and w not in stop_words]

    def detect_arbitrage(self) -> List[ArbitrageOpportunity]:
        """检测套利机会 - 专注于真实可执行的机会"""
        opportunities = []
        markets = list(self.markets.values())

        # 过滤掉流动性不足的市场
        markets = [m for m in markets if m.liquidity >= self.liquidity_threshold]

        logger.info(f"分析 {len(markets)} 个市场的套利机会...")

        # 1. Surebet 检测 (多结果套利) - 最可靠的套利类型
        for market in markets:
            opportunity = self._check_multi_outcome_arbitrage(market)
            if opportunity:
                opportunities.append(opportunity)

        # 2. 价格异常检测 - 极端价格但有流动性
        for market in markets:
            opportunity = self._check_price_anomaly(market)
            if opportunity:
                opportunities.append(opportunity)

        # 3. 高价差检测 - Yes + No 价格和超过 1 (可卖空套利)
        for market in markets:
            opportunity = self._check_overpriced_market(market)
            if opportunity:
                opportunities.append(opportunity)

        logger.info(f"发现 {len(opportunities)} 个套利机会")
        return opportunities

    def _check_price_anomaly(self, market: Market) -> Optional[ArbitrageOpportunity]:
        """检测价格异常 - 极端价格配合高流动性"""
        if len(market.outcome_prices) < 2:
            return None

        prices = list(market.outcome_prices.values())
        outcomes = list(market.outcome_prices.keys())

        # 检测极端低价（<5%）配合高流动性（>$10k）
        for i, price in enumerate(prices):
            if price < 0.05 and market.liquidity > 10000:
                # 低价结果可能被低估
                return ArbitrageOpportunity(
                    market1_id=market.id,
                    market2_id=market.id,
                    question1=market.question,
                    question2=market.question,
                    strategy="price_anomaly_low",
                    expected_profit=price * 100,  # 潜在回报倍数
                    trades=[
                        {"market": market.id, "outcome": outcomes[i], "action": "buy", "price": price}
                    ],
                    confidence=market.liquidity / 50000
                )

        return None

    def _check_overpriced_market(self, market: Market) -> Optional[ArbitrageOpportunity]:
        """检测高估市场 - 所有结果价格和 > 1"""
        if len(market.outcome_prices) < 2:
            return None

        total_price = sum(market.outcome_prices.values())

        # 价格和 > 1.02 (考虑费用后仍可套利)
        if total_price > 1.02:
            profit = (total_price - 1) * 100
            return ArbitrageOpportunity(
                market1_id=market.id,
                market2_id=market.id,
                question1=market.question,
                question2=market.question,
                strategy="overpriced_sell",
                expected_profit=profit,
                trades=[
                    {"market": market.id, "outcome": outcome, "action": "sell", "price": price}
                    for outcome, price in market.outcome_prices.items()
                ],
                confidence=market.liquidity / 10000
            )

        return None

    def _check_cross_market_arbitrage(
        self, m1: Market, m2: Market
    ) -> Optional[ArbitrageOpportunity]:
        """检查跨市场套利"""
        common_outcomes = set(m1.outcome_prices.keys()) & set(m2.outcome_prices.keys())

        for outcome in common_outcomes:
            price1 = m1.outcome_prices[outcome]
            price2 = m2.outcome_prices[outcome]

            price_diff = abs(price1 - price2)
            min_price = min(price1, price2)

            if min_price > 0.001:
                profit_pct = price_diff / min_price

                if profit_pct >= self.arbitrage_threshold:
                    return ArbitrageOpportunity(
                        market1_id=m1.id,
                        market2_id=m2.id,
                        question1=m1.question,
                        question2=m2.question,
                        strategy="cross_market",
                        expected_profit=profit_pct * 100,
                        trades=[
                            {"market": m1.id, "outcome": outcome, "action": "sell" if price1 > price2 else "buy", "price": price1},
                            {"market": m2.id, "outcome": outcome, "action": "buy" if price1 > price2 else "sell", "price": price2},
                        ],
                        confidence=min(m1.liquidity, m2.liquidity) / 10000
                    )

        return None

    def _check_multi_outcome_arbitrage(self, market: Market) -> Optional[ArbitrageOpportunity]:
        """检查同一市场内的多结果套利"""
        if len(market.outcome_prices) < 2:
            return None

        total_price = sum(market.outcome_prices.values())

        if total_price < (1 - self.arbitrage_threshold) and total_price > 0:
            profit = (1 - total_price) * 100
            return ArbitrageOpportunity(
                market1_id=market.id,
                market2_id=market.id,
                question1=market.question,
                question2=market.question,
                strategy="multi_outcome_surebet",
                expected_profit=profit,
                trades=[
                    {"market": market.id, "outcome": outcome, "action": "buy", "price": price}
                    for outcome, price in market.outcome_prices.items()
                ],
                confidence=market.liquidity / 10000
            )

        return None

    def get_end_game_markets(self, hours: int = 1) -> List[Market]:
        """获取即将关闭的市场（尾盘）"""
        now = datetime.now(timezone.utc)
        end_time_threshold = now + timedelta(hours=hours)

        end_game = [
            m for m in self.markets.values()
            if now < m.end_time <= end_time_threshold
        ]

        return sorted(end_game, key=lambda m: m.end_time)

    def get_top_volume_markets(self, limit: int = 10) -> List[Market]:
        """获取交易量最高的市场"""
        return sorted(self.markets.values(), key=lambda m: m.volume, reverse=True)[:limit]

    async def monitor_end_game(self, interval: int = 60):
        """尾盘监控 - 持续监控即将关闭的市场"""
        logger.info("开始尾盘监控...")

        while True:
            try:
                await self.fetch_markets(limit=500)
                end_game_markets = self.get_end_game_markets(hours=1)

                if end_game_markets:
                    logger.info(f"{len(end_game_markets)} 个市场将在 1 小时内关闭:")

                    for market in end_game_markets[:10]:
                        time_left = (market.end_time - datetime.now(timezone.utc)).total_seconds()
                        logger.info(
                            f"  - [{time_left//60:.0f}m] {market.question[:60]}\n"
                            f"    价格: {market.outcome_prices} | 交易量: ${market.volume:.0f}"
                        )

                    opportunities = self.detect_arbitrage()
                    end_game_opps = [o for o in opportunities if o.expected_profit > self.arbitrage_threshold * 100]

                    if end_game_opps:
                        logger.info(f"发现 {len(end_game_opps)} 个尾盘套利机会！")

                await asyncio.sleep(interval)

            except asyncio.CancelledError:
                logger.info("监控已停止")
                break
            except Exception as e:
                logger.error(f"监控出错: {e}")
                await asyncio.sleep(interval)

    def generate_report(self, opportunities: List[ArbitrageOpportunity]) -> str:
        """生成报告"""
        if not opportunities:
            return "未发现套利机会。\n"

        report = f"📊 套利报告 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        report += "=" * 60 + "\n\n"

        opportunities.sort(key=lambda x: x.expected_profit, reverse=True)

        for i, opp in enumerate(opportunities[:10], 1):
            report += f"{i}. [{opp.strategy.upper()}] {opp.expected_profit:.2f}% 利润\n"
            report += f"   市场 1: {opp.question1[:50]}...\n"
            if opp.market1_id != opp.market2_id:
                report += f"   市场 2: {opp.question2[:50]}...\n"
            report += f"   交易:\n"
            for trade in opp.trades:
                report += f"     - {trade['action'].upper()} {trade['outcome']} @ {trade['price']:.3f}\n"
            report += f"   置信度: {opp.confidence:.1f}\n\n"

        return report


async def main():
    """主函数"""
    async with PolymarketMonitor() as monitor:
        # 获取市场数据
        await monitor.fetch_markets(limit=500)

        # 显示交易量最高的市场
        top_markets = monitor.get_top_volume_markets(limit=10)
        print(f"\n📈 交易量 Top 10:")
        print("=" * 60)
        for i, m in enumerate(top_markets, 1):
            now = datetime.now(timezone.utc)
            time_left = (m.end_time - now).total_seconds() if m.end_time else 0
            time_str = f"{time_left//86400:.0f}d" if time_left > 86400 else f"{time_left//3600:.0f}h" if time_left > 3600 else f"{time_left//60:.0f}m"
            print(f"{i}. [{time_str} 剩余] {m.question[:60]}...")
            print(f"   价格: {m.outcome_prices}")
            print(f"   交易量: ${m.volume:.0f} | 流动性: ${m.liquidity:.0f}\n")

        # 检测套利机会
        opportunities = monitor.detect_arbitrage()

        # 生成并打印报告
        report = monitor.generate_report(opportunities)
        print(report)

        # 获取尾盘市场
        end_game = monitor.get_end_game_markets(hours=24)
        if end_game:
            print(f"🎯 {len(end_game)} 个市场将在 24 小时内关闭:")
            for m in end_game[:5]:
                time_left = (m.end_time - datetime.now(timezone.utc)).total_seconds()
                print(f"  - [{time_left//3600:.0f}h {time_left%3600//60:.0f}m] {m.question[:60]}...")


if __name__ == "__main__":
    print("""
    ╔════════════════════════════════════════════════════════════╗
    ║       Polymarket Arbitrage & End-Game Monitor              ║
    ║                套利和尾盘监控程序 (CDM API)                ║
    ╚════════════════════════════════════════════════════════════╝
    """)

    asyncio.run(main())
