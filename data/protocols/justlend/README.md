# JustLend TEV 数据维护说明

## 一、TEV 机制

JustLend DAO 2025-10-22 治理通过 **JST Buyback & Burn Program**：
- funding：100% JustLend DAO 净收入 + USDD 多链收益超 $10M 部分
- mechanics：市场买 JST → 发到 TRON Black Hole 永久销毁
- 初始储备 $41.42M（Q4 2026 前分 4 次 burn）

已执行 3 次（**链上链上验证**）：

| Burn | 日期 | JST | USD（公告）| 累计 % |
|------|-----|-----|-----------|--------|
| #1 | 2025-10-19 | 559.89M | $17.7M | 5.66% |
| #2 | 2026-01-14 | 525.00M | $21.0M | 11.00% |
| #3 | 2026-04-15 | 271.34M | $21.3M | **13.70%** |

累计 **1,356,228,332 JST**（= TRON Black Hole `T9yD14Nj9j7xAB4dbGeiX9h8unkKHxuWwb` 当前持仓，精确吻合）

---

## 二、为什么不用 DefiLlama

DefiLlama `justlend` slug 只算 lending interest spread（~$500k/年），完全没算 USDD / stTRX / USDJ 收入。**实际年化 ~$80-120M，DefiLlama 的 ~100 倍**。

按 CLAUDE.md "链上 > 治理 > 估算 > DefiLlama" 原则，直接链上追。

---

## 三、数据源与自动化

| 数据 | 来源 | 频率 |
|---|---|---|
| JST burn 事件 | TRONGrid 免费 API（无 key）`/v1/accounts/{black_hole}/transactions/trc20` | 每日 |
| JST 价格 / 市值 | CoinGecko `just` id | 每日 |
| 主表 yield 聚合 | `sync-tev-data.js` justlend 专属分支 | 每日 |

### 关键合约

- **JST (TRC-20)**: `TCFLL5dx5ZJdKnWuesXxi1VPwjLVmWZZy9`
- **TRON Black Hole**: `T9yD14Nj9j7xAB4dbGeiX9h8unkKHxuWwb`
- **JustLend DAO Buyback Executor**: `TZJVQuU3CJqBScwoxhRtkxQ7JjsNNrpEag`（3 次 burn 源头）

### 维护脚本

- `~/crypto3d-updater/scripts/update-justlend-tev.py`
  - 拉 black hole incoming JST transfers
  - 过滤 amount < 10B JST（排除 TRON approval 伪事件 ~2^256 金额）
  - 过滤 from = JustLend DAO Executor（排除用户随机销毁）
  - 写 `burn-history.json` 和 `tev-records.json`
  - 拉 CoinGecko JST 价格 + 市值

---

## 四、已知局限

1. **季度事件**：burn 3 个月一次，短周期窗口 0 或极高（7d=0% / 30d=38% / 90d=13% / 365d=16%）
2. **TRONGrid rate limit**：免费 tier ~几 QPS，每日一次调用足够
3. **from 过滤**：只认 JustLend DAO Executor（TZJVQuU3...），忽略用户个人 burn 的微量
4. **初始 $41.42M 储备已耗尽**，后续由新季度收入支撑

---

## 五、历史变更

- **2026-04-24**：调研 + 链上双确认；confidence low→high；tevStatus partial→active；A 口径上线
- **2025-10-22**：JustLend DAO 治理通过 JST Buyback & Burn
