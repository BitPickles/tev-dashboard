

## 📦 每日备份任务
- **Agent 全量备份**：每天 23:00 执行
- 仓库：https://github.com/BitPickles/agent-souls (私有)
- 脚本：`~/agent-souls/sync-backup.sh`
- 内容：`~/.openclaw/skills/` + `~/clawd/*.md`
- Cron ID：54a8b81f-aa90-4656-a3ee-7821d92205cf
- 2026-02-25 恢复此任务（之前 reset 后遗失）

## ⛔ 铁律：主站发版必须经 Boss 批准
- 2026-02-12 第二次违规，被 Boss 严厉批评
- 2026-03-20 运营擅自推 main 两次，总管回滚并加铁律
- 任何情况下，git push origin main 前必须有 Boss 明确批准
- 紧急修复也不例外！先推 dev 验证，再请示
- 运营 TASKS.md 已写入禁止 merge dev 到 main 的铁律

## 🏛️ 治理监控系统（2026-03-18~20 完成）
- 19 个协议、303 条提案、67 条 GLM-5 深度解读
- 正式站已上线：crypto3d.pro/governance/
- 采集脚本：`~/.openclaw/workspace-engineer/governance-monitor/governance-monitor.py`
- 详细项目文档：`memory/projects/governance-monitor.md`
- Skill 文档：`~/.openclaw/skills/crypto3d-dashboard/governance.md`
- 运营每日 9:00/21:00 更新（已交接确认）

## 🤖 运营模型注意
- 运营模型已从 gpt-5.4-codex 切换到 claude-opus-4-6（2026-03-20）
- 旧模型跨 session 通信有 bug，切 Claude 后正常
- openclaw agent CLI 触发的是独立 session，不共享 Telegram session context

## 📢 推特日报系统（进行中）
- 工程师2号在开发，代码在 dev 分支 poster/ 目录
- 未验收，正式站已删除 poster/
- 任务书：`memory/projects/twitter-daily.md`
- 2026-03-22 设计师已将海报重构为 9:16 竖屏单列布局，并修复精确 1080×1920 导出；视觉仍待 Boss 最终审美验收

## 📰 新闻监控雷达（2026-03-22 进入正式验收）
- 工程师2号已完成多源新闻采集、Top 25 筛选、中文标题/摘要生成、review 页面和验收清单
- 真实全量跑测约 183.8 秒，已满足 5 分钟内要求
- 当前纪律：**先正式验收，不加 cron，不接正式页面**
- 产物：`tev-dashboard/data/news.json`、`review/news-radar.html`、`docs/news-radar-review-checklist.md`

## 🎨 设计师 Agent（2026-03-20 部署）
- Agent ID: designer，TG Bot: @designer_sandy_bot
- 模型: claude-opus-4-6
- Skills: frontend-design-pro、ui-ux-pro-max、happy-hues、crypto3d-design-system（自建）
- 职责：UI/UX 设计、配色方案、HTML/CSS 原型、UI 审查
- 不写业务代码，通过总管调度

## 🧪 整站视觉升级实验（2026-03-20~21）
- 实验站：https://bitpickles.github.io/crypto3d-design-lab/
- 任务看板：https://bitpickles.github.io/crypto3d-design-lab/tasks/
- 三条业务线分区：TEV+治理 / BTC周期指标 / 宏观风险
- 默认浅色主题，子页面只改 UI 不重构功能
- 三阶段流程：实验站(设计) → 测试站(数据对接) → 正式站(Boss批准)

## 📋 task-orchestrator Skill（2026-03-21）
- 持续任务编排，解决「派了就丢」问题
- Web 看板：/tasks/ 页面，Boss 看「待确认」列即可
- 铁律：完成必须 Boss 确认，进 reviewing 必须主动通知 Boss
- 监控 Cron 走 GLM，不占 Anthropic 额度
- 2026-03-22 新增管理铁律：**下属自报完成 ≠ 总管已验收**；总管必须先做独立验收，再决定是否向 Boss 上报
- 2026-03-22 Boss 明确要求：判断是否真的在推进，只看**新的可验证产出**（commit、文件、图片、修复证据、明确阻塞说明），不接受“我在看/我在查/有 session 活动”这类空进展
- 2026-03-22 沟通偏好补充：对可继续推进的任务，默认直接推进，不要反复向 Boss 征求是否继续

## 🏗️ 组织架构（2026-03-21 调整）
- 指挥层：总管 / 研究员 / 运营
- 中台执行层：设计师 / 工程师1 / 工程师2

## 🔧 模型配置（2026-03-25 更新）
- 默认：Codex
- 备用：GLM 5.0
- 第二备用：MiniMax
- ⚠️ **铁律：持续任务（心跳+汇报 Cron）最差用 Codex，禁止用 GLM**
  - GLM 在持续任务中会偷懒回 HEARTBEAT_OK、不执行检查、汇报不投递
  - 2026-03-25 Boss 明确要求
- GLM 仅允许用于非持续任务的轻量 Cron（每日备份、数据采集等）

## 💬 沟通方式
- 公司已无群聊，改为逐个直接对话
- group-chat-rules.md 已删除（2026-03-20）

## ⛏️ 什么值得挖项目（2026-03-25 架构切换）
- **已从 Vercel SSR + Supabase 切换到 纯静态 + GitHub Pages**
- 测试站：https://bitpickles.github.io/what-to-mine/
- 仓库：https://github.com/BitPickles/what-to-mine（已改为 public）
- 分支：dev（源码）、gh-pages（静态产物）
- 代码目录：`~/.openclaw/workspace-engineer/what-to-mine`
- 技术方案：`memory/projects/what-to-mine-v2-static-migration.md`
- 需求文档：`memory/projects/what-to-mine-v2-spec.md`
- Vercel 部署彻底失败原因：serverless 在美东 ↔ Supabase 在新加坡，跨洋连接池超时
- Workers 认证代码已写好（workers/ 目录），未部署到 Cloudflare
- 已交接工程师，Boss 直接和工程师聊后续优化
- ⚠️ 部署 GitHub Pages 要点：必须 touch .nojekyll（否则 _next 目录被过滤）、basePath 必须设为仓库名

## 🔥 持续任务复盘教训（2026-03-24~25）
- **2026-03-25 严重事故**：三个 Agent 凌晨 04:49 后全停了，8 小时零产出无人发现
  - 根因：心跳没有真正执行 git log 检查，只是机械读 checks 文件
  - 汇报 Cron 每 10 分钟发同一段旧内容，Boss 被误导以为在正常工作
  - 修复：HEARTBEAT.md 明确要求必须执行 git log 命令获取真实数据，30分钟无产出必须催促
  - 催促方法必须用 `openclaw agent --agent <id> -m`，不用 sessions_send
- AI Agent 5 分钟一个任务，一天 50+，绝对不能按人类节奏排计划
- 每个 Agent 至少准备 8 天深度的任务队列，支持线完工立即转主线
- 启动持续任务必须跑完 10 步 checklist，"配了就假设生效"会空转
- 创建 Cron 必须加 --channel telegram，多 channel 环境不加必报错
- 心跳模型用 GLM 不用主模型，主模型容易 overloaded
- 检查和汇报都要去重：无变化不写记录、不发消息

## 💰 资产状况备忘（2026-03-23）
- 本周净资产 -36.18%（$835K → $533K），晚间进一步跌至 $501K
- 含手动负债约 $140K
