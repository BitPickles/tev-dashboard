# 数据 Schema

## 协议数据结构

```json
{
  "protocol": {
    "name": "Pendle",
    "ticker": "PENDLE",
    "category": "yield_tokenization",
    "website": "https://pendle.finance",
    "coingecko_id": "pendle"
  },
  
  "market_data": {
    "price_usd": 1.88,
    "circulating_supply": 168500000,
    "market_cap_usd": 316780000,
    "fdv_usd": null,
    "updated_at": "2026-01-28"
  },
  
  "financials": {
    "period": "FY2025",
    
    "gross_fees_usd": 40000000,
    "gross_fees_source": "official",
    "gross_fees_note": "5% 收益费 + 交易费",
    
    "net_revenue_usd": 38000000,
    "net_revenue_source": "official",
    "net_revenue_ratio": 0.95,
    
    "tev_usd": 31000000,
    "tev_breakdown": {
      "buyback_usd": 0,
      "burn_usd": 0,
      "staking_rewards_usd": 31000000,
      "other_usd": 0
    },
    "tev_source": "official",
    "tev_note": "80% → vePENDLE 分成",
    
    "treasury_retained_usd": 7000000
  },
  
  "metrics": {
    "earnings_yield": 0.12,
    "tev_yield": 0.098,
    "distribution_ratio": 0.80
  },
  
  "tokenomics": {
    "annual_inflation": 27000000,
    "inflation_note": "周释放 ~600K，递减 1.1%/周",
    "burn_mechanism": false,
    "buyback_program": false,
    "staking_rewards": true
  },
  
  "data_quality": {
    "overall_confidence": "high",
    "has_official_report": true,
    "report_url": "https://...",
    "last_researched": "2026-01-28",
    "notes": "官方 2025 年报 + Medium 确认"
  },
  
  "sources": [
    {
      "url": "https://pendle.finance/2025-report",
      "type": "official",
      "accessed_at": "2026-01-28"
    }
  ]
}
```

## 字段说明

### data_quality.overall_confidence
- `high`: 官方年报/公告，数据完整
- `medium`: 第三方数据源，或部分估算
- `low`: 主要靠推断，数据缺口大

### financials.xxx_source
- `official`: 官方年报/公告
- `third_party`: Token Terminal / DefiLlama 等
- `estimate`: LLM 估算
- `user_input`: 用户提供

### category 分类
- `lending`: 借贷 (Aave, Compound)
- `dex`: 去中心化交易所 (Uniswap, Curve)
- `yield_tokenization`: 收益代币化 (Pendle)
- `stablecoin`: 稳定币 (Sky/Maker, Frax)
- `liquid_staking`: 流动性质押 (Lido, Rocket Pool)
- `perpetuals`: 永续合约 (GMX, dYdX)
- `options`: 期权 (Lyra, Dopex)
- `other`: 其他

## 计算公式

```
earnings_yield = net_revenue_usd / market_cap_usd
tev_yield = tev_usd / market_cap_usd
distribution_ratio = tev_usd / net_revenue_usd
```
