#!/usr/bin/env python3
"""
Polymarket Trading Module
自动下单、取消订单功能
"""

import json
import time
import secrets
import requests
from datetime import datetime
from typing import Dict, Optional, Any
from eth_account import Account

from utils import generate_wallet, get_eip712_auth_headers
from config_manager import get_config_manager
from logger import get_logger

# 获取日志器
logger = get_logger("trading")

# Polymarket API 端点（从配置加载）
_api_base: Optional[str] = None


def get_api_base() -> str:
    """获取 API 基础 URL"""
    global _api_base
    if _api_base is None:
        config = get_config_manager().get_config()
        _api_base = config.api_url
    return _api_base


class PolymarketTrader:
    """Polymarket 交易器"""

    def __init__(self, private_key: str):
        """
        初始化交易器

        Args:
            private_key: EVM 私钥

        Raises:
            ValueError: 如果私钥无效
        """
        if not private_key:
            raise ValueError("私钥不能为空")

        if not private_key.startswith("0x"):
            private_key = "0x" + private_key

        try:
            self.private_key = private_key
            self.account = Account.from_key(private_key)
            self.address = self.account.address
        except Exception as e:
            raise ValueError(f"无效的私钥: {e}")

        logger.info(f"交易器初始化完成，地址: {self.address}")

    def get_auth_headers(self) -> Dict[str, str]:
        """
        生成认证请求头（EIP-712）

        Returns:
            Dict[str, str]: 认证请求头
        """
        return get_eip712_auth_headers(self.private_key)

    def create_order(
        self,
        market_id: str,
        outcome_index: int,
        side: str,
        price: float,
        amount: float,
        expires_in_hours: int = 24,
    ) -> Dict[str, Any]:
        """
        创建订单

        Args:
            market_id: 市场 ID
            outcome_index: 结果索引 (0 或 1)
            side: 买或卖 ("buy" 或 "sell")
            price: 价格 (0-1)
            amount: 数量 (USDC)
            expires_in_hours: 订单有效期（小时）

        Returns:
            Dict: 订单结果
        """
        # 参数验证
        if not market_id:
            return {"success": False, "error": "市场 ID 不能为空"}

        if outcome_index not in [0, 1]:
            return {"success": False, "error": "结果索引必须为 0 或 1"}

        if side.lower() not in ["buy", "sell"]:
            return {"success": False, "error": "交易方向必须为 buy 或 sell"}

        if not 0 < price < 1:
            return {"success": False, "error": "价格必须在 0-1 之间"}

        if amount <= 0:
            return {"success": False, "error": "数量必须大于 0"}

        timestamp = int(time.time())
        expiration = timestamp + (expires_in_hours * 3600)
        salt = int(secrets.token_hex(8), 16)

        order_data = {
            "marketId": market_id,
            "outcomeIndex": outcome_index,
            "side": side.upper(),
            "price": price,
            "amount": amount,
            "expiration": expiration,
            "salt": salt,
            "maker": self.address,
        }

        logger.info(f"创建订单: 市场={market_id}, 方向={side.upper()}, 价格={price}, 数量=${amount}")

        return self._call_api("/orders", "POST", order_data)

    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """
        取消订单

        Args:
            order_id: 订单 ID

        Returns:
            Dict: 取消结果
        """
        if not order_id:
            return {"success": False, "error": "订单 ID 不能为空"}

        logger.info(f"取消订单: {order_id}")
        return self._call_api(f"/orders/{order_id}", "DELETE")

    def get_orders(self, limit: int = 100) -> Dict[str, Any]:
        """
        获取当前订单

        Args:
            limit: 返回数量限制

        Returns:
            Dict: 订单列表
        """
        logger.info("获取订单列表...")
        return self._call_api(f"/orders?limit={limit}", "GET")

    def get_balances(self) -> Dict[str, Any]:
        """
        获取用户余额

        Returns:
            Dict: 余额信息
        """
        logger.info("获取余额...")
        return self._call_api("/balances", "GET")

    def _call_api(
        self,
        endpoint: str,
        method: str = "GET",
        data: Optional[Dict] = None,
        timeout: int = 30
    ) -> Dict[str, Any]:
        """
        调用 Polymarket API

        Args:
            endpoint: API 端点
            method: HTTP 方法
            data: 请求数据
            timeout: 超时时间（秒）

        Returns:
            Dict: API 响应
        """
        url = f"{get_api_base()}{endpoint}"
        headers = self.get_auth_headers()

        try:
            if method == "GET":
                response = requests.get(url, headers=headers, timeout=timeout)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=data, timeout=timeout)
            elif method == "DELETE":
                response = requests.delete(url, headers=headers, timeout=timeout)
            else:
                raise ValueError(f"不支持的 HTTP 方法: {method}")

            logger.debug(f"API 响应: {response.status_code}")

            return {
                "success": response.status_code in [200, 201],
                "status_code": response.status_code,
                "data": response.json() if response.text else None,
                "raw": response.text,
            }

        except requests.Timeout:
            logger.error(f"API 请求超时: {endpoint}")
            return {"success": False, "error": "请求超时"}
        except requests.ConnectionError as e:
            logger.error(f"API 连接错误: {e}")
            return {"success": False, "error": f"连接错误: {e}"}
        except json.JSONDecodeError as e:
            logger.error(f"API 响应解析错误: {e}")
            return {"success": False, "error": f"响应解析错误: {e}"}
        except Exception as e:
            logger.error(f"API 错误: {e}")
            return {"success": False, "error": str(e)}

    def place_arbitrage_trade(
        self,
        opportunity: Dict[str, Any],
        trade_amount: float = 100
    ) -> Dict[str, Any]:
        """
        执行套利交易

        Args:
            opportunity: 套利机会数据
            trade_amount: 交易金额（USDC）

        Returns:
            Dict: 交易结果
        """
        logger.info(f"执行套利交易，金额: ${trade_amount}")

        opp_type = opportunity.get("type", "")

        if opp_type == "surebet":
            return self._execute_surebet(opportunity, trade_amount)
        elif opp_type == "cross_market":
            return self._execute_cross_market_arb(opportunity, trade_amount)
        else:
            logger.error(f"未知的套利类型: {opp_type}")
            return {"success": False, "error": f"未知的套利类型: {opp_type}"}

    def _execute_surebet(
        self,
        opportunity: Dict[str, Any],
        trade_amount: float
    ) -> Dict[str, Any]:
        """
        执行 Surebet 交易

        Args:
            opportunity: 套利机会
            trade_amount: 交易金额

        Returns:
            Dict: 交易结果
        """
        logger.info(f"执行 Surebet，预期利润: {opportunity.get('expected_profit', 0):.2f}%")

        market_id = opportunity.get("market_id")
        if not market_id:
            return {"success": False, "error": "缺少市场 ID"}

        results = []
        for outcome_index in [0, 1]:
            amount = trade_amount / 2

            result = self.create_order(
                market_id=market_id,
                outcome_index=outcome_index,
                side="buy",
                price=0.5,
                amount=amount,
                expires_in_hours=1,
            )
            results.append(result)

        success = all(r.get("success") for r in results)

        return {
            "success": success,
            "type": "surebet",
            "results": results,
            "total_expected_profit": opportunity.get("expected_profit", 0),
        }

    def _execute_cross_market_arb(
        self,
        opportunity: Dict[str, Any],
        trade_amount: float
    ) -> Dict[str, Any]:
        """
        执行跨市场套利

        Args:
            opportunity: 套利机会
            trade_amount: 交易金额

        Returns:
            Dict: 交易结果
        """
        logger.info(f"执行跨市场套利，预期利润: {opportunity.get('expected_profit', 0):.2f}%")

        price1 = opportunity.get("price1", 0)
        price2 = opportunity.get("price2", 0)

        if price1 <= 0 or price2 <= 0:
            return {"success": False, "error": "无效的价格数据"}

        # 确定买卖市场
        if price1 < price2:
            buy_market = opportunity.get("market1_id")
            sell_market = opportunity.get("market2_id")
            buy_price = price1
            sell_price = price2
        else:
            buy_market = opportunity.get("market2_id")
            sell_market = opportunity.get("market1_id")
            buy_price = price2
            sell_price = price1

        if not buy_market or not sell_market:
            return {"success": False, "error": "缺少市场 ID"}

        logger.info(f"买入市场: {buy_market}, 卖出市场: {sell_market}")

        # 下买单
        buy_result = self.create_order(
            market_id=buy_market,
            outcome_index=0,
            side="buy",
            price=buy_price,
            amount=trade_amount,
            expires_in_hours=1,
        )

        # 下卖单
        sell_result = self.create_order(
            market_id=sell_market,
            outcome_index=0,
            side="sell",
            price=sell_price,
            amount=trade_amount,
            expires_in_hours=1,
        )

        success = buy_result.get("success") and sell_result.get("success")

        return {
            "success": success,
            "type": "cross_market",
            "buy_order": buy_result,
            "sell_order": sell_result,
            "total_expected_profit": opportunity.get("expected_profit", 0),
        }


if __name__ == "__main__":
    print("=" * 70)
    print("Polymarket 交易模块测试")
    print("=" * 70)

    pk, addr = generate_wallet()
    print(f"\n新钱包:")
    print(f"  Private Key: {pk}")
    print(f"  Address: {addr}")

    trader = PolymarketTrader(pk)

    balance = trader.get_balances()
    print(f"\n余额查询结果:")
    print(json.dumps(balance, indent=2, ensure_ascii=False))
