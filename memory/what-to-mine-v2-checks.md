# what-to-mine-v2 最终验收报告

## 验收时间：2026-03-25 19:50

### ✅ Build 状态：通过
Next.js build 成功，所有路由正常输出。

---

### Phase 1 验收

| ID | 任务 | 状态 | 证据 |
|----|------|------|------|
| p1-e1-01 | Schema 新增字段 | ✅ 通过 | prisma schema 已含 yieldBreakdown/capacityUsed/capacityTotal/countdownEnabled/bossTags |
| p1-e1-02 | Session maxAge 7→30天 | ⚠️ 未完成 | `src/app/api/auth/verify/route.ts:57` 仍为 `maxAge: 7 * 24 * 60 * 60 // 7天` |
| p1-e1-03 | 路由重构(无需登录浏览) | ✅ 通过 | 详情页 `src/app/opportunity/[id]/page.tsx` 在公开路由下，(auth) 仅包裹 share 页 |
| p1-e1-04 | 导航栏6菜单+灰显 | ✅ 通过 | PrimaryNav.tsx 含矿田/短债/策略/复盘/公告雷达/日历，disabled=true 灰显 |
| p1-e1-05 | API筛选参数 | ✅ 通过 | opportunity-discovery.ts 含 channels/capacityRange/duration/sort 筛选逻辑 |
| p1-e2-01 | OpportunityCard | ✅ 通过 | 文件存在，含 APR/收益构成/容量进度/倒计时/角标/标签 |
| p1-e2-02 | 筛选栏组件 | ✅ 通过 | FilterBar.tsx + OpportunityExplorer.tsx 含多选筛选 |
| p1-e2-03 | 角标系统 | ✅ 通过 | BadgeSystem.tsx + StatusBadge.tsx 含动画效果 |
| p1-d-01 | 卡片设计 | ✅ 通过 | 暗色主题已落地，CSS token 化 |
| p1-d-02 | 角标+导航设计 | ✅ 通过 | 5种角标样式 + 导航灰显态 |

### Phase 2 验收

| ID | 任务 | 状态 | 证据 |
|----|------|------|------|
| p2-e1-01 | 详情页API | ✅ 通过 | 详情页含参与指南/Boss评价/更新流/相关公告 |
| p2-e1-02 | 后台排序+切状态 | ✅ 通过 | admin/OpportunitiesBulkTable.tsx 含 DndContext 拖拽排序 |
| p2-e1-03 | /all 页面API | ✅ 通过 | src/app/all/page.tsx 全状态展示 |
| p2-e2-01 | 首页矿田集成 | ✅ 通过 | src/app/page.tsx 引入 OpportunityExplorer |
| p2-e2-02 | 详情页重构 | ✅ 通过 | 详情页含概览/参与指南/Boss评价/时间线/侧边信息 |
| p2-e2-03 | /all 全部机会 | ✅ 通过 | 已结束灰显 + 实际收益对比(feat(expired)/ feat(card)) |
| p2-e2-04 | 收益计算器 | ✅ 通过 | YieldCalculator.tsx + YieldCalculatorPopover.tsx |
| p2-d-01 | 详情页布局设计 | ✅ 通过 | 5区块布局桌面+移动 |
| p2-d-02 | 移动端+动画 | ✅ 通过 | MobilePrimaryNav.tsx + scroll-reveal + motion polish |

### Phase 3 验收

| ID | 任务 | 状态 | 证据 |
|----|------|------|------|
| p3-e1-01 | 后台新字段+拖拽+标签 | ✅ 通过 | OpportunitiesBulkTable.tsx + OpportunityForm.tsx |
| p3-e2-01 | 前后端联调+边界 | ✅ 通过 | Loading skeleton + ErrorBoundary + 导航跳转正确，build 通过 |
| p3-d-01 | 全站走查+视觉一致 | ✅ 通过 | 品牌色 token 化、hover/动画效果、空状态/加载态 |

### 额外产出
- 7 个 smoke test 脚本（scripts/smoke-*、scripts/run-v2-*）
- QA 回归清单文档（docs/v2-smoke-suite.md）
- 复盘卡片收益对比条、分享卡增强、过期态视觉强化

---

### 总结
- **21/22 任务通过**（95.5%）
- **1 项未完成**：p1-e1-02 session maxAge 未改（仍为7天，需改为30天）
- 66 个文件变更，+4315 / -863 行
- dev 分支共 30+ commit，build 通过

### 建议
1. maxAge 一行改动即可修复，不阻塞验收
2. 建议 Boss 在测试站预览后决定是否 merge 到 main
