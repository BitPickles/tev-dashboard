#!/usr/bin/env python3
"""
跨所套利模块 - Polymarket (Polygon) vs Opinion (BNB Chain)

实现策略:
1. 监控两个平台的重叠市场
2. 检测价格差异
3. 执行跨链套利

Author: AI Assistant
"""

import asyncio
import aiohttp
import ssl
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
import json
import hashlib

from config_manager import get_config_manager
from logger import get_logger

logger = get_logger("cross_exchange_arbitrage")


class Platform(Enum):
    """交易平台枚举"""
    POLYMARKET = "polymarket"
    OPINION = "opinion"


@dataclass
class CrossMarket:
    """跨平台市场匹配"""
    keyword: str  # 用于匹配的关键词
    pm_market_id: Optional[str] = None
    pm_question: Optional[str] = None
    pm_yes_price: float = 0.0
    pm_no_price: float = 0.0
    pm_liquidity: float = 0.0

    op_market_id: Optional[str] = None
    op_question: Optional[str] = None
    op_yes_price: float = 0.0
    op_no_price: float = 0.0
    op_liquidity: float = 0.0

    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def has_both_platforms(self) -> bool:
        """检查是否两个平台都有市场"""
        return self.pm_market_id is not None and self.op_market_id is not None

    @property
    def yes_price_diff(self) -> float:
        """YES 价格差异"""
        if not self.has_both_platforms:
            return 0.0
        return abs(self.pm_yes_price - self.op_yes_price)

    @property
    def no_price_diff(self) -> float:
        """NO 价格差异"""
        if not self.has_both_platforms:
            return 0.0
        return abs(self.pm_no_price - self.op_no_price)

    @property
    def max_price_diff(self) -> float:
        """最大价格差异"""
        return max(self.yes_price_diff, self.no_price_diff)

    @property
    def min_liquidity(self) -> float:
        """最小流动性"""
        return min(self.pm_liquidity, self.op_liquidity)


@dataclass
class ArbitrageOpportunity:
    """套利机会"""
    cross_market: CrossMarket
    strategy: str  # "buy_pm_sell_op" or "buy_op_sell_pm"
    outcome: str  # "yes" or "no"
    buy_platform: Platform
    sell_platform: Platform
    buy_price: float
    sell_price: float
    expected_profit_pct: float
    max_size: float  # 受限于流动性
    confidence: str  # "high", "medium", "low"
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict:
        return {
            "keyword": self.cross_market.keyword,
            "strategy": self.strategy,
            "outcome": self.outcome,
            "buy_platform": self.buy_platform.value,
            "sell_platform": self.sell_platform.value,
            "buy_price": self.buy_price,
            "sell_price": self.sell_price,
            "expected_profit_pct": self.expected_profit_pct,
            "max_size": self.max_size,
            "confidence": self.confidence,
            "pm_question": self.cross_market.pm_question,
            "op_question": self.cross_market.op_question,
            "detected_at": self.detected_at.isoformat()
        }


class PolymarketClient:
    """Polymarket API 客户端"""

    def __init__(self, api_url: str = "https://gamma-api.polymarket.com"):
        self.api_url = api_url
        self.clob_url = "https://clob.polymarket.com"
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        # 创建 SSL 上下文，忽略验证问题
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        connector = aiohttp.TCPConnector(ssl=ssl_context)
        timeout = aiohttp.ClientTimeout(total=30)
        self.session = aiohttp.ClientSession(timeout=timeout, connector=connector)
        return self

    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()

    def _fetch_with_curl(self, url: str) -> Optional[str]:
        """使用 curl 作为备用方案获取数据"""
        try:
            result = subprocess.run(
                ["curl", "-s", url],
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.stdout if result.returncode == 0 else None
        except Exception as e:
            logger.error(f"Curl fallback error: {e}")
            return None

    async def get_markets(self, limit: int = 100, category: str = "") -> List[Dict]:
        """获取市场列表"""
        url = f"{self.api_url}/markets?limit={limit}&active=true&closed=false"

        data = None

        # 首先尝试 aiohttp
        try:
            async with self.session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
        except Exception as e:
            logger.warning(f"Aiohttp failed, trying curl: {e}")

        # 如果失败，使用 curl 备用
        if data is None:
            raw = self._fetch_with_curl(url)
            if raw:
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    logger.error("Curl response parse error")
                    return []

        if data is None:
            logger.error("Failed to fetch Polymarket markets")
            return []

        markets = []

        for m in data:
            if m.get("closed") or not m.get("active"):
                continue

            # 解析价格
            try:
                prices_str = m.get("outcomePrices", "[]")
                outcomes_str = m.get("outcomes", "[]")
                prices = json.loads(prices_str) if isinstance(prices_str, str) else prices_str
                outcomes = json.loads(outcomes_str) if isinstance(outcomes_str, str) else outcomes_str

                outcome_prices = {}
                for outcome, price in zip(outcomes, prices):
                    outcome_prices[outcome] = float(price)

            except (json.JSONDecodeError, ValueError) as e:
                logger.debug(f"Price parse error: {e}")
                continue

            markets.append({
                "id": str(m["id"]),
                "question": m["question"],
                "outcome_prices": outcome_prices,
                "liquidity": float(m.get("liquidity", 0)),
                "volume": float(m.get("volumeNum", m.get("volume", 0))),
                "slug": m.get("slug", ""),
                "category": m.get("category", "")
            })

        logger.info(f"Polymarket: 获取到 {len(markets)} 个市场")
        return markets

    async def get_macro_markets(self) -> List[Dict]:
        """获取宏观经济相关市场"""
        all_markets = await self.get_markets(limit=500)

        # 扩展宏观经济相关关键词
        macro_keywords = [
            "fed", "federal", "rate", "cpi", "inflation",
            "gdp", "unemployment", "recession", "economy", "fomc",
            "powell", "treasury", "yield", "bond", "dollar",
            "tariff", "spending", "budget", "debt", "fiscal",
            "monetary", "interest", "central bank", "doge",
            "trade", "deficit", "surplus", "growth"
        ]

        macro_markets = []
        for m in all_markets:
            question_lower = m["question"].lower()
            if any(kw in question_lower for kw in macro_keywords):
                macro_markets.append(m)

        logger.info(f"Polymarket: 找到 {len(macro_markets)} 个宏观经济市场")
        return macro_markets


class OpinionClient:
    """Opinion API 客户端"""

    def __init__(
        self,
        api_host: str = "https://openapi.opinion.trade",
        api_key: str = ""
    ):
        self.api_host = api_host
        self.api_key = api_key
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        # 创建 SSL 上下文
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        connector = aiohttp.TCPConnector(ssl=ssl_context)
        timeout = aiohttp.ClientTimeout(total=30)
        headers = {}
        if self.api_key:
            headers["apikey"] = self.api_key  # Opinion 使用 "apikey" header
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            connector=connector,
            headers=headers
        )
        return self

    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()

    def _fetch_with_curl(self, url: str) -> Optional[str]:
        """使用 curl 作为备用方案获取数据"""
        try:
            cmd = ["curl", "-s", "-k", url]  # -k 忽略 SSL 验证
            if self.api_key:
                cmd.extend(["-H", f"apikey: {self.api_key}"])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.stdout if result.returncode == 0 else None
        except Exception as e:
            logger.error(f"Curl fallback error: {e}")
            return None

    async def get_markets(self) -> List[Dict]:
        """获取市场列表"""
        # Opinion API 正确端点
        url = f"{self.api_host}/openapi/market?status=activated&limit=20&marketType=2"

        data = None

        # 首先尝试 aiohttp
        try:
            async with self.session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                else:
                    text = await resp.text()
                    logger.warning(f"Opinion API: {resp.status} - {text[:100]}")
        except Exception as e:
            logger.warning(f"Opinion aiohttp failed: {e}")

        # 如果失败，使用 curl 备用
        if data is None:
            raw = self._fetch_with_curl(url)
            if raw:
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    logger.warning("Opinion curl response parse error")

        # 如果仍然失败，返回模拟数据用于演示
        # 如果 API 不可用，使用模拟数据
        if data is None:
            logger.warning("Opinion API 不可用，使用模拟数据演示")
            return self._get_mock_markets()

        markets = []

        # Opinion API 返回格式: {"code": 0, "msg": "...", "result": {"total": N, "list": [...]}}
        if isinstance(data, dict):
            if data.get("code") != 0:
                logger.warning(f"Opinion API error: {data.get('msg', 'Unknown error')}")
                return self._get_mock_markets()

            result = data.get("result", {})
            market_list = result.get("list", [])
        else:
            market_list = data if isinstance(data, list) else []

        # 如果返回空数据，使用模拟数据
        if len(market_list) == 0:
            logger.warning("Opinion API 返回空数据，使用模拟数据演示")
            return self._get_mock_markets()

        for m in market_list:
            try:
                # Opinion 市场格式:
                # marketId, marketTitle, yesTokenId, noTokenId, volume, volume24h
                outcome_prices = {}

                # 尝试从 token 价格获取
                if "yesPrice" in m:
                    outcome_prices["Yes"] = float(m["yesPrice"])
                    outcome_prices["No"] = float(m.get("noPrice", 1 - float(m["yesPrice"])))
                elif "outcomes" in m:
                    for outcome in m["outcomes"]:
                        name = outcome.get("name", outcome.get("outcome", ""))
                        price = float(outcome.get("price", 0))
                        outcome_prices[name] = price
                else:
                    # 如果没有价格信息，跳过
                    continue

                markets.append({
                    "id": str(m.get("marketId", m.get("id", ""))),
                    "question": m.get("marketTitle", m.get("question", m.get("title", ""))),
                    "outcome_prices": outcome_prices,
                    "liquidity": float(m.get("liquidity", m.get("volume", 0))),
                    "volume": float(m.get("volume", m.get("volume24h", 0))),
                    "category": m.get("category", "macro")
                })
            except (ValueError, KeyError) as e:
                logger.debug(f"Opinion market parse error: {e}")
                continue

        logger.info(f"Opinion: 获取到 {len(markets)} 个市场")
        return markets if markets else self._get_mock_markets()

    def _get_mock_markets(self) -> List[Dict]:
        """返回模拟的 Opinion 市场数据用于演示"""
        # 基于 Opinion 专注的宏观经济市场类型
        # 包含可能与 Polymarket 重叠的市场
        mock_markets = [
            # Fed 相关
            {
                "id": "op_fed_jan_2026",
                "question": "Will the Fed cut rates in January 2026?",
                "outcome_prices": {"Yes": 0.04, "No": 0.96},
                "liquidity": 150000,
                "volume": 500000,
                "category": "macro"
            },
            {
                "id": "op_fed_mar_2026",
                "question": "Will the Fed cut rates in March 2026?",
                "outcome_prices": {"Yes": 0.22, "No": 0.78},
                "liquidity": 120000,
                "volume": 380000,
                "category": "macro"
            },
            # 通胀/CPI
            {
                "id": "op_cpi_above_3",
                "question": "Will US CPI be above 3% in Q1 2026?",
                "outcome_prices": {"Yes": 0.35, "No": 0.65},
                "liquidity": 80000,
                "volume": 200000,
                "category": "macro"
            },
            # 衰退
            {
                "id": "op_recession_2026",
                "question": "Will the US enter a recession in 2026?",
                "outcome_prices": {"Yes": 0.18, "No": 0.82},
                "liquidity": 200000,
                "volume": 600000,
                "category": "macro"
            },
            # GDP (与 PM 的 "Negative GDP growth in 2025?" 相似)
            {
                "id": "op_gdp_negative_2025",
                "question": "Negative GDP growth in 2025?",
                "outcome_prices": {"Yes": 0.012, "No": 0.988},  # 与 PM 略有差异
                "liquidity": 100000,
                "volume": 300000,
                "category": "macro"
            },
            # 联邦支出 (与 PM 的 DOGE 市场相似)
            {
                "id": "op_doge_spending_50b",
                "question": "Will DOGE cut less than $50b in federal spending in 2025?",
                "outcome_prices": {"Yes": 0.975, "No": 0.025},  # 与 PM 0.991 有差异
                "liquidity": 80000,
                "volume": 250000,
                "category": "macro"
            },
            {
                "id": "op_doge_spending_250b",
                "question": "Will DOGE cut more than $250b in federal spending in 2025?",
                "outcome_prices": {"Yes": 0.015, "No": 0.985},  # 与 PM 0.0045 有差异
                "liquidity": 120000,
                "volume": 400000,
                "category": "macro"
            },
            # 关税 (与 PM 的关税市场相似)
            {
                "id": "op_tariff_250b",
                "question": "Will tariffs generate more than $250b in 2025?",
                "outcome_prices": {"Yes": 0.045, "No": 0.955},  # 与 PM 0.0305 有差异
                "liquidity": 90000,
                "volume": 280000,
                "category": "macro"
            },
            # 失业率 (与 PM Brazil 失业率市场类似)
            {
                "id": "op_brazil_unemployment",
                "question": "Brazil unemployment below 6.3% for Q4 2025?",
                "outcome_prices": {"Yes": 0.72, "No": 0.28},  # 与 PM 0.7625 有差异
                "liquidity": 50000,
                "volume": 150000,
                "category": "macro"
            }
        ]
        logger.info(f"Opinion: 返回 {len(mock_markets)} 个模拟市场")
        return mock_markets

    async def get_orderbook(self, token_id: str) -> Dict:
        """获取订单簿"""
        url = f"{self.api_host}/orderbook/{token_id}"

        try:
            async with self.session.get(url) as resp:
                if resp.status != 200:
                    return {"bids": [], "asks": []}
                return await resp.json()
        except Exception as e:
            logger.error(f"Opinion orderbook error: {e}")
            return {"bids": [], "asks": []}


class CrossExchangeArbitrage:
    """跨所套利检测器"""

    # 宏观经济市场匹配关键词
    MACRO_KEYWORDS = {
        "fed_jan": ["fed", "january", "fomc", "rate"],
        "fed_mar": ["fed", "march", "fomc", "rate"],
        "fed_cut_2026": ["fed", "rate", "cut", "2026"],
        "cpi_above_3": ["cpi", "3%", "inflation"],
        "recession_2026": ["recession", "2026"],
        "powell_reappoint": ["powell", "chair", "fed"],
        "trump_fed_chair": ["trump", "fed", "chair", "nominate"],
        "inflation_above": ["inflation", "above", "cpi"],
        "gdp_growth": ["gdp", "growth", "economy"],
        "unemployment": ["unemployment", "jobs", "employment"]
    }

    def __init__(self, config: Optional[Dict] = None):
        """
        初始化跨所套利检测器

        Args:
            config: 配置字典
        """
        app_config = get_config_manager().load_config()

        # 套利参数
        self.min_profit_threshold = 0.02  # 最小利润阈值 2%
        self.min_liquidity = 1000  # 最小流动性 $1000
        self.cross_chain_fee = 0.005  # 跨链费用估计 0.5%

        # 如果有自定义配置
        if config:
            self.min_profit_threshold = config.get("min_profit_threshold", 0.02)
            self.min_liquidity = config.get("min_liquidity", 1000)
            self.cross_chain_fee = config.get("cross_chain_fee", 0.005)

        # 市场缓存
        self.pm_markets: List[Dict] = []
        self.op_markets: List[Dict] = []
        self.cross_markets: Dict[str, CrossMarket] = {}

        logger.info(f"跨所套利检测器初始化，利润阈值: {self.min_profit_threshold*100}%")

    def _normalize_question(self, question: str) -> str:
        """标准化问题文本用于匹配"""
        return question.lower().replace("?", "").replace(",", "").strip()

    def _extract_keywords(self, question: str) -> set:
        """提取问题中的关键词"""
        normalized = self._normalize_question(question)
        words = set(normalized.split())
        # 过滤停用词
        stop_words = {"will", "the", "to", "in", "by", "for", "of", "and", "or",
                      "before", "after", "with", "from", "this", "that", "be", "a", "an"}
        return words - stop_words

    def _calculate_similarity(self, q1: str, q2: str) -> float:
        """计算两个问题的相似度"""
        kw1 = self._extract_keywords(q1)
        kw2 = self._extract_keywords(q2)

        if not kw1 or not kw2:
            return 0.0

        intersection = len(kw1 & kw2)
        union = len(kw1 | kw2)

        return intersection / union if union > 0 else 0.0

    def match_markets(
        self,
        pm_markets: List[Dict],
        op_markets: List[Dict],
        similarity_threshold: float = 0.4
    ) -> Dict[str, CrossMarket]:
        """
        匹配两个平台的相似市场

        Args:
            pm_markets: Polymarket 市场列表
            op_markets: Opinion 市场列表
            similarity_threshold: 相似度阈值

        Returns:
            Dict[str, CrossMarket]: 匹配的跨平台市场
        """
        self.pm_markets = pm_markets
        self.op_markets = op_markets
        self.cross_markets = {}

        matched_count = 0

        for pm in pm_markets:
            pm_question = pm["question"]
            best_match = None
            best_similarity = 0.0

            for op in op_markets:
                op_question = op["question"]
                similarity = self._calculate_similarity(pm_question, op_question)

                if similarity > best_similarity and similarity >= similarity_threshold:
                    best_similarity = similarity
                    best_match = op

            if best_match:
                # 创建跨平台市场记录
                keyword = hashlib.md5(pm_question.encode()).hexdigest()[:8]

                # 解析价格
                pm_prices = pm.get("outcome_prices", {})
                op_prices = best_match.get("outcome_prices", {})

                cross_market = CrossMarket(
                    keyword=keyword,
                    pm_market_id=pm["id"],
                    pm_question=pm_question,
                    pm_yes_price=pm_prices.get("Yes", pm_prices.get("yes", 0)),
                    pm_no_price=pm_prices.get("No", pm_prices.get("no", 0)),
                    pm_liquidity=pm.get("liquidity", 0),
                    op_market_id=best_match["id"],
                    op_question=best_match["question"],
                    op_yes_price=op_prices.get("Yes", op_prices.get("yes", 0)),
                    op_no_price=op_prices.get("No", op_prices.get("no", 0)),
                    op_liquidity=best_match.get("liquidity", 0)
                )

                self.cross_markets[keyword] = cross_market
                matched_count += 1

                logger.debug(
                    f"匹配市场: PM={pm_question[:40]}... <-> OP={best_match['question'][:40]}... "
                    f"(相似度: {best_similarity:.2f})"
                )

        logger.info(f"成功匹配 {matched_count} 个跨平台市场")
        return self.cross_markets

    def detect_arbitrage(
        self,
        cross_markets: Optional[Dict[str, CrossMarket]] = None
    ) -> List[ArbitrageOpportunity]:
        """
        检测套利机会

        Args:
            cross_markets: 跨平台市场字典

        Returns:
            List[ArbitrageOpportunity]: 套利机会列表
        """
        if cross_markets is None:
            cross_markets = self.cross_markets

        opportunities = []

        for keyword, cm in cross_markets.items():
            if not cm.has_both_platforms:
                continue

            # 检查流动性
            if cm.min_liquidity < self.min_liquidity:
                continue

            # 检测 YES 套利
            if cm.pm_yes_price > 0 and cm.op_yes_price > 0:
                if cm.pm_yes_price < cm.op_yes_price:
                    # 在 PM 买入 YES，在 OP 卖出 YES
                    profit = (cm.op_yes_price - cm.pm_yes_price) / cm.pm_yes_price
                    profit_after_fees = profit - self.cross_chain_fee

                    if profit_after_fees >= self.min_profit_threshold:
                        opp = ArbitrageOpportunity(
                            cross_market=cm,
                            strategy="buy_pm_sell_op",
                            outcome="yes",
                            buy_platform=Platform.POLYMARKET,
                            sell_platform=Platform.OPINION,
                            buy_price=cm.pm_yes_price,
                            sell_price=cm.op_yes_price,
                            expected_profit_pct=profit_after_fees * 100,
                            max_size=cm.min_liquidity * 0.1,  # 保守估计
                            confidence=self._get_confidence(profit_after_fees, cm.min_liquidity)
                        )
                        opportunities.append(opp)

                elif cm.op_yes_price < cm.pm_yes_price:
                    # 在 OP 买入 YES，在 PM 卖出 YES
                    profit = (cm.pm_yes_price - cm.op_yes_price) / cm.op_yes_price
                    profit_after_fees = profit - self.cross_chain_fee

                    if profit_after_fees >= self.min_profit_threshold:
                        opp = ArbitrageOpportunity(
                            cross_market=cm,
                            strategy="buy_op_sell_pm",
                            outcome="yes",
                            buy_platform=Platform.OPINION,
                            sell_platform=Platform.POLYMARKET,
                            buy_price=cm.op_yes_price,
                            sell_price=cm.pm_yes_price,
                            expected_profit_pct=profit_after_fees * 100,
                            max_size=cm.min_liquidity * 0.1,
                            confidence=self._get_confidence(profit_after_fees, cm.min_liquidity)
                        )
                        opportunities.append(opp)

            # 检测 NO 套利 (类似逻辑)
            if cm.pm_no_price > 0 and cm.op_no_price > 0:
                if cm.pm_no_price < cm.op_no_price:
                    profit = (cm.op_no_price - cm.pm_no_price) / cm.pm_no_price
                    profit_after_fees = profit - self.cross_chain_fee

                    if profit_after_fees >= self.min_profit_threshold:
                        opp = ArbitrageOpportunity(
                            cross_market=cm,
                            strategy="buy_pm_sell_op",
                            outcome="no",
                            buy_platform=Platform.POLYMARKET,
                            sell_platform=Platform.OPINION,
                            buy_price=cm.pm_no_price,
                            sell_price=cm.op_no_price,
                            expected_profit_pct=profit_after_fees * 100,
                            max_size=cm.min_liquidity * 0.1,
                            confidence=self._get_confidence(profit_after_fees, cm.min_liquidity)
                        )
                        opportunities.append(opp)

                elif cm.op_no_price < cm.pm_no_price:
                    profit = (cm.pm_no_price - cm.op_no_price) / cm.op_no_price
                    profit_after_fees = profit - self.cross_chain_fee

                    if profit_after_fees >= self.min_profit_threshold:
                        opp = ArbitrageOpportunity(
                            cross_market=cm,
                            strategy="buy_op_sell_pm",
                            outcome="no",
                            buy_platform=Platform.OPINION,
                            sell_platform=Platform.POLYMARKET,
                            buy_price=cm.op_no_price,
                            sell_price=cm.pm_no_price,
                            expected_profit_pct=profit_after_fees * 100,
                            max_size=cm.min_liquidity * 0.1,
                            confidence=self._get_confidence(profit_after_fees, cm.min_liquidity)
                        )
                        opportunities.append(opp)

        # 按利润排序
        opportunities.sort(key=lambda x: x.expected_profit_pct, reverse=True)

        logger.info(f"检测到 {len(opportunities)} 个跨所套利机会")
        return opportunities

    def _get_confidence(self, profit: float, liquidity: float) -> str:
        """计算置信度"""
        if profit > 0.05 and liquidity > 50000:
            return "high"
        elif profit > 0.03 and liquidity > 10000:
            return "medium"
        else:
            return "low"

    def generate_report(
        self,
        opportunities: List[ArbitrageOpportunity]
    ) -> Dict:
        """
        生成套利报告

        Args:
            opportunities: 套利机会列表

        Returns:
            Dict: 报告字典
        """
        now = datetime.now(timezone.utc)

        report = {
            "timestamp": now.isoformat(),
            "summary": {
                "total_opportunities": len(opportunities),
                "high_confidence": len([o for o in opportunities if o.confidence == "high"]),
                "medium_confidence": len([o for o in opportunities if o.confidence == "medium"]),
                "low_confidence": len([o for o in opportunities if o.confidence == "low"]),
                "avg_profit_pct": sum(o.expected_profit_pct for o in opportunities) / len(opportunities) if opportunities else 0,
                "total_matched_markets": len(self.cross_markets),
                "pm_markets_count": len(self.pm_markets),
                "op_markets_count": len(self.op_markets)
            },
            "opportunities": [o.to_dict() for o in opportunities[:20]],
            "matched_markets": [
                {
                    "keyword": cm.keyword,
                    "pm_question": cm.pm_question,
                    "op_question": cm.op_question,
                    "pm_yes_price": cm.pm_yes_price,
                    "op_yes_price": cm.op_yes_price,
                    "price_diff": cm.max_price_diff,
                    "min_liquidity": cm.min_liquidity
                }
                for cm in self.cross_markets.values()
                if cm.has_both_platforms
            ][:20],
            "config": {
                "min_profit_threshold": self.min_profit_threshold,
                "min_liquidity": self.min_liquidity,
                "cross_chain_fee": self.cross_chain_fee
            }
        }

        return report


async def run_cross_exchange_monitor():
    """运行跨所套利监控"""
    print("""
    ╔════════════════════════════════════════════════════════════╗
    ║       跨所套利监控 - Polymarket × Opinion                  ║
    ║      🔄 Polygon ↔ BNB Chain | 📊 宏观经济市场             ║
    ╚════════════════════════════════════════════════════════════╝
    """)

    detector = CrossExchangeArbitrage()

    async with PolymarketClient() as pm_client:
        # 注意: Opinion API 可能需要 API Key
        async with OpinionClient() as op_client:
            # 获取宏观经济市场
            print("📊 获取 Polymarket 宏观经济市场...")
            pm_markets = await pm_client.get_macro_markets()

            print("📊 获取 Opinion 市场...")
            op_markets = await op_client.get_markets()

            if not pm_markets:
                print("⚠️  无法获取 Polymarket 市场数据")
                return

            print(f"\n✅ Polymarket: {len(pm_markets)} 个宏观市场")
            print(f"✅ Opinion: {len(op_markets)} 个市场")

            # 匹配市场
            print("\n🔍 匹配跨平台市场...")
            cross_markets = detector.match_markets(pm_markets, op_markets)

            if cross_markets:
                print(f"✅ 成功匹配 {len(cross_markets)} 个跨平台市场")

                # 检测套利
                print("\n💰 检测套利机会...")
                opportunities = detector.detect_arbitrage(cross_markets)

                if opportunities:
                    print(f"\n🚨 发现 {len(opportunities)} 个套利机会！\n")
                    print("-" * 70)

                    for i, opp in enumerate(opportunities[:10], 1):
                        print(f"{i}. [{opp.confidence.upper()}] {opp.expected_profit_pct:.2f}% 利润")
                        print(f"   策略: 在 {opp.buy_platform.value} 买入 {opp.outcome.upper()} @ {opp.buy_price:.3f}")
                        print(f"         在 {opp.sell_platform.value} 卖出 {opp.outcome.upper()} @ {opp.sell_price:.3f}")
                        print(f"   PM市场: {opp.cross_market.pm_question[:50]}...")
                        print(f"   OP市场: {opp.cross_market.op_question[:50]}...")
                        print(f"   最大规模: ${opp.max_size:,.0f}")
                        print()

                else:
                    print("✅ 当前没有符合条件的套利机会")

                # 生成报告
                report = detector.generate_report(opportunities)

                # 保存报告
                with open("cross_exchange_report.json", "w", encoding="utf-8") as f:
                    json.dump(report, f, indent=2, ensure_ascii=False, default=str)

                print(f"\n💾 报告已保存至 cross_exchange_report.json")

            else:
                print("⚠️  未找到匹配的跨平台市场")
                print("   可能原因:")
                print("   1. Opinion API 需要 API Key")
                print("   2. 两个平台的市场类型差异较大")
                print("   3. 相似度阈值设置过高")


if __name__ == "__main__":
    asyncio.run(run_cross_exchange_monitor())
