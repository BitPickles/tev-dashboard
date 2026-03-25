#!/usr/bin/env python3
"""
保存并分析 Polymarket HTML
"""

import subprocess
from datetime import datetime

def save_html():
    """保存 HTML 到文件"""
    print("📡 正在获取并保存 Polymarket HTML...")

    result = subprocess.run(
        ["curl", "-s", "https://polymarket.com/"],
        capture_output=True,
        text=True,
        timeout=30
    )

    html = result.stdout

    # 保存到文件
    filename = f"polymarket_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"✅ HTML 已保存到: {filename}")
    print(f"   大小: {len(html):,} 字节")

    # 保存精简版本（前 5000 行）
    lines = html.split('\n')[:5000]
    filename_short = f"polymarket_short_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    with open(filename_short, "w", encoding="utf-8") as f:
        f.write('\n'.join(lines))

    print(f"✅ 精简版 HTML 已保存到: {filename_short}")
    print(f"   行数: {len(lines)}")

    return filename, filename_short


def main():
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║         Polymarket HTML 保存器                            ║
    ╚═════════════════════════════════════════════════════════════╝
    """)

    # 会议提醒
    now = datetime.now()
    if now.hour == 14 and now.minute < 5:
        print("\n" + "🔔" * 30)
        print("⏰  会议提醒：下午 2 点有会！")
        print("🔔" * 30 + "\n")

    # 保存 HTML
    full_file, short_file = save_html()

    print(f"\n📂 HTML 文件已保存！")
    print(f"   完整版: {full_file}")
    print(f"   精简版: {short_file}")
    print(f"\n💡 下一步：检查文件中的实际数据结构")


if __name__ == "__main__":
    main()
