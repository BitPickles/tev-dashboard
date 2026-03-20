#!/usr/bin/env python3
"""Crypto3D Daily Poster - v7 精修版"""
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
        with open(path) as f: return json.load(f)
    except: return None

def load_all():
    data = {}
    ahr = load_json(INDICATORS_DIR / "ahr999.json")
    if ahr:
        c, h = ahr["current"], ahr.get("history", [])
        data["ahr999"] = dict(value=c["value"], status=c["status"], price=c["price"],
            cost_200d=c["cost_200d"], prices=[x["close"] for x in h[-7:]])
    mvrv = load_json(INDICATORS_DIR / "mvrv.json")
    if mvrv:
        c, h = mvrv["current"], mvrv.get("history", [])
        data["mvrv"] = dict(value=c["value"], status=c["status"], week=[x["mvrv"] for x in h[-7:]])
    bmri = load_json(INDICATORS_DIR / "bmri.json")
    if bmri:
        c, h = bmri["1m"]["current"], bmri["1m"].get("history", [])
        data["bmri"] = dict(value=c["value"], regime=c["regime"], week=[x["bmri"] for x in h[-7:]])
    btcd = load_json(INDICATORS_DIR / "btc-dominance.json")
    if btcd:
        c, h = btcd["current"], btcd.get("history", [])
        data["btcd"] = dict(value=c["value"], zone=c["zone"], week=[x["value"] for x in h[-7:]])
    return data

def select_focus(data):
    a = data.get("ahr999",{}).get("value",1)
    m = data.get("mvrv",{}).get("value",1)
    b = data.get("bmri",{}).get("value",50)
    if a < 0.5: return "ahr999"
    if m > 3: return "mvrv"
    if b < 30 or b > 70: return "bmri"
    return ["ahr999","btcd","mvrv","bmri","ahr999","ahr999","ahr999"][datetime.now().weekday()]

def color_for(st):
    s = str(st).lower()
    if any(k in s for k in ["抄底","合理","neutral","balanced","low","fair"]): return "#34d399"
    if any(k in s for k in ["过热","high","extreme","danger"]): return "#fb7185"
    return "#60a5fa"

def mk_area(vals, color, w, h):
    if not vals or len(vals) < 2: return ""
    mn, mx = min(vals), max(vals)
    rng = mx - mn if mx != mn else 1
    pts = []
    for i, v in enumerate(vals):
        x = i * w / (len(vals) - 1)
        y = h - ((v - mn) / rng * h * 0.75) - h * 0.1
        pts.append((x, y))
    line = " ".join(f"{x:.0f},{y:.0f}" for x,y in pts)
    fill = line + f" {w},{h} 0,{h}"
    return (
        f'<svg viewBox="0 0 {w} {h}" preserveAspectRatio="none" '
        f'style="display:block;width:100%;height:100%">'
        f'<defs><linearGradient id="af" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0%" stop-color="{color}" stop-opacity="0.4"/>'
        f'<stop offset="100%" stop-color="{color}" stop-opacity="0"/>'
        f'</linearGradient></defs>'
        f'<polygon fill="url(#af)" points="{fill}"/>'
        f'<polyline fill="none" stroke="{color}" stroke-width="3" '
        f'stroke-linecap="round" stroke-linejoin="round" points="{line}"/>'
        f'</svg>'
    )

def mk_spark(vals, color, w, h):
    if not vals or len(vals) < 2: return ""
    mn, mx = min(vals), max(vals)
    rng = mx - mn if mx != mn else 1
    pts = []
    for i, v in enumerate(vals):
        x = i * w / (len(vals) - 1)
        y = h - ((v - mn) / rng * h * 0.7) - h * 0.15
        pts.append((x, y))
    line = " ".join(f"{x:.0f},{y:.0f}" for x,y in pts)
    lx, ly = pts[-1]
    return (
        f'<svg viewBox="0 0 {w} {h}" style="display:block;width:100%;height:100%">'
        f'<polyline fill="none" stroke="{color}" stroke-width="2.5" '
        f'stroke-linecap="round" stroke-linejoin="round" points="{line}"/>'
        f'<circle cx="{lx:.0f}" cy="{ly:.0f}" r="4" fill="{color}"/>'
        f'</svg>'
    )

def mk_gauge(val, lo, hi, zones):
    rng = hi - lo
    pct = max(2, min((val - lo) / rng * 100, 98))
    active_c = zones[0]["c"]
    for z in zones:
        if z["fr"] <= val <= z["to"]: active_c = z["c"]

    segs = ""
    for z in zones:
        x1 = (z["fr"] - lo) / rng * 100
        x2 = (z["to"] - lo) / rng * 100
        segs += f'<div style="position:absolute;left:{x1}%;width:{x2-x1}%;height:100%;background:{z["c"]};opacity:0.12;border-radius:6px"></div>'
    segs += f'<div style="position:absolute;left:0;width:{pct}%;height:100%;background:linear-gradient(90deg,{active_c}00,{active_c});opacity:0.4;border-radius:6px"></div>'
    segs += f'<div style="position:absolute;left:{pct}%;top:50%;transform:translate(-50%,-50%);width:18px;height:18px;border-radius:50%;background:{active_c};box-shadow:0 0 16px {active_c}80"></div>'
    segs += f'<div style="position:absolute;left:{pct}%;top:50%;transform:translate(-50%,-50%);width:8px;height:8px;border-radius:50%;background:#fff"></div>'

    labels = ""
    for z in zones:
        x = ((z["fr"]+z["to"])/2 - lo) / rng * 100
        labels += f'<span style="position:absolute;left:{x}%;transform:translateX(-50%);font-size:15px;color:#52525b;font-weight:500">{z["lb"]}</span>'

    return f'<div style="position:relative;height:12px;border-radius:6px;background:#1a1a1f">{segs}</div><div style="position:relative;height:24px;margin-top:6px">{labels}</div>'


def render(focus, data):
    now = datetime.now()
    date_str = now.strftime("%Y.%m.%d")
    wd = ["周一","周二","周三","周四","周五","周六","周日"][now.weekday()]

    ahr = data.get("ahr999", {})
    prices = ahr.get("prices", [])
    btc_price = ahr.get("price", 0)
    btc_area = mk_area(prices, "#f59e0b", 1000, 140)
    btc_chg = ""
    if len(prices) >= 2:
        ch = ((prices[-1] - prices[0]) / prices[0]) * 100
        cc = "#34d399" if ch > 0 else "#fb7185"
        btc_chg = f'<span class="chg" style="color:{cc}">{"+" if ch>0 else ""}{ch:.1f}%</span>'

    fd = data.get(focus, {})
    fval = fd.get("value", 0)
    fst = fd.get("status", fd.get("regime", ""))
    fc = color_for(fst)

    if focus == "ahr999":
        cost = ahr.get("cost_200d", 1)
        ratio = int(btc_price / cost * 100) if cost else 0
        g = mk_gauge(fval, 0, 1.5, [
            {"fr":0,"to":0.45,"c":"#34d399","lb":"抄底"},
            {"fr":0.45,"to":1.2,"c":"#fbbf24","lb":"定投"},
            {"fr":1.2,"to":1.5,"c":"#fb7185","lb":"观望"},
        ])
        card = f'''
<div class="card">
  <div class="c-row"><span class="c-lb">🔥 AHR999</span><span class="c-st" style="color:{fc}">{fst}</span></div>
  <div class="c-num" style="color:{fc}">{fval:.2f}</div>
  <div class="c-gauge">{g}</div>
  <div class="c-meta">
    <div><span class="c-ml">BTC</span><span class="c-mv">${btc_price:,}</span></div>
    <div><span class="c-ml">200日成本</span><span class="c-mv">${cost:,.0f}</span></div>
    <div><span class="c-ml">价格/成本</span><span class="c-mv" style="color:{fc}">{ratio}%</span></div>
  </div>
</div>'''
    elif focus == "mvrv":
        pnl = int((fval-1)*100)
        g = mk_gauge(fval, 0, 4, [
            {"fr":0,"to":1,"c":"#34d399","lb":"低估"},
            {"fr":1,"to":3,"c":"#fbbf24","lb":"合理"},
            {"fr":3,"to":4,"c":"#fb7185","lb":"过热"},
        ])
        card = f'''
<div class="card">
  <div class="c-row"><span class="c-lb">📈 MVRV</span><span class="c-st" style="color:{fc}">{fst}</span></div>
  <div class="c-num" style="color:{fc}">{fval:.2f}</div>
  <div class="c-gauge">{g}</div>
  <div class="c-meta">
    <div><span class="c-ml">持币盈利</span><span class="c-mv" style="color:{fc}">{pnl}%</span></div>
  </div>
</div>'''
    elif focus == "bmri":
        risk = "低风险" if fval<30 else "高风险" if fval>70 else "中性"
        g = mk_gauge(fval, 0, 100, [
            {"fr":0,"to":30,"c":"#34d399","lb":"低风险"},
            {"fr":30,"to":70,"c":"#fbbf24","lb":"中性"},
            {"fr":70,"to":100,"c":"#fb7185","lb":"高风险"},
        ])
        card = f'''
<div class="card">
  <div class="c-row"><span class="c-lb">⚠️ BMRI</span><span class="c-st" style="color:{fc}">{risk}</span></div>
  <div class="c-num" style="color:{fc}">{fval:.1f}</div>
  <div class="c-gauge">{g}</div>
</div>'''
    else:
        z = fd.get("zone","BALANCED")
        zt = "BTC主导" if z=="BTC_DOMINANT" else "山寨季" if z=="ALT_SEASON" else "平衡"
        g = mk_gauge(fval, 40, 70, [
            {"fr":40,"to":50,"c":"#34d399","lb":"山寨季"},
            {"fr":50,"to":60,"c":"#fbbf24","lb":"平衡"},
            {"fr":60,"to":70,"c":"#fb7185","lb":"BTC主导"},
        ])
        card = f'''
<div class="card">
  <div class="c-row"><span class="c-lb">₿ BTC.D</span><span class="c-st" style="color:{fc}">{zt}</span></div>
  <div class="c-num" style="color:{fc}">{fval:.1f}%</div>
  <div class="c-gauge">{g}</div>
</div>'''

    # 副指标
    sub_order = {"ahr999":["mvrv","bmri","btcd"],"mvrv":["ahr999","bmri","btcd"],
                 "bmri":["ahr999","mvrv","btcd"],"btcd":["ahr999","mvrv","bmri"]}
    rows = ""
    for nm in sub_order.get(focus, ["mvrv","bmri","btcd"]):
        d = data.get(nm, {})
        v = d.get("value", 0)
        st = d.get("status", d.get("regime", d.get("zone", "")))
        c = color_for(st)
        wk = d.get("week", [])
        sp = mk_spark(wk, c, 240, 48)
        if nm=="ahr999": lb,vs,sx = "AHR999",f"{v:.2f}",d.get("status","")
        elif nm=="mvrv": lb,vs,sx = "MVRV",f"{v:.2f}",d.get("status","")
        elif nm=="bmri":
            lb,vs = "BMRI",f"{v:.1f}"
            sx = "低风险" if v<30 else "高风险" if v>70 else "中性"
        else:
            lb,vs = "BTC.D",f"{v:.1f}%"
            zz = d.get("zone","BALANCED")
            sx = "BTC主导" if zz=="BTC_DOMINANT" else "山寨季" if zz=="ALT_SEASON" else "平衡"
        rows += f'''
    <div class="s-row">
      <div class="s-left"><span class="s-name">{lb}</span><span class="s-val" style="color:{c}">{vs}</span></div>
      <div class="s-mid">{sp}</div>
      <span class="s-tag" style="color:{c}">{sx}</span>
    </div>'''

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
*{{margin:0;padding:0;box-sizing:border-box}}
body{{
  font-family:'Inter',-apple-system,sans-serif;
  width:1080px;height:1350px;overflow:hidden;
  color:#e4e4e7;
  display:flex;flex-direction:column;
  background:#08080c;
  background-image:radial-gradient(ellipse 120% 50% at 50% 20%,#111118,#08080c);
}}

/* HEADER */
.hdr{{text-align:center;padding:40px 0 24px}}
.h-title{{font-size:36px;font-weight:800;letter-spacing:-0.5px;color:#fafafa}}
.h-date{{font-size:14px;font-weight:500;color:#3f3f46;letter-spacing:2px;margin-top:6px;text-transform:uppercase}}

/* BTC */
.btc{{padding:0 56px}}
.btc-row{{display:flex;align-items:baseline;gap:14px}}
.btc-lb{{font-size:14px;font-weight:600;color:#52525b;text-transform:uppercase;letter-spacing:2px}}
.btc-p{{font-size:52px;font-weight:800;color:#fafafa;letter-spacing:-2px}}
.chg{{font-size:20px;font-weight:700}}
.btc-chart{{height:130px;margin:0 -56px;overflow:hidden}}

/* CARD */
.card{{
  margin:20px 48px;
  padding:32px 36px 28px;
  background:linear-gradient(160deg,#111116,#0b0b10);
  border:1px solid #1a1a20;
  border-radius:20px;
}}
.c-row{{display:flex;justify-content:space-between;align-items:center;margin-bottom:4px}}
.c-lb{{font-size:18px;font-weight:600;color:#71717a}}
.c-st{{font-size:18px;font-weight:800}}
.c-num{{font-size:76px;font-weight:800;letter-spacing:-3px;margin:4px 0 16px;line-height:1}}
.c-gauge{{margin-bottom:20px}}
.c-meta{{
  display:flex;gap:28px;padding-top:16px;
  border-top:1px solid #1a1a20;
}}
.c-meta>div{{display:flex;flex-direction:column;gap:2px}}
.c-ml{{font-size:12px;font-weight:500;color:#52525b;text-transform:uppercase;letter-spacing:0.5px}}
.c-mv{{font-size:20px;font-weight:700;color:#d4d4d8}}

/* SUBS */
.subs{{
  margin:12px 48px 0;
  padding:28px 36px;
  background:linear-gradient(160deg,#111116,#0b0b10);
  border:1px solid #1a1a20;
  border-radius:20px;
  flex:1;
  display:flex;flex-direction:column;justify-content:space-evenly;
}}
.s-row{{
  display:flex;align-items:center;
  padding:20px 0;
  border-bottom:1px solid #15151a;
}}
.s-row:last-child{{border-bottom:none}}
.s-left{{width:160px;display:flex;flex-direction:column;gap:4px}}
.s-name{{font-size:15px;font-weight:600;color:#52525b;letter-spacing:0.5px}}
.s-val{{font-size:36px;font-weight:800;letter-spacing:-0.5px}}
.s-mid{{flex:1;height:48px;padding:0 24px}}
.s-tag{{width:90px;text-align:right;font-size:20px;font-weight:700}}

/* FOOTER */
.ftr{{
  padding:20px 56px;
  display:flex;justify-content:space-between;align-items:center;
  font-size:13px;color:#27272a;
}}
.ftr-l{{color:#3b82f6;font-weight:700;font-size:17px}}
</style>
</head>
<body>

<div class="hdr">
  <div class="h-title">Crypto3D 数据日报</div>
  <div class="h-date">{wd} · {date_str}</div>
</div>

<div class="btc">
  <div class="btc-row">
    <span class="btc-lb">Bitcoin</span>
    <span class="btc-p">${btc_price:,}</span>
    {btc_chg}
  </div>
  <div class="btc-chart">{btc_area}</div>
</div>

{card}

<div class="subs">
{rows}
</div>

<div class="ftr">
  <span>DAILY MARKET SNAPSHOT</span>
  <span class="ftr-l">crypto3d.pro</span>
</div>

</body>
</html>"""


async def generate():
    data = load_all()
    focus = select_focus(data)
    print(f"焦点: {focus.upper()}")
    html = render(focus, data)
    ts = datetime.now().strftime("%Y-%m-%d")
    hp = OUTPUT_DIR / f"{ts}.html"
    pp = OUTPUT_DIR / f"{ts}.png"
    with open(hp, "w") as f: f.write(html)
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        b = await p.chromium.launch(headless=True)
        pg = await b.new_page(viewport={"width":1080,"height":1350})
        await pg.goto(f"file://{hp}")
        await pg.wait_for_timeout(800)
        await pg.screenshot(path=str(pp), type="png")
        await b.close()
    print(f"OK → {pp}")

if __name__ == "__main__":
    asyncio.run(generate())
