# task-orchestrator — 多 Agent 持续任务编排系统

## 一句话

给多个 AI Agent 派任务，自动监控进度、催促偷懒的、检测完成，Boss 只看 Telegram 汇报。

---

## 快速上手（3 步启动）

### 1. 写配置

```bash
cp config.example.json config.json
```

编辑 `config.json`，**只需要改这一个文件**：

```json
{
  "project": {
    "name": "你的项目名",           // 汇报标题用
    "dir": "~/path/to/git/repo",    // 主仓库绝对路径
    "branch": "dev"                 // 主开发分支
  },
  "agents": {
    "engineer": {                   // Agent ID（必须是 openclaw 已配置的 agent）
      "branch": "dev-engineer",     // 该 Agent 的专属分支
      "worktree": "~/path/to/repo-engineer",  // Git worktree 目录
      "role": "后端+数据"            // 角色描述（派任务时告知 Agent）
    }
    // 可以加任意多个 agent...
  },
  "telegram": {
    "chat_id": "Boss 的 Telegram user ID",
    "bot_token_env": "TG_BOT_TOKEN",        // 环境变量名，token 存在 ~/.openclaw/.env
    "proxy": "http://127.0.0.1:7890"        // 可选，没代理就删掉
  },
  "thresholds": {
    "nudge_minutes": 30,         // 多久没 commit 开始催
    "reset_minutes": 120,        // 多久没 commit 重置 session
    "nudge_cooldown_minutes": 15,// 催促冷却（防轰炸）
    "session_max_lines": 300     // session 超多少行轮换
  },
  "paths": {
    "state_dir": "~/clawd/state",
    "logs_dir": "~/clawd/logs",
    "task_registry": "~/clawd/tasks/xxx/task-registry.json",  // 任务清单
    "checks_file": "~/clawd/memory/xxx-checks.md"             // 检查记录
  }
}
```

### 2. 准备任务注册表

在 `paths.task_registry` 指向的位置创建 JSON：

```json
{
  "tasks": [
    {
      "id": "T001",
      "name": "实现用户登录页面",
      "assignee": "engineer",
      "status": "todo"
    },
    {
      "id": "T002", 
      "name": "设计登录页 UI",
      "assignee": "designer",
      "status": "todo"
    }
  ]
}
```

字段说明：
- `id`: 任务编号，唯一
- `name`: 任务描述，会直接发给 Agent
- `assignee`: 必须对应 config.json 中 agents 的 key
- `status`: `todo` / `in_progress` / `done`

### 3. 启动

```bash
# 先 dry run 确认没问题
bash task-start.sh --dry-run

# 正式启动
bash task-start.sh
```

启动后系统自动运行，**不需要人工干预**：
- 每 5 分钟检查所有 Agent 进度
- 有变化时发 Telegram 汇报（无变化不发，不刷屏）
- Agent 偷懒自动催促
- Agent 完成自动唤醒总管验收

---

## 停止

```bash
bash task-stop.sh
```

自动完成：通知 Agent 收尾 → 等 3 分钟 → 归档 WRAP-UP → 兜底 commit → 卸载调度 → 合并分支

---

## Agent 如何标记"我完成了"

Agent 必须用以下两种方式之一（**不是在对话里说"完成了"**）：

| 方式 | 操作 |
|------|------|
| `.done` 文件 | 在工作目录创建 `.done` 文件并 commit |
| `[DONE]` tag | commit message 包含 `[DONE]`，如 `git commit -m "[DONE] 完成登录页"` |

⚠️ 派任务时必须告知 Agent 这个规则。`task-start.sh` 已经自动在派发消息中包含了。

---

## 目录结构

```
~/clawd/scripts/task-orchestrator/
├── config.json          ← 你的配置（唯一需要改的）
├── config.example.json  ← 配置示例
├── config-schema.json   ← JSON Schema（IDE 自动补全用）
├── helpers.py           ← Python 工具集（bash 调用，不要直接改）
├── task-monitor.sh      ← 主巡逻脚本（launchd 自动调度）
├── system-watchdog.sh   ← 看门狗（launchd 自动调度）
├── task-start.sh        ← 一键启动
├── task-stop.sh         ← 一键停止
├── task-logs.sh         ← 日志查询
└── auto-merge.sh        ← 手动合并各 Agent 分支
```

运行时产生的文件：
```
~/clawd/state/                ← 运行状态（重启不丢）
├── completed-agents          ← 已完成的 Agent 列表
├── last-report-hash          ← 汇报去重用
├── last-heartbeat-ts         ← 心跳时间戳
├── latest-report.txt         ← 最新汇报文本
└── nudge-cooldown/           ← 催促冷却

~/clawd/logs/                 ← 日志
├── task-events.jsonl         ← 结构化事件（最重要）
├── task-monitor.log          ← 监控文本日志
├── watchdog.log              ← 看门狗日志
└── launchd-*.log             ← 系统调度日志
```

---

## 查日志

```bash
bash task-logs.sh                  # 最近 20 条事件
bash task-logs.sh -a engineer      # 某 Agent 的事件
bash task-logs.sh -e nudge         # 只看催促事件
bash task-logs.sh -e done_signal   # 只看完成事件
bash task-logs.sh -t 60            # 最近 60 分钟
bash task-logs.sh --errors         # 只看错误
bash task-logs.sh --all            # 所有日志摘要
```

---

## 工作原理

```
task-start.sh 启动时：
  1. 为每个 Agent 创建 git worktree（独立工作目录）
  2. 安装 macOS launchd 定时任务
  3. 向每个 Agent 派发任务

运行中（全自动）：
  task-monitor.sh 每 5 分钟：
    ├─ git log 检查每个 Agent 有没有新 commit
    ├─ 检查 .done 文件 / [DONE] commit（完成信号）
    ├─ 分析 session 行为模式（假忙检测）
    ├─ 30 分钟没产出 → 催促
    ├─ 2 小时没产出 → 重建 session
    ├─ session 太长 → 自动轮换
    ├─ 有人完成 → 唤醒总管验收
    └─ 内容有变 → curl Telegram 发汇报

  system-watchdog.sh 每 30 分钟：
    ├─ Gateway 进程还在吗
    ├─ 心跳脚本还在跑吗
    └─ 全部 Agent 是不是都停了

task-stop.sh 停止时：
  1. 通知 Agent 写 WRAP-UP.md
  2. 等 3 分钟
  3. 兜底 commit 未保存改动
  4. 卸载 launchd
  5. 合并各分支到主分支
```

---

## 并发安全

task-monitor.sh 用 `mkdir` 原子锁防止重叠执行：
- 上一轮还在跑 → 本轮自动跳过
- 僵尸锁（超过 10 分钟）自动清除
- 正常退出时 `trap EXIT` 自动释放

不用担心 launchd 5 分钟间隔和脚本执行时间冲突。

---

## 前置条件

| 依赖 | 说明 |
|------|------|
| OpenClaw | 已安装运行，agents 已配置 |
| macOS | launchd 调度（Linux 需改为 systemd/cron） |
| Git | 项目是 git 仓库 |
| Python 3 | helpers.py 需要 |
| curl + shasum | 发 Telegram + 内容去重（macOS 自带） |
| `~/.openclaw/.env` | 含 `TG_BOT_TOKEN=xxx`（权限 600） |

⚠️ **macOS 兼容说明**：脚本专为 macOS 设计，不依赖 `md5`/`md5sum`/`flock`（macOS 没有）。使用 `shasum -a 256` 做 hash，`mkdir` 做进程锁。

---

## 常见问题

### Q: 换个项目怎么办？
改 `config.json` 就行。项目名、目录、分支、Agent 列表、任务注册表路径全在里面。

### Q: Telegram 收不到汇报？
1. 检查 `TG_BOT_TOKEN` 环境变量：`source ~/.openclaw/.env && echo $TG_BOT_TOKEN`
2. 检查代理：`curl --proxy http://127.0.0.1:7890 https://api.telegram.org/bot${TG_BOT_TOKEN}/getMe`
3. 检查日志：`bash task-logs.sh --all`

### Q: Agent 不干活怎么办？
系统自动处理：30 分钟催促 → 2 小时重建 session。如果还不行，查 `task-logs.sh -a <agent>` 看具体情况。

### Q: 怎么加新 Agent？
在 `config.json` 的 `agents` 里加一项，确保 OpenClaw 里已有同名 agent 配置。

### Q: 怎么中途加任务？
直接编辑 `task_registry` JSON 文件，加新 task 条目。下轮监控会自动读取。

### Q: macOS 重启后还能自动跑吗？
能。launchd plist 设了 `RunAtLoad: true`，系统启动后自动恢复。

### Q: 我想手动合并分支？
```bash
bash auto-merge.sh
```

---

## 铁律

1. **持续任务模型最差用 Codex，禁止 GLM** — GLM 会偷懒
2. **不直接操作 OpenClaw 内部文件** — 用 `openclaw agent --session-id` 命令
3. **汇报直接 curl Telegram** — 不绕 Agent，减少故障链
4. **完成用结构化信号** — `.done` 文件或 `[DONE]` commit，不 grep 对话内容
5. **Telegram 用纯文本 + data-urlencode** — 不用 Markdown 解析，避免 `_` `*` 导致发送失败
6. **hash 用 shasum 不用 md5** — macOS 没有 md5/md5sum

---

## 生产验证

2026-03-25 端到端测试全部通过：

| 测试项 | 结果 |
|--------|------|
| `--session-id` 新建 session | ✅ |
| 并发锁（mkdir 原子） | ✅ |
| launchd 精简环境兼容 | ✅ |
| Telegram 直发 + 去重 | ✅ |
| 完成信号检测（.done） | ✅ |
| 全部完成 → 唤醒总管验收 | ✅ |
