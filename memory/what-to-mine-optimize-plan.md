# 什么值得挖 - 全站逐页自查优化计划

## 规则
- 按页面逐个推进，一个页面完成后才进入下一个
- 每个页面 3 个 Agent 各做 2 轮 = 6 次优化
- 不给具体需求，问 Agent"你认为这个页面还有什么需要优化的地方？"
- Agent 自己发现问题、自己修复
- 第一轮：自查 + 修复
- 第二轮：再检查一遍有没有遗漏

## 页面清单（19 个）

### 前台（10 个）
1. / — 首页机会列表
2. /opportunity/[id] — 机会详情
3. /opportunity/[id]/share — 分享卡片
4. /favorites — 收藏
5. /alerts — 监控快讯
6. /reviews — 历史复盘列表
7. /reviews/[id] — 复盘详情
8. /connect — 连接钱包
9. /blocked — 非白名单拦截
10. (layout) — 全局布局/导航

### 后台（9 个）
11. /admin — 后台首页(重定向)
12. /admin/dashboard — 数据仪表盘
13. /admin/opportunities — 机会管理列表
14. /admin/opportunities/new — 新建机会
15. /admin/opportunities/[id]/edit — 编辑机会
16. /admin/whitelist — 白名单管理
17. /admin/analytics — 访问统计
18. /admin/monitoring — 监控健康度
19. /admin/access-logs — 访问日志

## 当前进度
- 前台 10 页：已全部完成 2 轮自查
- 后台 9 页：已全部完成 2 轮自查
- 额外扩展页：`/admin/monitor/cex` 已完成 2 轮自查
- 当前状态：**全站逐页优化主计划已完成**
- engineer: `/admin` R2✅，待命
- engineer2: 补充优化（白名单批量导入反馈）✅，待命
- designer: `/admin` R2✅，待命
