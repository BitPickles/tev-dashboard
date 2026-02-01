# DeFi TEV Dashboard

基于「代币赋能价值 (TEV)」的 DeFi 协议估值数据平台。

## 核心理念

传统 DeFi 数据平台关注 TVL/收入，但忽略了一个关键问题：**收入中有多少真正流向代币持有者？**

本项目以 TEV (Token Empowerment Value) 为核心，追踪：
- 回购销毁
- 质押分红
- 协议分润

帮助投资者用「股东回报」视角评估 DeFi 协议。

## 方法论

| 指标 | 定义 | 传统金融类比 |
|-----|------|-------------|
| Gross Fees | 协议产生的全部费用 | 总收入 |
| Net Revenue | 扣除 LP 分成后的净收入 | 净收入 |
| TEV | 归集到代币持有者的价值 | 股东回报 |
| Earnings Yield | Net Revenue ÷ 市值 | P/E 倒数 |
| TEV Yield | TEV ÷ 市值 | 股息率 |
| Distribution Ratio | TEV ÷ Net Revenue | 派息率 |

**核心公式**: `Net Revenue = 国库留存 + TEV`

## 数据来源

- **自动化**: CoinGecko API, DefiLlama API, Dune Analytics
- **LLM 调研**: 官方年报、治理提案、博客文章
- **人工输入**: 用户纠正、补充资料

## 数据标注

每个数据点标注置信度：
- ✅ **官方数据** - 来自官方年报/公告
- ⚠️ **估算值** - 基于多源推断
- ❓ **待确认** - 数据不足

## 协作模式

- **维护者**: AibotClawd (AI Agent)
- **监督者**: 用户
- **工作流**: 用户可随时纠错、提供资料、给建议

## 目录结构

```
├── data/           # 协议数据 JSON
├── research/       # 调研记录
├── docs/           # 文档
├── scripts/        # 自动化脚本
└── web/            # 前端网站 (待建)
```

## 已覆盖协议

- [ ] Pendle
- [ ] Aave
- [ ] Sky (MakerDAO)
- [ ] Uniswap
- [ ] (更多待扩展)

---

Created: 2026-02-01
