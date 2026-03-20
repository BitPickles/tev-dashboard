#!/usr/bin/env python3
"""Crypto3D Daily Poster - 简洁优雅版"""
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
            "week_prices": [x.get("close", 0) for x in h[-7:]] if h else []
        }
    
    # MVRV
    mvrv = load_json(INDICATORS_DIR / "mvrv.json")
    if mvrv:
        c = mvrv.get("current", {})
        h = mvrv.get("history", [])
        data["mvrv"] = {
            "value": c.get("value", 0),
            "status": c.get("status", ""),
            "week": [x.get("mvrv", 0) for x in h[-7:]] if h else []
        }
    
    # BMRI
    bmri = load_json(INDICATORS_DIR / "bmri.json")
    if bmri and "1m" in bmri:
        c = bmri["1m"].get("current", {})
        h = bmri["1m"].get("history", [])
        data["bmri"] = {
            "value": c.get("value", 50),
            "week": [x.get("bmri", 50) for x in h[-7:]] if h else []
        }
    
    # BTC.D
    btcd = load_json(INDICATORS_DIR / "btc-dominance.json")
    if btcd:
        c = btcd.get("current", {})
        h = btcd.get("history", [])
        data["btcd"] = {
            "value": c.get("value", 50),
            "zone": c.get("zone", "BALANCED"),
            "week": [x.get("value", 50) for x in h[-7:]] if h else []
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
    if bmri.get("value", 50) < 30 or bmri.get("value", 50) > 70:
        return "bmri"
    
    weekday = datetime.now().weekday()
    return ["ahr999", "btcd", "mvrv", "bmri", "ahr999", "ahr999", "ahr999"][weekday]

def sparkline(data, color, w=120, h=32):
    if not data or len(data) < 2:
        return ""
    mn, mx = min(data), max(data)
    r = mx - mn if mx > mn else 1
    pts = []
    for i in range(len(data)):
        x = i * (w / (len(data) - 1))
        y = h - ((data[i] - mn) / r * (h - 8)) - 4
        pts.append(f"{x:.0f},{y:.0f}")
    ly = h - ((data[-1] - mn) / r * (h - 8)) - 4
    return f'<svg viewBox="0 0 {w} {h}"><polyline fill="none" stroke="{color}" stroke-width="2.5" stroke-linecap="round" points="{" ".join(pts)}"/><circle cx="{w}" cy="{ly:.0f}" r="3" fill="{color}"/></svg>'

def render(focus, data):
    today = datetime.now().strftime("%Y.%m.%d")
    
    # BTC 价格
    prices = data.get("ahr999", {}).get("week_prices", [])
    btc_price = prices[-1] if prices else 0
    btc_chart = sparkline(prices, "#f59e0b", 100, 24)
    btc_change = ""
    if len(prices) >= 2:
        ch = ((prices[-1] - prices[0]) / prices[0]) * 100
        btc_change = f'<span style="color:{"#22c55e" if ch>0 else "#ef4444"}">{"+" if ch>0 else ""}{ch:.1f}%</span>'
    
    # 主指标
    main = data.get(focus, {})
    main_val = main.get("value", 0)
    main_status = main.get("status", "中性")
    
    # 颜色逻辑
    def col(v, s=""):
        s = str(s).lower()
        if "抄底" in s or "合理" in s or v < 0.5:
            return "#22c55e"
        if "过热" in s or v > 3:
            return "#ef4444"
        return "#3b82f6"
    
    main_color = col(main_val, main_status)
    
    # 主卡片内容
    if focus == "ahr999":
        main_html = f'''
    <div class="main">
      <div class="m-hd"><span class="ic">🔥</span><span class="lb">AHR999</span></div>
      <div class="m-num" style="color:{main_color}">{main_val:.2f}</div>
      <div class="m-tag" style="background:{main_color}">{main_status}</div>
      <div class="m-info">BTC ${data["ahr999"]["price"]:,} · 200日成本 ${data["ahr999"]["cost_200d"]:,.0f}</div>
      <div class="m-desc">价格低于200日成本线，历史上此位置定投收益显著</div>
    </div>'''
    elif focus == "mvrv":
        main_html = f'''
    <div class="main">
      <div class="m-hd"><span class="ic">📈</span><span class="lb">MVRV</span></div>
      <div class="m-num" style="color:{main_color}">{main_val:.2f}</div>
      <div class="m-tag" style="background:{main_color}">{main_status}</div>
      <div class="m-desc">持币者盈利倍数，<1.5 为低估，>3 为过热</div>
    </div>'''
    elif focus == "bmri":
        risk = "低风险" if main_val < 30 else "高风险" if main_val > 70 else "中性"
        main_html = f'''
    <div class="main">
      <div class="m-hd"><span class="ic">⚠️</span><span class="lb">BMRI</span></div>
      <div class="m-num" style="color:{main_color}">{main_val:.1f}</div>
      <div class="m-tag" style="background:{main_color}">{risk}</div>
      <div class="m-desc">综合风险指数，<30 低风险，>70 高风险</div>
    </div>'''
    else:
        zone = "BTC主导" if main.get("zone") == "BTC_DOMINANT" else "山寨季" if main.get("zone") == "ALT_SEASON" else "平衡"
        main_html = f'''
    <div class="main">
      <div class="m-hd"><span class="ic">₿</span><span class="lb">BTC.D</span></div>
      <div class="m-num" style="color:{main_color}">{main_val:.1f}%</div>
      <div class="m-tag" style="background:{main_color}">{zone}</div>
      <div class="m-desc">BTC 市值占比，>60% BTC主导，<50% 山寨季</div>
    </div>'''
    
    # 副指标
    mvrv = data.get("mvrv", {})
    mvrv_v = mvrv.get("value", 0)
    mvrv_c = col(mvrv_v, mvrv.get("status", ""))
    mvrv_ch = sparkline(mvrv.get("week", []), mvrv_c, 80, 20)
    
    bmri = data.get("bmri", {})
    bmri_v = bmri.get("value", 50)
    bmri_c = "#22c55e" if bmri_v < 30 else "#ef4444" if bmri_v > 70 else "#3b82f6"
    bmri_ch = sparkline(bmri.get("week", []), bmri_c, 80, 20)
    
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=Space+Grotesk:wght@500;700&display=swap');
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
  font-family: 'DM Sans', sans-serif;
  background: #09090b;
  color: #fafafa;
  width: 1080px;
  height: 1350px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}}

/* Header */
.hd {{
  padding: 48px 64px 32px;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}}
.logo {{
  display: flex;
  flex-direction: column;
  gap: 8px;
}}
.logo-t {{
  font-family: 'Space Grotesk', sans-serif;
  font-size: 32px;
  font-weight: 700;
  letter-spacing: -0.5px;
}}
.logo-s {{
  font-size: 13px;
  color: #52525b;
  letter-spacing: 0.5px;
}}
.date {{
  font-family: 'Space Grotesk', sans-serif;
  font-size: 15px;
  color: #71717a;
  font-weight: 500;
}}

/* BTC Bar */
.btc {{
  margin: 0 64px;
  padding: 20px 28px;
  background: #18181b;
  border-radius: 16px;
  display: flex;
  align-items: center;
  gap: 20px;
}}
.btc-ic {{
  font-size: 32px;
}}
.btc-info {{
  display: flex;
  flex-direction: column;
  gap: 4px;
}}
.btc-lb {{
  font-size: 11px;
  color: #71717a;
  text-transform: uppercase;
  letter-spacing: 1px;
}}
.btc-num {{
  font-family: 'Space Grotesk', sans-serif;
  font-size: 32px;
  font-weight: 700;
  color: #f59e0b;
}}
.btc-rt {{
  margin-left: auto;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 6px;
}}
.btc-ch {{
  height: 24px;
  width: 100px;
}}
.btc-chg {{
  font-size: 15px;
  font-weight: 600;
}}

/* Main */
.cnt {{
  flex: 1;
  padding: 48px 64px;
  display: flex;
  flex-direction: column;
  gap: 32px;
}}
.main {{
  background: linear-gradient(135deg, #18181b 0%, #0f0f11 100%);
  border-radius: 24px;
  padding: 40px;
  border: 1px solid rgba(255,255,255,0.03);
}}
.m-hd {{
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 24px;
}}
.ic {{
  font-size: 28px;
}}
.lb {{
  font-size: 14px;
  color: #71717a;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 1px;
}}
.m-num {{
  font-family: 'Space Grotesk', sans-serif;
  font-size: 80px;
  font-weight: 700;
  letter-spacing: -2px;
  margin-bottom: 16px;
}}
.m-tag {{
  display: inline-block;
  padding: 8px 20px;
  border-radius: 20px;
  font-size: 15px;
  font-weight: 600;
  color: #fafafa;
  margin-bottom: 20px;
}}
.m-info {{
  font-size: 15px;
  color: #a1a1aa;
  margin-bottom: 16px;
}}
.m-desc {{
  font-size: 14px;
  color: #71717a;
  line-height: 1.6;
  padding-top: 16px;
  border-top: 1px solid #27272a;
}}

/* Subs */
.subs {{
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}}
.sub {{
  background: #18181b;
  border-radius: 16px;
  padding: 24px;
}}
.s-hd {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}}
.s-lb {{
  font-size: 13px;
  color: #71717a;
  font-weight: 500;
}}
.s-val {{
  font-family: 'Space Grotesk', sans-serif;
  font-size: 28px;
  font-weight: 700;
  margin-bottom: 8px;
}}
.s-ch {{
  height: 20px;
  width: 80px;
  margin-bottom: 8px;
}}
.s-st {{
  font-size: 12px;
  font-weight: 500;
}}

/* Footer */
.ft {{
  padding: 32px 64px;
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  color: #52525b;
}}
.link {{
  color: #3b82f6;
  font-weight: 600;
}}
</style>
</head>
<body>

<div class="hd">
  <div class="logo">
    <div class="logo-t">Crypto3D Daily</div>
    <div class="logo-s">Market Intelligence</div>
  </div>
  <div class="date">{today}</div>
</div>

<div class="btc">
  <span class="btc-ic">₿</span>
  <div class="btc-info">
    <div class="btc-lb">Bitcoin</div>
    <div class="btc-num">${btc_price:,.0f}</div>
  </div>
  <div class="btc-rt">
    <div class="btc-ch">{btc_chart}</div>
    <div class="btc-chg">{btc_change}</div>
  </div>
</div>

<div class="cnt">
{main_html}
<div class="subs">
  <div class="sub">
    <div class="s-hd">
      <span class="s-lb">📈 MVRV</span>
    </div>
    <div class="s-val" style="color:{mvrv_c}">{mvrv_v:.2f}</div>
    <div class="s-ch">{mvrv_ch}</div>
    <div class="s-st" style="color:{mvrv_c}">{mvrv.get("status", "")}</div>
  </div>
  <div class="sub">
    <div class="s-hd">
      <span class="s-lb">⚠️ BMRI</span>
    </div>
    <div class="s-val" style="color:{bmri_c}">{bmri_v:.1f}</div>
    <div class="s-ch">{bmri_ch}</div>
    <div class="s-st" style="color:{bmri_c}">{"低风险" if bmri_v<30 else "高风险" if bmri_v>70 else "中性"}</div>
  </div>
</div>
</div>

<div class="ft">
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
    
    print("[3/4] 渲染...")
    html = render(focus, data)
    
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
