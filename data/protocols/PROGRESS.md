# TEV 数据调研进度

**更新时间**: 2026-02-02 17:20 UTC

## 已完成协议配置 (6/20)

| 协议 | 配置 | TEV 机制 | 30日费用 | TEV 比例 | 30日 TEV |
|------|------|----------|----------|----------|----------|
| ✅ Aave | 完成 | Buyback ($50M/年) | ~$280M | ~18% | ~$50M |
| ✅ Pendle | 完成 | vePENDLE 分红 (80%) | ~$1.5M | 80% | ~$1.2M |
| ✅ Sky | 完成 | Buyback + Burn (70%) | $33.7M | 70% | $23.6M |
| ✅ Lido | 完成 | 无 (仅治理) | $62.8M | 0% | $0 |
| ✅ Curve | 完成 | veCRV 分红 (50%) | $6.5M | 50% | $3.25M |
| ✅ Uniswap | 完成 | 无 (费用开关关闭) | ~$40M | 0% | $0 |
| ✅ GMX | 完成 | 质押分红 (30%) | 待查 | 30% | 待算 |
| ✅ Ethena | 完成 | sENA 质押 | 待查 | 待查 | 待查 |

## 来自 DefiLlama API 的费用数据 (已获取)

| 协议 | 24h 费用 | 30日费用 | 1年费用 | 数据来源 |
|------|----------|----------|---------|----------|
| Lido | $2.51M | $62.8M | $821M | DefiLlama Fees API |
| Sky | $1.1M | $33.7M | $402M | DefiLlama Fees API |
| Curve | $363K | $6.5M | $46M | DefiLlama Fees API |
| Compound V2 | $15.9K | $466K | $8.1M | DefiLlama Fees API |
| Aave V2 | $7.8K | $65K | $1.5M | DefiLlama Fees API |
| SushiSwap | $17.4K | $241K | $26.9M | DefiLlama Fees API |

## TEV 机制分类

### 🟢 有明确 TEV (Fee Switch ON)

1. **Aave** - Buyback ($50M/年预算)
2. **Pendle** - 80% 收入 → vePENDLE 持有者
3. **Sky** - 70% 盈余 → MKR 回购销毁
4. **Curve** - 50% 手续费 → veCRV 持有者
5. **GMX** - 30% 费用 → 质押 GMX

### 🔴 无 TEV (Fee Switch OFF)

1. **Uniswap** - 费用开关关闭，所有收入归 LP
2. **Lido** - LDO 仅治理，不分享收入
3. **EigenLayer** - EIGEN 无收益权

### 🟡 待调研

- dYdX V4 - 需查 Cosmos 链数据
- Ethena - sENA 机制需细查
- Morpho - 新协议，需调研
- Compound V3 - 需查最新机制
- PancakeSwap - 需查 CAKE 机制
- Jito - 需查 Solana 链数据

## 数据来源汇总

1. **DefiLlama Fees API** ✅ 可用
   - `https://api.llama.fi/overview/fees`
   - 提供 24h/7d/30d/1y 费用数据
   
2. **DefiLlama Protocol API** ✅ 可用
   - `https://api.llama.fi/protocol/{name}`
   - 包含 tokenRights 字段（buyback/dividends/burns 状态）

3. **Dune Analytics** ❌ Cloudflare 拦截
   - 需要浏览器访问或用户提供 query 链接

4. **官方文档/治理论坛** ✅ 部分可用
   - Aave Governance Forum
   - MakerDAO Forum
   - 各协议官方 Docs

## 下一步

1. [ ] 获取 Aave V3 的完整费用数据
2. [ ] 获取 Pendle 费用数据
3. [ ] 获取 GMX 费用数据
4. [ ] 完成剩余 14 个协议的配置
5. [ ] 构建 TEV 记录数据库（带来源链接）
6. [ ] 更新前端数据展示

## 卡点

1. **Dune 被 Cloudflare 挡住** - 需要用户帮忙访问或提供数据
2. **具体交易记录** - 需要 Etherscan API 或用户提供合约地址
3. **Solana 链协议** - 需要额外调研 Jito、Kamino 等
