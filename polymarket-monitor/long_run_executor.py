#!/usr/bin/env python3
"""
通用长脚本运行器
永远不卡住，实时输出进度
"""

import subprocess
import time
import signal
import sys
from datetime import datetime

def run_long_command(cmd, max_duration_minutes=10, log_file="long_run.log"):
    """
    运行长命令，实时输出进度，不会卡住
    
    Args:
        cmd: 命令（字符串或列表）
        max_duration_minutes: 最大运行时间（分钟）
        log_file: 日志文件路径
    """
    print(f"🚀 启动长任务运行器...")
    print(f"⏰ 最大时长: {max_duration_minutes} 分钟")
    print(f"📝 日志文件: {log_file}")
    print("=" * 70)

    # 启动子进程（不等待）
    process = subprocess.Popen(
        cmd if isinstance(cmd, list) else cmd.split(),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True
    )

    print(f"\n✅ 进程已启动 (PID: {process.pid})")
    print(f"📊 实时输出:\n")

    # 实时读取输出
    start_time = time.time()
    line_count = 0

    try:
        while True:
            # 检查进程是否结束
            return_code = process.poll()

            if return_code is not None:
                print(f"\n⏰ 进程结束 (返回码: {return_code})")
                break

            # 读取新行
            for line in process:
                line_count += 1
                # 写入日志文件（带 flush，防止缓冲）
                with open(log_file, "a", encoding='utf-8') as f:
                    f.write(f"[{datetime.now().isoformat()}] {line}\n")
                    f.flush()

                # 实时打印（带 flush，防止缓冲）
                print(f"\r⏰ {time.time() - start_time:.1f}s | 行 {line_count} | {line.strip()[:80]}", end="", flush=True)

            # 检查是否超时
            elapsed = time.time() - start_time
            if elapsed > max_duration_minutes * 60:
                print(f"\n⏰ 达到最大时长 {max_duration_minutes} 分钟，终止进程...")
                process.terminate()
                time.sleep(2)
                if process.poll() is None:
                    process.kill()
                break

            # 短暂等待，避免 CPU 过高
            time.sleep(0.1)

    except KeyboardInterrupt:
        print(f"\n\n⚠️  收到中断信号，终止进程...")
        process.terminate()
        time.sleep(2)
        if process.poll() is None:
            process.kill()
        print(f"✅ 进程已终止")

    except Exception as e:
        print(f"\n\n❌ 发生错误: {e}")
        if process.poll() is None:
            process.kill()

    print("\n" + "=" * 70)
    print(f"✅ 运行完成！")
    print(f"📝 日志已保存到: {log_file}")
    print(f"⏰ 总时长: {time.time() - start_time:.1f} 秒")
    print("=" * 70)

    return return_code if return_code is not None else 0


def flush_print(text):
    """强制实时输出（防止缓冲）"""
    print(text, flush=True)


if __name__ == "__main__":
    # 示例：运行调研脚本
    if len(sys.argv) > 1:
        cmd = " ".join(sys.argv[1:])
        run_long_command(cmd, max_duration_minutes=10, log_file="task_output.log")
    else:
        print(__doc__)
