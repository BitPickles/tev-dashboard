#!/usr/bin/env python3
"""Crypto3D Daily Poster - 信息密集型设计"""
import json
import asyncio
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
TEV_DIR = SCRIPT_DIR.parent
INDICATORS_DIR = TEV_DIR / "indicators" / "data"
OUTPUT_DIR = SCRIPT_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

def load_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except:
        return None

def load_all():
    data = {}
    
    # AHR999
    ahr999 = load_json(INDICATORS_DIR / "ahr999.json")
    if ahr999:
        c = ahr999.get("current", {})
        h = ahr999.get("history", [])
        data["ahr999"] = {
            "value": c.get("value", 0),
            "status": c.get("status", ""),
            "price": c.get("price", 0),
            "cost_200d": c.get("cost_200d", 0),
            "week_data": [x.get("close", 0) for x in h[-7:]] if h else [],
            "week_ahr999": [x.get("ahr999", 0) for x in h[-7:]] if h else []
        }
    
    # MVRV
    mvrv = load_json(INDICATORS_DIR / "mvrv.json")
    if mvrv:
        c = mvrv.get("current", {})
        h = mvrv.get("history", [])
        data["mvrv"] = {
            "value": c.get("value", 0),
            "status": c.get("status", ""),
            "week_data": [x.get("mvrv", 0) for x in h[-7:]] if h else []
        }
    
    # BMRI
    bmri = load_json(INDICATORS_DIR / "bmri.json")
    if bmri and "1m" in bmri:
        c = bmri["1m"].get("current", {})
        h = bmri["1m"].get("history", [])
        data["bmri"] = {
            "value": c.get("value", 50),
            "regime": c.get("regime", "NEUTRAL"),
            "week_data": [x.get("bmri", 50) for x in h[-7:]] if h else []
        }
    
    # BTC.D
    btcd = load_json(INDICATORS_DIR / "btc-dominance.json")
    if btcd:
        c = btcd.get("current", {})
        h = btcd.get("history", [])
        data["btcd"] = {
            "value": c.get("value", 50),
            "zone": c.get("zone", "BALANCED"),
            "week_data": [x.get("value", 50) for x in h[-7:]] if h else []
        }
    
    return data

def select_focus(data):
    ahr999 = data.get("ahr999", {})
    mvrv = data.get("mvrv", {})
    bmri = data.get("bmri", {})
    
    if ahr999.get("value", 1) < 0.5:
        return "ahr999"
    if mvrv.get("value", 0) > 3:
        return "mvrv"
    
    bmri_val = bmri.get("value", 50)
    if bmri_val < 30 or bmri_val > 70:
        return "bmri"
    
    weekday = datetime.now().weekday()
    rotation = ["ahr999", "btcd", "mvrv", "bmri", "ahr999", "ahr999", "ahr999"]
    return rotation[weekday]

def get_color(status):
    s = str(status).lower()
    if any(k in s for k in ["抄底", "合理", "neutral", "balanced", "low", "fair"]):
        return "#22c55e"
    if any(k in s for k in ["过热", "high", "extreme", "danger"]):
        return "#ef4444"
    return "#3b82f6"

def make_chart(data, color, w=200, h=30):
    if not data or len(data) < 2:
        return ""
    
    mn, mx = min(data), max(data)
    r = mx - mn if mx > mn else 1
    
    pts = []
    for i in range(len(data)):
        x = i * (w / (len(data) - 1))
        y = h - ((data[i] - mn) / r * (h - 6)) - 3
        pts.append(f"{x:.0f},{y:.1f}")
    
    last_y = h - ((data[-1] - mn) / r * (h - 6)) - 3
    pts_str = " ".join(pts)
    
    return f'<svg viewBox="0 0 {w} {h}" preserveAspectRatio="none"><polyline fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" points="{pts_str}"/><circle cx="{w}" cy="{last_y:.1f}" r="2.5" fill="{color}"/></svg>'

def render_btc_bar(data):
    """BTC 价格条 - 顶部"""
    prices = data.get("week_data", [])
    price = prices[-1] if prices else 0
    
    # 计算涨跌
    if len(prices) >= 2:
        change = ((prices[-1] - prices[0]) / prices[0]) * 100
        change_str = f"+{change:.1f}%" if change > 0 else f"{change:.1f}%"
        change_color = "#22c55e" if change > 0 else "#ef4444"
    else:
        change_str = "+0.0%"
        change_color = "#71717a"
    
    chart = make_chart(prices, "#f59e0b", 150, 20)
    
    return f'''
<div class="btc-bar">
  <div class="btc-left">
    <span class="btc-icon">₿</span>
    <span class="btc-label">BTC/USD</span>
    <span class="btc-price">${price:,.0f}</span>
  </div>
  <div class="btc-right">
    <div class="btc-chart">{chart}</div>
    <span class="btc-change" style="color:{change_color}">{change_str}</span>
  </div>
</div>'''

def render_main_card(focus, data):
    """主卡片 - 带解读"""
    value = data.get("value", 0)
    status = data.get("status", data.get("regime", ""))
    color = get_color(status)
    
    if focus == "ahr999":
        price = data.get("price", 0)
        cost_200d = data.get("cost_200d", 0)
        week_data = data.get("week_ahr999", [])
        chart = make_chart(week_data, color, 300, 40)
        
        # 计算进度条 (0-1.5 范围)
        progress = min(value / 1.5 * 100, 100)
        
        # 解读
        if value < 0.45:
            interpretation = "BTC 价格低于 200 日成本线，历史上定投收益显著"
        elif value < 0.75:
            interpretation = "价格接近合理区间，可继续持有"
        else:
            interpretation = "价格高于历史成本线，注意风险"
        
        return f'''
<div class="main-card">
  <div class="main-header">
    <span class="main-icon">🔥</span>
    <span class="main-title">AHR999</span>
    <span class="main-value" style="color:{color}">{value:.2f}</span>
  </div>
  <div class="progress-row">
    <div class="progress-bar"><div class="progress-fill" style="width:{progress}%;background:{color}"></div></div>
    <span class="progress-status" style="color:{color}">{status}</span>
  </div>
  <div class="main-detail">
    <span>BTC ${price:,}</span>
    <span>200日成本 ${cost_200d:,.0f}</span>
  </div>
  <div class="main-chart">{chart}</div>
  <div class="main-hint">{interpretation}</div>
</div>'''
    
    elif focus == "mvrv":
        week_data = data.get("week_data", [])
        chart = make_chart(week_data, color, 300, 40)
        progress = min(value / 4 * 100, 100)
        
        if value < 1.5:
            interpretation = "持币者整体亏损，历史底部信号"
        elif value < 2.5:
            interpretation = "市场处于合理估值区间"
        else:
            interpretation = "市场过热，注意回调风险"
        
        return f'''
<div class="main-card">
  <div class="main-header">
    <span class="main-icon">📈</span>
    <span class="main-title">MVRV</span>
    <span class="main-value" style="color:{color}">{value:.2f}</span>
  </div>
  <div class="progress-row">
    <div class="progress-bar"><div class="progress-fill" style="width:{progress}%;background:{color}"></div></div>
    <span class="progress-status" style="color:{color}">{status}</span>
  </div>
  <div class="main-chart">{chart}</div>
  <div class="main-hint">{interpretation}</div>
</div>'''
    
    elif focus == "bmri":
        week_data = data.get("week_data", [])
        chart = make_chart(week_data, color, 300, 40)
        risk_text = "低风险" if value < 30 else "高风险" if value > 70 else "中性"
        progress = value
        
        if value < 30:
            interpretation = "市场风险较低，适合增加仓位"
        elif value > 70:
            interpretation = "市场风险较高，注意止损"
        else:
            interpretation = "市场风险中性，保持观望"
        
        return f'''
<div class="main-card">
  <div class="main-header">
    <span class="main-icon">⚠️</span>
    <span class="main-title">BMRI</span>
    <span class="main-value" style="color:{color}">{value:.1f}</span>
  </div>
  <div class="progress-row">
    <div class="progress-bar"><div class="progress-fill" style="width:{progress}%;background:{color}"></div></div>
    <span class="progress-status" style="color:{color}">{risk_text}</span>
  </div>
  <div class="main-chart">{chart}</div>
  <div class="main-hint">{interpretation}</div>
</div>'''
    
    else:  # btcd
        week_data = data.get("week_data", [])
        chart = make_chart(week_data, color, 300, 40)
        zone = data.get("zone", "BALANCED")
        zone_text = "BTC主导" if zone == "BTC_DOMINANT" else "山寨季" if zone == "ALT_SEASON" else "平衡"
        
        if zone == "BTC_DOMINANT":
            interpretation = "资金集中在 BTC，山寨币表现疲软"
        elif zone == "ALT_SEASON":
            interpretation = "山寨季信号，可关注山寨币机会"
        else:
            interpretation = "市场资金分布均衡"
        
        return f'''
<div class="main-card">
  <div class="main-header">
    <span class="main-icon">₿</span>
    <span class="main-title">BTC.D</span>
    <span class="main-value" style="color:{color}">{value:.1f}%</span>
  </div>
  <div class="progress-row">
    <div class="progress-bar"><div class="progress-fill" style="width:{value}%;background:{color}"></div></div>
    <span class="progress-status" style="color:{color}">{zone_text}</span>
  </div>
  <div class="main-chart">{chart}</div>
  <div class="main-hint">{interpretation}</div>
</div>'''

def render_sub_row(data):
    """副卡片行 - MVRV + BMRI"""
    mvrv = data.get("mvrv", {})
    bmri = data.get("bmri", {})
    
    # MVRV
    mvrv_val = mvrv.get("value", 0)
    mvrv_status = mvrv.get("status", "")
    mvrv_color = get_color(mvrv_status)
    mvrv_chart = make_chart(mvrv.get("week_data", []), mvrv_color, 140, 24)
    
    # BMRI
    bmri_val = bmri.get("value", 50)
    bmri_status = "低" if bmri_val < 30 else "高" if bmri_val > 70 else "中"
    bmri_color = "#22c55e" if bmri_val < 30 else "#ef4444" if bmri_val > 70 else "#3b82f6"
    bmri_chart = make_chart(bmri.get("week_data", []), bmri_color, 140, 24)
    
    return f'''
<div class="sub-row">
  <div class="sub-card">
    <div class="sub-head">
      <span class="sub-icon">📈</span>
      <span class="sub-title">MVRV</span>
      <span class="sub-val" style="color:{mvrv_color}">{mvrv_val:.2f}</span>
    </div>
    <div class="sub-chart">{mvrv_chart}</div>
    <div class="sub-status" style="color:{mvrv_color}">{mvrv_status}</div>
  </div>
  <div class="sub-card">
    <div class="sub-head">
      <span class="sub-icon">⚠️</span>
      <span class="sub-title">BMRI</span>
      <span class="sub-val" style="color:{bmri_color}">{bmri_val:.1f}</span>
    </div>
    <div class="sub-chart">{bmri_chart}</div>
    <div class="sub-status" style="color:{bmri_color}">{bmri_status}风险</div>
  </div>
</div>'''

def render_poster(focus, data):
    today = datetime.now().strftime("%b %d, %Y")
    
    btc_bar = render_btc_bar(data.get("ahr999", {}))
    main_card = render_main_card(focus, data.get(focus, {}))
    sub_row = render_sub_row(data)
    
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
  font-family: 'Inter', sans-serif;
  background: #0a0a0b;
  color: #fafafa;
  width: 1080px;
  height: 1350px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}}

/* Header */
.hdr {{
  padding: 30px 50px 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}}
.logo {{
  display: flex;
  align-items: center;
  gap: 14px;
  font-size: 26px;
  font-weight: 700;
}}
.logo-ic {{
  width: 44px;
  height: 44px;
  background: linear-gradient(135deg, #3b82f6, #22c55e);
  border-radius: 11px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
}}
.date {{ color: #71717a; font-size: 16px; }}

/* BTC Bar */
.btc-bar {{
  margin: 0 50px;
  padding: 16px 24px;
  background: linear-gradient(145deg, #1a1a1d, #141416);
  border-radius: 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}}
.btc-left {{
  display: flex;
  align-items: center;
  gap: 14px;
}}
.btc-icon {{
  font-size: 28px;
}}
.btc-label {{
  font-size: 14px;
  color: #71717a;
  font-weight: 500;
}}
.btc-price {{
  font-size: 28px;
  font-weight: 700;
  color: #f59e0b;
}}
.btc-right {{
  display: flex;
  align-items: center;
  gap: 16px;
}}
.btc-chart {{
  width: 150px;
  height: 20px;
}}
.btc-change {{
  font-size: 16px;
  font-weight: 600;
  min-width: 60px;
  text-align: right;
}}

/* Content */
.cnt {{
  flex: 1;
  padding: 30px 50px;
  display: flex;
  flex-direction: column;
  gap: 24px;
}}

/* Main Card */
.main-card {{
  background: linear-gradient(145deg, #18181b, #0f0f11);
  border-radius: 24px;
  padding: 32px;
  border: 1px solid rgba(255,255,255,0.05);
}}
.main-header {{
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 20px;
}}
.main-icon {{
  font-size: 32px;
}}
.main-title {{
  font-size: 16px;
  color: #71717a;
  font-weight: 500;
}}
.main-value {{
  margin-left: auto;
  font-size: 48px;
  font-weight: 700;
  letter-spacing: -1px;
}}

/* Progress */
.progress-row {{
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 16px;
}}
.progress-bar {{
  flex: 1;
  height: 8px;
  background: #27272a;
  border-radius: 4px;
  overflow: hidden;
}}
.progress-fill {{
  height: 100%;
  border-radius: 4px;
  transition: width 0.3s;
}}
.progress-status {{
  font-size: 14px;
  font-weight: 600;
  min-width: 60px;
}}

.main-detail {{
  display: flex;
  gap: 32px;
  font-size: 14px;
  color: #a1a1aa;
  margin-bottom: 16px;
}}

.main-chart {{
  height: 40px;
  margin-bottom: 16px;
}}

.main-hint {{
  font-size: 14px;
  color: #71717a;
  line-height: 1.5;
  padding-top: 12px;
  border-top: 1px solid #27272a;
}}

/* Sub Row */
.sub-row {{
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}}
.sub-card {{
  background: linear-gradient(145deg, #18181b, #0f0f11);
  border-radius: 16px;
  padding: 20px;
  border: 1px solid rgba(255,255,255,0.05);
}}
.sub-head {{
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}}
.sub-icon {{
  font-size: 22px;
}}
.sub-title {{
  font-size: 13px;
  color: #71717a;
  font-weight: 500;
}}
.sub-val {{
  margin-left: auto;
  font-size: 26px;
  font-weight: 700;
}}
.sub-chart {{
  height: 24px;
  margin-bottom: 8px;
}}
.sub-status {{
  font-size: 12px;
  font-weight: 500;
}}

/* Footer */
.ftr {{
  padding: 24px 50px;
  border-top: 1px solid #27272a;
  display: flex;
  justify-content: space-between;
  font-size: 14px;
  color: #71717a;
}}
.link {{
  color: #3b82f6;
  font-weight: 600;
  font-size: 16px;
}}
</style>
</head>
<body>

<div class="hdr">
  <div class="logo"><div class="logo-ic">📊</div>Crypto3D Daily</div>
  <div class="date">{today}</div>
</div>

{btc_bar}

<div class="cnt">
{main_card}
{sub_row}
</div>

<div class="ftr">
  <span>每日加密市场晴雨表</span>
  <span class="link">crypto3d.pro</span>
</div>

</body>
</html>"""

async def generate():
    print("[1/4] 加载数据...")
    data = load_all()
    
    print("[2/4] 选择焦点...")
    focus = select_focus(data)
    print(f"  焦点: {focus.upper()}")
    
    print("[3/4] 渲染海报...")
    html = render_poster(focus, data)
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    html_path = OUTPUT_DIR / f"{today_str}.html"
    with open(html_path, "w") as f:
        f.write(html)
    
    print("[4/4] 截图...")
    png_path = OUTPUT_DIR / f"{today_str}.png"
    
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1080, "height": 1350})
        await page.goto(f"file://{html_path}")
        await page.wait_for_timeout(500)
        await page.screenshot(path=str(png_path), type="png")
        await browser.close()
    
    print(f"[OK] {png_path}")
    return png_path

if __name__ == "__main__":
    asyncio.run(generate())
