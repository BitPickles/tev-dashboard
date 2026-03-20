#!/usr/bin/env python3
"""Crypto3D Daily Poster - v8 平衡版"""
import json
import asyncio
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
TEV_DIR = SCRIPT_DIR.parent
INDICATORS_DIR = TEV_DIR / "indicators" / "data"
OUTPUT_DIR = SCRIPT_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

def load_json(p):
    try: return json.load(open(p))
    except: return None

def load_all():
    D = {}
    a = load_json(INDICATORS_DIR / "ahr999.json")
    if a: D["ahr999"] = dict(v=a["current"]["value"], s=a["current"]["status"], p=a["current"]["price"], c=a["current"]["cost_200d"], px=[x["close"] for x in a.get("history",[])[-7:]])
    m = load_json(INDICATORS_DIR / "mvrv.json")
    if m: D["mvrv"] = dict(v=m["current"]["value"], s=m["current"]["status"], w=[x["mvrv"] for x in m.get("history",[])[-7:]])
    b = load_json(INDICATORS_DIR / "bmri.json")
    if b: D["bmri"] = dict(v=b["1m"]["current"]["value"], w=[x["bmri"] for x in b["1m"].get("history",[])[-7:]])
    d = load_json(INDICATORS_DIR / "btc-dominance.json")
    if d: D["btcd"] = dict(v=d["current"]["value"], z=d["current"]["zone"], w=[x["value"] for x in d.get("history",[])[-7:]])
    return D

def pick(D):
    a, m, b = D.get("ahr999",{}).get("v",1), D.get("mvrv",{}).get("v",1), D.get("bmri",{}).get("v",50)
    if a < 0.5: return "ahr999"
    if m > 3: return "mvrv"
    if b < 30 or b > 70: return "bmri"
    return ["ahr999","btcd","mvrv","bmri","ahr999","ahr999","ahr999"][datetime.now().weekday()]

def col(s):
    x = str(s).lower()
    if any(k in x for k in ["抄底","合理","neutral","balanced","low","fair"]): return "#34d399"
    if any(k in x for k in ["过热","high","extreme"]): return "#fb7185"
    return "#60a5fa"

def area(vals, c, w, h):
    if not vals or len(vals)<2: return ""
    mn, mx, r = min(vals), max(vals), max(vals)-min(vals) or 1
    P = [(i*w/(len(vals)-1), h-((v-mn)/r*h*0.7)-h*0.1) for i,v in enumerate(vals)]
    L = " ".join(f"{x:.0f},{y:.0f}" for x,y in P)
    F = L + f" {w},{h} 0,{h}"
    return f'<svg viewBox="0 0 {w} {h}" style="display:block;width:100%;height:100%"><defs><linearGradient id="ag" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="{c}" stop-opacity="0.35"/><stop offset="100%" stop-color="{c}" stop-opacity="0"/></linearGradient></defs><polygon fill="url(#ag)" points="{F}"/><polyline fill="none" stroke="{c}" stroke-width="2.5" stroke-linecap="round" points="{L}"/></svg>'

def spark(vals, c, w, h):
    if not vals or len(vals)<2: return ""
    mn, mx, r = min(vals), max(vals), max(vals)-min(vals) or 1
    P = [(i*w/(len(vals)-1), h-((v-mn)/r*h*0.65)-h*0.15) for i,v in enumerate(vals)]
    L = " ".join(f"{x:.0f},{y:.0f}" for x,y in P)
    lx, ly = P[-1]
    return f'<svg viewBox="0 0 {w} {h}" style="display:block;width:100%;height:100%"><polyline fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" points="{L}"/><circle cx="{lx:.0f}" cy="{ly:.0f}" r="3" fill="{c}"/></svg>'

def gauge(v, lo, hi, Z):
    R = hi - lo
    P = max(3, min((v-lo)/R*100, 97))
    ac = Z[0]["c"]
    for z in Z:
        if z["fr"] <= v <= z["to"]: ac = z["c"]
    S = ""
    for z in Z:
        x1, x2 = (z["fr"]-lo)/R*100, (z["to"]-lo)/R*100
        S += f'<div style="position:absolute;left:{x1}%;width:{x2-x1}%;height:100%;background:{z["c"]};opacity:0.1;border-radius:5px"></div>'
    S += f'<div style="position:absolute;left:0;width:{P}%;height:100%;background:linear-gradient(90deg,{ac}00,{ac});opacity:0.35;border-radius:5px"></div>'
    S += f'<div style="position:absolute;left:{P}%;top:50%;transform:translate(-50%,-50%);width:16px;height:16px;border-radius:50%;background:{ac};box-shadow:0 0 12px {ac}88"></div>'
    S += f'<div style="position:absolute;left:{P}%;top:50%;transform:translate(-50%,-50%);width:7px;height:7px;border-radius:50%;background:#fff"></div>'
    L = ""
    for z in Z:
        x = ((z["fr"]+z["to"])/2 - lo)/R*100
        L += f'<span style="position:absolute;left:{x}%;transform:translateX(-50%);font-size:18px;font-weight:600;color:#71717a">{z["lb"]}</span>'
    return f'<div style="position:relative;height:12px;border-radius:6px;background:#1a1a1f">{S}</div><div style="position:relative;height:28px;margin-top:6px">{L}</div>'

def render(F, D):
    now = datetime.now()
    ds = now.strftime("%Y.%m.%d")
    wd = ["周一","周二","周三","周四","周五","周六","周日"][now.weekday()]
    
    a = D.get("ahr999", {})
    px = a.get("px", [])
    bp = a.get("p", 0)
    bc = a.get("c", 1)
    chg = ""
    if len(px) >= 2:
        ch = ((px[-1]-px[0])/px[0])*100
        cc = "#34d399" if ch>0 else "#fb7185"
        chg = f'<span class="chg" style="color:{cc}">{"+"if ch>0 else""}{ch:.1f}%</span>'
    
    ar = area(px, "#f59e0b", 1000, 130)
    
    fd = D.get(F, {})
    fv = fd.get("v", 0)
    fs = fd.get("s", fd.get("z", ""))
    fc = col(fs)
    
    if F == "ahr999":
        rt = int(bp/bc*100) if bc else 0
        g = gauge(fv, 0, 1.5, [{"fr":0,"to":0.45,"c":"#34d399","lb":"抄底"},{"fr":0.45,"to":1.2,"c":"#fbbf24","lb":"定投"},{"fr":1.2,"to":1.5,"c":"#fb7185","lb":"观望"}])
        card = f'''
<div class="card">
  <div class="c-hd"><span class="c-ic">🔥</span><span class="c-nm">AHR999</span><span class="c-st" style="color:{fc}">{fs}</span></div>
  <div class="c-num" style="color:{fc}">{fv:.2f}</div>
  <div class="c-g">{g}</div>
  <div class="c-m">
    <span><b>BTC</b> ${bp:,}</span>
    <span><b>200日成本</b> ${bc:,.0f}</span>
    <span style="color:{fc}"><b>价格/成本</b> {rt}%</span>
  </div>
</div>'''
    elif F == "mvrv":
        pn = int((fv-1)*100)
        g = gauge(fv, 0, 4, [{"fr":0,"to":1,"c":"#34d399","lb":"低估"},{"fr":1,"to":3,"c":"#fbbf24","lb":"合理"},{"fr":3,"to":4,"c":"#fb7185","lb":"过热"}])
        card = f'''
<div class="card">
  <div class="c-hd"><span class="c-ic">📈</span><span class="c-nm">MVRV</span><span class="c-st" style="color:{fc}">{fs}</span></div>
  <div class="c-num" style="color:{fc}">{fv:.2f}</div>
  <div class="c-g">{g}</div>
  <div class="c-m"><span style="color:{fc}"><b>持币盈利</b> {pn}%</span></div>
</div>'''
    elif F == "bmri":
        rx = "低风险" if fv<30 else "高风险" if fv>70 else "中性"
        g = gauge(fv, 0, 100, [{"fr":0,"to":30,"c":"#34d399","lb":"低风险"},{"fr":30,"to":70,"c":"#fbbf24","lb":"中性"},{"fr":70,"to":100,"c":"#fb7185","lb":"高风险"}])
        card = f'''
<div class="card">
  <div class="c-hd"><span class="c-ic">⚠️</span><span class="c-nm">BMRI</span><span class="c-st" style="color:{fc}">{rx}</span></div>
  <div class="c-num" style="color:{fc}">{fv:.1f}</div>
  <div class="c-g">{g}</div>
</div>'''
    else:
        zt = "BTC主导" if fd.get("z")=="BTC_DOMINANT" else "山寨季" if fd.get("z")=="ALT_SEASON" else "平衡"
        g = gauge(fv, 40, 70, [{"fr":40,"to":50,"c":"#34d399","lb":"山寨季"},{"fr":50,"to":60,"c":"#fbbf24","lb":"平衡"},{"fr":60,"to":70,"c":"#fb7185","lb":"BTC主导"}])
        card = f'''
<div class="card">
  <div class="c-hd"><span class="c-ic">₿</span><span class="c-nm">BTC.D</span><span class="c-st" style="color:{fc}">{zt}</span></div>
  <div class="c-num" style="color:{fc}">{fv:.1f}%</div>
  <div class="c-g">{g}</div>
</div>'''
    
    SM = {"ahr999":["mvrv","bmri","btcd"],"mvrv":["ahr999","bmri","btcd"],"bmri":["ahr999","mvrv","btcd"],"btcd":["ahr999","mvrv","bmri"]}
    rows = ""
    for nm in SM.get(F, ["mvrv","bmri","btcd"]):
        d = D.get(nm, {})
        v = d.get("v", 0)
        s = d.get("s", d.get("z", ""))
        c = col(s)
        w = d.get("w", [])
        sp = spark(w, c, 180, 40)
        if nm=="ahr999": lb, vs, sx = "AHR999", f"{v:.2f}", d.get("s","")
        elif nm=="mvrv": lb, vs, sx = "MVRV", f"{v:.2f}", d.get("s","")
        elif nm=="bmri": lb, vs, sx = "BMRI", f"{v:.1f}", ("低风险" if v<30 else "高风险" if v>70 else "中性")
        else: lb, vs, sx = "BTC.D", f"{v:.1f}%", ("BTC主导" if d.get("z")=="BTC_DOMINANT" else "山寨季" if d.get("z")=="ALT_SEASON" else "平衡")
        rows += f'''
  <div class="s-r">
    <div class="s-l"><span class="s-n">{lb}</span><span class="s-v" style="color:{c}">{vs}</span></div>
    <div class="s-c">{sp}</div>
    <span class="s-t" style="color:{c}">{sx}</span>
  </div>'''
    
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@500;600;700;800&display=swap');
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Inter',sans-serif;width:1080px;height:1350px;overflow:hidden;color:#e4e4e7;display:flex;flex-direction:column;background:#08080c;background-image:radial-gradient(ellipse 120% 50% at 50% 20%,#101018,#08080c)}}

/* HEADER - 居中紧凑 */
.hdr{{text-align:center;padding:36px 0 20px}}
.h-t{{font-size:38px;font-weight:800;letter-spacing:-0.5px;color:#fafafa}}
.h-d{{font-size:15px;font-weight:600;color:#52525b;margin-top:4px}}

/* BTC - 紧凑 */
.btc{{padding:0 56px}}
.btc-r{{display:flex;align-items:baseline;gap:12px}}
.btc-l{{font-size:14px;font-weight:700;color:#52525b;text-transform:uppercase;letter-spacing:2px}}
.btc-p{{font-size:48px;font-weight:800;color:#fafafa;letter-spacing:-1px}}
.chg{{font-size:18px;font-weight:700}}
.btc-c{{height:120px;margin:0 -56px;overflow:hidden}}

/* CARD */
.card{{margin:16px 48px;padding:28px 32px 24px;background:linear-gradient(160deg,#111116,#0b0b10);border:1px solid #1a1a20;border-radius:18px}}
.c-hd{{display:flex;align-items:center;gap:10px;margin-bottom:4px}}
.c-ic{{font-size:22px}}
.c-nm{{font-size:17px;font-weight:600;color:#71717a;flex:1}}
.c-st{{font-size:17px;font-weight:800}}
.c-num{{font-size:64px;font-weight:800;letter-spacing:-2px;margin:2px 0 14px;line-height:1}}
.c-g{{margin-bottom:18px}}
.c-m{{display:flex;gap:24px;padding-top:14px;border-top:1px solid #1a1a20;font-size:15px;color:#a1a1aa}}
.c-m b{{color:#71717a;font-weight:600}}

/* SUBS */
.subs{{margin:8px 48px;padding:24px 32px;background:linear-gradient(160deg,#111116,#0b0b10);border:1px solid #1a1a20;border-radius:18px;flex:1;display:flex;flex-direction:column;justify-content:space-evenly}}
.s-r{{display:flex;align-items:center;padding:18px 0;border-bottom:1px solid #15151a}}
.s-r:last-child{{border-bottom:none}}
.s-l{{width:150px;display:flex;flex-direction:column;gap:3px}}
.s-n{{font-size:15px;font-weight:600;color:#52525b}}
.s-v{{font-size:32px;font-weight:800;letter-spacing:-0.5px}}
.s-c{{flex:1;height:40px;padding:0 16px}}
.s-t{{width:85px;text-align:right;font-size:18px;font-weight:700}}

/* FOOTER */
.ftr{{padding:18px 56px;display:flex;justify-content:space-between;align-items:center;font-size:13px;color:#27272a}}
.ftr-l{{color:#3b82f6;font-weight:700;font-size:16px}}
</style>
</head>
<body>

<div class="hdr">
  <div class="h-t">Crypto3D 数据日报</div>
  <div class="h-d">{wd} · {ds}</div>
</div>

<div class="btc">
  <div class="btc-r">
    <span class="btc-l">Bitcoin</span>
    <span class="btc-p">${bp:,}</span>
    {chg}
  </div>
  <div class="btc-c">{ar}</div>
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


async def gen():
    D = load_all()
    F = pick(D)
    print(f"焦点: {F.upper()}")
    html = render(F, D)
    ts = datetime.now().strftime("%Y-%m-%d")
    hp, pp = OUTPUT_DIR/f"{ts}.html", OUTPUT_DIR/f"{ts}.png"
    open(hp,"w").write(html)
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
    asyncio.run(gen())
