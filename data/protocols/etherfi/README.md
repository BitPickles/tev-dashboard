# ether.fi (ETHFI) TEV 数据维护说明

## 一、口径

**主口径**：DefiLlama `dailyRevenue` × tevRatio 0.25
- 365d revenue $55.7M × 0.25 = $13.9M
- 与 DefiLlama dailyHoldersRevenue $15.5M 一致（独立校验）

**分母**：ETHFI 流通市值 ~$729M（FDV $1.04B；用流通因解锁仍在）

**结果**：$13.9M / $729M ≈ **1.9%**

## 二、机制（仅 ETHFI 持有人捕获的部分）

```
User eETH 提现 → 提现费（慢速 + 0.3% 快速）
              → Foundation Multisig (0x7A6A...)
              → 月度回购 ETHFI（市场买入）
              → 分配给 sETHFI 质押者
```

**只有 stake ETHFI 拿 sETHFI** 才能接收回购分配，裸 ETHFI 不直接拿。

## 三、关键地址

| 角色 | 地址 |
|---|---|
| ETHFI (ERC-20) | `0xFe0c30065B384F05761f15d0CC899D4F9F9Cc0eB` |
| Foundation Multisig (回购执行) | `0x7A6A41F353B3002751d94118aA7f4935dA39bB53` |

## 四、Caveats（详情页展示）

1. **eETH 收益 ≠ ETHFI TEV**：易混淆。eETH 拿 ~3.2% ETH 原生收益（给 eETH 持有者），ETHFI TEV 是 sETHFI 质押者拿到的回购分配
2. **$50M Treasury Buyback (pocket-to-pocket 嫌疑)**：价格<$3 启用，资金来自 Foundation 国库——需定期核 Multisig 链上是否真转出执行；做账式回购应排除
3. **裸 ETHFI 不参与**：必须 stake → sETHFI
4. **流通 vs FDV**：当前用流通；用 FDV $1.04B 会把 yield 降到 ~1.3%

## 五、数据流

- **更新频率**：每日 09:03 / 21:03 由 `sync-tev-data.js` 通用流程更新
- **tev-records 维护**：由 `fetch-tev-history.js` 月度聚合
- **新鲜度校验**：`validate-tev-records.py` 监控 26h 阈值
- **无独立 Python 脚本**

## 六、链上验证方法

- Foundation Multisig 0x7A6A...: 看 ETH/USDT 转出 + ETHFI 流入
- 月度 buyback tx: Etherscan 看 Multisig outgoing
- $50M Treasury 是否启动: 核国库地址有无大额 USDC/USDT 转出

## 七、引用

- DAO Proposal #11 (Withdrawal Revenue Buyback): https://governance.ether.fi/t/11-ether-fi-dao-proposal-withdrawal-revenue-buyback-program/2920
- $50M Treasury Buyback 提案: https://governance.ether.fi/t/ether-fi-dao-proposal-treasury-deployment-for-ethfi-buy-back-program/3178
- Dune (回购+收入): https://dune.com/ether_fi/ethfi-buybacks-and-protocol-revenue-sources

## 八、历史变更

- 2026-04-25：tev_yield 修正到 1.9%（之前一度算成 67.48%——分母用了 $343M 旧市值）；加 Caveats + calc_pipeline
- 2025-10-30：$50M Treasury Buyback 提案通过
- 2025-04-25：Withdrawal Revenue Buyback 启动
