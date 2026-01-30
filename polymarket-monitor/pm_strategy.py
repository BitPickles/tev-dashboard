#!/usr/bin/env python3
"""
Polymarket 三级策略引擎
P0: 已确定事件 (已有结果但未结算) - 最高优先级，~0风险
P1: 高确定性分散 (>=98%, >=50k流动性) - 中等优先级，分散投资
P2: 尾盘狙击 (>=95%, <=6h) - 低优先级，快进快出
"""

import json
import os
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Set
from enum import Enum

from logger import get_logger

logger = get_logger("pm_strategy")


class StrategyTier(Enum):
    """策略等级"""
    P0 = "P0_DETERMINED"  # 已确定事件
    P1 = "P1_HIGH_CERTAINTY"  # 高确定性分散
    P2 = "P2_ENDGAME"  # 尾盘狙击


@dataclass
class StrategyConfig:
    """策略配置"""
    # 总资金配置
    total_capital: float = 1000.0

    # P0: 已确定事件
    p0_allocation: float = 300.0
    p0_max_per_trade: float = 100.0
    p0_min_certainty: float = 0.995  # 99.5% 确定性
    p0_min_liquidity: float = 10000.0

    # P1: 高确定性分散
    p1_allocation: float = 500.0
    p1_max_per_trade: float = 50.0
    p1_min_per_trade: float = 25.0
    p1_min_certainty: float = 0.98  # 98% 确定性
    p1_min_liquidity: float = 50000.0
    p1_max_days: float = 365.0  # 1年内结束 (长期持仓)
    p1_target_markets: int = 15  # 目标分散到15个市场

    # P2: 尾盘狙击
    p2_allocation: float = 200.0
    p2_max_per_trade: float = 20.0
    p2_min_certainty: float = 0.95  # 95% 确定性
    p2_min_liquidity: float = 5000.0
    p2_max_hours: float = 6.0  # 6小时内结束

    # 风险控制
    max_per_trade: float = 100.0  # 单笔最大
    daily_loss_limit: float = 100.0  # 日亏损限制
    cumulative_loss_pause: float = 200.0  # 累计亏损暂停线
    max_category_concentration: float = 0.30  # 单一类别最大占比

    # 排除关键词 (体育等)
    exclude_keywords: List[str] = field(default_factory=lambda: [
        "nba", "nfl", "mlb", "nhl", "super bowl", "finals",
        "mvp", "coach", "stanley cup", "world series",
        "premier league", "champions league", "ufc", "boxing",
        "tennis", "golf", "f1", "formula", "olympics",
        "grizzlies", "lakers", "celtics", "warriors", "knicks",
        "patriots", "seahawks", "chiefs", "eagles", "cowboys",
        "world cup", "fifa", "euro 2024", "copa america"
    ])


@dataclass
class StrategyOpportunity:
    """策略机会"""
    tier: StrategyTier
    market_id: str
    question: str
    outcome: str  # 推荐买入的结果
    price: float  # 当前价格
    certainty: float  # 确定性 (即价格)
    liquidity: float
    hours_left: float
    suggested_amount: float  # 建议投资金额
    expected_return: float  # 预期回报率
    reason: str
    category: str = ""  # 市场类别
    risk_score: float = 0.0  # 风险评分 (0-100)


@dataclass
class Portfolio:
    """投资组合"""
    positions: List[Dict] = field(default_factory=list)
    total_invested: float = 0.0
    p0_invested: float = 0.0
    p1_invested: float = 0.0
    p2_invested: float = 0.0
    daily_pnl: float = 0.0
    cumulative_pnl: float = 0.0
    last_updated: str = ""

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "Portfolio":
        return cls(**data)


class StrategyEngine:
    """策略引擎"""

    def __init__(self, config: Optional[StrategyConfig] = None):
        self.config = config or StrategyConfig()
        self.portfolio = self._load_portfolio()

    def _load_portfolio(self) -> Portfolio:
        """加载投资组合"""
        try:
            if os.path.exists("pm_portfolio.json"):
                with open("pm_portfolio.json", "r") as f:
                    data = json.load(f)
                return Portfolio.from_dict(data)
        except Exception as e:
            logger.warning(f"加载组合失败: {e}")
        return Portfolio()

    def _save_portfolio(self):
        """保存投资组合"""
        self.portfolio.last_updated = datetime.now(timezone.utc).isoformat()
        with open("pm_portfolio.json", "w") as f:
            json.dump(self.portfolio.to_dict(), f, indent=2)

    def _is_excluded(self, question: str) -> bool:
        """检查是否应排除"""
        q_lower = question.lower()
        return any(kw in q_lower for kw in self.config.exclude_keywords)

    def _categorize_market(self, question: str) -> str:
        """对市场分类"""
        q_lower = question.lower()

        # 按优先级检查 (政治 > 体育 > 其他)
        political_keywords = [
            "president", "presidential", "election", "prime minister",
            "trump", "biden", "congress", "senate", "democrat", "republican",
            "governor", "mayor", "nominee", "cabinet", "minister"
        ]
        if any(kw in q_lower for kw in political_keywords):
            return "politics"

        # 体育市场
        sports_keywords = [
            "world cup", "fifa", "nba", "nfl", "nhl", "mlb",
            "stanley cup", "super bowl", "champions league",
            "premier league", "finals", "playoff", "mvp"
        ]
        if any(kw in q_lower for kw in sports_keywords):
            return "sports"

        # 其他类别
        categories = {
            "crypto": ["bitcoin", "ethereum", "crypto", "btc", "eth", "solana"],
            "economy": ["fed", "inflation", "interest rate", "gdp", "recession", "unemployment"],
            "tech": ["ai", "openai", "google", "apple", "microsoft", "meta", "tesla"],
            "entertainment": ["oscar", "grammy", "emmy", "movie", "album", "award"],
        }

        for cat, keywords in categories.items():
            if any(kw in q_lower for kw in keywords):
                return cat

        return "other"

    def _calculate_risk_score(self, certainty: float, hours_left: float, liquidity: float) -> float:
        """计算风险评分 (0-100, 越低越好)"""
        # 确定性越高，风险越低
        certainty_risk = (1 - certainty) * 50

        # 时间越短，风险越低 (对于高确定性)
        time_risk = min(10, hours_left / 24) if hours_left > 0 else 0

        # 流动性越高，风险越低
        liq_risk = max(0, (50000 - liquidity) / 50000 * 20)

        return certainty_risk + time_risk + liq_risk

    def find_p0_opportunities(self, markets: List[Dict]) -> List[StrategyOpportunity]:
        """
        P0: 寻找已确定事件

        标准:
        - 某个结果 >= 99.5% 确定性
        - 流动性 >= $10k
        - 优先选择已有明确结果的事件
        """
        opportunities = []
        available = self.config.p0_allocation - self.portfolio.p0_invested

        if available <= 0:
            return []

        for m in markets:
            if self._is_excluded(m["question"]):
                continue

            if m["liquidity"] < self.config.p0_min_liquidity:
                continue

            prices = m["outcome_prices"]

            for outcome, price in prices.items():
                if price >= self.config.p0_min_certainty:
                    # 计算建议金额
                    expected_return = (1 / price - 1) * 100  # 预期回报百分比
                    suggested = min(
                        self.config.p0_max_per_trade,
                        available,
                        m["liquidity"] * 0.05  # 不超过5%流动性
                    )

                    if suggested < 10:  # 最小投资$10
                        continue

                    risk_score = self._calculate_risk_score(price, m["hours_left"], m["liquidity"])

                    opportunities.append(StrategyOpportunity(
                        tier=StrategyTier.P0,
                        market_id=m["id"],
                        question=m["question"],
                        outcome=outcome,
                        price=price,
                        certainty=price,
                        liquidity=m["liquidity"],
                        hours_left=m["hours_left"],
                        suggested_amount=suggested,
                        expected_return=expected_return,
                        reason=f"几乎确定: {outcome} @ {price:.2%}",
                        category=self._categorize_market(m["question"]),
                        risk_score=risk_score
                    ))
                    break

        # 按风险评分排序 (越低越好)
        return sorted(opportunities, key=lambda x: x.risk_score)[:10]

    def find_p1_opportunities(self, markets: List[Dict]) -> List[StrategyOpportunity]:
        """
        P1: 高确定性分散投资

        标准:
        - 某个结果 >= 98% 确定性
        - 流动性 >= $50k
        - 7天内结束
        - 分散到10-20个市场
        """
        opportunities = []
        available = self.config.p1_allocation - self.portfolio.p1_invested

        if available <= 0:
            return []

        max_hours = self.config.p1_max_days * 24

        for m in markets:
            if self._is_excluded(m["question"]):
                continue

            if m["liquidity"] < self.config.p1_min_liquidity:
                continue

            if m["hours_left"] > max_hours or m["hours_left"] <= 0:
                continue

            prices = m["outcome_prices"]

            for outcome, price in prices.items():
                if price >= self.config.p1_min_certainty:
                    expected_return = (1 / price - 1) * 100

                    # P1 分散投资，每笔 $25-50
                    suggested = min(
                        self.config.p1_max_per_trade,
                        max(self.config.p1_min_per_trade, available / self.config.p1_target_markets),
                        m["liquidity"] * 0.02
                    )

                    if suggested < self.config.p1_min_per_trade:
                        continue

                    risk_score = self._calculate_risk_score(price, m["hours_left"], m["liquidity"])

                    opportunities.append(StrategyOpportunity(
                        tier=StrategyTier.P1,
                        market_id=m["id"],
                        question=m["question"],
                        outcome=outcome,
                        price=price,
                        certainty=price,
                        liquidity=m["liquidity"],
                        hours_left=m["hours_left"],
                        suggested_amount=suggested,
                        expected_return=expected_return,
                        reason=f"高确定性: {outcome} @ {price:.1%}",
                        category=self._categorize_market(m["question"]),
                        risk_score=risk_score
                    ))
                    break

        # 按确定性和流动性排序
        opportunities = sorted(opportunities, key=lambda x: (-x.certainty, -x.liquidity))

        # 分散投资：确保类别分散
        return self._diversify_opportunities(opportunities, self.config.p1_target_markets)

    def find_p2_opportunities(self, markets: List[Dict]) -> List[StrategyOpportunity]:
        """
        P2: 尾盘狙击

        标准:
        - 某个结果 >= 95% 确定性
        - 6小时内结束
        - 流动性 >= $5k
        - 快进快出
        """
        opportunities = []
        available = self.config.p2_allocation - self.portfolio.p2_invested

        if available <= 0:
            return []

        for m in markets:
            if self._is_excluded(m["question"]):
                continue

            if m["liquidity"] < self.config.p2_min_liquidity:
                continue

            if m["hours_left"] > self.config.p2_max_hours or m["hours_left"] <= 0:
                continue

            prices = m["outcome_prices"]

            for outcome, price in prices.items():
                if price >= self.config.p2_min_certainty:
                    expected_return = (1 / price - 1) * 100

                    suggested = min(
                        self.config.p2_max_per_trade,
                        available / 10,  # 分散到约10笔
                        m["liquidity"] * 0.02
                    )

                    if suggested < 10:
                        continue

                    risk_score = self._calculate_risk_score(price, m["hours_left"], m["liquidity"])

                    # 尾盘优先级：时间越紧迫，确定性越高越好
                    priority_score = (1 - m["hours_left"] / 6) * 50 + price * 50

                    opportunities.append(StrategyOpportunity(
                        tier=StrategyTier.P2,
                        market_id=m["id"],
                        question=m["question"],
                        outcome=outcome,
                        price=price,
                        certainty=price,
                        liquidity=m["liquidity"],
                        hours_left=m["hours_left"],
                        suggested_amount=suggested,
                        expected_return=expected_return,
                        reason=f"尾盘机会: {m['hours_left']:.1f}h剩余, {outcome} @ {price:.1%}",
                        category=self._categorize_market(m["question"]),
                        risk_score=risk_score
                    ))
                    break

        # 按剩余时间排序 (越紧迫越优先)
        return sorted(opportunities, key=lambda x: x.hours_left)[:10]

    def _diversify_opportunities(
        self,
        opportunities: List[StrategyOpportunity],
        target_count: int
    ) -> List[StrategyOpportunity]:
        """分散投资选择"""
        if not opportunities:
            return []

        selected = []
        category_counts: Dict[str, int] = {}
        max_per_category = max(2, int(target_count * self.config.max_category_concentration))

        for opp in opportunities:
            cat = opp.category
            current_count = category_counts.get(cat, 0)

            if current_count < max_per_category:
                selected.append(opp)
                category_counts[cat] = current_count + 1

            if len(selected) >= target_count:
                break

        return selected

    def analyze_markets(self, markets: List[Dict]) -> Dict:
        """
        分析市场，返回三级策略机会

        Returns:
            包含 p0, p1, p2 机会列表的字典
        """
        # 检查风控
        risk_status = self._check_risk_controls()

        if risk_status["paused"]:
            logger.warning(f"策略暂停: {risk_status['reason']}")
            return {
                "status": "paused",
                "reason": risk_status["reason"],
                "p0": [],
                "p1": [],
                "p2": [],
                "portfolio": self.portfolio.to_dict(),
                "risk_status": risk_status
            }

        # 寻找各级机会
        p0_opps = self.find_p0_opportunities(markets)
        p1_opps = self.find_p1_opportunities(markets)
        p2_opps = self.find_p2_opportunities(markets)

        # 计算汇总
        summary = {
            "p0_count": len(p0_opps),
            "p1_count": len(p1_opps),
            "p2_count": len(p2_opps),
            "p0_total_suggested": sum(o.suggested_amount for o in p0_opps),
            "p1_total_suggested": sum(o.suggested_amount for o in p1_opps),
            "p2_total_suggested": sum(o.suggested_amount for o in p2_opps),
            "p0_avg_certainty": sum(o.certainty for o in p0_opps) / len(p0_opps) if p0_opps else 0,
            "p1_avg_certainty": sum(o.certainty for o in p1_opps) / len(p1_opps) if p1_opps else 0,
            "p2_avg_certainty": sum(o.certainty for o in p2_opps) / len(p2_opps) if p2_opps else 0,
        }

        return {
            "status": "active",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "summary": summary,
            "p0": [self._opp_to_dict(o) for o in p0_opps],
            "p1": [self._opp_to_dict(o) for o in p1_opps],
            "p2": [self._opp_to_dict(o) for o in p2_opps],
            "portfolio": self.portfolio.to_dict(),
            "risk_status": risk_status,
            "config": {
                "total_capital": self.config.total_capital,
                "p0_allocation": self.config.p0_allocation,
                "p1_allocation": self.config.p1_allocation,
                "p2_allocation": self.config.p2_allocation,
            }
        }

    def _opp_to_dict(self, opp: StrategyOpportunity) -> Dict:
        """转换机会为字典"""
        return {
            "tier": opp.tier.value,
            "market_id": opp.market_id,
            "question": opp.question,
            "outcome": opp.outcome,
            "price": opp.price,
            "certainty": opp.certainty,
            "liquidity": opp.liquidity,
            "hours_left": opp.hours_left,
            "suggested_amount": opp.suggested_amount,
            "expected_return": opp.expected_return,
            "reason": opp.reason,
            "category": opp.category,
            "risk_score": opp.risk_score
        }

    def _check_risk_controls(self) -> Dict:
        """检查风险控制"""
        status = {
            "paused": False,
            "reason": "",
            "daily_loss": self.portfolio.daily_pnl,
            "cumulative_loss": self.portfolio.cumulative_pnl,
            "daily_limit": self.config.daily_loss_limit,
            "cumulative_limit": self.config.cumulative_loss_pause
        }

        # 检查日亏损
        if self.portfolio.daily_pnl < -self.config.daily_loss_limit:
            status["paused"] = True
            status["reason"] = f"日亏损超限: ${abs(self.portfolio.daily_pnl):.0f}"

        # 检查累计亏损
        if self.portfolio.cumulative_pnl < -self.config.cumulative_loss_pause:
            status["paused"] = True
            status["reason"] = f"累计亏损超限: ${abs(self.portfolio.cumulative_pnl):.0f}"

        return status

    def record_trade(
        self,
        tier: StrategyTier,
        market_id: str,
        outcome: str,
        amount: float,
        price: float
    ):
        """记录交易"""
        trade = {
            "tier": tier.value,
            "market_id": market_id,
            "outcome": outcome,
            "amount": amount,
            "price": price,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        self.portfolio.positions.append(trade)
        self.portfolio.total_invested += amount

        if tier == StrategyTier.P0:
            self.portfolio.p0_invested += amount
        elif tier == StrategyTier.P1:
            self.portfolio.p1_invested += amount
        elif tier == StrategyTier.P2:
            self.portfolio.p2_invested += amount

        self._save_portfolio()
        logger.info(f"记录交易: {tier.value} ${amount:.2f} on {outcome}")

    def record_pnl(self, amount: float):
        """记录盈亏"""
        self.portfolio.daily_pnl += amount
        self.portfolio.cumulative_pnl += amount
        self._save_portfolio()

    def reset_daily_pnl(self):
        """重置日盈亏"""
        self.portfolio.daily_pnl = 0.0
        self._save_portfolio()


def test_strategy():
    """测试策略引擎"""
    from pm_monitor import fetch_markets, parse_market

    print("=" * 70)
    print("策略引擎测试")
    print("=" * 70)

    # 获取市场数据
    raw_markets = fetch_markets(500)
    markets = [parse_market(m) for m in raw_markets if parse_market(m)]

    print(f"获取到 {len(markets)} 个市场\n")

    # 初始化策略引擎
    engine = StrategyEngine()

    # 分析市场
    result = engine.analyze_markets(markets)

    print(f"策略状态: {result['status']}")
    print(f"\n汇总:")
    summary = result['summary']
    print(f"  P0 (已确定): {summary['p0_count']} 个机会, 建议投资 ${summary['p0_total_suggested']:.0f}")
    print(f"  P1 (高确定性): {summary['p1_count']} 个机会, 建议投资 ${summary['p1_total_suggested']:.0f}")
    print(f"  P2 (尾盘): {summary['p2_count']} 个机会, 建议投资 ${summary['p2_total_suggested']:.0f}")

    print("\n" + "=" * 70)
    print("P0 - 已确定事件 (最高优先级)")
    print("=" * 70)
    for opp in result['p0'][:5]:
        print(f"\n  {opp['question'][:50]}...")
        print(f"    买入: {opp['outcome']} @ {opp['price']:.2%}")
        print(f"    建议金额: ${opp['suggested_amount']:.0f} | 预期回报: {opp['expected_return']:.2f}%")

    print("\n" + "=" * 70)
    print("P1 - 高确定性分散 (中等优先级)")
    print("=" * 70)
    for opp in result['p1'][:5]:
        print(f"\n  {opp['question'][:50]}...")
        print(f"    买入: {opp['outcome']} @ {opp['price']:.1%}")
        print(f"    建议金额: ${opp['suggested_amount']:.0f} | 类别: {opp['category']}")

    print("\n" + "=" * 70)
    print("P2 - 尾盘狙击 (低优先级)")
    print("=" * 70)
    for opp in result['p2'][:5]:
        print(f"\n  [{opp['hours_left']:.1f}h] {opp['question'][:45]}...")
        print(f"    买入: {opp['outcome']} @ {opp['price']:.1%}")
        print(f"    建议金额: ${opp['suggested_amount']:.0f}")

    # 保存结果
    with open("pm_strategy_result.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\n\n详细结果已保存至 pm_strategy_result.json")


if __name__ == "__main__":
    test_strategy()
