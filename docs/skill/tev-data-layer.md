# TEV 数据层规范

> 本文档定义 crypto3d.pro TEV（Token Economic Value）数据的核心方法论、公式口径、数据源规范、以及每新增一个协议时的工作流程。是 CLAUDE.md 里"核心公式不可更改"规则的权威定义文件。

---

## 一、TEV 是什么

**TEV = Token 持有人实际能捕获的价值**（年化，以 USD 计）。

不是协议总收入（那是 Revenue），不是 TVL（那是锁仓量），不是价格涨幅。TEV 刻画的是"协议通过哪些机制把价值流向 token 持有人"。

**TEV Yield** = TEV USD ÷ 代币市值（全流通或循环，取决于协议口径）

---

## 二、核心原则：每个协议 TEV 独立

**不能用通用公式给所有协议批量算 TEV**。

原因：每个协议"价值怎么传给 token 持有人"的机制完全不一样——

| 协议 | 机制 | TEV 计算方式 |
|---|---|---|
| Aave | DAO 年度回购预算 | 固定 $50M/年（不依赖 fee） |
| Pendle | 80% 收入给 vePENDLE | fee × 80% |
| Sky | 70% 盈余回购销毁 MKR | 盈余 × 70% |
| Curve | 50% fee 给 veCRV | fee × 50% |
| Uniswap | fee switch（目前关） | 接近 0 |
| Lido | LDO 只治理，无分润 | 0 |
| **BNB** | Auto-Burn + BEP-95 + asBNB 质押 | 供给收缩 + 质押收益（无 fee 分润） |
| **HYPE** | AF 回购 + spot 手续费销毁 | treasury buyback + 真实销毁 |

**机械套"fee × ratio"会严重失真**：
- BNB 没有 fee 分润 → 正确 TEV 是 ~11-12%，机械套会算出错误值
- HYPE 的 AF 买入不等于销毁（是 treasury），需标注可被动用风险
- Lido 根本没 TEV，硬给一个比例会得到虚假的数字

---

## 三、三件事框架

每接手一个新协议，先回答三个问题：

### 1. 机制是什么

- 是 fee 分润？回购？销毁？质押奖励？多种组合？
- 有没有治理提案/白皮书明确定义了比例？
- 这个机制是否稳定（季度事件 vs 连续流？）？
- 有没有 "看起来像 TEV 但其实不是" 的陷阱（如 HYPE 的 AF 买入其实是 treasury）？

### 2. 拿数据的逻辑

数据源优先级（**CLAUDE.md 铁律**）：

```
链上 > 官方治理 > 估算 > DefiLlama
```

- **链上**：BscScan/Etherscan/链上合约事件、区块遍历。最权威但实施复杂。
- **官方治理**：governance forum 提案（Aave AIP / Maker MIP / etc）、官方年报。有明确数字但可能滞后。
- **估算**：基于公开数据推算（TokenLogic 报告等）。有不确定性。
- **DefiLlama**：`dailyFees` / `dailyRevenue` / `dailyHoldersRevenue`。方便但需验证口径。

**关键**：`dailyRevenue` ≠ `dailyFees`。
- `dailyFees` = 总手续费
- `dailyRevenue` = 协议归属部分（扣除 LP 分润）
- `dailyHoldersRevenue` = 归 token 持有人部分

不同协议这三个口径不同，**要逐个协议验证**（如 Hyperliquid 上 revenue = holdersRevenue）。

### 3. 计算逻辑

把原始数据套进 TEV 公式，注意：

- **年化因子**：7d 年化 = 金额 × 365/7；30d = × 365/30；365d 不年化（已是 365 天累计）
- **USD 口径**：用当前价重估（历史 BNB/HYPE 按现在 $XX 算）还是用历史价（按销毁当日的 $XX 算）——两种都合理，但要一致且在 analyst_notes 说清楚
- **多周期一致性**：TEV Yield 和 Earning Yield 的周期公式必须一致（不能一个变另一个不变）

---

## 四、周期口径的典型陷阱

### 陷阱 1：季度事件不能用滚动窗口

**例子**：BNB Auto-Burn 一年 4 次。如果 30 天窗口抓不到 burn 事件，滚动窗口年化 = 0，严重低估。

**解决**：季度性机制用"近 4 季度"稳定态，或短周期/长周期双口径。

### 陷阱 2：BNB 的双口径

- **短周期（7/30/90d）**：近 4 季 `usd_value` 累加（每次 burn 公告时的历史 USD）= 官方披露口径，固定到下次 burn
- **365d**：近 4 季 `bnb_burned` × 当前价（重估）= 按市价年化

差异反映 BNB 价格变动。两个口径都有意义，用户切换能看到趋势。

### 陷阱 3：连续性数据必须时间序列

**例子**：BNB BEP-95 每天波动（27~632 BNB/天）。用"周均 × 52"硬算 = 看不到波动。

**解决**：存日时间序列（`bep95-history.json`），各周期按窗口求和。

---

## 五、三层更新机制

| 层级 | 频率 | 实现方式 | 举例 |
|---|---|---|---|
| **日度自动** | 每天 | cron 脚本 | 市值（CoinGecko）、链上数据（RPC）、DefiLlama revenue |
| **季度半自动** | 3 个月 | 脚本告警 + 人工确认 | BNB 新 Auto-Burn、治理提案变更 |
| **事件驱动** | 不定 | 纯人工 | asBNB APY、tokenomics 改版、新机制上线、AF 被动用 |

### 日度自动的实现

主流程：`~/crypto3d-updater/update.sh`（LaunchAgent `com.crypto3d.data-updater` 每日 9:03/21:03）

```
Step 3: TEV + 协议数据
  ├── fetch-*.py                各协议的专属数据采集
  ├── update-bnb-tev.py         BNB 专属（BEP-95 累积 + 市值 + Auto-Burn 检测）
  ├── update-hype-tev.py        HYPE 链上校验
  └── ...

Step 4: TEV 协议汇总
  └── sync-tev-data.js          聚合所有协议，重算 yield → 写入 data/all-protocols.json
```

### 校验脚本

对用 DefiLlama 作主数据源的协议，**强烈建议**加链上校验脚本（如 `update-hype-tev.py`）：
- 每日拉链上真实状态（AF 余额、dead address 余额等）
- 和 DefiLlama 数字对比，差异 > 阈值告警
- 不修改主数据流，只做"哨兵"

---

## 六、文件布局

### 每协议标准文件

```
data/protocols/<id>/
  ├── config.json            # 元数据、机制、analyst_notes、tev_data 计算说明
  ├── tev-records.json       # TEV 历史记录（可选，部分协议有）
  ├── README.md              # 协议专属文档（机制/数据源/自动化/调试）
  └── [协议特有的时间序列文件]
       - burn-history.json   # BNB 的季度 burn + asBNB
       - bep95-history.json  # BNB 的 BEP-95 日时间序列
       - af-history.json     # HYPE 的 AF buyback 日时间序列
       - af-snapshot.json    # HYPE 的链上校验 snapshot
       - dead-balance-snapshot.json  # BNB 的链上校验 snapshot
```

### config.json 关键字段

```jsonc
{
  "id": "...",
  "name": "...",
  "ticker": "...",
  "category": "...",
  "tev_mechanisms": [       // 每个机制：type/name/description/status/source
    {
      "type": "buyback | burn | staking_reward | dividend | ...",
      "source": { "type": "governance|official|contract|api", "url": "..." }
    }
  ],
  "tev_data": {
    "tev_yield_percent": 12.78,   // 365d，由脚本刷新
    "methodology": "...",          // 计算方法说明
    "calculation": "...",          // 具体公式
    "sources": [...],              // 数据来源
    "caveats": [...],              // 已知缺陷/注意事项
    "validation": {...}            // 链上校验数据
  },
  "analyst_notes": "...",          // 深度中文说明（Markdown）
  "confidence": "high | medium | low",
  "confidence_reason": {"zh": "...", "en": "..."},
  "tevRatio": 1.0 | null | 0,     // null 表示不适用（无 fee 分润），0 表示有 fee 但 0% 给持有人
  "tevRatioNote": "...",           // 当 tevRatio=null 时用它解释
  "display_precision": 3,          // 可选，默认 2。某些占比极小的协议（如 BNB）用 3
  "last_updated": "YYYY-MM-DD"
}
```

### 主表 data/all-protocols.json

```jsonc
{
  "generated_at": "...",
  "protocols": {
    "<id>": {
      // 从各协议 config.json 聚合而来（由 sync-tev-data.js 写入）
      "tev_yield_percent": 12.78,     // 365d
      "earning_yield_percent": 12.78, // 365d
      "market_cap_usd": 7368065201,
      "tvl": 5326286571,
      "tevRatio": 1,
      "confidence": "high",
      "tevStatus": "active",
      "metrics": {
        "trailing_7d_revenue_usd": 13459322,
        "trailing_30d_revenue_usd": 55375124,
        "trailing_90d_revenue_usd": 189940000,
        "trailing_365d_revenue_usd": 941960000,
        "tev_yield_7d_ann": 9.52,
        "tev_yield_30d_ann": 9.14,
        "tev_yield_90d_ann": 10.51,
        "earning_yield_7d_ann": 9.52,
        "earning_yield_30d_ann": 9.14,
        "earning_yield_90d_ann": 10.51
      },
      "display_precision": 3     // 可选
    }
  }
}
```

---

## 七、前端渲染约定

- 主表 `tev/index.html`：读 `data/all-protocols.json`
- 详情页 `tev/protocol.html`：读 `data/protocols/<id>/config.json`（**两边可能不同步，改动要两边核对**）

### 精度

默认 2 位小数。某些协议 TEV 贡献占比极小（如 BNB 的 BEP-95 ≈ 0.02%），2 位小数会吞掉周期差异——这类协议在 config.json 标 `display_precision: 3`，前端据此渲染。

### tevRatio 显示

| tevRatio 值 | 前端显示 | 含义 |
|---|---|---|
| 数字 > 0 | `{v*100}%` | 明确的分润比例 |
| `'dynamic'` | `dynamic` | 动态计算，不是固定比例 |
| `null` | `—` | 不适用（协议无 fee 分润机制，如 BNB） |
| `0` | `—` | 有 fee 但 0% 给持有人（但前端当前和 null 一样处理）|

### tevRatio 按周期独立

分配率（tevRatio = TEV ÷ Earning）**应该随周期变化**，如果 TEV 和 Earning 用独立 signal。主表切换周期时需同步变。

对 `TEV = Earning × 固定 ratio` 的协议（Pendle/Curve/dYdX 等），四个周期 ratio 数学上就相等，不用特别处理。

对 `TEV` 和 `Earning` 用独立 signal 的协议（Sky 用 holdersRevenue vs revenue；Aave 用固定 $30M vs 动态 fee；BNB 用 burn+asBNB vs fee 等）——需在主表 entry 里写四个字段：

```json
{
  "tevRatio_7d":   0.0789,
  "tevRatio_30d":  0.0790,
  "tevRatio_90d":  0.3193,
  "tevRatio_365d": 0.4830,
  "tevRatio": 0.4830  // 顶层保留，= tevRatio_365d，向后兼容
}
```

前端 `tev/index.html` 按当前周期 fallback 到 `tevRatio_Xd`，未填的字段 fallback 到顶层 `tevRatio`。

---

## 八、新增协议工作流

按主表默认顺序（`有 tev_yield > 0 优先 + 市值降序`）逐个做：

1. **调研机制**（optional subagent）：读 governance forum、官方文档、tokenomics。搞清楚"价值怎么传给持有人"
2. **分类**：
   - 有明确 fee 分润比例 → 用主分支（tevRatio × DefiLlama revenue）
   - 独立机制（BNB/HYPE 类）→ 加到 `sync-tev-data.js` 的专属分支
3. **数据源**：
   - 能用 DefiLlama 就用（必须验证 dailyRevenue 口径是否等于归属持有人部分）
   - 否则写独立采集脚本（参考 `update-bnb-tev.py` / `update-hype-tev.py`）
4. **链上校验**（推荐）：至少写一个 snapshot 法脚本，对比 DefiLlama 和链上，差异告警
5. **文档**：在 `data/protocols/<id>/README.md` 写清楚机制、数据源、手动介入触发条件、调试命令
6. **前端验收**：
   - 推 `dev` 分支
   - 让 Boss 在 https://bitpickles.github.io/tev-dashboard 测试站看
   - 明确指出要验收的几个点（具体到 "第 X 行 X 列显示 Y"）
   - Boss 点头后再做下一个

---

## 九、部署纪律（同 CLAUDE.md）

1. 所有开发在 `dev` 分支完成
2. Push `dev` → GitHub Pages 测试站自动部署
3. 向 Boss 展示测试站效果，**等待确认**
4. Boss 确认后才 merge `dev` → `main`，push `main`
5. Push `main` 自动触发 Cloudflare Pages 部署到正式站
6. **严禁未经验证直接 push main**
7. 唯一例外：安全修复类紧急变更可直接推 main，但必须说明原因

---

## 十、已踩过的坑清单

从做 BNB 和 Hyperliquid 学到的：

1. **周期同值陷阱**：把 4 个周期填同一个值让周期切换失去意义（BNB v1 被否决）
2. **上次事件 × 4**：用最近一次 burn 乘 4 作为年化，不如用"近 4 季累加"（BNB v2 被否决）
3. **AF 买入 ≠ 销毁**：treasury buyback 可被 consensus 动用，不是真 burn（Hyperliquid 修正）
4. **DefiLlama 口径**：`dailyRevenue` 对不同协议可能不同，必须逐个验证（HYPE 上 revenue=holdersRevenue，其他协议未必）
5. **365d 字段被遗漏**：早期 SKIP_PROTOCOLS 分支只算 7/30/90d，365d 停留在手写 stale 值
6. **TEV vs Earning 不自洽**：tevRatio=1 时 TEV 应等于 Earning；如果其中一个刷新另一个不刷新，会有数学矛盾
7. **精度吞掉差异**：BEP-95 占比 0.02%，2 位小数四周期都显示 6.89%，要加 `display_precision: 3`
8. **tevRatio = 0 显示"0%"误导**：无 fee 分润的协议用 `null`，让前端渲染 `—`
9. **前端两套数据源**：主表和详情页读不同 JSON，改动要两边同步
10. **旧文件僵尸**：根目录 `all-protocols.json`（8.5MB 垃圾）没人用但脚本还在生成。保留备份但不依赖

---

## 附录：BNB 和 HYPE 的具体实现

详见 `data/protocols/bnb/README.md` 和 `data/protocols/hype/README.md`。

---

## 十一、部署日志

| 日期 | 协议 | 变更 | commit | 状态 |
|---|---|---|---|---|
| 2026-04-19 | BNB | TEV 周期口径修正 + BEP-95 日时间序列 + 自动更新脚本 + 文档 | `2a7bfc4` | ✅ 已上 main（正式站） |
| 2026-04-19 | Hyperliquid | AF 口径修正（不是 burn）+ 365d bug 修复 + 链上校验 + 文档 | `02c6747` | ✅ 已上 main（正式站） |
| 2026-04-19 | — | 新增 TEV 总规范文档 | `4be0332` | ✅ 已上 main |
| 2026-04-22 | Uniswap | 切换到链上直查 0xdead burn（A 口径）+ 链上数据核实 + 每日增量脚本 + 文档 | `c2bff2e1` | ✅ 已上 main |
| 2026-04-22 | Sky (MakerDAO) | 切换到 DefiLlama `dailyHoldersRevenue` 口径（= Splitter burn 部分）；链上核实 MKR/SKY@0xdead 几乎为 0（SBE burn LP token 非 MKR 本身）；动态 tevRatio 替代写死 fixedTevUsd；文档 | — | 🚧 dev，待验收 |

每次协议上线后应在本表追加一行，形成可追溯的 changelog。
