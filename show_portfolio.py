#!/usr/bin/env python3
import sys
sys.path.insert(0, '/Users/aibot/.openclaw/workspace-engineer/crypto-portfolio/src')

from db.database import Database
db = Database('/Users/aibot/.openclaw/workspace-engineer/crypto-portfolio/portfolio.db')

# 使用内置方法
summary = db.get_asset_summary()

if not summary:
    print("No data")
    sys.exit(1)

snapshot = summary['snapshot']
print("=== 最新快照 ===")
print(f"时间: {snapshot['collected_at']}")
print(f"总资产: ${snapshot['total_assets']:,.2f}")
print(f"总负债: ${snapshot['total_debt']:,.2f}")
print(f"CEX净值: ${snapshot['net_value']:,.2f}")
print(f"手动记账: ${snapshot['manual_value']:,.2f}")
print(f"最终总计: ${snapshot['grand_total']:,.2f}")

print()
print("=== 按来源 ===")
for source, data in summary['by_source'].items():
    if data['debt'] > 0:
        print(f"{source:25} 资产:${data['assets']:>12,.2f}  负债:${data['debt']:>10,.2f}")
    else:
        print(f"{source:25} ${data['assets']:>12,.2f}")

print()
print("=== 前15大持仓 (按价值) ===")
for i, (coin, data) in enumerate(list(summary['by_coin'].items())[:15]):
    print(f"{coin:10} {data['quantity']:>15.4f}  ${data['value']:>12,.2f}")

print()
print("=== 手动记账 ===")
for entry in summary['manual_entries']:
    status = 'Y' if entry['is_active'] else 'N'
    expires = entry['expires_at'] if entry['expires_at'] else '-'
    print(f"{status} {entry['project']:20} {entry['coin']:6} {entry['quantity']:>12.4f}  到期:{expires}")

# 显示负债明细
print()
print("=== 负债明细 ===")
balances = db.get_latest_balances()
for b in balances:
    if b['is_debt']:
        print(f"{b['source']:20} {b['coin']:10} ${abs(b['value_usd']):>12,.2f}")
