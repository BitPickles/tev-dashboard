# Crypto3D TEV Dashboard - 开发维护规范

## 部署流程（铁律）

1. **所有开发在 `dev` 分支完成**
2. Push `dev` 后在测试站验证：https://bitpickles.github.io/tev-dashboard
3. **向 Boss 展示测试站效果，等待确认**
4. Boss 确认后才 merge `dev` → `main` 并 push `main`
5. Push `main` 自动触发 GitHub Actions → Cloudflare Pages 部署到正式站
6. **严禁未经验证直接 push main**
7. 唯一例外：安全修复类紧急变更可直接推 main，但必须说明原因

## TEV 数据口径

数据源优先级：**链上 > 官方治理 > 估算 > DefiLlama**

- 所有 TEV 计算统一为「过去 365 天」口径
- Revenue 用 DefiLlama `dailyRevenue`，不是 `dailyFees`
- TEV Ratio 变更必须有治理提案或官方文档支撑
- 核心公式不可更改，参见 `docs/skill/tev-data-layer.md`

## 分支纪律

- `dev`：开发分支，GitHub Pages 测试站
- `main`：正式发布分支，Cloudflare Pages 正式站
- 数据自动更新：commit 到 `dev` → merge `main` → 自动部署

## 定时任务

- 数据更新：LaunchAgent `com.crypto3d.data-updater`（9:03/21:03）
- 治理监控：LaunchAgent `com.crypto3d.governance-monitor`（9:05/21:05）
- 日志目录：`~/scheduled-tasks/logs/` 和 `~/crypto3d-updater/logs/`
