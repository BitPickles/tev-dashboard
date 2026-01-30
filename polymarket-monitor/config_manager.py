#!/usr/bin/env python3
"""
配置管理模块
统一管理配置加载、验证和默认值
"""

import json
import os
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class ArbitrageConfig:
    """套利检测配置"""
    threshold: float = 0.02  # 套利阈值 (2%)
    liquidity_threshold: float = 1000  # 最小流动性 ($1000)
    surebet_threshold: float = 0.98  # Surebet 阈值
    high_liquidity_min: float = 100000  # 高流动性阈值
    price_anomaly_threshold: float = 0.20  # 价格异常阈值 (20%)
    liquidity_change_threshold: float = 0.50  # 流动性变化阈值 (50%)


@dataclass
class MonitoringConfig:
    """监控配置"""
    enabled: bool = False
    interval_seconds: int = 60
    end_game_window: int = 3600  # 尾盘窗口 (秒)
    max_iterations: int = 100
    meeting_hour: int = 14  # 会议时间
    meeting_minute: int = 0


@dataclass
class TradingConfig:
    """交易配置"""
    enabled: bool = False
    auto_execute_arbitrage: bool = False
    min_profit_threshold: float = 0.5  # 最小利润阈值 (%)
    default_amount: float = 100  # 默认交易金额
    max_amount: float = 1000  # 最大交易金额
    order_expiry_hours: int = 1


@dataclass
class RiskControlConfig:
    """风控配置"""
    max_daily_trades: int = 50
    max_daily_volume: float = 5000
    max_position_per_market: float = 500
    min_profit_threshold: float = 0.5


@dataclass
class NotificationsConfig:
    """通知配置"""
    enabled: bool = False
    webhook_url: str = ""
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""


@dataclass
class AppConfig:
    """应用程序配置"""
    api_url: str = "https://gamma-api.polymarket.com"
    graphql_url: str = "https://gamma-api.polymarket.com/query"
    arbitrage: ArbitrageConfig = field(default_factory=ArbitrageConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    trading: TradingConfig = field(default_factory=TradingConfig)
    risk_control: RiskControlConfig = field(default_factory=RiskControlConfig)
    notifications: NotificationsConfig = field(default_factory=NotificationsConfig)


class ConfigManager:
    """配置管理器"""

    DEFAULT_CONFIG_FILE = "config.json"
    DEFAULT_TRADING_CONFIG_FILE = "trading_config.json"

    def __init__(self, config_file: str = None, trading_config_file: str = None):
        self.config_file = config_file or self.DEFAULT_CONFIG_FILE
        self.trading_config_file = trading_config_file or self.DEFAULT_TRADING_CONFIG_FILE
        self._config: Optional[AppConfig] = None
        self._trading_config: Optional[Dict[str, Any]] = None

    def load_config(self) -> AppConfig:
        """
        加载主配置文件

        Returns:
            AppConfig: 配置对象
        """
        config = AppConfig()

        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # 解析配置
                config.api_url = data.get("api_url", config.api_url)
                config.graphql_url = data.get("graphql_url", config.graphql_url)

                # 套利配置
                config.arbitrage.threshold = data.get("arbitrage_threshold", config.arbitrage.threshold)
                config.arbitrage.liquidity_threshold = data.get("liquidity_threshold", config.arbitrage.liquidity_threshold)

                if "arbitrage" in data:
                    arb = data["arbitrage"]
                    config.arbitrage.surebet_threshold = arb.get("surebet_threshold", config.arbitrage.surebet_threshold)
                    config.arbitrage.high_liquidity_min = arb.get("high_liquidity_min", config.arbitrage.high_liquidity_min)
                    config.arbitrage.price_anomaly_threshold = arb.get("price_anomaly_threshold", config.arbitrage.price_anomaly_threshold)
                    config.arbitrage.liquidity_change_threshold = arb.get("liquidity_change_threshold", config.arbitrage.liquidity_change_threshold)

                # 监控配置
                if "monitoring" in data:
                    mon = data["monitoring"]
                    config.monitoring.enabled = mon.get("enabled", config.monitoring.enabled)
                    config.monitoring.interval_seconds = mon.get("interval_seconds", config.monitoring.interval_seconds)
                    config.monitoring.max_iterations = mon.get("max_iterations", config.monitoring.max_iterations)
                    config.monitoring.meeting_hour = mon.get("meeting_hour", config.monitoring.meeting_hour)
                    config.monitoring.meeting_minute = mon.get("meeting_minute", config.monitoring.meeting_minute)

                config.monitoring.end_game_window = data.get("end_game_window", config.monitoring.end_game_window)

                # 交易配置
                if "trading" in data:
                    trd = data["trading"]
                    config.trading.enabled = trd.get("enabled", config.trading.enabled)
                    config.trading.auto_execute_arbitrage = trd.get("auto_execute_arbitrage", config.trading.auto_execute_arbitrage)
                    config.trading.min_profit_threshold = trd.get("min_profit_threshold", config.trading.min_profit_threshold)

                # 通知配置
                if "notifications" in data:
                    notif = data["notifications"]
                    config.notifications.enabled = notif.get("enabled", config.notifications.enabled)
                    config.notifications.webhook_url = notif.get("webhook_url", config.notifications.webhook_url)
                    config.notifications.telegram_bot_token = notif.get("telegram_bot_token", config.notifications.telegram_bot_token)
                    config.notifications.telegram_chat_id = notif.get("telegram_chat_id", config.notifications.telegram_chat_id)

            except json.JSONDecodeError as e:
                raise ValueError(f"配置文件格式错误: {e}")
            except Exception as e:
                raise ValueError(f"加载配置文件失败: {e}")

        self._config = config
        return config

    def load_trading_config(self) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        加载交易配置文件

        Returns:
            Tuple[bool, Optional[Dict], Optional[str]]: (success, config, error_message)
        """
        if not os.path.exists(self.trading_config_file):
            return False, None, f"交易配置文件不存在: {self.trading_config_file}"

        try:
            with open(self.trading_config_file, "r", encoding="utf-8") as f:
                config = json.load(f)

            # 验证必需字段
            errors = self._validate_trading_config(config)
            if errors:
                return False, None, f"配置验证失败: {', '.join(errors)}"

            self._trading_config = config
            return True, config, None

        except json.JSONDecodeError as e:
            return False, None, f"配置文件格式错误: {e}"
        except Exception as e:
            return False, None, f"加载配置文件失败: {e}"

    def _validate_trading_config(self, config: Dict[str, Any]) -> list:
        """
        验证交易配置

        Args:
            config: 配置字典

        Returns:
            list: 错误列表
        """
        errors = []

        # 检查私钥
        if "private_key" not in config:
            errors.append("缺少 private_key")
        elif not config["private_key"]:
            errors.append("private_key 不能为空")

        # 检查交易配置
        if "trading" not in config:
            errors.append("缺少 trading 配置")
        else:
            trading = config["trading"]
            if "default_amount" in trading and trading["default_amount"] <= 0:
                errors.append("default_amount 必须大于 0")
            if "max_amount" in trading and trading["max_amount"] <= 0:
                errors.append("max_amount 必须大于 0")

        # 检查风控配置
        if "risk_control" not in config:
            errors.append("缺少 risk_control 配置")
        else:
            risk = config["risk_control"]
            if "max_daily_trades" in risk and risk["max_daily_trades"] <= 0:
                errors.append("max_daily_trades 必须大于 0")
            if "max_daily_volume" in risk and risk["max_daily_volume"] <= 0:
                errors.append("max_daily_volume 必须大于 0")

        return errors

    def save_trading_config(self, config: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        保存交易配置

        Args:
            config: 配置字典

        Returns:
            Tuple[bool, Optional[str]]: (success, error_message)
        """
        try:
            # 验证配置
            errors = self._validate_trading_config(config)
            if errors:
                return False, f"配置验证失败: {', '.join(errors)}"

            # 设置文件权限（仅所有者可读写）
            with open(self.trading_config_file, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            # 设置文件权限为 600（仅所有者可读写）
            os.chmod(self.trading_config_file, 0o600)

            self._trading_config = config
            return True, None

        except Exception as e:
            return False, f"保存配置失败: {e}"

    def get_config(self) -> AppConfig:
        """获取配置（如果未加载则加载）"""
        if self._config is None:
            self.load_config()
        return self._config

    def get_trading_config(self) -> Optional[Dict[str, Any]]:
        """获取交易配置"""
        if self._trading_config is None:
            success, config, _ = self.load_trading_config()
            if success:
                return config
            return None
        return self._trading_config


# 全局配置管理器实例
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """获取全局配置管理器"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def load_config() -> AppConfig:
    """加载配置（便捷函数）"""
    return get_config_manager().load_config()


def load_trading_config() -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
    """加载交易配置（便捷函数）"""
    return get_config_manager().load_trading_config()


if __name__ == "__main__":
    # 测试配置加载
    manager = ConfigManager()
    config = manager.load_config()

    print("主配置:")
    print(f"  API URL: {config.api_url}")
    print(f"  套利阈值: {config.arbitrage.threshold}")
    print(f"  流动性阈值: {config.arbitrage.liquidity_threshold}")
    print(f"  监控间隔: {config.monitoring.interval_seconds}s")

    success, trading_config, error = manager.load_trading_config()
    if success:
        print("\n交易配置加载成功")
    else:
        print(f"\n交易配置加载失败: {error}")
