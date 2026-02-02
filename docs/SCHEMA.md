# TEV Dashboard 数据 Schema v3

## 设计原则

**每一笔 TEV 都要有据可查**：
- 链上交易 → 附 tx hash
- Dune 查询 → 附 query 链接
- 官方报告 → 附文章链接
- 治理提案 → 附 snapshot/forum 链接

## 目录结构

```
data/
├── protocols/
│   ├── aave/
│   │   ├── config.json          # 协议基本信息
│   │   ├── tev-records.json     # TEV 记录（带来源）
│   │   └── sources.json         # 数据源汇总
│   ├── pendle/
│   ├── sky/
│   └── uniswap/
└── cache/                       # API 缓存
```

## config.json - 协议配置

```json
{
  "id": "aave",
  "name": "Aave",
  "ticker": "AAVE",
  "icon": "👻",
  "category": "lending",
  "description": "去中心化借贷协议",
  "website": "https://aave.com",
  "docs": "https://docs.aave.com",
  "token": {
    "address": "0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9",
    "chain": "ethereum",
    "coingecko_id": "aave",
    "total_supply": 16000000,
    "circulating_supply": 15000000
  },
  "tev_mechanisms": [
    {
      "type": "buyback_burn",
      "name": "AAVE Buyback",
      "description": "协议收入用于在公开市场回购 AAVE",
      "contract": "0x...",
      "start_date": "2024-07-01"
    },
    {
      "type": "staking_reward",
      "name": "Safety Module",
      "description": "质押 AAVE 获得协议收入分成",
      "contract": "0x4da27a545c0c5B758a6BA100e3a049001de870f5",
      "start_date": "2020-09-01"
    }
  ],
  "confidence": "high",
  "notes": "数据来源主要是 Dune 和官方报告"
}
```

## tev-records.json - TEV 记录

```json
{
  "protocol": "aave",
  "updated_at": "2026-02-02T00:00:00Z",
  "records": [
    {
      "id": "aave-buyback-2026-01-15",
      "date": "2026-01-15",
      "type": "buyback_burn",
      "mechanism": "AAVE Buyback",
      "amount_usd": 1500000,
      "amount_token": 5000,
      "token_price_usd": 300,
      "source": {
        "type": "onchain",
        "chain": "ethereum",
        "tx_hash": "0x...",
        "explorer_url": "https://etherscan.io/tx/0x..."
      },
      "notes": "Weekly buyback execution"
    },
    {
      "id": "aave-sm-reward-2026-01",
      "date": "2026-01-31",
      "type": "staking_reward",
      "mechanism": "Safety Module",
      "amount_usd": 2000000,
      "period": "2026-01",
      "source": {
        "type": "dune",
        "query_id": "123456",
        "query_url": "https://dune.com/queries/123456",
        "query_name": "Aave Safety Module Rewards"
      },
      "notes": "Monthly SM rewards distribution"
    },
    {
      "id": "aave-report-2025-q4",
      "date": "2025-12-31",
      "type": "aggregate",
      "mechanism": "Quarterly Report",
      "amount_usd": 25000000,
      "period": "2025-Q4",
      "source": {
        "type": "report",
        "title": "Aave Q4 2025 Financial Report",
        "url": "https://governance.aave.com/...",
        "publisher": "Aave DAO"
      },
      "breakdown": {
        "buyback": 15000000,
        "safety_module": 8000000,
        "other": 2000000
      }
    }
  ],
  "summary": {
    "total_tev_usd": 50000000,
    "by_mechanism": {
      "buyback_burn": 30000000,
      "staking_reward": 18000000,
      "other": 2000000
    },
    "by_period": {
      "2025-Q4": 25000000,
      "2026-01": 15000000
    }
  }
}
```

## sources.json - 数据源

```json
{
  "protocol": "aave",
  "data_sources": [
    {
      "name": "Aave Dune Dashboard",
      "type": "dune",
      "url": "https://dune.com/aave/aave-revenue",
      "description": "官方 Dune Dashboard",
      "reliability": "high"
    },
    {
      "name": "TokenLogic Reports",
      "type": "report",
      "url": "https://tokenlogic.xyz/aave",
      "description": "Aave 财务服务商报告",
      "reliability": "high"
    },
    {
      "name": "Etherscan Token Tracker",
      "type": "onchain",
      "url": "https://etherscan.io/token/0x...",
      "description": "链上交易记录",
      "reliability": "verified"
    }
  ]
}
```

## TEV 类型定义

| type | 说明 | 示例 |
|------|------|------|
| `buyback_burn` | 回购销毁 | MKR burn, AAVE buyback |
| `buyback_accumulate` | 回购但不销毁 | 协议金库积累 |
| `staking_reward` | 质押分红 | Safety Module, vePENDLE |
| `direct_distribution` | 直接分配 | Fee sharing |
| `ve_reward` | veToken 奖励 | vePENDLE, veCRV |
| `aggregate` | 汇总数据 | 来自季度报告 |

## Source 类型定义

| source.type | 必填字段 | 说明 |
|-------------|----------|------|
| `onchain` | chain, tx_hash, explorer_url | 链上交易 |
| `dune` | query_id, query_url | Dune Analytics |
| `report` | title, url, publisher | 官方/第三方报告 |
| `governance` | proposal_id, url | 治理提案 |
| `api` | endpoint, provider | API 数据源 |

## 数据质量等级

- **verified**: 链上可验证
- **high**: 官方数据源
- **medium**: 第三方可信来源
- **low**: 估算/推断
- **unverified**: 待验证

---

## 待办

- [ ] Aave: 搜集 buyback tx 记录
- [ ] Aave: 搜集 Safety Module 分红数据
- [ ] Pendle: 搜集 vePENDLE 分红记录
- [ ] Sky: 搜集 Smart Burn Engine 回购记录
- [ ] Uniswap: 确认费用开关状态
