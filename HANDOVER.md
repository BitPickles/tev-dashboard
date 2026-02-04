# TEV Dashboard 项目交接

## 项目位置
`~/clawd/projects/defi-tev-dashboard/`

## 当前状态

### ✅ 已完成
1. **20 个 DeFi 协议 TEV 调研** — 每个协议都有 `data/protocols/{id}/config.json`
   - 9 个 TEV Active：Aave, Sky, Pendle, Curve, GMX, dYdX, Maple, PancakeSwap, Radiant
   - 4 个 Partial：ether.fi, Ethena, JustLend, Kamino
   - 7 个 None：Lido, EigenLayer, Morpho, Uniswap, Compound, Jito, Spark

2. **首页 `web/index.html`**（46KB）
   - 中英双语、暗色主题
   - 20 协议表格（TVL、TEV 状态、分配比例、市值、TEV Yield）
   - TEV 方法论说明 + 作者简介 + YouTube 嵌入
   - 底部 YouTube CTA banner

3. **详情页 `web/protocol.html`**
   - 从 config.json 动态加载协议信息
   - 展示 TEV 概览、机制详情、数据来源、分析师备注
   - 访问方式：`protocol.html?id=aave`

4. **历史数据**（仅 Aave/Pendle/Sky/Uniswap 有）
   - `data/daily/{protocol}/` 下有月度 JSON + latest.json
   - 其余 16 个协议只有 placeholder latest.json

### 🔜 待做
1. **填充真实数据** — 16 个新协议缺少市值/费用/价格数据，需要写脚本从 CoinGecko + DefiLlama 拉取
2. **历史图表** — protocol.html 有 Chart.js 图表框架但新协议没数据可显示
3. **部署上线** — 目前只能本地 `python3 -m http.server 8080` 预览，可部署到 GitHub Pages 或 Vercel
4. **数据精度** — 用户强调每个 TEV 数据必须有可溯源的来源（tx hash、Dune 查询、报告链接）

## 关键文件
```
web/index.html          — 首页（主表格 + 方法论 + 作者）
web/protocol.html       — 协议详情页
data/protocols/*/config.json — 协议 TEV 配置（核心数据）
data/protocols/README.md     — 调研总结
data/daily/*/latest.json     — 最新数据快照
docs/SCHEMA.md          — 数据 Schema v3 设计
```

## 用户信息
- YouTube: https://www.youtube.com/@Crypto36D
- Twitter: https://x.com/22333D
- 作者定位：「8年加密老兵 | DeFi 实战派」（不是 researcher）
- 语言偏好：中文优先

## 本地预览
```bash
cd ~/clawd/projects/defi-tev-dashboard/web
python3 -m http.server 8080
# 浏览器打开 http://localhost:8080
```
