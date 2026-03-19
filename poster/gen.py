#!/usr/bin/env python3
"""Crypto3D Daily Poster Generator"""
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
            "price": c.get("price", 1),
            "cost_200d": c.get("cost_200d", 1),
            "week_data": [x.get("close", x.get("price", 1)) for x in h[-7:]] if h else []
        }
    
    # MVRV
    mvrv = load_json(INDICATORS_DIR / "mvrv.json")
    if mvrv:
        c = mvrv.get("current", {})
        h = mvrv.get("history", [])
        data["mvrv"] = {
            "value": c.get("value", 1),
            "status": c.get("status", ""),
            "week_data": [x.get("mvrv", 1) for x in h[-7:]] if h else []
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

def make_chart(data, color, w=300, h=40):
    if not data or len(data) < 2:
        return ""
    
    mn, mx = min(data), max(data)
    r = mx - mn if mx > mn else 1
    
    pts = []
    for i in range(len(data)):
        x = i * (w / (len(data) - 1))
        y = h - ((data[i] - mn) / r * (h - 10)) - 5
        pts.append(f"{x:.0f},{y:.1f}")
    
    return f'<svg viewBox="0 0 {w} {h}"><polyline fill="none" stroke="{color}" stroke-width="2" points="{" ".join(pts)}"/><circle cx="{w}" cy="{pts[-1].split(',')[1]}" r="3" fill="{color}"/></svg>'

def render_main(focus, data):
    value = data.get("value", 0)
    status = data.get("status", data.get("regime", ""))
    color = get_color(status)
    week_data = data.get("week_data", [])
    chart = make_chart(week_data, color, 700, 60)
    
    if focus == "ahr999":
        price = data.get("price", 1)
        cost_200d = data.get("cost_200d", 1)
        return f'''
<div class="main">
  <div class="card-head"><span class="ic">🔥</span><span class="nm">AHR999</span></div>
  <div class="big" style="color:{color}">{value:.2f}</div>
  <div class="tag" style="background:{color}">{status}</div>
  <div class="hint">BTC ${price:,} | 200日成本 {cost_200d:,.0f}</div>
  <div class="chart">{chart}</div>
</div>'''
    elif focus == "mvrv":
        return f'''
<div class="main">
  <div class="card-head"><span class="ic">📈</span><span class="nm">MVRV</span></div>
  <div class="big" style="color:{color}">{value:.2f}</div>
  <div class="tag" style="background:{color}">{status}</div>
  <div class="chart">{chart}</div>
</div>'''
    elif focus == "bmri":
        risk = "低风险" if value < 30 else "高风险" if value > 70 else "中性"
        return f'''
<div class="main">
  <div class="card-head"><span class="ic">⚠️</span><span class="nm">BMRI</span></div>
  <div class="big" style="color:{color}">{value:.1f}</div>
  <div class="tag" style="background:{color}">{risk}</div>
  <div class="chart">{chart}</div>
</div>'''
    else:  # btcd
        zone_text = "BTC主导" if data.get("zone") == "BTC_DOMINANT" else "山寨季" if data.get("zone") == "ALT_SEASON" else "平衡"
        return f'''
<div class="main">
  <div class="card-head"><span class="ic">₿</span><span class="nm">BTC.D</span></div>
  <div class="big" style="color:{color}">{value:.1f}%</div>
  <div class="tag" style="background:{color}">{zone_text}</div>
  <div class="chart">{chart}</div>
</div>'''

def render_btc(price_data):
    """BTC 价格卡片 - 固定显示"""
    prices = price_data.get("week_data", [])
    if not prices or len(prices) < 2:
        return ""
    
    price = prices[-1] if prices else 0
    mn, mx = min(prices), max(prices)
    r = mx - mn if mx > mn else 1
    
    w, h = 200, 50
    pts = []
    for i in range(len(prices)):
        x = i * (w / (len(prices) - 1))
        y = h - ((prices[i] - mn) / r * (h - 10)) - 5
        pts.append(f"{x:.0f},{y:.1f}")
    
    svg = f'<svg viewBox="0 0 {w} {h}"><polyline fill="none" stroke="#f59e0b" stroke-width="2" points="{" ".join(pts)}"/><circle cx="{w}" cy="{pts[-1].split(',')[1]}" r="3" fill="#f59e0b"/></svg>'
    
    return f'''
<div class="btc-card">
  <div class="btc-head"><span class="ic">₿</span><span class="nm">BTC/USD</span></div>
  <div class="btc-price">${price:,.0f}</div>
  <div class="chart">{svg}</div>
</div>'''

def render_sub(name, data):
    value = data.get("value", 0)
    status = data.get("status", data.get("regime", ""))
    color = get_color(status)
    week_data = data.get("week_data", [])
    chart = make_chart(week_data, color, 200, 30)
    
    if name == "ahr999":
        icon, "🔥"
        label = "AHR999"
    elif name == "mvrv":
        icon = "📈"
        label = "MVRV"
    elif name == "bmri":
        icon = "⚠️"
        label = "BMRI"
        status = "低" if value < 30 else "高" if value > 70 else "中"
    else:
        icon = "₿"
        label = "BTC.D"
        status = f"{value:.1f}%"
    
    return f'''
<div class="sub">
  <div class="sub-head"><span class="ic">{icon}</span><span class="nm">{label}</span></div>
  <div class="sub-val" style="color:{color}">{value:.2f}</div>
  <div class="sub-st" style="color:{color}">{status}</div>
  <div class="chart">{chart}</div>
</div>'''

def render_poster(focus, data):
    today = datetime.now().strftime("%b %d, %Y")
    
    # 主卡片
    main_html = render_main(focus, data.get(focus, {}))
    
    # BTC 价格卡片（固定）
    btc_html = render_btc(data.get("ahr999", {}))
    
    # 副卡片
    sub_names = {"ahr999": ["mvrv", "bmri"], "mvrv": ["ahr999", "btcd"], "bmri": ["ahr999", "mvrv"], "btcd": ["ahr999", "mvrv"]}
    subs = sub_names.get(focus, ["mvrv", "bmri"])
    
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
.hdr {{
  display: flex;
  justify-content: space-between;
  padding: 36px 50px;
  border-bottom: 1px solid #27272a;
}}
.logo {{
  display: flex;
  align-items: center;
  gap: 14px;
  font-size: 26px;
  font-weight: 700;
}}
.logo-ic {{
  width: 42px;
  height: 42px;
  background: linear-gradient(135deg, #3b82f6, #22c55e);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
}}
.date {{ color: #71717a; font-size: 16px; }}
.cnt {{
  flex: 1;
  padding: 40px 50px;
  display: flex;
  flex-direction: column;
  gap: 24px;
}}
.main {{
  background: linear-gradient(145deg, #18181b, #0f0f11);
  border-radius: 24px;
  padding: 36px;
  border: 1px solid rgba(255,255,255,0.05);
}}
.card-head {{
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}}
.ic {{ font-size: 28px; }}
.nm {{ font-size: 15px; color: #71717a; font-weight: 500; }}
.big {{
  font-size: 56px;
  font-weight: 700;
  letter-spacing: -1px;
  margin-bottom: 12px;
}}
.tag {{
  display: inline-block;
  padding: 8px 18px;
  border-radius: 20px;
  font-size: 14px;
  font-weight: 600;
  color: #fafafa;
}}
.hint {{ font-size: 13px; color: #71717a; margin-top: 16px; }}
.chart {{ margin-top: 16px; }}
.row {{
  display: grid;
  grid-template-columns: 200px 1fr;
  gap: 24px;
}}
.btc-card {{
  background: linear-gradient(145deg, #18181b, #0f0f11);
  border-radius: 20px;
  padding: 24px;
  border: 1px solid rgba(255,255,255,0.05);
  text-align: center;
}}
.btc-head {{
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-bottom: 12px;
  font-size: 14px;
  color: #71717a;
}}
.btc-price {{
  font-size: 28px;
  font-weight: 700;
  color: #f59e0b;
}}
.subs {{
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}}
.sub {{
  background: linear-gradient(145deg, #18181b, #0f0f11);
  border-radius: 16px;
  padding: 20px;
  border: 1px solid rgba(255,255,255,0.05);
}}
.sub-head {{
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
  font-size: 14px;
  color: #71717a;
}}
.sub-val {{ font-size: 28px; font-weight: 700; margin-bottom: 6px; }}
.sub-st {{ font-size: 12px; font-weight: 500; }}
.ftr {{
  padding: 24px 50px;
  border-top: 1px solid #27272a;
  display: flex;
  justify-content: space-between;
  font-size: 14px;
  color: #71717a;
}}
.link {{ color: #3b82f6; font-weight: 600; font-size: 16px; }}
</style>
</head>
<body>
<div class="hdr">
  <div class="logo"><div class="logo-ic">📊</div>Crypto3D Daily</div>
  <div class="date">{today}</div>
</div>
<div class="cnt">
{main_html}
<div class="row">
{btc_html}
<div class="subs">{sub_html}</div>
</div>
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
