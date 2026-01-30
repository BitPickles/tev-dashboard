# Polymarket Monitor

Polymarket 三级策略监控系统 - 自动扫描和筛选预测市场机会

## 功能特点

### 三级策略筛选
- **P0 已确定事件**：>=99.5% 确定性，几乎无风险
- **P1 高确定性分散**：>=98% 确定性，分散投资到多个市场
- **P2 尾盘狙击**：>=95% 确定性，6小时内结束

### 风险控制
- 单笔投资上限
- 日亏损限额
- 累计亏损暂停线
- 自动排除体育市场
- 类别分散（避免集中）

### Web 界面
- 实时显示策略机会
- 投资组合仪表盘
- 风控状态指示
- 30秒自动刷新

### Telegram 通知（可选）
- P0/P2 机会告警
- 汇总报告

## 快速开始

```bash
# 克隆项目
git clone https://github.com/yourusername/polymarket-monitor.git
cd polymarket-monitor

# 运行一次扫描
python3 pm_monitor.py

# 启动循环监控（每5分钟）
python3 pm_monitor.py --loop

# 启动 Web 界面
python3 pm_web.py
# 访问 http://localhost:8080
```

## 策略配置

默认配置（$1000 本金）：

| 等级 | 配额 | 确定性 | 流动性 | 单笔上限 |
|-----|------|-------|--------|---------|
| P0 已确定 | $300 | >=99.5% | >=$10k | $100 |
| P1 高确定性 | $500 | >=98% | >=$50k | $50 |
| P2 尾盘 | $200 | >=95% | >=$5k | $20 |

风控参数：
- 日亏损限额：$100
- 累计亏损暂停：$200
- 单笔最大：$100

可在 `pm_strategy.py` 中的 `StrategyConfig` 类修改参数。

## 命令行参数

```bash
# 基本扫描
python3 pm_monitor.py

# 静默模式（不发送 Telegram）
python3 pm_monitor.py --no-telegram

# 循环监控模式
python3 pm_monitor.py --loop

# 自定义扫描间隔（分钟）
python3 pm_monitor.py --loop --interval=3

# 测试 Telegram 连接
python3 pm_monitor.py --test-telegram
```

## 文件说明

```
├── pm_monitor.py       # 主监控程序
├── pm_strategy.py      # 三级策略引擎
├── pm_web.py           # Web 界面（零依赖）
├── notifier.py         # Telegram 通知
├── config_manager.py   # 配置管理
├── logger.py           # 日志模块
├── utils.py            # 工具函数
├── config.example.json # 配置示例
└── requirements.txt    # 依赖
```

## Telegram 配置（可选）

1. 从 @BotFather 创建 Bot 获取 token
2. 获取 Chat ID
3. 创建配置文件：

```bash
cp config.example.json config.json
```

```json
{
  "notifications": {
    "telegram_bot_token": "YOUR_BOT_TOKEN",
    "telegram_chat_id": "YOUR_CHAT_ID"
  }
}
```

## 输出示例

```
======================================================================
🎯 P0 - 已确定事件 (最高优先级, $300 配额)
======================================================================

1. Will X become the next Prime Minister...
   买入: No @ 99.95%
   建议: $100 | 流动性: $111,111

======================================================================
📊 P1 - 高确定性分散 (中等优先级, $500 配额)
======================================================================

1. [politics] Will Y win the election...
   买入: Yes @ 98.5%
   建议: $33 | 剩余: 168h

======================================================================
💼 投资组合 & 风控状态
======================================================================
   已投资: P0 $0 | P1 $0 | P2 $0
   日盈亏: $0 (限额: $100)
   ✅ 状态: 正常运行
```

## API 说明

项目使用 Polymarket Gamma API：
- 端点：`https://gamma-api.polymarket.com/markets`
- 无需 API Key
- 使用 curl 请求（零依赖设计）

## 输出文件

- `pm_opportunities.json` - 扫描结果
- `pm_portfolio.json` - 投资组合状态
- `pm_monitor.log` - 运行日志

## 注意事项

⚠️ **风险提示**

- 本项目仅供学习研究，不构成投资建议
- 预测市场存在风险，请谨慎投资
- 建议先用小额资金测试策略
- 高确定性不等于100%确定，黑天鹅事件可能发生

## License

MIT
