# PancakeSwap (CAKE) TEV 数据维护说明

## 一、口径（2026-04-25 切换）

**主口径**：DefiLlama `dailyHoldersRevenue` × 1.0
- DefiLlama 已映射 burn 部分作 holdersRevenue（91% of revenue）
- 之前用 `dailyRevenue × 0.15` 严重低估

**分母**：CAKE 流通市值 ~$494M

**结果**：$99.9M / $494M ≈ **20.22%**（DefiLlama 口径，含未实际烧毁的 fees pending）

**下界估算**：链上实际 burn ~45M CAKE/yr × $1.45 ≈ $65M → yield ≈ **13%**

## 二、机制（Tokenomics 3.0, 2025-04-23 起）

```
Trading fees (V2/V3) + Perp + Prediction + Lottery + CAKE.PAD
  → Treasury 按比例归集
  → 自动换 CAKE
  → 销毁到 0x000...dEaD
```

veCAKE 已 sunset，原 5% 分红（2025-05-07 终止）已全部转 burn。

**与 JustLend 完全不同**：源头是真实用户 trading fee，无 pocket-to-pocket 嫌疑。

## 三、关键地址

| 角色 | 地址 |
|---|---|
| CAKE (BEP-20) | `0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82` |
| Burn 目的地 | `0x000000000000000000000000000000000000dEaD` |

## 四、Caveats（详情页展示）

1. **DefiLlama 口径不全**：仅覆盖 AMM/StableSwap，可能漏 Perpetual/Prediction/Lottery/CAKE.PAD 等其他销毁源
2. **数字偏高**：DefiLlama $99.9M 比链上实际 burn (~$65M, 45M CAKE/yr) 高 30-40%；可能是 fees-pending-burn 也被计入
3. **veCAKE 已 sunset**：2025-04-23 起原 5% 分红终止
4. **Burn 完全链上可验证**：与 JustLend 那种做账销毁本质不同

## 五、数据流

- **更新频率**：每日 09:03 / 21:03 由 `sync-tev-data.js` 通用流程更新
- **tev-records 维护**：由 `fetch-tev-history.js` 月度聚合
- **新鲜度校验**：`validate-tev-records.py` 监控
- **未来增强**：写专属 script 直查 CAKE→0xdead transfers 求和（精确化）

## 六、引用

- CAKE Tokenomics: https://docs.pancakeswap.finance/protocol/cake-tokenomics
- veCAKE Sunset: https://docs.pancakeswap.finance/welcome-to-pancakeswap/vecake-sunset
- BSCScan burn 持仓: https://bscscan.com/token/0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82?a=0x000000000000000000000000000000000000dead
- 周度 burn 报告: https://blog.pancakeswap.finance/

## 七、历史变更

- 2026-04-25：主口径切到 dailyHoldersRevenue，加 Caveats + calc_pipeline
- 2025-05-07：Revenue Share 5% 终止
- 2025-04-23：veCAKE sunset (Tokenomics 3.0 上线)
