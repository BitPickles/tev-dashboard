#!/usr/bin/env python3
"""
Crypto3D 推特日报系统 - 每日海报生成与发推

功能：
1. 读取指标数据 + 治理动态
2. AI 选题（选最有话题性的焦点）
3. 生成海报 HTML → 截图 PNG
4. 生成推文文案
5. Playwright 浏览器发推（可选）

使用：
  python3 poster-daily.py              # 生成海报 + 文案
  python3 poster-daily.py --tweet      # 生成并发布
  python3 poster-daily.py --headless   # 无头模式
"""

import json
import os
import sys
import asyncio
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, List, Any

# 路径配置
SCRIPT_DIR = Path(__file__).parent
TEV_DIR = SCRIPT_DIR.parent
INDICATORS_DIR = TEV_DIR / "indicators" / "data"
DATA_DIR = TEV_DIR / "data"
OUTPUT_DIR = SCRIPT_DIR / "output"

# 确保输出目录存在
OUTPUT_DIR.mkdir(exist_ok=True)


def load_json(path: Path) -> Optional[Dict]:
    """加载 JSON 文件"""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"[ERROR] 加载 {path} 失败: {e}")
        return None


def load_indicators() -> Dict[str, Any]:
    """加载所有指标数据"""
    indicators = {}
    
    # AHR999
    ahr999 = load_json(INDICATORS_DIR / "ahr999.json")
    if ahr999 and "current" in ahr999:
        indicators["ahr999"] = {
            "value": ahr999["current"].get("value", 0),
            "status": ahr999["current"].get("status", ""),
            "price": ahr999["current"].get("price", 0),
            "cost_200d": ahr999["current"].get("cost_200d", 0),
            "date": ahr999["current"].get("date", "")
        }
    
    # MVRV
    mvrv = load_json(INDICATORS_DIR / "mvrv.json")
    if mvrv and "current" in mvrv:
        indicators["mvrv"] = {
            "value": mvrv["current"].get("value", 0),
            "status": mvrv["current"].get("status", ""),
            "date": mvrv["current"].get("date", "")
        }
    
    # BMRI
    bmri = load_json(INDICATORS_DIR / "bmri.json")
    if bmri and "1m" in bmri and "current" in bmri["1m"]:
        indicators["bmri"] = {
            "value": bmri["1m"]["current"].get("value", 0),
            "regime": bmri["1m"]["current"].get("regime", "NEUTRAL"),
            "date": bmri["1m"]["current"].get("date", "")
        }
    
    # BTC.D
    btcd = load_json(INDICATORS_DIR / "btc-dominance.json")
    if btcd and "current" in btcd:
        indicators["btcd"] = {
            "value": btcd["current"].get("value", 0),
            "zone": btcd["current"].get("zone", "BALANCED"),
            "date": btcd["current"].get("date", "")
        }
    
    return indicators


def load_governance() -> List[Dict]:
    """加载治理动态，筛选 TEV 相关"""
    gov = load_json(DATA_DIR / "governance.json")
    if not gov or "proposals" not in gov:
        return []
    
    tev_related = []
    for p in gov["proposals"]:
        if p.get("is_tev_related") or p.get("isTEV"):
            tev_related.append({
                "protocol": p.get("protocol", ""),
                "title": p.get("title", ""),
                "status": p.get("status", ""),
                "isTEV": True
            })
    
    return tev_related


def select_focus(indicators: Dict, governance: List[Dict]) -> str:
    """
    AI 选题逻辑 - 选择最有话题性的焦点
    
    优先级：
    1. 指标进入关键区间（AHR999 < 0.5 抄底、MVRV > 3 过热、BMRI < 30 低风险）
    2. 治理动态（TEV 相关提案）
    3. 按周几轮换（周一 AHR999、周二 BTC.D、周三 MVRV、周四 BMRI、周五治理、周末回顾）
    """
    
    # 检查关键区间
    ahr999 = indicators.get("ahr999", {})
    if ahr999.get("value", 1) < 0.5:
        return "ahr999"
    
    mvrv = indicators.get("mvrv", {})
    if mvrv.get("value", 1) > 3:
        return "mvrv"
    
    bmri = indicators.get("bmri", {})
    if bmri.get("value", 50) < 30:
        return "bmri"
    
    # 检查治理动态
    if governance:
        return "governance"
    
    # 按周几轮换
    weekday = datetime.now().weekday()  # 0=周一
    rotation = ["ahr999", "btcd", "mvrv", "bmri", "governance", "ahr999", "ahr999"]
    return rotation[weekday]


def generate_tweet_text(focus: str, indicators: Dict, governance: List[Dict]) -> str:
    """生成推文文案"""
    today = datetime.now().strftime("%Y-%m-%d")
    
    if focus == "ahr999":
        ind = indicators.get("ahr999", {})
        value = ind.get("value", 0)
        status = ind.get("status", "")
        price = ind.get("price", 0)
        cost = ind.get("cost_200d", 0)
        
        emoji = "🔥" if value < 0.5 else "📊"
        text = f"""{emoji} AHR999 跌至 {value:.2f}，{status}。

当前 BTC ${price:,}，200日成本线 ${cost:,.0f}。

MVRV {indicators['mvrv']['value']:.2f} 处于合理区，市场没有过热迹象。

历史不会简单重复，但定投窗口值得关注 🎯

完整数据 → crypto3d.pro

#Crypto3D #BTC #AHR999"""
    
    elif focus == "mvrv":
        ind = indicators.get("mvrv", {})
        value = ind.get("value", 0)
        status = ind.get("status", "")
        
        text = f"""📊 MVRV 当前 {value:.2f}，{status}。

MVRV < 1 意味着持币者整体亏损，通常是底部信号。
MVRV > 3 则意味着市场过热，需警惕回调。

当前 AHR999 {indicators['ahr999']['value']:.2f}，BTC.D {indicators['btcd']['value']:.1f}%

数据驱动决策 → crypto3d.pro

#Crypto3D #BTC #MVRV"""
    
    elif focus == "bmri":
        ind = indicators.get("bmri", {})
        value = ind.get("value", 0)
        regime = ind.get("regime", "NEUTRAL")
        
        risk_level = "低风险 🟢" if value < 30 else "高风险 🔴" if value > 70 else "中性 🟡"
        
        text = f"""⚠️ BMRI 风险指数 {value:.1f}，市场体制 {regime}。

{risk_level}环境。

BMRI 综合评估流动性、利率、市场风险等多个维度。
< 30 为低风险，> 70 为高风险。

当前 BTC ${indicators['ahr999']['price']:,}

更多指标 → crypto3d.pro

#Crypto3D #BTC #BMRI"""
    
    elif focus == "btcd":
        ind = indicators.get("btcd", {})
        value = ind.get("value", 0)
        zone = ind.get("zone", "BALANCED")
        
        zone_text = "BTC 主导 🟠" if zone == "BTC_DOMINANT" else "山寨季 🟢" if zone == "ALT_SEASON" else "平衡 ⚪"
        
        text = f"""₿ BTC 市值占比 {value:.1f}%，{zone_text}。

BTC.D > 60% 说明资金集中在 BTC，山寨币表现疲软。
BTC.D < 50% 则可能是山寨季的信号。

当前 AHR999 {indicators['ahr999']['value']:.2f}，MVRV {indicators['mvrv']['value']:.2f}

市场全景 → crypto3d.pro

#Crypto3D #BTC #BTCD"""
    
    elif focus == "governance" and governance:
        gov = governance[0]
        protocol = gov.get("protocol", "")
        title = gov.get("title", "")[:50]
        
        text = f"""🏛️ {protocol} 治理动态

{title}...

TEV 相关提案可能影响代币经济和回购分红。

追踪治理 → crypto3d.pro

#Crypto3D #DeFi #{protocol}"""
    
    else:
        # 兜底
        text = f"""📊 Crypto3D 每日数据更新

AHR999: {indicators['ahr999']['value']:.2f} ({indicators['ahr999']['status']})
MVRV: {indicators['mvrv']['value']:.2f} ({indicators['mvrv']['status']})
BMRI: {indicators['bmri']['value']:.1f} ({indicators['bmri']['regime']})
BTC.D: {indicators['btcd']['value']:.1f}%

完整分析 → crypto3d.pro

#Crypto3D #BTC #DeFi"""
    
    return text


def generate_html_data(focus: str, indicators: Dict, governance: List[Dict]) -> Dict:
    """生成 HTML 模板所需的数据结构"""
    today = datetime.now().strftime("%Y-%m-%d")
    
    data = {
        "date": today,
        "focus": focus,
        "indicators": {
            "ahr999": {
                "value": indicators.get("ahr999", {}).get("value", 0),
                "status": indicators.get("ahr999", {}).get("status", ""),
                "price": indicators.get("ahr999", {}).get("price", 0),
                "cost_200d": indicators.get("ahr999", {}).get("cost_200d", 0)
            },
            "mvrv": {
                "value": indicators.get("mvrv", {}).get("value", 0),
                "status": indicators.get("mvrv", {}).get("status", "")
            },
            "bmri": {
                "value": indicators.get("bmri", {}).get("value", 0),
                "regime": indicators.get("bmri", {}).get("regime", "NEUTRAL")
            },
            "btcd": {
                "value": indicators.get("btcd", {}).get("value", 0),
                "zone": indicators.get("btcd", {}).get("zone", "BALANCED")
            }
        },
        "governance": None
    }
    
    if focus == "governance" and governance:
        gov = governance[0]
        data["governance"] = {
            "protocol": gov.get("protocol", ""),
            "title": gov.get("title", ""),
            "isTEV": gov.get("isTEV", False)
        }
    
    return data


async def capture_poster(headless: bool = True) -> Optional[Path]:
    """使用 Playwright 截图生成海报"""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("[ERROR] 请安装 playwright: pip install playwright && playwright install chromium")
        return None
    
    today = datetime.now().strftime("%Y-%m-%d")
    output_path = OUTPUT_DIR / f"{today}.png"
    
    # 加载数据
    indicators = load_indicators()
    governance = load_governance()
    focus = select_focus(indicators, governance)
    
    # 生成 HTML 数据
    html_data = generate_html_data(focus, indicators, governance)
    
    # 读取模板
    template_path = SCRIPT_DIR / "template.html"
    with open(template_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # 注入数据到 HTML
    data_script = f"<script>window.posterData = {json.dumps(html_data)};</script>"
    html_content = html_content.replace(
        '<script>',
        data_script + '\n<script>\n// 覆盖默认数据\nif (window.posterData) { data = window.posterData; }'
    )
    
    # 写入临时文件
    temp_html = OUTPUT_DIR / f"{today}.html"
    with open(temp_html, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        page = await browser.new_page(viewport={"width": 1200, "height": 675})
        
        await page.goto(f"file://{temp_html}")
        await page.wait_for_timeout(500)  # 等待渲染
        
        await page.screenshot(path=str(output_path), type="png")
        await browser.close()
    
    print(f"[OK] 海报已生成: {output_path}")
    return output_path


def save_daily_record(tweet_text: str, focus: str, indicators: Dict, poster_path: Path):
    """保存每日记录"""
    today = datetime.now().strftime("%Y-%m-%d")
    record = {
        "date": today,
        "focus": focus,
        "tweet": tweet_text,
        "indicators": indicators,
        "poster": str(poster_path),
        "created_at": datetime.now().isoformat()
    }
    
    record_path = OUTPUT_DIR / f"{today}.json"
    with open(record_path, 'w', encoding='utf-8') as f:
        json.dump(record, f, ensure_ascii=False, indent=2)
    
    print(f"[OK] 记录已保存: {record_path}")


async def send_tweet(tweet_text: str, image_path: Path, headless: bool = True) -> bool:
    """使用 Playwright 浏览器发推"""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("[ERROR] 请安装 playwright")
        return False
    
    # 检查 Twitter session 文件
    session_file = SCRIPT_DIR / "twitter-session.json"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context()
        
        # 尝试加载 session
        if session_file.exists():
            try:
                await context.add_cookies(json.loads(session_file.read_text()))
                print("[INFO] 已加载 Twitter session")
            except:
                print("[WARN] session 加载失败，需要重新登录")
        
        page = await context.new_page()
        
        # 访问 Twitter
        await page.goto("https://twitter.com/compose/tweet")
        await page.wait_for_timeout(2000)
        
        # 检查是否需要登录
        if "login" in page.url or "i/flow/login" in page.url:
            print("[ERROR] 需要登录 Twitter！请先手动登录并保存 session")
            print("提示: 运行 python3 poster-daily.py --login 先登录")
            await browser.close()
            return False
        
        # 输入推文
        try:
            textbox = await page.wait_for_selector('[data-testid="tweetTextarea_0"]', timeout=5000)
            await textbox.fill(tweet_text)
        except:
            print("[ERROR] 找不到推文输入框")
            await browser.close()
            return False
        
        # 上传图片
        try:
            file_input = await page.wait_for_selector('input[type="file"]', timeout=3000)
            await file_input.set_input_files(str(image_path))
            await page.wait_for_timeout(2000)  # 等待上传
        except:
            print("[WARN] 图片上传失败，将只发送文字")
        
        # 点击发布
        try:
            tweet_btn = await page.wait_for_selector('[data-testid="tweetButton"]', timeout=3000)
            await tweet_btn.click()
            await page.wait_for_timeout(2000)
            print("[OK] 推文已发布！")
        except:
            print("[ERROR] 发布失败")
            await browser.close()
            return False
        
        # 保存 session
        cookies = await context.cookies()
        session_file.write_text(json.dumps(cookies))
        print("[INFO] Session 已保存")
        
        await browser.close()
        return True


async def login_twitter():
    """手动登录 Twitter 并保存 session"""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("[ERROR] 请安装 playwright")
        return
    
    session_file = SCRIPT_DIR / "twitter-session.json"
    
    print("=== Twitter 登录 ===")
    print("即将打开浏览器，请手动登录 Twitter 账号 @Crypto3DChannel")
    print("登录完成后，回到此终端按回车继续...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        await page.goto("https://twitter.com")
        
        input("\n登录完成后按回车继续...")
        
        # 保存 session
        cookies = await context.cookies()
        session_file.write_text(json.dumps(cookies))
        print(f"[OK] Session 已保存到: {session_file}")
        
        await browser.close()


async def main():
    parser = argparse.ArgumentParser(description="Crypto3D 推特日报系统")
    parser.add_argument("--tweet", action="store_true", help="生成并发布推文")
    parser.add_argument("--headless", action="store_true", default=True, help="无头模式运行")
    parser.add_argument("--login", action="store_true", help="手动登录 Twitter 保存 session")
    args = parser.parse_args()
    
    if args.login:
        await login_twitter()
        return
    
    print("=== Crypto3D 推特日报 ===")
    print(f"日期: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print()
    
    # 1. 加载数据
    print("[1/4] 加载指标数据...")
    indicators = load_indicators()
    print(f"  - AHR999: {indicators.get('ahr999', {}).get('value', 'N/A')}")
    print(f"  - MVRV: {indicators.get('mvrv', {}).get('value', 'N/A')}")
    print(f"  - BMRI: {indicators.get('bmri', {}).get('value', 'N/A')}")
    print(f"  - BTC.D: {indicators.get('btcd', {}).get('value', 'N/A')}%")
    
    print("\n[2/4] 加载治理动态...")
    governance = load_governance()
    print(f"  - TEV 相关提案: {len(governance)} 个")
    
    # 2. AI 选题
    print("\n[3/4] AI 选题...")
    focus = select_focus(indicators, governance)
    print(f"  - 焦点: {focus.upper()}")
    
    # 3. 生成文案
    tweet_text = generate_tweet_text(focus, indicators, governance)
    print("\n--- 推文文案 ---")
    print(tweet_text)
    print("----------------")
    
    # 4. 生成海报
    print("\n[4/4] 生成海报...")
    poster_path = await capture_poster(headless=args.headless)
    
    if poster_path:
        # 保存记录
        save_daily_record(tweet_text, focus, indicators, poster_path)
        
        # 发推
        if args.tweet:
            print("\n[发布] 正在发送推文...")
            success = await send_tweet(tweet_text, poster_path, headless=args.headless)
            if success:
                print("✅ 推文发布成功！")
            else:
                print("❌ 推文发布失败")
    else:
        print("❌ 海报生成失败")


if __name__ == "__main__":
    asyncio.run(main())
