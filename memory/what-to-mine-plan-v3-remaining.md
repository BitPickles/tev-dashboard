# 什么值得挖 - 剩余任务（2026-03-24 15:19 恢复持续任务）

## 当前状态
- build 通过，65 个 commit
- v3 计划推进约 75%，以下为剩余任务

## engineer 剩余

### 测试+部署（Phase 10）
- [ ] T-03: 性能检查（首页 LCP < 2s，SSR 正常）
- [ ] T-04: SEO meta 标签完善
- [ ] T-05: 最终 Vercel 部署验证
- [ ] T-06: CEX 监控 cron 配置（每 10 分钟）
- [ ] T-07: 全站冒烟测试修复（T-01 发现的 4 个问题）

### 补漏+打磨
- [ ] FIX-01: 检查三个 Agent 改同一项目是否有 git 冲突
- [ ] FIX-02: 确认所有新页面路由可访问（/alerts /reviews /admin/analytics /admin/monitoring /admin/access-logs）
- [ ] FIX-03: 确认 Prisma schema 是否需要 migration（新表 OpportunityUpdate 等）
- [ ] FIX-04: 环境变量完整性检查（MiniMax/GLM API key、TG bot token 等）
- [ ] FIX-05: 检查 dev.db 和 Supabase 生产 DB schema 一致性

## engineer2 剩余

### 体验优化（Phase 8）
- [ ] X-01: 页面过渡动画集成验证
- [ ] X-02: 无限滚动性能验证（1000+ 条数据）
- [ ] X-03: 错误边界全站集成验证
- [ ] X-04: 空状态组件全站集成

### 测试联调（Phase 9）
- [ ] X-05: 全站 SEO meta 验证
- [ ] X-06: PWA manifest + SW 验证
- [ ] X-07: 与 engineer 代码合并联调
- [ ] X-08: Bug 修复

## designer 剩余

### 响应式验证（Phase 7）
- [ ] V-31: 375px 全站截图+修复
- [ ] V-32: 768px 全站截图+修复
- [ ] V-33: 1024px 全站截图+修复
- [ ] V-34: 1440px 全站截图+修复
- [ ] V-35: 触摸手势适配验证

### 最终走查（Phase 8）
- [ ] V-36: 全站逐页 UI 走查
- [ ] V-37: 间距/对齐/字号一致性检查
- [ ] V-38: 交互细节（focus/disabled/active 态）
- [ ] V-39: 最终视觉打磨
- [ ] V-40: 修复走查发现的问题
