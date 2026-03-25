# 推特日报系统 — Phase 1 任务书

> 交给工程师执行

## 目标

每天上午 10:00 自动发布一条推文到 @Crypto3DChannel，包含：
1. 一条有引爆点的中文推文文案（100-200 字）
2. 一张信息图海报（PNG，暗色主题）

## 数据源

所有数据在 `~/.openclaw/workspace-engineer/tev-dashboard/` 下：

### 指标数据（4 个）
| 指标 | 文件 | 当前值示例 |
|------|------|-----------|
| AHR999 | `indicators/data/ahr999.json` → `.current.value` `.current.status` `.current.price` | 0.3666, 抄底区, $71,225 |
| MVRV | `indicators/data/mvrv.json` → `.current.value` `.current.status` | 1.31, 合理区 |
| BMRI | `indicators/data/bmri.json` → `.["1m"].current.value` `.["1m"].current.regime` | 47.43, NEUTRAL |
| BTC.D | `indicators/data/btc-dominance.json` → `.current.value` `.current.zone` | 58.43%, BALANCED |

### TEV 数据
- `data/all-protocols.json` → 各协议 TEV Yield、市值、收入
- `data/governance.json` → 治理提案动态

### 指标含义参考
- `docs/skill/indicators/ahr999.md`
- `docs/skill/indicators/mvrv.md`
- `docs/skill/indicators/bmri.md`
- `docs/skill/indicators/btc-dominance.md`

## 推文文案生成

### AI 选题逻辑
每天把 4 个指标最新值 + 变化量 + 治理动态喂给 AI，让它选最有话题性的 1 个焦点。

### 选题优先级
1. **指标进入关键区间**（AHR999 进抄底区、MVRV > 3 过热、BMRI < 30 风险低）
2. **指标日/周变化显著**（BTC.D 单日 > 1%、AHR999 穿越阈值）
3. **重大治理动态**（回购调整、费用分配变更等 tev_related 提案）
4. **兜底**：按周几固定轮换（周一 AHR999、周二 BTC.D、周三 MVRV、周四 BMRI、周五治理、周末回顾）

### 文案风格
- 中文为主，专有名词英文
- 100-200 字，不面面俱到
- 数据驱动 + 有观点 + 引导讨论（问句结尾）
- 带话题标签：#Crypto3D #BTC #DeFi（根据内容选）
- 附带网站链接：https://crypto3d.pro

### 文案示例
```
📊 AHR999 跌至 0.37，进入抄底区间。

上次出现这个位置是 2024 年 9 月，随后 BTC 从 $54K 涨到 $100K。当前 BTC $71,225，200日成本线 $93,199。

MVRV 1.31 处于合理区，市场没有过热迹象。

历史不会简单重复，但定投窗口值得关注 🎯

完整数据 → crypto3d.pro

#Crypto3D #BTC #AHR999
```

## 海报设计

### 风格：信息图（暗色主题）
- 和网站 crypto3d.pro 风格一致
- 背景色：#0a0a0b
- 文字色：#fafafa（主）/ #a1a1aa（次）/ #71717a（辅）
- 强调色：#22c55e（绿/正向）/ #ef4444（红/警示）/ #3b82f6（蓝）
- 字体：Inter / Noto Sans SC
- 尺寸：1200x675px（推特推荐 16:9）

### 海报布局
```
┌─────────────────────────────────────────┐
│  [Logo] Crypto3D Daily    March 19, 2026│  ← 顶部品牌栏
│─────────────────────────────────────────│
│                                         │
│  🔥 焦点区域（大字）                      │
│  AHR999 = 0.37                          │
│  ██████████░░░░░░░░ 抄底区间             │  ← 进度条/图形化展示
│  BTC $71,225 | 200日成本 $93,199        │
│                                         │
│─────────────────────────────────────────│
│  其他指标（小字一行带过）                  │
│  MVRV 1.31 合理 | BMRI 47 中性 | BTC.D 58.4% │
│─────────────────────────────────────────│
│  📊 crypto3d.pro                        │  ← 底部水印
└─────────────────────────────────────────┘
```

### 技术实现
- 用 HTML/CSS 写一个海报模板页面
- 数据通过 JS 从 JSON 文件读取
- 用 Playwright/Puppeteer 截图生成 PNG
- 模板文件放在 `~/.openclaw/workspace-engineer/tev-dashboard/poster/` 下

## 发推流程

### 浏览器模拟发推
- 使用 Playwright 模拟前端操作
- 不需要 Twitter API，直接浏览器登录态操作
- 账号：@Crypto3DChannel
- 需要先手动登录一次，保存 session

### 发布脚本
```
poster-daily.py (或 .sh)
  1. 读取 4 个指标 JSON + governance.json
  2. AI 选题 + 生成文案（用 GLM-5 或其他可用模型）
  3. 渲染海报 HTML → 截图 PNG
  4. Playwright 打开 twitter.com → 写推文 → 上传图片 → 发布
  5. 记录发布结果到 log
```

### Cron 配置
- 时间：每天 09:50 生成 + 10:00 发布
- 通过 OpenClaw cron 配置

## 输出文件

| 文件 | 说明 |
|------|------|
| `poster/template.html` | 海报 HTML 模板 |
| `poster/poster-daily.py` | 主脚本（采集+选题+渲染+发推）|
| `poster/output/YYYY-MM-DD.png` | 每日海报存档 |
| `poster/output/YYYY-MM-DD.json` | 每日推文记录 |

## 注意事项
- 所有中文内容，专有名词保留英文
- 海报不要太多文字，信息图为主
- 推文和海报内容互补：文字抛问题，图片给数据
- 暂时不接新闻源（Phase 2 再做）
- ⚠️ 主站发版需 Boss 批准，海报系统不涉及主站代码修改
