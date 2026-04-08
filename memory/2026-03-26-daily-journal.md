# 2026-03-26 每日摘要

## 1) 重要决策
- Boss 确认「什么值得挖」项目放弃 Vercel SSR 架构，切换为**纯静态 Next.js + GitHub Pages + Cloudflare Workers**。
- 项目仓库改为 **public**，采用 `dev`（源码）+ `gh-pages`（静态产物）分支结构。
- 后续页面优化已明确交接给工程师，Boss 可直接与工程师对接。

## 2) 完成的任务
- 「什么值得挖」静态化改造完成，测试站已上线：<https://bitpickles.github.io/what-to-mine/>
- 完成 91 个文件级改造：前端改读 `data/*.json`、收藏改 `localStorage`、Admin 后台迁移到 dev-only、删除 Vercel 配置。
- 完成 GitHub Pages 部署关键配置：`basePath`、`.nojekyll`、静态导出链路打通。
- 完成交接文档 `HANDOVER.md`，项目已可进入后续优化阶段。
- task-orchestrator v4 改造在昨日已完成并验证通过，当前状态为生产就绪。

## 3) 待跟进事项
- 将 Supabase 数据导入本地 `dev.db`。
- 运行 `export-data.ts` 导出 JSON；当前页面仍显示“暂无机会数据”。
- 将 Workers 认证代码部署到 Cloudflare。
- 按 Boss 指示继续做页面优化。
- 后续需要刷新 **Claude Code OAuth token**（当前已过期，执行时报 401）。

## 4) Boss 的指示
- 明确要求放弃继续折腾 Vercel 部署，改走静态站方案。
- 指定后续页面优化继续推进，并允许直接和工程师对接。

## 补充记录
- 本次静态化关键教训：
  - Vercel 失败根因不是 Git author，而是 **Vercel 美东 serverless 与 Supabase 新加坡实例跨洋连接池超时**。
  - GitHub Pages 部署 Next.js 必须处理 `.nojekyll`、`basePath` 和缓存重建问题。
  - 项目内 `.env` 可能覆盖 Vercel 面板环境变量，需特别警惕。
