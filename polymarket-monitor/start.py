#!/usr/bin/env python3
"""
启动器 - 立即启动监控并显示会议提醒
"""

import subprocess
import json
from datetime import datetime, timedelta
import time
import os

def start_monitor():
    """启动监控程序"""
    print("""
    ╔═════════════════════════════════════════════════════════════╗
    ║                 Polymarket 监控启动器                          ║
    ║                  (REAL DATA - 2026)                           ║
    ╚═══════════════════════════════════════════════════════════════╝
    """)

    # 立即显示会议提醒（因为用户可能在看）
    now = datetime.now()
    print(f"\n⏰ 当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")

    if now.hour < 14:
        hours_until = 14 - now.hour
        print(f"⏰ 会议提醒: 距离下午 2 点还有 {hours_until} 小时")
    elif now.hour == 14 and now.minute < 5:
        print("\n" + "🔔" * 30)
        print("⚠️  会议提醒：下午 2 点有会！")
        print("🔔" * 30 + "\n")
    else:
        print("⏰ 会议提醒：今天下午 2 点的会议已过")

    # 检查文件是否存在
    files_to_check = [
        "continuous_monitor.py",
        "real_data_final.py"
        "check_dependencies.py"
        "monitor_report.json"
    ]

    print(f"\n📂 检查文件...")
    for f in files_to_check:
        exists = "✅" if os.path.exists(f) else "❌"
        print(f"   {exists} {f}")

    # 启动监控
    print("\n" + "=" * 70)
    print("🚀 启动 Polymarket 持续监控程序...")
    print("=" * 70)
    print("\n📡 正在获取实时数据...")
    print("🔍 正在解析市场...")
    print("🎯 正在检测套利机会...")
    print("⏰ 已设置下午 2 点会议提醒")
    print("\n程序将持续运行，每 30 秒刷新一次数据\n")

    # 启动真正的监控脚本
    if os.path.exists("continuous_monitor.py"):
        try:
            subprocess.run(
                ["python3", "continuous_monitor.py"],
                check=True
            )
        except KeyboardInterrupt:
            print("\n\n⚠️  监控程序已停止")
    else:
        print("❌ 找不到 continuous_monitor.py")


if __name__ == "__main__":
    start_monitor()
