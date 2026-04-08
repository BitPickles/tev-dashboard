#!/usr/bin/env python3
import subprocess
import sys

# 核心依赖列表
deps = ["web3", "aiohttp", "beautifulsoup4", "lxml", "requests", "pyunormalize", "cytoolz"]

print("=" * 60)
print("📦 Python 包依赖检查")
print("=" * 60)
print()

missing = []
installed = []

for pkg in deps:
    try:
        result = subprocess.run(
            ["pip3", "show", pkg],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            # 提取版本号
            for line in result.stdout.split('\n'):
                if 'Version:' in line:
                    version = line.split('Version:')[1].strip()
                    print(f"✅ {pkg:20s} - {version}")
                    installed.append(pkg)
                    break
            else:
                print(f"✅ {pkg:20s} - installed")
                installed.append(pkg)
        else:
            print(f"❌ {pkg:20s} - missing")
            missing.append(pkg)
    except:
        print(f"❌ {pkg:20s} - missing")
        missing.append(pkg)

print()
print("=" * 60)
print(f"📊 Summary:")
print(f"   Installed: {len(installed)}")
print(f"   Missing:   {len(missing)}")
print("=" * 60)

# 显示会议提醒
now = __import__('datetime').datetime.now()
if now.hour == 14:
    print()
    print("⏰ 会议提醒：下午 2 点有会！")

# 安装缺失的包
if missing:
    print()
    print("📦 正在安装缺失的包...")
    for pkg in missing:
        print(f"   安装 {pkg}...")
        subprocess.run(["pip3", "install", pkg, "-q"], check=True, timeout=120)
        print(f"   ✅ {pkg} 安装完成")
