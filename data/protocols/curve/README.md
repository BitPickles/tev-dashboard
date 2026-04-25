# Curve TEV 数据维护说明

## 一、口径（2026-04-25 切换）

**主口径**：DefiLlama `dailyHoldersRevenue` × 1.0
- DefiLlama 已映射 FeeAllocator (90% to veCRV) 之后的部分
- 之前用 `dailyRevenue × 0.45` 等于在 90% 之上又少算一半，已撤

**分母**：CRV 流通市值（~$340M）

**结果**：365d holdersRevenue $8.66M / $340M ≈ **2.55%**

## 二、机制（2025-06-27 起 FeeAllocator 激活）

```
Trading fees → 50% LP / 50% admin (DAO)
           → 周度兑换为 crvUSD
           → FeeAllocator: 90% veCRV / 10% Treasury
           → Fee Distributor (0xA464...8922Dc) 按锁仓份额发给 veCRV
```

**只有 veCRV（锁仓 CRV）持有人才捕获**，裸 CRV 持有人 ≈ 0。

## 三、关键地址

| 角色 | 地址 |
|---|---|
| CRV (ERC-20) | `0xD533a949740bb3306d119CC777fa900bA034cd52` |
| veCRV Lock | `0x5f3b5DfEb7B28CDbD7FAba78963EE202a494e2A2` |
| Fee Distributor | `0xA464e6DCda8AC41e03616F95f4BC98a13b8922Dc` |
| Community Fund Treasury (10%) | `0x6508ef65b0bd57eabd0f1d52685a70433b2d290b` |

## 四、Caveats（详情页展示）

1. **veCRV-only**：本 TEV 仅 veCRV 捕获，裸 CRV ≈ 0
2. **Bribes 不计入**：Convex / Stake DAO 投票贿选是 veCRV 额外收入，但来自外部协议
3. **分母失真**：用 CRV 全市值会低估 veCRV 实际 yield；veCRV 无市价，无法独立估值
4. **crvUSD 利息流向比例可调**：5-50% 进 scrvUSD，治理可改

## 五、数据流

- **更新频率**：每日 09:03 / 21:03 由 `sync-tev-data.js` 通用流程更新
- **tev-records 维护**：由 `fetch-tev-history.js` 月度聚合 holdersRevenue
- **新鲜度校验**：`validate-tev-records.py` 监控 26h 阈值
- **无独立 Python 脚本**（DefiLlama 一次拉到位）

## 六、引用

- Curve Resources / Fee Distribution: https://resources.curve.finance/vecrv/fee-collection-distribution/
- FeeAllocator 治理提案: https://gov.curve.finance/t/activate-the-fee-allocator-and-redirect-10-of-revenue-to-community-fund/10676
- Curve Docs / FeeSplitter: https://docs.curve.finance/fees/FeeSplitter/

## 七、未来增强（可选）

- 链上扫描 veCRV 锁仓总量 → 用 "锁仓 CRV 市值" 作分母（更精确反映 veCRV 持有人 yield）
- 把 Bribes 数据并入详情页（标 "外部贿选, 非协议分润"）
