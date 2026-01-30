#!/usr/bin/env python3
"""
通知模块 - Telegram 告警
"""

import subprocess
import json
from typing import Optional, List, Dict
from datetime import datetime

from config_manager import get_config_manager
from logger import get_logger

logger = get_logger("notifier")


class TelegramNotifier:
    """Telegram 通知器"""

    def __init__(self, bot_token: str = "", chat_id: str = ""):
        """
        初始化 Telegram 通知器

        Args:
            bot_token: Telegram Bot Token (从 @BotFather 获取)
            chat_id: 目标 Chat ID (用户或群组)
        """
        config = get_config_manager().load_config()

        self.bot_token = bot_token or config.notifications.telegram_bot_token
        self.chat_id = chat_id or config.notifications.telegram_chat_id
        self.enabled = bool(self.bot_token and self.chat_id)

        if self.enabled:
            logger.info("Telegram 通知已启用")
        else:
            logger.warning("Telegram 通知未配置 (缺少 bot_token 或 chat_id)")

    def send_message(self, text: str, parse_mode: str = "HTML") -> bool:
        """
        发送消息

        Args:
            text: 消息内容
            parse_mode: 解析模式 (HTML 或 Markdown)

        Returns:
            bool: 是否发送成功
        """
        if not self.enabled:
            logger.debug("Telegram 未启用，跳过发送")
            return False

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True
        }

        try:
            result = subprocess.run(
                [
                    "curl", "-s", "-X", "POST", url,
                    "-H", "Content-Type: application/json",
                    "-d", json.dumps(payload)
                ],
                capture_output=True,
                text=True,
                timeout=10
            )

            response = json.loads(result.stdout)

            if response.get("ok"):
                logger.info("Telegram 消息发送成功")
                return True
            else:
                logger.error(f"Telegram 发送失败: {response.get('description', 'Unknown error')}")
                return False

        except Exception as e:
            logger.error(f"Telegram 发送异常: {e}")
            return False

    def send_alert(
        self,
        title: str,
        opportunities: List[Dict],
        alert_type: str = "info"
    ) -> bool:
        """
        发送告警

        Args:
            title: 告警标题
            opportunities: 机会列表
            alert_type: 告警类型 (info, warning, urgent)

        Returns:
            bool: 是否发送成功
        """
        if not opportunities:
            return False

        # 选择图标
        icons = {
            "info": "📊",
            "warning": "⚠️",
            "urgent": "🚨"
        }
        icon = icons.get(alert_type, "📊")

        # 构建消息
        now = datetime.now().strftime("%H:%M:%S")
        lines = [
            f"{icon} <b>{title}</b>",
            f"⏰ {now}",
            ""
        ]

        for i, opp in enumerate(opportunities[:10], 1):
            question = opp.get("question", "")[:45]
            reason = opp.get("reason", "")
            liquidity = opp.get("liquidity", 0)

            lines.append(f"<b>{i}.</b> {question}...")
            lines.append(f"   💰 ${liquidity:,.0f} | {reason}")
            lines.append("")

        if len(opportunities) > 10:
            lines.append(f"<i>...还有 {len(opportunities) - 10} 个机会</i>")

        message = "\n".join(lines)

        return self.send_message(message)

    def send_endgame_alert(self, markets: List[Dict]) -> bool:
        """发送尾盘告警"""
        if not markets:
            return False

        lines = [
            "🎯 <b>尾盘市场告警</b>",
            f"⏰ {datetime.now().strftime('%H:%M:%S')}",
            ""
        ]

        for m in markets[:5]:
            hours = m.get("hours_left", 0)
            question = m.get("question", "")[:40]
            prices = m.get("prices", {})
            liquidity = m.get("liquidity", 0)

            # 找出领先方
            if prices:
                leading = max(prices.items(), key=lambda x: x[1])
                price_str = f"{leading[0]} @ {leading[1]:.1%}"
            else:
                price_str = "N/A"

            lines.append(f"⏳ <b>{hours:.1f}h</b> | {question}...")
            lines.append(f"   {price_str} | ${liquidity:,.0f}")
            lines.append("")

        return self.send_message("\n".join(lines))

    def send_politics_alert(self, markets: List[Dict]) -> bool:
        """发送高确定性政治市场告警"""
        if not markets:
            return False

        lines = [
            "🏛️ <b>高确定性政治市场</b>",
            f"⏰ {datetime.now().strftime('%H:%M:%S')}",
            ""
        ]

        for m in markets[:8]:
            question = m.get("question", "")[:40]
            reason = m.get("reason", "")
            liquidity = m.get("liquidity", 0)

            lines.append(f"📌 {question}...")
            lines.append(f"   {reason} | ${liquidity:,.0f}")
            lines.append("")

        return self.send_message("\n".join(lines))

    def send_high_liquidity_alert(self, markets: List[Dict]) -> bool:
        """发送高流动性市场告警"""
        if not markets:
            return False

        lines = [
            "💰 <b>高流动性市场</b>",
            f"⏰ {datetime.now().strftime('%H:%M:%S')}",
            ""
        ]

        for m in markets[:5]:
            question = m.get("question", "")[:40]
            reason = m.get("reason", "")
            liquidity = m.get("liquidity", 0)

            lines.append(f"💎 {question}...")
            lines.append(f"   ${liquidity:,.0f} | {reason}")
            lines.append("")

        return self.send_message("\n".join(lines))

    def send_summary(
        self,
        endgame_count: int,
        politics_count: int,
        high_liq_count: int,
        extreme_count: int
    ) -> bool:
        """发送汇总"""
        lines = [
            "📊 <b>Polymarket 监控汇总</b>",
            f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            f"🎯 尾盘市场: <b>{endgame_count}</b>",
            f"🏛️ 高确定性政治: <b>{politics_count}</b>",
            f"💰 高流动性: <b>{high_liq_count}</b>",
            f"📈 极端价格: <b>{extreme_count}</b>",
        ]

        return self.send_message("\n".join(lines))

    def test_connection(self) -> bool:
        """测试连接"""
        return self.send_message("✅ Polymarket Monitor 连接测试成功!")


def test_telegram():
    """测试 Telegram 通知"""
    notifier = TelegramNotifier()

    if not notifier.enabled:
        print("❌ Telegram 未配置")
        print("请在 config.json 中设置:")
        print('  "notifications": {')
        print('    "telegram_bot_token": "YOUR_BOT_TOKEN",')
        print('    "telegram_chat_id": "YOUR_CHAT_ID"')
        print('  }')
        return

    print("📤 发送测试消息...")
    if notifier.test_connection():
        print("✅ 测试成功!")
    else:
        print("❌ 测试失败")


if __name__ == "__main__":
    test_telegram()
