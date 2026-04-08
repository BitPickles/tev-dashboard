#!/usr/bin/env python3
"""
自动交易监控程序
整合市场监控、套利检测和自动下单
"""

import json
import os
import sys
from datetime import datetime
from typing import Dict, Any, Optional

from trading import PolymarketTrader
from utils import generate_wallet, validate_private_key, validate_price, validate_amount
from config_manager import ConfigManager, get_config_manager
from logger import get_logger

# 获取日志器
logger = get_logger("auto_trader")


class AutoTrader:
    """自动交易器"""

    def __init__(self):
        """初始化自动交易器"""
        print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║       Polymarket 自动交易器                                  ║
    ║      📊 实时监控 | 🔁 套利检测 | 💰 自动下单                 ║
    ╚══════════════════════════════════════════════════════════════╝
        """)

        self.config_manager = get_config_manager()
        self.config = self.config_manager.load_config()

        # 加载交易配置
        success, self.trading_config, error = self.config_manager.load_trading_config()
        if not success:
            logger.error(f"无法加载交易配置: {error}")
            print(f"❌ {error}")
            print("   请复制 trading_config.example.json 为 trading_config.json 并填入你的私钥")
            sys.exit(1)

        # 初始化交易器
        try:
            self.trader = PolymarketTrader(self.trading_config["private_key"])
        except ValueError as e:
            logger.error(f"初始化交易器失败: {e}")
            print(f"❌ 初始化交易器失败: {e}")
            sys.exit(1)

        # 统计
        self.daily_trades = 0
        self.daily_volume = 0.0
        self.last_reset_date = datetime.now().date()

        # 显示配置信息
        trading = self.trading_config.get("trading", {})
        risk = self.trading_config.get("risk_control", {})

        print(f"🔐 交易地址: {self.trader.address}")
        print(f"💰 默认交易额: ${trading.get('default_amount', 100)}")
        print(f"🎯 最小利润阈值: {risk.get('min_profit_threshold', 0.5)}%")
        print(f"🔁 自动套利: {'启用' if trading.get('auto_arbitrage', False) else '禁用'}")

    def check_daily_limits(self) -> bool:
        """检查每日限额"""
        today = datetime.now().date()
        if today != self.last_reset_date:
            self.last_reset_date = today
            self.daily_trades = 0
            self.daily_volume = 0.0
            logger.info(f"每日限额已重置 (日期: {today})")

        risk = self.trading_config.get("risk_control", {})
        max_trades = risk.get("max_daily_trades", 50)
        max_volume = risk.get("max_daily_volume", 5000)

        if self.daily_trades >= max_trades:
            logger.warning(f"已达到每日最大交易次数 ({max_trades})")
            return False

        if self.daily_volume >= max_volume:
            logger.warning(f"已达到每日最大交易金额 (${max_volume})")
            return False

        return True

    def check_risk_limits(self, amount: float, market_id: str) -> bool:
        """检查单个市场持仓限额"""
        risk = self.trading_config.get("risk_control", {})
        max_position = risk.get("max_position_per_market", 500)

        if amount > max_position:
            logger.warning(f"交易金额 ${amount} 超过单市场最大限额 ${max_position}")
            return False

        return True

    def execute_arbitrage(self, opportunity: Dict[str, Any]) -> Dict[str, Any]:
        """执行套利交易"""
        print("\n" + "=" * 70)
        print("💎 检测到套利机会！")
        print("=" * 70)

        trading = self.trading_config.get("trading", {})
        risk = self.trading_config.get("risk_control", {})

        # 检查是否启用自动套利
        if not trading.get("auto_arbitrage", False):
            logger.info("自动套利未启用，跳过执行")
            return {"success": False, "reason": "auto_arbitrage_disabled"}

        # 检查利润阈值
        min_profit = risk.get("min_profit_threshold", 0.5)
        expected_profit = opportunity.get("expected_profit", 0)

        if expected_profit < min_profit:
            logger.info(f"利润 {expected_profit:.2f}% 低于最小阈值 {min_profit}%")
            return {"success": False, "reason": "profit_below_threshold"}

        # 检查每日限额
        if not self.check_daily_limits():
            return {"success": False, "reason": "daily_limit_reached"}

        # 计算交易金额
        default_amount = trading.get("default_amount", 100)
        max_amount = trading.get("max_amount", 1000)
        trade_amount = min(default_amount, max_amount)

        # 检查单笔交易限额
        market_id = opportunity.get("market_id", opportunity.get("market1_id", ""))
        if not self.check_risk_limits(trade_amount, market_id):
            return {"success": False, "reason": "risk_limit"}

        # 执行交易
        result = self.trader.place_arbitrage_trade(opportunity, trade_amount)

        # 更新统计
        if result.get("success"):
            self.daily_trades += 1
            self.daily_volume += trade_amount

            max_trades = risk.get("max_daily_trades", 50)
            max_volume = risk.get("max_daily_volume", 5000)

            logger.info(f"交易成功！每日交易: {self.daily_trades}/{max_trades}, 金额: ${self.daily_volume:,.0f}/${max_volume:,.0f}")
        else:
            logger.error(f"交易失败: {result.get('error', 'Unknown')}")

        return result

    def _get_validated_input(
        self,
        prompt: str,
        validator: callable,
        error_msg: str = "输入无效"
    ) -> Optional[Any]:
        """
        获取并验证用户输入

        Args:
            prompt: 提示信息
            validator: 验证函数
            error_msg: 错误提示

        Returns:
            验证后的值或 None
        """
        try:
            value = input(prompt).strip()
            if not value:
                return None
            return validator(value)
        except ValueError as e:
            print(f"❌ {error_msg}: {e}")
            return None
        except KeyboardInterrupt:
            return None

    def manual_trade_menu(self) -> bool:
        """手动交易菜单"""
        print("\n" + "=" * 70)
        print("🎯 手动交易模式")
        print("=" * 70)

        print("\n请选择操作:")
        print("  1. 查询余额")
        print("  2. 查询订单")
        print("  3. 创建买单")
        print("  4. 创建卖单")
        print("  5. 取消订单")
        print("  6. 执行套利交易")
        print("  0. 退出")

        choice = input("\n请输入选项: ").strip()

        try:
            if choice == "1":
                balance = self.trader.get_balances()
                print(json.dumps(balance, indent=2, ensure_ascii=False))

            elif choice == "2":
                orders = self.trader.get_orders()
                print(json.dumps(orders, indent=2, ensure_ascii=False))

            elif choice in ["3", "4"]:
                side = "buy" if choice == "3" else "sell"
                self._handle_create_order(side)

            elif choice == "5":
                order_id = input("订单 ID: ").strip()
                if order_id:
                    result = self.trader.cancel_order(order_id)
                    print(json.dumps(result, indent=2, ensure_ascii=False))
                else:
                    print("❌ 订单 ID 不能为空")

            elif choice == "6":
                self._handle_arbitrage_trade()

            elif choice == "0":
                return False

            else:
                print("❌ 无效的选项")

        except KeyboardInterrupt:
            print("\n操作已取消")
        except Exception as e:
            logger.error(f"操作失败: {e}")
            print(f"❌ 操作失败: {e}")

        return True

    def _handle_create_order(self, side: str):
        """处理创建订单"""
        print(f"\n创建{side}单:")

        # 市场 ID
        market_id = input("市场 ID: ").strip()
        if not market_id:
            print("❌ 市场 ID 不能为空")
            return

        # 结果索引
        try:
            outcome_index = int(input("结果索引 (0/1): ").strip())
            if outcome_index not in [0, 1]:
                print("❌ 结果索引必须为 0 或 1")
                return
        except ValueError:
            print("❌ 结果索引必须是数字")
            return

        # 价格
        try:
            price = float(input("价格 (0-1): ").strip())
            valid, error = validate_price(price)
            if not valid:
                print(f"❌ {error}")
                return
        except ValueError:
            print("❌ 价格必须是数字")
            return

        # 数量
        try:
            amount = float(input("数量 (USDC): ").strip())
            valid, error = validate_amount(amount)
            if not valid:
                print(f"❌ {error}")
                return
        except ValueError:
            print("❌ 数量必须是数字")
            return

        # 创建订单
        result = self.trader.create_order(
            market_id=market_id,
            outcome_index=outcome_index,
            side=side,
            price=price,
            amount=amount,
        )

        print(json.dumps(result, indent=2, ensure_ascii=False))

    def _handle_arbitrage_trade(self):
        """处理套利交易"""
        print("\n输入套利机会信息:")

        market_id = input("市场 ID: ").strip()
        if not market_id:
            print("❌ 市场 ID 不能为空")
            return

        try:
            expected_profit = float(input("预期利润 (%): ").strip())
            if expected_profit <= 0:
                print("❌ 预期利润必须大于 0")
                return
        except ValueError:
            print("❌ 预期利润必须是数字")
            return

        opportunity = {
            "type": "surebet",
            "market_id": market_id,
            "market": f"Market {market_id}",
            "expected_profit": expected_profit,
        }

        result = self.execute_arbitrage(opportunity)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    def run_manual_mode(self):
        """运行手动交易模式"""
        print("\n" + "🎯" * 35)
        print("进入手动交易模式")
        print("🎯" * 35)

        while True:
            try:
                if not self.manual_trade_menu():
                    break
            except KeyboardInterrupt:
                print("\n\n退出手动交易模式")
                break


def setup_trading_config():
    """设置交易配置"""
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║       Polymarket 交易配置                                    ║
    ╚══════════════════════════════════════════════════════════════╝
    """)

    print("\n选项:")
    print("  1. 生成新钱包")
    print("  2. 使用现有私钥")
    print("  0. 退出")

    choice = input("\n请选择: ").strip()

    if choice == "1":
        # 生成新钱包
        print("\n🔐 正在生成新钱包...")
        pk, addr = generate_wallet()

        print(f"\n✅ 新钱包已生成！")
        print(f"   地址: {addr}")
        print(f"   私钥: {pk}")
        print(f"\n⚠️  重要：请保存好私钥！丢失后无法恢复！")

        _save_trading_config(pk)

    elif choice == "2":
        pk = input("\n请输入私钥: ").strip()

        if not pk:
            print("❌ 私钥不能为空")
            return

        # 验证私钥
        valid, addr, error = validate_private_key(pk)
        if not valid:
            print(f"❌ 无效的私钥: {error}")
            return

        print(f"\n✅ 私钥有效！")
        print(f"   地址: {addr}")

        save = input("\n是否保存到配置文件? (y/n): ").strip().lower()
        if save == "y":
            if not pk.startswith("0x"):
                pk = "0x" + pk
            _save_trading_config(pk)

    elif choice == "0":
        return

    print("\n✅ 配置完成！")


def _save_trading_config(private_key: str):
    """保存交易配置"""
    config = {
        "private_key": private_key,
        "trading": {
            "enabled": False,
            "default_amount": 100,
            "max_amount": 1000,
            "order_expiry_hours": 1,
            "auto_arbitrage": False,
        },
        "risk_control": {
            "max_daily_trades": 50,
            "max_daily_volume": 5000,
            "max_position_per_market": 500,
            "min_profit_threshold": 0.5
        }
    }

    manager = get_config_manager()
    success, error = manager.save_trading_config(config)

    if success:
        print(f"\n💾 配置已保存到 trading_config.json")
        print("   （文件权限已设置为仅所有者可读写）")
    else:
        print(f"\n❌ 保存配置失败: {error}")


def main():
    """主函数"""
    config_file = "trading_config.json"

    # 检查是否已配置
    if not os.path.exists(config_file):
        print("\n⚠️  尚未配置交易设置")
        setup_trading_config()

        if input("\n是否进入手动交易模式? (y/n): ").strip().lower() == "y":
            if os.path.exists(config_file):
                trader = AutoTrader()
                trader.run_manual_mode()
    else:
        print("\n模式选择:")
        print("  1. 重新配置")
        print("  2. 手动交易")
        print("  3. 退出")

        choice = input("\n请选择: ").strip()

        if choice == "1":
            setup_trading_config()
        elif choice == "2":
            trader = AutoTrader()
            trader.run_manual_mode()


if __name__ == "__main__":
    main()
