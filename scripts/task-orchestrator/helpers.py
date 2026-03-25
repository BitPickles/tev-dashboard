#!/usr/bin/env python3
"""
task-orchestrator helpers — 集中所有 Python 逻辑
所有 bash 脚本通过 `python3 helpers.py <command> [args]` 调用
"""
import json, os, sys, time, re, subprocess
from pathlib import Path
from datetime import datetime, timezone

def expand(p: str) -> str:
    return os.path.expanduser(p)

def load_env():
    """从 ~/.openclaw/.env 加载环境变量"""
    env_file = expand("~/.openclaw/.env")
    if os.path.exists(env_file):
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line.startswith("#") or not line or "=" not in line:
                    continue
                # 处理 export KEY='VALUE' 格式
                line = line.removeprefix("export ")
                key, _, val = line.partition("=")
                key = key.strip()
                val = val.strip().strip("'\"")
                if key and val:
                    os.environ.setdefault(key, val)

# 启动时加载
load_env()

def load_config(path=None) -> dict:
    p = path or os.environ.get("TASK_CONFIG", expand("~/clawd/scripts/task-orchestrator/config.json"))
    with open(p) as f:
        return json.load(f)

def cfg_get(cfg: dict, dotpath: str, default=None):
    """从配置中按点路径取值，key 不存在返回 default"""
    d = cfg
    for k in dotpath.split("."):
        if isinstance(d, dict) and k in d:
            d = d[k]
        else:
            return default
    return d

# ============================================================
# 命令: read_config <dotpath>
# ============================================================
def cmd_read_config():
    cfg = load_config()
    dotpath = sys.argv[2]
    val = cfg_get(cfg, dotpath)
    if val is None:
        print("")
    elif isinstance(val, (dict, list)):
        print(json.dumps(val, ensure_ascii=False))
    else:
        print(val)

# ============================================================
# 命令: list_agents
# ============================================================
def cmd_list_agents():
    cfg = load_config()
    print(" ".join(cfg["agents"].keys()))

# ============================================================
# 命令: agent_config <agent_id> <field>
# ============================================================
def cmd_agent_config():
    cfg = load_config()
    agent = sys.argv[2]
    field = sys.argv[3]
    val = cfg["agents"][agent][field]
    print(val)

# ============================================================
# 命令: check_fake_busy <session_jsonl_path>
# 输出: status|suggestion 或 ok|
# ============================================================
def cmd_check_fake_busy():
    fpath = sys.argv[2]
    if not os.path.exists(fpath):
        print("ok|")
        return
    
    msgs = []
    with open(fpath) as fh:
        for line in fh:
            try:
                d = json.loads(line.strip())
                if d.get("type") == "message":
                    msgs.append(d)
            except:
                pass
    
    recent = msgs[-50:]
    read_c = write_c = edit_c = exec_c = exec_fail = text_only = 0
    last_cmds = []
    
    for m in recent:
        r = m.get("message", {}).get("role", "")
        c = m.get("message", {}).get("content", "")
        if r == "assistant":
            has_tool = False
            if isinstance(c, list):
                for x in c:
                    t = x.get("type", "")
                    if t == "toolCall":
                        has_tool = True
                        n = x.get("name", "")
                        if n in ("read", "Read"): read_c += 1
                        elif n in ("write", "Write"): write_c += 1
                        elif n in ("edit", "Edit"): edit_c += 1
                        elif n == "exec":
                            exec_c += 1
                            last_cmds.append(str(x.get("arguments", {}).get("command", ""))[:80])
                if not has_tool:
                    text_only += 1
            elif isinstance(c, str):
                text_only += 1
        elif r == "toolResult":
            if m.get("message", {}).get("isError"):
                exec_fail += 1
    
    # 重复命令检测
    repeated = 0
    for i in range(len(last_cmds) - 2):
        if last_cmds[i] == last_cmds[i+1] == last_cmds[i+2]:
            repeated += 1
    
    productive = write_c + edit_c
    if productive == 0 and read_c > 10:
        print("read_loop|停止读文件，开始写代码")
    elif repeated > 0:
        print("stuck_retry|换个方法解决")
    elif exec_fail > 5:
        print("error_loop|分析错误原因，换思路")
    elif text_only > 8 and productive == 0:
        print("chatting|停止解释，直接写代码提交")
    else:
        print("ok|")

# ============================================================
# 命令: get_remaining_tasks <agent_id>
# ============================================================
def cmd_get_remaining_tasks():
    cfg = load_config()
    agent = sys.argv[2]
    registry_path = expand(cfg.get("paths", {}).get("task_registry", ""))
    if not registry_path or not os.path.exists(registry_path):
        return
    with open(registry_path) as f:
        d = json.load(f)
    for t in d.get("tasks", []):
        if t.get("assignee") == agent and t.get("status") != "done":
            print(f"- {t['id']}: {t['name']}")

# ============================================================
# 命令: mark_agent_done <agent_id>
# ============================================================
def cmd_mark_agent_done():
    cfg = load_config()
    agent = sys.argv[2]
    registry_path = expand(cfg.get("paths", {}).get("task_registry", ""))
    if not registry_path or not os.path.exists(registry_path):
        return
    with open(registry_path) as f:
        d = json.load(f)
    for t in d.get("tasks", []):
        if t.get("assignee") == agent and t.get("status") != "done":
            t["status"] = "done"
    with open(registry_path, "w") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)

# ============================================================
# 命令: check_done_signal <worktree_dir>
# 输出: done 或 not_done
# 结构化完成信号：检查 .done 文件或 [DONE] commit tag
# ============================================================
def cmd_check_done_signal():
    wdir = expand(sys.argv[2])
    
    # 方式1: .done 文件
    done_file = os.path.join(wdir, ".done")
    if os.path.exists(done_file):
        print("done")
        return
    
    # 方式2: 最近 commit message 含 [DONE] tag
    try:
        result = subprocess.run(
            ["git", "-C", wdir, "log", "--oneline", "-5", "--format=%s"],
            capture_output=True, text=True, timeout=10
        )
        for line in result.stdout.strip().split("\n"):
            if "[DONE]" in line.upper():
                print("done")
                return
    except:
        pass
    
    print("not_done")

# ============================================================
# 命令: last_session_ts <agent_id>
# 输出: unix timestamp 或 0
# ============================================================
def cmd_last_session_ts():
    agent = sys.argv[2]
    session_dir = expand(f"~/.openclaw/agents/{agent}/sessions")
    if not os.path.isdir(session_dir):
        print("0")
        return
    
    jsonl_files = sorted(
        [f for f in os.listdir(session_dir) if f.endswith(".jsonl") and "reset" not in f and "deleted" not in f],
        key=lambda x: os.path.getmtime(os.path.join(session_dir, x)),
        reverse=True
    )
    if not jsonl_files:
        print("0")
        return
    
    latest = os.path.join(session_dir, jsonl_files[0])
    lines = 0
    last_ts = 0
    last_line = ""
    try:
        with open(latest) as f:
            for line in f:
                lines += 1
                stripped = line.strip()
                if stripped:
                    last_line = stripped
        
        if last_line:
            d = json.loads(last_line)
            ts_str = d.get("timestamp", "")
            if ts_str:
                dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                last_ts = int(dt.timestamp())
    except:
        pass
    
    # 输出: timestamp lines path
    print(f"{last_ts} {lines} {latest}")

# ============================================================
# 命令: build_report
# 从 stdin 读取 "agent_name|status|commits" 格式的行
# ============================================================
def cmd_build_report():
    cfg = load_config()
    project_name = cfg["project"]["name"]
    
    lines = [f"📊 {project_name} 进度"]
    total_commits = 0
    commit_details = []
    
    for raw in sys.stdin:
        raw = raw.strip()
        if not raw:
            continue
        parts = raw.split("|", 2)
        if len(parts) == 3:
            name, status, commits_str = parts
            commits = int(commits_str) if commits_str.isdigit() else 0
            lines.append(f"- {name}: {status}")
            if commits > 0:
                commit_details.append(f"{name}: {commits} commits")
                total_commits += commits
        else:
            lines.append(raw)
    
    if commit_details:
        lines.append("")
        lines.extend(commit_details)
        lines.append(f"总计: {total_commits} commits")
    
    print("\n".join(lines))

# ============================================================
# 命令: trim_checks <checks_file> <max_rounds>
# ============================================================
def cmd_trim_checks():
    fpath = expand(sys.argv[2])
    max_rounds = int(sys.argv[3]) if len(sys.argv) > 3 else 50
    if not os.path.exists(fpath):
        return
    with open(fpath) as f:
        c = f.read()
    sections = re.split(r"(?=## 第)", c)
    header = sections[0] if sections and not sections[0].startswith("## 第") else ""
    rounds = [x for x in sections if x.startswith("## 第")]
    if len(rounds) > max_rounds:
        with open(fpath, "w") as f:
            f.write(header + "".join(rounds[-30:]))

# ============================================================
# 命令: validate_config [config_path]
# ============================================================
def cmd_validate_config():
    try:
        cfg = load_config(sys.argv[2] if len(sys.argv) > 2 else None)
    except Exception as e:
        print(f"❌ 配置文件读取失败: {e}")
        sys.exit(1)
    
    errors = []
    # 必需字段
    for key in ["project", "agents", "telegram"]:
        if key not in cfg:
            errors.append(f"缺少必需字段: {key}")
    
    if "project" in cfg:
        for k in ["name", "dir", "branch"]:
            if k not in cfg["project"]:
                errors.append(f"project 缺少: {k}")
        d = expand(cfg["project"].get("dir", ""))
        if d and not os.path.isdir(d):
            errors.append(f"项目目录不存在: {d}")
    
    if "agents" in cfg:
        for name, acfg in cfg["agents"].items():
            for k in ["branch", "worktree", "role"]:
                if k not in acfg:
                    errors.append(f"agents.{name} 缺少: {k}")
    
    if "telegram" in cfg:
        if "chat_id" not in cfg["telegram"]:
            errors.append("telegram 缺少: chat_id")
    
    if errors:
        for e in errors:
            print(f"❌ {e}")
        sys.exit(1)
    else:
        print("✅ 配置验证通过")
        print(f"   项目: {cfg['project']['name']}")
        print(f"   Agent 数: {len(cfg['agents'])}")
        print(f"   Telegram chat: {cfg['telegram']['chat_id']}")

# ============================================================
# 路由
# ============================================================
COMMANDS = {
    "read_config": cmd_read_config,
    "list_agents": cmd_list_agents,
    "agent_config": cmd_agent_config,
    "check_fake_busy": cmd_check_fake_busy,
    "get_remaining_tasks": cmd_get_remaining_tasks,
    "mark_agent_done": cmd_mark_agent_done,
    "check_done_signal": cmd_check_done_signal,
    "last_session_ts": cmd_last_session_ts,
    "build_report": cmd_build_report,
    "trim_checks": cmd_trim_checks,
    "validate_config": cmd_validate_config,
}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(f"用法: python3 {sys.argv[0]} <command> [args]")
        print(f"可用命令: {', '.join(COMMANDS.keys())}")
        sys.exit(1)
    COMMANDS[sys.argv[1]]()
