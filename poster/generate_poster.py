#!/usr/bin/env python3
"""
Crypto3D Daily Poster Generator
"""
import json
import asyncio
from datetime import datetime
from pathlib import Path

# 路径配置
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

def load_all_indicators():
    data = {}
    
    # AHR999
    ahr999 = load_json(INDICATORS_DIR / "ahr999.json")
    if ahr999:
        current = ahr999.get("current", {})
        history = ahr999.get("history", [])
        data["ahr999"] = {
            "value": current.get("value", 0),
            "status": current.get("status", ""),
            "price": current.get("price", 0),
            "cost_200d": current.get("cost_200d", 0),
            "week_data": [h.get("ahr999", 0) for h in history[-7:]] if history else []
        }
    
    # MVRV
    mvrv = load_json(INDICATORS_DIR / "mvrv.json")
    if mvrv:
        current = mvrv.get("current", {})
        history = mvrv.get("history", [])
        data["mvrv"] = {
            "value": current.get("value", 0),
            "status": current.get("status", ""),
            "week_data": [h.get("mvrv", 0) for h in history[-7:]] if history else []
        }
    
    # BMRI
    bmri = load_json(INDICATORS_DIR / "bmri.json")
    if bmri and "1m" in bmri:
        current = bmri["1m"].get("current", {})
        history = bmri["1m"].get("history", [])
        data["bmri"] = {
            "value": current.get("value", 0),
                "regime": current.get("regime", "NEUTRAL"),
                "week_data": [h.get("bmri", 0) for h in history[-7:]] if history else []
        }
    
    # BTC.D
    btcd = load_json(INDICATORS_DIR / "btc-dominance.json")
    if btcd:
        current = btcd.get("current", {})
        history = btcd.get("history", [])
        data["btcd"] = {
            "value": current.get("value", 0),
                "zone": current.get("zone", "BALANCED"),
                "week_data": [h.get("value", 0) for h in history[-7:]] if history else []
        }
    
    return data

def select_focus(indicators):
    """选择最有话题性的焦点"""
    ahr999 = indicators.get("ahr999", {})
    mvrv = indicators.get("mvrv", {})
    bmri = indicators.get("bmri", {})
    
    # 1. AHR999 < 0.5
    if ahr999.get("value", 1) < 0.5:
        return "ahr999"
    
    # 2. MVRV > 3
    if mvrv.get("value", 0) > 3:
        return "mvrv"
    
    # 3. BMRI < 30 or > 70
    bmri_val = bmri.get("value", 50)
    if bmri_val < 30 or bmri_val > 70:
        return "bmri"
    
    # 4. 默认轮换
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

def make_chart(week_data, color, width=300, height=40):
    if not week_data or len(week_data) < 2:
        return ""
    
    min_val = min(week_data)
    max_val = max(week_data)
    range_val = max_val - min_val if max_val != min_val else 1
    
    points = []
    for i in range(len(week_data)):
        x = i * (width / (len(week_data) - 1))
        y = height - ((week_data[i] - min_val) / range_val * (height - 10) - 5
        points.append(f"{x:.1f},{y:.1f}")
    
    svg = f'''<svg viewBox="0 0 {width} {height}" preserveAspectRatio="none"><polyline fill="none" stroke="{color}" stroke-width="2" points="{" ".join(points)}"/><circle cx="{width}" cy="{points[-1].split(',')[1]}" r="3" fill="{color}"/></svg>'''
    return svg

def render_main(focus_type, data):
    value = data.get("value", 0)
    status = data.get("status", data.get("regime", "")
    color = get_color(status)
    week_data = data.get("week_data", [])
    chart = make_chart(week_data, color, 800, 50)
    
    if focus_type == "ahr999":
        price = data.get("price", 0)
        cost_200d = data.get("cost_200d", 0)
        return f'''
    <div class="main-card">
      <div class="card-header"><span class="icon">🔥</span><span class="title">AHR999</span></div>
      <div class="big-value" style="color:{color}">{value:.2f}</div>
      <div class="status-tag" style="background:{color}">{status}</div>
      <div class="hint">BTC ${price:,} | 200日成本 {cost_200d:,.0f}</div>
      {chart}
    </div>'''
    elif focus_type == "mvrv":
        return f'''
    <div class="main-card">
      <div class="card-header"><span class="icon">📈</span><span class="title">MVRV</span></div>
      <div class="big-value" style="color:{color}">{value:.2f}</div>
      <div class="status-tag" style="background:{color}">{status}</div>
      {chart}
    </div>'''
    elif focus_type == "bmri":
        risk = "低风险" if value < 30 else "高风险" if value > 70 else "中性"
        return f'''
    <div class="main-card">
      <div class="card-header"><span class="icon">⚠️</span><span class="title">BMRI</span></div>
      <div class="big-value" style="color:{color}">{value:.1f}</div>
      <div class="status-tag" style="background:{color}">{risk}</div>
      {chart}
    </div>'''
    else:  # btcd
        zone_text = "BTC主导" if data.get("zone") == "BTC_DOMINANT" else "山寨季" if data.get("zone") == "ALT_SEASON" else "平衡"
        return f'''
    <div class="main-card">
      <div class="card-header"><span class="icon">₿</span><span class="title">BTC.D</span></div>
      <div class="big-value" style="color:{color}">{value:.1f}%</div>
      <div class="status-tag" style="background:{color}">{zone_text}</div>
      {chart}
    </div>'''

def render_sub(card_type, data):
    value = data.get("value", 0)
    status = data.get("status", data.get("regime", ""))
    color = get_color(status)
    week_data = data.get("week_data", [])
    chart = make_chart(week_data, color, 300, 40)
    
    if card_type == "ahr999":
        icon, "🔥"
        label = "AHR999"
    elif card_type == "mvrv":
        icon = "📈"
        label = "MVRV"
    elif card_type == "bmri":
        icon = "⚠️"
        label = "BMRI"
        status = "低" if value < 30 else "高" if value > 70 else "中"
    else:
        icon = "₿"
        label = "BTC.D"
        status = f"{value:.1f}%"
    
    return f'''
    <div class="sub-card">
      <div class="sub-header"><span class="icon">{icon}</span><span class="label">{label}</span></div>
      <div class="sub-value" style="color:{color}">{value:.2f}</div>
      <div class="sub-status" style="color:{color}">{status}</div>
      {chart}
    </div>'''

def render_poster(focus, data):
    today = datetime.now().strftime("%b %d, %Y")
    
    # 确定副卡片
    sub_map = {
        "ahr999": ["mvrv", "bmri"],
        "mvrv": ["ahr999", "btcd"],
        "bmri": ["ahr999", "mvrv"],
        "btcd": ["ahr999", "mvrv"]
    }
    subs = sub_map.get(focus, ["mvrv", "bmri"])
    
    main_html = render_main(focus, data.get(focus, {}))
    
    sub_html = ""
    for s in subs[:2]:
        if s in data:
            sub_html += render_sub(s, data[s])
    
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
.header {{
  display: flex;
  justify-content: space-between;
  padding: 40px 60px;
  border-bottom: 1px solid #27272a;
}}
.logo {{
  display: flex;
  align-items: center;
  gap: 16px;
  font-size: 28px;
  font-weight: 700;
}}
.logo-icon {{
  width: 44px;
  height: 44px;
  background: linear-gradient(135deg, #3b82f6, #22c55e);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
}}
.date {{ color: #71717a; font-size: 18px; }}
.content {{
  flex: 1;
  padding: 60px;
  display: flex;
  flex-direction: column;
  gap: 40px;
}}
.main-card {{
  background: linear-gradient(145deg, #18181b, #0f0f11);
  border-radius: 32px;
  padding: 50px;
  border: 1px solid rgba(255,255,255,0.05);
}}
.card-header {{
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 20px;
}}
.icon {{ font-size: 32px; }}
.title {{ font-size: 18px; color: #71717a; font-weight: 500; }}
.big-value {{
  font-size: 72px;
  font-weight: 700;
  letter-spacing: -2px;
  margin-bottom: 16px;
}}
.status-tag {{
  display: inline-block;
  padding: 10px 24px;
  border-radius: 24px;
  font-size: 16px;
  font-weight: 600;
  color: #fafafa;
}}
.hint {{ font-size: 14px; color: #71717a; margin-top: 20px; }}
.sub-cards {{
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}}
.sub-card {{
  background: linear-gradient(145deg, #18181b, #0f0f11);
  border-radius: 20px;
  padding: 28px;
  border: 1px solid rgba(255,255,255,0.05);
}}
.sub-header {{
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
  font-size: 16px;
  color: #71717a;
}}
.sub-value {{ font-size: 32px; font-weight: 700; margin-bottom: 8px; }}
.sub-status {{ font-size: 13px; font-weight: 500; }}
.footer {{
  padding: 30px 60px;
  border-top: 1px solid #27272a;
  display: flex;
  justify-content: space-between;
  font-size: 16px;
  color: #71717a;
}}
.link {{ color: #3b82f6; font-weight: 600; font-size: 18px; }}
</style>
</head>
<body>
<div class="header">
  <div class="logo"><div class="logo-icon">📊</div>Crypto3D Daily</div>
  <div class="date">{today}</div>
</div>
<div class="content">
{main_html}
<div class="sub-cards">{sub_html}</div>
</div>
<div class="footer">
  <span>每日加密市场晴雨表</span>
  <span class="link">crypto3d.pro</span>
</div>
</body>
</html>"""

async def generate(headless=True):
    print("[1/4] 加载数据...")
    data = load_all_indicators()
    
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
        browser = await p.chromium.launch(headless=headless)
        page = await browser.new_page(viewport={"width": 1080, "height": 1350})
        await page.goto(f"file://{html_path}")
        await page.wait_for_timeout(500)
        await page.screenshot(path=str(png_path), type="png")
        await browser.close()
    
    print(f"[OK] {png_path}")
    return png_path

if __name__ == "__main__":
    asyncio.run(generate())
