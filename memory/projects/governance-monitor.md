# TEV 治理提案监控项目

> 最后更新: 2026-03-20 16:25
> 状态: ✅ 已上线正式站，运营已交接

## 项目概述

为 TEV Dashboard 构建治理提案监控系统，自动采集、翻译、展示 DeFi 协议的治理投票和提案。

## 架构

```
governance-monitor.py (采集脚本)
    ├── Snapshot GraphQL API → 15 个 space
    ├── dYdX Cosmos 提案 API
    ├── BNB Chain GitHub BEPs (需 GITHUB_TOKEN)
    ├── Fluid 论坛 (gov.fluid.io Discourse API)
    ├── Sky/MakerDAO 投票 (vote.makerdao.com via curl)
    ├── Mantle MIP (forum.mantle.xyz Discourse API)
    ├── 9 个 Discourse 论坛 (新提案提醒)
    └── GLM (glm-4-flash) 自动中文翻译

输出 → governance.json → GitHub Pages (dev 分支)
前端 → governance/index.html (协议卡片) + protocol.html (详情页)
```

## 关键文件

| 文件 | 路径 |
|------|------|
| 采集脚本 | `~/.openclaw/workspace-engineer/governance-monitor/governance-monitor.py` |
| 已通知提案记录 | `~/.openclaw/workspace-engineer/governance-monitor/seen_proposals.json` |
| 摘要缓存 | `~/.openclaw/workspace-engineer/governance-monitor/summaries_cache_v2.json` |
| 前端数据 | `~/.openclaw/workspace-engineer/tev-dashboard/data/governance.json` |
| 前端首页 | `~/.openclaw/workspace-engineer/tev-dashboard/governance/index.html` |
| 前端详情页 | `~/.openclaw/workspace-engineer/tev-dashboard/governance/protocol.html` |

## 数据源配置

### Snapshot Spaces (15 个)
```
aavedao.eth, uniswapgovernance.eth, curve.eth, gmx.eth, cakevote.eth,
lido-snapshot.eth, morpho.eth, comp-vote.eth, etherfi-dao.eth,
ethenagovernance.eth, maple.eth, sparkfi.eth, sdpendle.eth,
eigenlayer1.eth, fluiddao.eth
```

### Discourse 论坛 (9 个，用于新提案提醒)
```
Aave: governance.aave.com
Uniswap: gov.uniswap.org
Curve: gov.curve.fi
dYdX: dydx.forum
Lido: research.lido.fi
Morpho: forum.morpho.org
Maker/Sky: forum.makerdao.com
Fluid: gov.fluid.io
Mantle: forum.mantle.xyz
```

### 特殊数据源
- **dYdX Cosmos**: `https://dydx-rest.publicnode.com/cosmos/gov/v1/proposals`
- **BNB BEPs**: `https://api.github.com/repos/bnb-chain/BEPs/issues` (需 GITHUB_TOKEN)
- **Fluid 论坛提案**: `https://gov.fluid.io/c/proposals/9.json` (Discourse API, category 9)
- **Sky/MakerDAO**: `https://vote.makerdao.com/polling` → curl + 解析 `__NEXT_DATA__`
- **Mantle MIP**: `https://forum.mantle.xyz/search.json?q=MIP` (Discourse API)

## API Keys

| Key | 环境变量 | 用途 |
|-----|---------|------|
| 智谱AI GLM | `ZHIPUAI_API_KEY` | 中文翻译 (glm-4-flash) |
| GitHub | `GITHUB_TOKEN` | BNB BEP API (避免 rate limit) |

所有 key 存放在 `~/.openclaw/.env`

⚠️ Python 3.9 + LibreSSL 2.8.3 有 SSL 兼容问题，Snapshot/Script API 通过 `subprocess.run(curl)` 调用。

## Cron 定时任务

| ID | 名称 | 频率 | 说明 |
|----|------|------|------|
| `295fca82-d4f9-4686-ae5a-5c5ff62a5557` | 治理提案监控（每日9点） | `0 9 * * *` | 采集+导出+翻译+推送 dev |

## 当前覆盖状态 (19/25 有提案)

### ✅ 已有数据 (19 个协议, 302 条提案)
| 协议 | 数量 | 数据源 |
|------|------|--------|
| Aave | 21 | Snapshot |
| BNB Chain | 10 | GitHub BEP |
| Compound | 20 | Snapshot |
| Curve | 20 | Snapshot |
| dYdX | 10 | Cosmos API |
| EigenLayer | 2 | Snapshot |
| Ethena | 6 | Snapshot |
| ether.fi | 13 | Snapshot |
| Fluid | 30 | gov.fluid.io 论坛 |
| GMX | 21 | Snapshot |
| Lido | 20 | Snapshot |
| **Mantle** | **19** | **forum.mantle.xyz** |
| Maple Finance | 12 | Snapshot |
| Morpho | 21 | Snapshot |
| PancakeSwap | 16 | Snapshot |
| Pendle | 20 | Snapshot |
| Sky (MakerDAO) | 5 | vote.makerdao.com |
| Spark | 23 | Snapshot |
| Uniswap | 21 | Snapshot |

### ❌ 缺失 (6 个)
| 协议 | 原因 | 可修复性 |
|------|------|---------|
| **Jito** | Solana Realms 治理，不在 Snapshot | 🔸 中 — 需新数据源 |
| **Kamino** | Solana Realms 治理，不在 Snapshot | 🔸 中 — 需新数据源 |
| **Aster** | 新项目，暂无治理平台 | ⛔ 低 |
| **BGB (Bitget)** | CEX 代币，无链上治理 | ⛔ 不适用 |
| **Hyperliquid** | 无治理机制 | ⛔ 不适用 |
| **JustLend** | TRON 生态，治理不透明 | ⛔ 低 |
| **OKB** | CEX 代币，无链上治理 | ⛔ 不适用 |

## Git 信息

- **仓库**: `https://github.com/BitPickles/tev-dashboard.git`
- **分支**: `dev`（⚠️ 主站发版需 Boss 批准）
- **测试站**: `https://bitpickles.github.io/tev-dashboard/governance/`
- **最新 commit**: `452d23a` — BNB BEP + SSL issues fixed, Mantle MIP added

## 待办事项 (按优先级)

1. ~~修 BNB BEP 解析 bug~~ ✅ 已完成
2. ~~修 SSL 问题 (Spark/Sky)~~ ✅ 已完成
3. ~~接入 Mantle~~ ✅ 已完成
4. **调研 Jito/Kamino** — Solana Realms 治理 API
5. **前端优化** — 按需

## 重要规则

- 解读文案**不使用相对时间描述**（如"几天后"），用具体日期或中性表述
- 主站发版**必须经 Boss 批准**
- 翻译用 GLM glm-4-flash，通过 curl 调用（绕过 Python SSL）
