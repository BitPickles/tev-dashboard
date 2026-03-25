# Polymarket × Opinion 跨所套利策略

## 平台对比

| 特性 | Polymarket | Opinion |
|------|------------|---------|
| **链** | Polygon (Chain ID: 137) | BNB Chain (Chain ID: 56) |
| **交易模型** | Hybrid CLOB | On-chain CLOB |
| **结算货币** | USDC | USDC/BNB |
| **手续费** | 0% Maker/Taker | 低费用 |
| **预言机** | UMA Optimistic Oracle | AI Oracle (Opinion AI) |
| **主要市场** | 政治、体育、加密、宏观 | 宏观经济 |
| **API** | REST + WebSocket | REST + WebSocket |
| **SDK** | py-clob-client | opinion-clob-sdk |
| **累计交易量** | $10B+ | $3.1B+ |

## 市场重叠分析

### 高度重叠的市场类型

1. **Fed 利率决议**
   - "Fed decision in January" / "Fed cuts rates in January"
   - "How many Fed rate cuts in 2026?"
   - "Fed decision in March"

2. **通胀/CPI 数据**
   - "US CPI prints above 3%"
   - "Inflation above X% in Q1"

3. **宏观经济指标**
   - GDP 增长预测
   - 失业率预测
   - 经济衰退概率

4. **Fed 主席相关**
   - "Who will Trump nominate as Fed Chair?"
   - "Will Powell be reappointed?"

## 套利策略

### 策略 1: 价格差异套利

```
条件: 同一事件在两个平台价格差异 > 2%

示例:
- PM: Fed January "No change" = 96%
- OP: Fed January "No change" = 93%
- 差异: 3%

操作:
1. 在 Opinion 买入 "No change" @ $0.93
2. 在 Polymarket 卖出 "No change" @ $0.96
3. 净利润: 3% - 跨链费用(~0.5%) = 2.5%
```

### 策略 2: 对冲套利

```
条件: 两平台价格和 < 1 (扣除费用后)

示例:
- PM YES = $0.45, PM NO = $0.52 (总和 = 0.97)
- OP YES = $0.48, OP NO = $0.50 (总和 = 0.98)

操作:
1. 在 PM 买入全部结果 @ $0.97
2. 无论结果如何，获得 $1.00
3. 净利润: 3% - 费用
```

### 策略 3: 时间差套利

```
条件: 重大事件公布时，两平台反应速度不同

操作:
1. 监控 CPI/Fed 等数据发布
2. 快速在反应慢的平台建仓
3. 等待价格收敛后平仓
```

## 风险因素

### 1. 结算风险 (Resolution Risk)
- **问题**: 两平台可能对同一事件有不同的结算规则
- **缓解**: 仔细阅读两边的结算规则，只交易规则明确一致的市场

### 2. 跨链延迟 (Cross-chain Latency)
- **问题**: Polygon ↔ BSC 跨链需要时间
- **缓解**:
  - 预先在两边准备资金
  - 使用跨链桥（如 Multichain, Stargate）
  - 考虑 10-30 分钟的结算延迟

### 3. 流动性风险 (Liquidity Risk)
- **问题**: 大额订单可能导致滑点
- **缓解**:
  - 限制单笔交易规模为流动性的 10%
  - 使用限价单而非市价单

### 4. Oracle 差异风险
- **问题**: UMA vs Opinion AI 可能有不同裁决
- **缓解**:
  - 只交易客观可验证的事件
  - 避免模糊定义的市场

## 技术实现

### 资金准备

```
Polygon (Polymarket):
├── USDC: $10,000+
├── MATIC: 少量用于 Gas
└── 授权: USDC → Exchange 合约

BNB Chain (Opinion):
├── USDC: $10,000+
├── BNB: 少量用于 Gas
└── API Key: 从 Opinion 申请
```

### 监控流程

```
1. 每 30 秒获取两边市场数据
2. 匹配相似市场（相似度 > 40%）
3. 计算价格差异
4. 过滤条件:
   - 利润 > 2%（扣除跨链费用后）
   - 流动性 > $1,000
5. 生成告警 / 自动执行
```

### API 端点

**Polymarket:**
```
Markets: GET https://gamma-api.polymarket.com/markets
CLOB: https://clob.polymarket.com
认证: EIP-712 签名
```

**Opinion:**
```
Markets: GET https://proxy.opinion.trade:8443/markets
Orderbook: GET https://proxy.opinion.trade:8443/orderbook/{token_id}
认证: X-API-Key header
```

## 预期收益

| 场景 | 频率 | 单次利润 | 月收益估计 |
|------|------|---------|-----------|
| 常规价差 | 10次/天 | 1-2% | 30-60% |
| 重大事件 | 5次/月 | 3-5% | 15-25% |
| 异常波动 | 2次/月 | 5-10% | 10-20% |

**风险提示**: 以上为理论估计，实际收益受市场条件、执行速度、资金规模等因素影响。

## 运行方式

```bash
# 安装依赖
pip install aiohttp py-clob-client opinion-clob-sdk

# 配置 API Key (config.json)
{
  "cross_exchange": {
    "platforms": {
      "opinion": {
        "api_key": "YOUR_OPINION_API_KEY"
      }
    }
  }
}

# 运行监控
python cross_exchange_arbitrage.py
```

## 下一步

1. [ ] 申请 Opinion API Key
2. [ ] 在两边准备测试资金
3. [ ] 运行监控程序验证市场匹配
4. [ ] 小额测试执行流程
5. [ ] 评估跨链桥选择（Stargate, Multichain 等）
6. [ ] 逐步放大规模
