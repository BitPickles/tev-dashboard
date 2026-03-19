#!/usr/bin/env python3
"""
Crypto3D 推特日报生成器 - 简洁版 v2
"""

import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

SCRIPT_DIR = Path(__file__).parent
TEV_DIR = SCRIPT_DIR.parent
INDICATORS_DIR = TEV_DIR / "indicators" / "data"
OUTPUT_DIR = SCRIPT_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

def load_json(path: Path) -> Optional[Dict]:
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except:
        return None

def load_all_indicators() -> Dict:
    data = {}
    
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
    
    mvrv = load_json(INDICATORS_DIR / "mvrv.json")
    if mvrv:
        current = mvrv.get("current", {})
        history = mvrv.get("history", [])
        data["mvrv"] = {
            "value": current.get("value", 0),
            "status": current.get("status", ""),
            "week_data": [h.get("mvrv", 0) for h in history[-7:]] if history else []
        }
    
    bmri = load_json(INDICATORS_DIR / "bmri.json")
    if bmri and "1m" in bmri:
        current = bmri["1m"].get("current", {})
        history = bmri["1m"].get("history", [])
        data["bmri"] = {
            "value": current.get("value", 0),
            "regime": current.get("regime", "NEUTRAL"),
            "week_data": [h.get("bmri", 0) for h in history[-7:]] if history else []
        }
    
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

def select_focus(indicators: Dict) -> Dict:
    ahr999 = indicators.get("ahr999", {})
    mvrv = indicators.get("mvrv", {})
    bmri = indicators.get("bmri", {})
    
    if ahr999.get("value", 1) < 0.5:
        return {"focus": "ahr999", "subs": ["mvrv", "bmri"]}
    if mvrv.get("value", 0) > 3:
        return {"focus": "mvrv", "subs": ["ahr999", "btcd"]}
    
    bmri_val = bmri.get("value", 50)
    if bmri_val < 30 or bmri_val > 70:
        return {"focus": "bmri", "subs": ["ahr999", "mvrv"]}
    
    weekday = datetime.now().weekday()
    rotation = ["ahr999", "btcd", "mvrv", "bmri", "ahr999", "ahr999", "ahr999"]
    focus = rotation[weekday]
    sub_map = {
        "ahr999": ["mvrv", "bmri"],
        "mvrv": ["ahr999", "btcd"],
        "bmri": ["ahr999", "mvrv"],
        "btcd": ["ahr999", "mvrv"]
    }
    return {"focus": focus, "subs": sub_map.get(focus, ["mvrv", "bmri"])}

def get_color(status: str) -> str:
    if any(k in status for k in ["抄底", "合理", "NEUTRAL", "BALANCED", "LOW"]):
        return "#22c55e"
    if any(k in status for k in ["过热", "HIGH", "EXTREME"]):
        return "#ef4444"
    return "#3b82f6"

def render_main(card_type: str, data: Dict) -> str:
    value = data.get("value", 0)
    status = data.get("status", data.get("regime", ""))
    color = get_color(status)
    
    if card_type == "ahr999":
        price = data.get("price", 0)
        cost = data.get("cost_200d", 0)
        return f'''
    <div class="main-card">
      <div class="card-header"><span class="icon">🔥</span><span class="title">AHR999</span></div>
      <div class="big-value" style="color:{color}">{value:.2f}</div>
      <div class="status-tag" style="background:{color}">{status}</div>
      <div class="hint">BTC ${price:,} | 200日成本 {cost:,.0f}</div>
    </div>'''
    elif card_type == "mvrv":
        return f'''
    <div class="main-card">
      <div class="card-header"><span class="icon">📈</span><span class="title">MVRV</span></div>
      <div class="big-value" style="color:{color}">{value:.2f}</div>
      <div class="status-tag" style="background:{color}">{status}</div>
    </div>'''
    elif card_type == "bmri":
        risk = "低风险" if value < 30 else "高风险" if value > 70 else "中性"
        return f'''
    <div class="main-card">
      <div class="card-header"><span class="icon">⚠️</span><span class="title">BMRI</span></div>
      <div class="big-value" style="color:{color}">{value:.1f}</div>
      <div class="status-tag" style="background:{color}">{risk}</div>
    </div>'''
    else:  # btcd
        zone = "BTC主导" if data.get("zone") == "BTC_DOMINANT" else "山寨季" if data.get("zone") == "ALT_SEASON" else "平衡"
        return f'''
    <div class="main-card">
      <div class="card-header"><span class="icon">₿</span><span class="title">BTC.D</span></div>
      <div class="big-value" style="color:{color}">{value:.1f}%</div>
      <div class="status-tag" style="background:{color}">{zone}</div>
    </div>'''

def render_sub(card_type: str, data: Dict) -> str:
    value = data.get("value", 0)
    status = data.get("status", data.get("regime", ""))
    color = get_color(status)
    
    labels = {"ahr999": ("🔥", "AHR999"), "mvrv": ("📈", "MVRV"), "bmri": ("⚠️", "BMRI"), "btcd": ("₿", "BTC.D")}
    icon, label = labels.get(card_type, ("📊", card_type.upper()))
    
    if card_type == "bmri":
        status = "低" if value < 30 else "高" if value > 70 else "中"
    elif card_type == "btcd":
        status = f"{value:.1f}%"
    
    return f'''
    <div class="sub-card">
      <div class="sub-header"><span class="icon">{icon}</span><span class="label">{label}</span></div>
      <div class="sub-value" style="color:{color}">{value:.2f}</div>
      <div class="sub-status" style="color:{color}">{status}</div>
    </div>'''

def render_poster(focus_type: str, focus_data: Dict, sub_types: List[str], indicators: Dict) -> str:
    today = datetime.now().strftime("%b %d, %Y")
    main_html = render_main(focus_type, focus_data)
    
    sub_html = ""
    for st in sub_types[:2]:
        if st in indicators:
            sub_html += render_sub(st, indicators[st])
    
    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>Crypto3D Daily</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Noto+Sans+SC:wght@400;500;600;700&display=swap');
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{
  font-family:'Inter','Noto Sans SC',sans-serif;
  background:#0a0a0b;
  color:#fafafa;
  width:1080px;
  height:1350px;
  overflow:hidden;
  display:flex;
  flex-direction:column;
}}
.header {{
  display:flex;
  justify-content:space-between;
  align-items:center;
  padding:40px 60px;
}}
.logo {{
  display:flex;
  align-items:center;
  gap:16px;
  font-size:28px;
  font-weight:700;
}}
.logo-icon {{
  width:44px;
  height:44px;
  background:linear-gradient(135deg,#3b82f6,#22c55e);
  border-radius:10px;
  display:flex;
  align-items:center;
  justify-content:center;
  font-size:22px;
}}
.date {{ color:#71717a; font-size:18px; }}
.content {{
  flex:1;
  padding:60px;
  display:flex;
  flex-direction:column;
  gap:40px;
}}
.main-card {{
  background:linear-gradient(145deg,#18181b,#0f0f11);
  border-radius:32px;
  padding:60px;
  border:1px solid rgba(255,255,255,0.05);
}}
.card-header {{
  display:flex;
  align-items:center;
  gap:16px;
  margin-bottom:30px;
}}
.card-header .icon {{ font-size:32px; }}
.card-header .title {{ font-size:20px; color:#71717a; font-weight:500; }}
.big-value {{
  font-size:96px;
  font-weight:700;
  letter-spacing:-4px;
  margin-bottom:20px;
}}
.status-tag {{
  display:inline-block;
  padding:10px 24px;
  border-radius:24px;
  font-size:18px;
  font-weight:600;
}}
.hint {{ font-size:16px; color:#71717a; margin-top:30px; }}
.sub-cards {{
  display:grid;
  grid-template-columns:1fr 1fr;
  gap:24px;
}}
.sub-card {{
  background:linear-gradient(145deg,#18181b,#0f0f11);
  border-radius:20px;
  padding:32px;
  border:1px solid rgba(255,255,255,0.05);
}}
.sub-header {{
  display:flex;
  align-items:center;
  gap:12px;
  margin-bottom:16px;
}}
.sub-header .icon {{ font-size:24px; }}
.sub-header .label {{ font-size:16px; color:#71717a; font-weight:500; }}
.sub-value {{ font-size:40px; font-weight:700; margin-bottom:8px; }}
.sub-status {{ font-size:14px; font-weight:500; }}
.footer {{
  padding:30px 60px;
  border-top:1px solid #27272a;
  display:flex;
  justify-content:space-between;
  align-items:center;
  font-size:16px;
  color:#71717a;
}}
.footer-link {{ color:#3b82f6; font-weight:600; font-size:18px; }}
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
  <span class="footer-link">crypto3d.pro</span>
</div>
</body>
</html>'''

async def generate_poster(headless: bool = True) -> Path:
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("[ERROR] 请安装 playwright")
        return None
    
    print("[1/4] 加载数据...")
    indicators = load_all_indicators()
    
    print("[2/4] 选择焦点...")
    focus_info = select_focus(indicators)
    print(f"  焦点: {focus_info['focus'].upper()}")
    
    print("[3/4] 渲染海报...")
    html = render_poster(
        focus_info["focus"],
        indicators.get(focus_info["focus"], {}),
        focus_info["subs"],
        indicators
    )
    
    today = datetime.now().strftime("%Y-%m-%d")
    html_path = OUTPUT_DIR / f"{today}.html"
    with open(html_path, 'w') as f:
        f.write(html)
    
    print("[4/4] 截图...")
    png_path = OUTPUT_DIR / f"{today}.png"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        page = await browser.new_page(viewport={"width": 1080, "height": 1350})
        await page.goto(f"file://{html_path}")
        await page.wait_for_timeout(500)
        await page.screenshot(path=str(png_path), type="png")
        await browser.close()
    
    print(f"[OK] 海报已生成: {png_path}")
    return png_path

if __name__ == "__main__":
    import sys
    headless = "--show" not in sys.argv
    asyncio.run(generate_poster(headless))
