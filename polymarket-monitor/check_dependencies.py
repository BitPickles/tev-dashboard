#!/usr/bin/env python3
"""
依赖包检查和更新程序
"""

import subprocess
import sys

def check_package(package_name):
    """检查包是否已安装"""
    try:
        result = subprocess.run(
            ["pip3", "show", package_name],
            capture_output=True,
            text=True,
            timeout=10
        )
        version = None
        for line in result.stdout.split('\n'):
            if 'Version:' in line:
                version = line.split('Version:')[1].strip()
                break
        return version
    except:
        return None


def install_package(package_name):
    """安装包"""
    print(f"📦 安装 {package_name}...")
    result = subprocess.run(
        ["pip3", "install", package_name, "-q"],
        capture_output=True,
        text=True,
        timeout=120
    )
    return result.returncode == 0


def upgrade_package(package_name):
    """升级包到最新版本"""
    print(f"📦 升级 {package_name}...")
    result = subprocess.run(
        ["pip3", "install", "--upgrade", package_name, "-q"],
        capture_output=True,
        text=True,
        timeout=120
    )
    return result.returncode == 0


def main():
    print("""
    ╔═════════════════════════════════════════════════╗
    ║         Polymarket 监控程序 - 依赖检查           ║
    ╚═════════════════════════════════════════════════╝
    """)

    # 核心依赖列表
    dependencies = {
        "web3": "web3==7.14.0",
        "aiohttp": "aiohttp==3.13.3",
        "beautifulsoup4": "beautifulsoup4==4.14.3",
        "lxml": "lxml==6.0.2",
        "requests": "requests==2.32.5",
        "types-requests": "types-requests==2.32.4",
        "pyunormalize": "pyunormalize==17.0.0",
        "cytoolz": "cytoolz==1.1.0",
        "eth-account": "eth-account==0.13.7",
        "eth-rlp": "eth-rlp==4.1.0",
        "hexbytes": "hexbytes==1.3.1",
        "rlp": "rlp==4.1.0"
    }

    print("🔍 检查已安装的包版本...\n")

    missing_packages = []
    upgrade_candidates = []

    for package, min_version in dependencies.items():
        current_version = check_package(package)

        if current_version:
            print(f"✅ {package:15s} - {current_version}")

            # 检查是否需要升级（如果版本过旧）
            try:
                # 简化：总是尝试升级核心包
                if package in ["web3", "aiohttp", "requests"]:
                    upgrade_candidates.append(package)
            except:
                pass
        else:
            print(f"❌ {package:15s} - 未安装")
            missing_packages.append(package)

    print(f"\n📊 检查结果:")
    print(f"   已安装: {len(dependencies) - len(missing_packages)}")
    print(f"   缺失: {len(missing_packages)}")
    print(f"   建议升级: {len(upgrade_candidates)}")

    # 安装缺失的包
    if missing_packages:
        print(f"\n📦 正在安装缺失的包...")
        for package in missing_packages:
            if install_package(package):
                print(f"   ✅ {package} 安装成功")
            else:
                print(f"   ❌ {package} 安装失败")

    # 升级核心包
    if upgrade_candidates:
        print(f"\n📦 正在升级核心包...")
        for package in upgrade_candidates:
            if upgrade_package(package):
                print(f"   ✅ {package} 升级成功")
            else:
                print(f"   ❌ {package} 升级失败")

    # 再次检查
    print("\n🔍 最终检查...\n")
    final_missing = []
    for package in dependencies.keys():
        if not check_package(package):
            final_missing.append(package)

    if final_missing:
        print(f"❌ 仍然缺失: {final_missing}")
        return 1
    else:
        print("✅ 所有依赖已满足！")
        return 0


if __name__ == "__main__":
    sys.exit(main())
