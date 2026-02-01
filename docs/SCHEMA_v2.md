# 数据 Schema v2 — 支持历史数据

## 设计原则

数据分两类：
1. **自动化采集** — 每日更新，脚本抓取
2. **手动输入** — 用户补充，低频更新

---

## 1. 协议元数据 (protocols.json)

静态信息，变动少：

```json
{
  "pendle": {
    "name": "Pendle",
    "ticker": "PENDLE",
    "category": "yield_tokenization",
    "coingecko_id": "pendle",
    "website": "https://pendle.finance",
    "contracts": {
      "treasury": "0x...",
      "fee_distributor": "0x...",
      "token": "0x..."
    },
    "data_sources": {
      "revenue": "defillama",
      "buyback": "manual",
      "staking_rewards": "chain:fee_distributor"
    }
  }
}
```

---

## 2. 时间序列数据

### 2.1 自动化采集 (daily/)

每日自动更新，按协议存储：

```
data/
├── daily/
│   ├── pendle/
│   │   ├── 2026-01.json    # 按月存储
│   │   └── 2026-02.json
│   ├── aave/
│   └── ...
```

**daily/{protocol}/2026-01.json**:
```json
{
  "protocol": "pendle",
  "period": "2026-01",
  "source": "auto",
  "records": [
    {
      "date": "2026-01-01",
      "price_usd": 1.85,
      "market_cap_usd": 311725000,
      "circulating_supply": 168500000,
      "daily_revenue_usd": 105000,
      "cumulative_revenue_usd": 105000,
      "daily_tev_usd": 84000,
      "cumulative_tev_usd": 84000
    },
    {
      "date": "2026-01-02",
      "price_usd": 1.92,
      "market_cap_usd": 323520000,
      "circulating_supply": 168500000,
      "daily_revenue_usd": 98000,
      "cumulative_revenue_usd": 203000,
      "daily_tev_usd": 78400,
      "cumulative_tev_usd": 162400
    }
    // ...
  ]
}
```

### 2.2 手动输入 (manual/)

用户补充的数据：

```
data/
├── manual/
│   ├── pendle.json
│   ├── aave.json
│   └── ...
```

**manual/aave.json**:
```json
{
  "protocol": "aave",
  "entries": [
    {
      "date": "2025-12-31",
      "type": "annual_report",
      "source": "Aave DAO 年报",
      "source_url": "https://...",
      "data": {
        "net_revenue_usd": 110000000,
        "tev_usd": 35000000,
        "tev_breakdown": {
          "buyback_usd": 35000000,
          "burn_usd": 0,
          "staking_rewards_usd": 0
        }
      },
      "note": "用户于 2026-01-28 补充"
    },
    {
      "date": "2025-06-30",
      "type": "quarterly",
      "source": "估算",
      "data": {
        "net_revenue_usd": 50000000,
        "tev_usd": 15000000
      }
    }
  ]
}
```

---

## 3. 计算逻辑

### TEV Yield 计算

```
trailing_30d_tev = sum(daily_tev_usd) for last 30 days
annualized_tev = trailing_30d_tev * 12
current_market_cap = latest market_cap_usd
tev_yield = annualized_tev / current_market_cap
```

### 历史 TEV Yield 曲线

每个数据点：
```
date: 2026-01-15
tev_yield = (30日滚动 TEV 年化) / (当日市值)
```

这样可以画出历史曲线，看估值高低。

---

## 4. 数据源配置

**data_sources.json**:
```json
{
  "defillama": {
    "type": "api",
    "base_url": "https://api.llama.fi",
    "endpoints": {
      "fees": "/summary/fees/{protocol}",
      "revenue": "/summary/revenue/{protocol}"
    },
    "update_frequency": "daily"
  },
  "coingecko": {
    "type": "api",
    "base_url": "https://api.coingecko.com/api/v3",
    "endpoints": {
      "price": "/simple/price",
      "market_chart": "/coins/{id}/market_chart"
    },
    "update_frequency": "daily"
  },
  "dune": {
    "type": "sql",
    "queries": {
      "sky_buyback": "SELECT ... FROM sky.smart_burn_engine",
      "uni_burn": "SELECT ... FROM uniswap.token_burns"
    },
    "update_frequency": "daily"
  }
}
```

---

## 5. 采集状态

跟踪每个协议的数据采集情况：

```json
{
  "pendle": {
    "last_auto_update": "2026-02-01T08:00:00Z",
    "auto_fields": ["price", "market_cap", "revenue"],
    "manual_fields": ["tev_breakdown"],
    "data_gaps": [],
    "confidence": "high"
  },
  "aave": {
    "last_auto_update": "2026-02-01T08:00:00Z",
    "auto_fields": ["price", "market_cap"],
    "manual_fields": ["revenue", "tev"],
    "data_gaps": ["2025-Q1", "2025-Q2"],
    "confidence": "medium"
  }
}
```
