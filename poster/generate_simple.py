#!/usr/bin/env python3
"""
Crypto3D 推特日报生成器 - 简洁版
"""
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
    ahr999 = load_json(INDICATORS_DIR / "ahr999.json")
    if ahr999:
        c = ahr999.get("current", {})
        h = ahr999.get("history", [])
        data["ahr999"] = {
            "value": c.get("value", 0),
            "status": c.get("status", ""),
            "price": c.get("price", 0),
            "cost_200d": c.get("cost_200d", 0),
            "week": [x.get("ahr999", 0) for x in h[-7:]] if h else []
        }
    mvrv = load_json(INDICATORS_DIR / "mvrv.json")
    if mvrv:
        c = mvrv.get("current", {})
        h = mvrv.get("history", [])
        data["mvrv"] = {
            "value": c.get("value", 0),
            "status": c.get("status", ""),
            "week": [x.get("mvrv", 0) for x in h[-7:]] if h else []
        }
    bmri = load_json(INDICATORS_DIR / "bmri.json")
    if bmri and "1m" in bmri:
        c = bmri["1m"].get("current", {})
        h = bmri["1m"].get("history", [])
        data["bmri"] = {
            "value": c.get("value", 0),
            "regime": c.get("regime", "NEUTRAL"),
            "week": [x.get("bmri", 0) for x in h[-7:]] if h else []
        }
    btcd = load_json(INDICATORS_DIR / "btc-dominance.json")
    if btcd:
        c = btcd.get("current", {})
        h = btcd.get("history", [])
        data["btcd"] = {
            "value": c.get("value", 0),
            "zone": c.get("zone", "BALANCED"),
            "week": [x.get("value", 0) for x in h[-7:]] if h else []
        }
    return data

def get_color(status):
    s = str(status).lower()
    if any(k in s for k in ["抄底", "合理", "neutral", "balanced", "low", "fair"]):
        return "#22c55e"
    if any(k in s for k in ["过热", "high", "extreme", "danger"]):
        return "#ef4444"
    return "#3b82f6"

def make_chart(week_data, color):
    if not week_data or len(week_data) < 2:
        return ""
    w, h = 300, 50
    mn, mx = min(week_data), max(week_data)
    r = mx - mn if mx > mn else 1
    pts = []
    for i, range(len(week_data)):
        x = i * w / (len(week_data) - 1)
        y = h - ((week_data[i] - mn) / r * (h - 10)) - 5
        pts.append(f"{x:.0f},{y:.0f}")
    return f'<svg viewBox="0 0 {w} {h}"><polyline fill="none" stroke="{color}" stroke-width="2" points="{" ".join(pts)}"/><circle cx="{w}" cy="{h - ((week_data[-1] - mn) / r * (h - 10) - 5:.0f}" r="3" fill="{color}"/></svg>'

def main_ahr999(d):
    v = d.get("value", 0)
    st = d.get("status", "")
    c = get_color(st)
    p = d.get("price", 0)
    c2 = d.get("cost_200d", 0)
    ch = make_chart(d.get("week", []), c)
    return f'''
<div class="main">
  <div class="card-head"><span class="ic">🔥</span><span class="nm">AHR999</span></div>
  <div class="big" style="color:{c}">{v:.2f}</div>
  <div class="tag" style="background:{c}">{st}</div>
  <div class="hint">BTC ${p:,} | 200日成本 {c2:,.0f}</div>
  {ch}
</div>'''

def main_mvrv(d):
    v = d.get("value", 0)
    st = d.get("status", "")
    c = get_color(st)
    ch = make_chart(d.get("week", []), c)
    return f'''
<div class="main">
  <div class="card-head"><span class="ic">📈</span><span class="nm">MVRV</span></div>
  <div class="big" style="color:{c}">{v:.2f}</div>
  <div class="tag" style="background:{c}">{st}</div>
  {ch}
</div>'''

def main_bmri(d):
    v = d.get("value", 0)
    c = "#22c55e" if v < 30 else "#ef4444" if v > 70 else "#3b82f6"
    ch = make_chart(d.get("week", []), c)
    return f'''
<div class="main">
  <div class="card-head"><span class="ic">⚠️</span><span class="nm">BMRI</span></div>
  <div class="big" style="color:{c}">{v:.1f}</div>
  <div class="tag" style="background:{c}">{"低风险" if v < 30 else "高风险" if v > 70 else "中性"}</div>
  {ch}
</div>'''

def main_btcd(d):
    v = d.get("value", 0)
    z = d.get("zone", "BALANCED")
    c = "#3b82f6"
    ch = make_chart(d.get("week", []), c)
    zt = "BTC主导" if z == "BTC_DOMINANT" else "山寨季" if z == "ALT_SEASON" else "平衡"
    return f'''
<div class="main">
  <div class="card-head"><span class="ic">₿</span><span class="nm">BTC.D</span></div>
  <div class="big" style="color:{c}">{v:.1f}%</div>
  <div class="tag" style="background:{c}">{zt}</div>
  {ch}
</div>'''

def sub_card(name, d):
    v = d.get("value", 0)
    st = d.get("status", d.get("regime", ""))
    c = get_color(st)
    ch = make_chart(d.get("week", []), c)
    icons = {"ahr999": "🔥", "mvrv": "📈", "bmri": "⚠️", "btcd": "₿"}
    ic = icons.get(name, "📊")
    return f'''
<div class="sub">
  <div class="sub-head"><span>{ic}</span><span>{name.upper()}</span></div>
  <div class="med" style="color:{c}">{v:.2f}</div>
  <div class="sub-tag" style="color:{c}">{st}</div>
  {ch}
</div>'''

def render(focus, data):
    today = datetime.now().strftime("%b %d, %Y")
    main_f = {"ahr999": main_ahr999, "mvrv": main_mvrv, "bmri": main_bmri, "btcd": main_btcd}
    main_html = main_f.get(focus, main_ahr999)(data.get(focus, {}))
    
    subs = {"ahr999": ["mvrv", "bmri"], "mvrv": ["ahr999", "btcd"], "bmri": ["ahr999", "mvrv"], "btcd": ["ahr999", "mvrv"]}
    sub_types = subs.get(focus, ["mvrv", "bmri"])
    sub_html = ""
    for t in sub_types[:2]:
        if t in data:
            sub_html += sub_card(t, data[t])
    
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=Noto+Sans+SC:wght@400;600;700&display=swap');
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Inter','Noto Sans SC',sans-serif;background:#0a0a0b;color:#fafafa;width:1080px;height:1350px;overflow:hidden;display:flex;flex-direction:column}}
.hdr{{display:flex;justify-content:space-between;align-items:center;padding:40px 60px;border-bottom:1px solid #27272a}}
.logo{{display:flex;align-items:center;gap:16px;font-size:26px;font-weight:700}}
.logo-ic{{width:44px;height:44px;background:linear-gradient(135deg,#3b82f6,#22c55e);border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:22px}}
.date{{color:#71717a;font-size:18px}}
.cnt{{flex:1;padding:60px;display:flex;flex-direction:column;gap:40px}}
.main{{background:linear-gradient(145deg,#18181b,#0f0f11);border-radius:32px;padding:50px;border:1px solid rgba(255,255, 255, 0.05)}flex:1}}
.card-head{{display:flex;align-items:center;gap:16px;margin-bottom:20px}}
.ic{{font-size:32px}}
.nm{{font-size:18px;color:#71717a;font-weight:500}}
.big{{font-size:72px;font-weight:700;letter-spacing:-2px;margin-bottom:16px}}
.tag{{display:inline-block;padding:10px 24px;border-radius:24px;font-size:16px;font-weight:600;color:#fafafa}
.hint{{font-size:14px;color:#71717a;margin-top:20px}}
.subs{{display:grid;grid-template-columns:1fr 1fr;gap:24px}}
.sub{{background:linear-gradient(145deg,#18181b,#0f0f11);border-radius:20px;padding:28px;border:1px solid rgba(255,255,255, 0.05)}
flex:1}
.sub-head{{display:flex;align-items:center;gap:12px;margin-bottom:12px;font-size:16px;color:#71717a;font-weight:500}}
.med{{font-size:32px;font-weight:700;margin-bottom:8px}
.sub-tag{{font-size:13px;font-weight:500}}
.ftr{{padding:30px 60px;border-top:1px solid #27272a;display:flex;justify-content:space-between;align-items:center;font-size:16px;color:#71717a}
.link{{color:#3b82f6;font-weight:600;font-size:18px}}
</style>
</head>
<body>
<div class="hdr">
  <div class="logo"><div class="logo-ic">📊</div>Crypto3D Daily</div>
  <div class="date">{today}</div>
</div>
<div class="cnt">
{main_html}
<div class="subs">{sub_html}</div>
</div>
<div class="ftr">
  <span>每日加密市场晴雨表</span>
  <span class="link">crypto3d.pro</span>
</div>
</body>
</html>"""

async def gen():
    try:
        from playwright.async_api import async_playwright
    except:
        print("[ERROR] 安装 playwright")
        return
    
    print("[1/4] 加载数据...")
    data = load_all()
    
    print("[2/4] 选择焦点...")
    focus = "ahr999"
    a = data.get("ahr999", {}).get("value", 0)
    if a < 0.5:
        focus = "ahr999"
    elif data.get("mvrv", {}).get("value", 0) > 3:
        focus = "mvrv"
    elif data.get("bmri", {}).get("value", 50) < 30 or data.get("bmri", {}).get("value", 50) > 70:
        focus = "bmri"
    print(f"  焦点: {focus.upper()}")
    
    print("[3/4] 渲染...")
    html = render(focus, data)
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    html_path = OUTPUT_DIR / f"{today_str}.html"
    with open(html_path, "w") as f:
        f.write(html)
    
    print("[4/4] 截图...")
    png_path = OUTPUT_DIR / f"{today_str}.png"
    
    async with async_playwright() as p:
        b = await p.chromium.launch(headless=True)
        pg = await b.new_page(viewport={"width": 1080, "height": 1350})
        await pg.goto(f"file://{html_path}")
        await pg.wait_for_timeout(500)
        await pg.screenshot(path=str(png_path), type="png")
        await b.close()
    
    print(f"[OK] {png_path}")
    return png_path

if __name__ == "__main__":
    asyncio.run(gen())
