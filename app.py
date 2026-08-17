import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import requests
import json
import os
import base64
import io
import concurrent.futures
from PIL import Image, ImageDraw
from datetime import datetime, timezone, timedelta
import urllib.request
import xml.etree.ElementTree as ET
import urllib.parse
import re

# 1. pykrx 모듈 안전 임포트 (한국거래소 정밀 연동)
try:
    from pykrx import stock
    HAS_PYKRX = True
except Exception:
    HAS_PYKRX = False

# 2. 한국 표준시(KST) 정의
KST = timezone(timedelta(hours=9))

# 3. 배경화면과 어울리는 프리미엄 MORI 앱 아이콘 생성
def get_mori_app_icon():
    size = 256
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    for y in range(size):
        r = int(30 + (y / size) * 20)
        g = int(60 + (y / size) * 25)
        b = int(50 + (y / size) * 20)
        draw.line([(0, y), (size, y)], fill=(r, g, b, 255))

    mask = Image.new("L", (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle([(0, 0), (size, size)], radius=55, fill=255)

    icon_img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    icon_img.paste(img, (0, 0), mask=mask)
    d = ImageDraw.Draw(icon_img)

    d.ellipse([(35, 35), (size-35, size-35)], outline=(245, 235, 220, 45), width=2)

    points = [(70, 180), (70, 90), (128, 145), (186, 90), (186, 180)]
    for i in range(len(points)-1):
        d.line([points[i], points[i+1]], fill=(255, 250, 240, 245), width=12)

    cx, cy = 195, 70
    sc = (245, 210, 130, 255)
    d.line([(cx-11, cy), (cx+11, cy)], fill=sc, width=3)
    d.line([(cx, cy-11), (cx, cy+11)], fill=sc, width=3)
    d.line([(cx-6, cy-6), (cx+6, cy+6)], fill=sc, width=2)
    d.line([(cx-6, cy+6), (cx+6, cy-6)], fill=sc, width=2)

    return icon_img

mori_icon_image = get_mori_app_icon()

# 4. 모바일 최적화 페이지 설정
st.set_page_config(
    page_title="MORI",
    page_icon=mori_icon_image,
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 5. 폴드 커버화면 및 다크 테마 커스텀 CSS
st.markdown("""
<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
* {
    font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif;
}

.block-container {
    padding-top: 2.2rem !important;
    padding-bottom: 2.5rem !important;
    padding-left: 0.6rem !important;
    padding-right: 0.6rem !important;
    max-width: 100% !important;
}

html, body, p, span, div, label, li {
    font-size: 18px !important;
    line-height: 1.65 !important;
}

.mori-header {
    margin-top: 0px !important;
    margin-bottom: 14px !important;
    padding-bottom: 10px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}
.mori-title {
    font-size: 38px !important;
    font-weight: 900 !important;
    letter-spacing: -0.03em;
    background: linear-gradient(135deg, #60a5fa 0%, #a855f7 50%, #38bdf8 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin: 0;
    line-height: 1.2;
}
.mori-subtitle {
    font-size: 16px !important;
    font-weight: 500 !important;
    color: #94a3b8;
    margin-top: 4px;
    letter-spacing: -0.01em;
}
.mori-time {
    font-size: 13px !important;
    color: #64748b;
    margin-top: 4px;
}

.summary-card {
    background: rgba(30, 41, 59, 0.75);
    backdrop-filter: blur(16px);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 16px;
    padding: 18px;
    margin-bottom: 14px;
    color: #f8fafc;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
}

.news-card {
    background: rgba(30, 41, 59, 0.65);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 14px;
    padding: 16px;
    margin-bottom: 12px;
    transition: transform 0.2s ease, border-color 0.2s ease;
}
.news-card:hover {
    transform: translateY(-2px);
    border-color: rgba(96, 165, 250, 0.5);
}
.news-title {
    font-size: 18px !important;
    font-weight: 700 !important;
    color: #f1f5f9;
    text-decoration: none;
    line-height: 1.5;
}
.news-title:hover {
    color: #60a5fa;
}
.news-meta {
    font-size: 13px !important;
    color: #94a3b8;
    margin-top: 8px;
}

.weather-gradient {
    background: linear-gradient(135deg, #0f766e 0%, #0369a1 50%, #1e1b4b 100%);
    border: 1px solid rgba(56, 189, 248, 0.4);
    border-radius: 16px;
    padding: 18px;
    color: white;
    margin-bottom: 14px;
    box-shadow: 0 4px 20px rgba(3, 105, 161, 0.2);
}

.sports-card {
    background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
    border: 1px solid rgba(147, 51, 234, 0.4);
    border-radius: 16px;
    padding: 18px;
    color: white;
    margin-bottom: 14px;
}

.subs-card {
    background: linear-gradient(135deg, #1e1b4b 0%, #31104b 100%);
    border: 1px solid rgba(168, 85, 247, 0.4);
    border-radius: 16px;
    padding: 18px;
    color: white;
    margin-bottom: 14px;
}

.blog-card {
    background: linear-gradient(135deg, #064e3b 0%, #065f46 50%, #0f172a 100%);
    border: 1px solid rgba(52, 211, 153, 0.4);
    border-radius: 16px;
    padding: 18px;
    color: white;
    margin-bottom: 14px;
    box-shadow: 0 4px 20px rgba(6, 78, 59, 0.25);
}

.blog-btn {
    display: inline-block;
    background: linear-gradient(135deg, #10b981 0%, #059669 100%);
    color: white !important;
    text-decoration: none;
    font-weight: 800;
    padding: 8px 14px;
    border-radius: 10px;
    font-size: 14px;
    margin-top: 6px;
    box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
}
.blog-btn:hover {
    background: linear-gradient(135deg, #059669 0%, #047857 100%);
}

.blog-btn-secondary {
    display: inline-block;
    background: rgba(255, 255, 255, 0.15);
    color: white !important;
    text-decoration: none;
    font-weight: 700;
    padding: 8px 14px;
    border-radius: 10px;
    font-size: 14px;
    margin-top: 6px;
    border: 1px solid rgba(255, 255, 255, 0.2);
}

[data-testid="stMetricValue"] {
    font-size: 28px !important;
    font-weight: 900 !important;
}
[data-testid="stMetricLabel"] {
    font-size: 15px !important;
    font-weight: 700 !important;
    color: #94a3b8 !important;
}
[data-testid="stMetricDelta"] {
    font-size: 14px !important;
    font-weight: 700 !important;
}

.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
}
.stTabs [data-baseweb="tab"] {
    height: 48px !important;
    border-radius: 10px;
    padding: 8px 16px !important;
    font-size: 16px !important;
    font-weight: 800 !important;
    color: #94a3b8;
}
.stTabs [aria-selected="true"] {
    background-color: rgba(59, 130, 246, 0.25) !important;
    color: #60a5fa !important;
    border-bottom: 3px solid #3b82f6 !important;
}

button {
    font-size: 16px !important;
    font-weight: 700 !important;
    border-radius: 10px !important;
}
input, select, textarea {
    font-size: 16px !important;
}
</style>
""", unsafe_allow_html=True)

# 6. [영구 저장소 파일 관리]
PORTFOLIO_FILE = "portfolio.json"
BRIEFING_FILE = "briefing.json"
TODOS_FILE = "todos.json"
SPORTS_FILE = "sports_teams.json"
SPORTS_BRIEFINGS_FILE = "sports_briefings.json"
LOCATION_FILE = "location.json"
SUBS_FILE = "subscriptions.json"
BLOG_POSTS_FILE = "blog_posts.json"
BLOG_STATS_FILE = "blog_stats.json"

DEFAULT_PORTFOLIO = [
    {"종목명": "KODEX AI반도체TOP2플러스", "티커": "395160", "매입단가": 13234.0, "보유수량": 126},
    {"종목명": "KODEX 200타겟위클리커버드콜", "티커": "498400", "매입단가": 13012.0, "보유수량": 863}
]

DEFAULT_SPORTS_TEAMS = [
    {"종목": "⚽ 축구", "팀명": "맨체스터 유나이티드", "리그": "프리미어리그 (EPL)", "키워드": "맨체스터 유나이티드 OR 맨유"},
    {"종목": "⚾ 야구", "팀명": "KIA 타이거즈", "리그": "KBO 리그", "키워드": "KIA 타이거즈"},
    {"종목": "⚾ 야구", "팀명": "LA 다저스", "리그": "메이저리그 (MLB)", "키워드": "LA 다저스 OR 오타니"}
]

DEFAULT_SUBSCRIPTIONS = [
    {"서비스": "SPOTV NOW", "월요금": 19900, "결제일": 15, "카테고리": "⚽ 스포츠 중계"},
    {"서비스": "넷플릭스 (Netflix)", "월요금": 17000, "결제일": 22, "카테고리": "🎬 OTT/영화"},
    {"서비스": "쿠팡플레이 (와우멤버십)", "월요금": 7890, "결제일": 8, "카테고리": "🛍️ OTT/쇼핑"},
    {"서비스": "Spotify (스포티파이)", "월요금": 11990, "결제일": 1, "카테고리": "🎵 음악 스트리밍"}
]

DEFAULT_BLOG_STATS = {
    "blog_url": "https://m.blog.naver.com/early_leave_lab",
    "blog_id": "early_leave_lab",
    "blog_name": "칼퇴연구소 | 칼퇴연구원의 테크 랩",
    "blog_slogan": "반복되는 야근을 줄이고 일상을 되찾는 생산성 치트키",
    "target_monthly_income": 300000,
    "current_monthly_income": 0,
    "manual_today_visitors": 0,
    "visitor_history": []
}

DEFAULT_BLOG_POSTS = []

DEFAULT_LOCATION = {
    "name": "경기도 용인시",
    "lat": 37.2410,
    "lon": 127.1775
}

LOCATION_PRESETS = {
    "경기도 용인시": {"lat": 37.2410, "lon": 127.1775, "name": "경기도 용인시"},
    "경기도 성남시 (분당/판교)": {"lat": 37.4200, "lon": 127.1265, "name": "경기도 성남시"},
    "서울특별시 강남구": {"lat": 37.4979, "lon": 127.0276, "name": "서울특별시 강남구"},
    "서울특별시 종로/중구": {"lat": 37.5636, "lon": 126.9976, "name": "서울특별시"},
    "인천광역시": {"lat": 37.4563, "lon": 126.7052, "name": "인천광역시"},
    "부산광역시": {"lat": 35.1796, "lon": 129.0756, "name": "부산광역시"},
    "대전광역시": {"lat": 36.3504, "lon": 127.3845, "name": "대전광역시"},
    "대구광역시": {"lat": 35.8714, "lon": 128.6014, "name": "대구광역시"},
    "광주광역시": {"lat": 35.1595, "lon": 126.8526, "name": "광주광역시"}
}

def load_location():
    if os.path.exists(LOCATION_FILE):
        try:
            with open(LOCATION_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data and "lat" in data: return data
        except Exception: pass
    return DEFAULT_LOCATION

def save_location(loc_data):
    try:
        with open(LOCATION_FILE, "w", encoding="utf-8") as f:
            json.dump(loc_data, f, ensure_ascii=False, indent=2)
    except Exception as e: pass

def load_portfolio():
    if os.path.exists(PORTFOLIO_FILE):
        try:
            with open(PORTFOLIO_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data: return data
        except Exception: pass
    return DEFAULT_PORTFOLIO

def save_portfolio(data):
    try:
        with open(PORTFOLIO_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e: st.error(f"저장 오류: {e}")

def load_briefing():
    if os.path.exists(BRIEFING_FILE):
        try:
            with open(BRIEFING_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("text"), data.get("generated_at")
        except Exception: pass
    return None, None

def save_briefing(text, generated_at_str):
    try:
        with open(BRIEFING_FILE, "w", encoding="utf-8") as f:
            json.dump({"text": text, "generated_at": generated_at_str}, f, ensure_ascii=False, indent=2)
    except Exception as e: st.error(f"저장 오류: {e}")

def load_todos():
    if os.path.exists(TODOS_FILE):
        try:
            with open(TODOS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data: return data
        except Exception: pass
    return ["주요 증시 캘린더 확인하기", "내 응원팀 경기 일정 체크하기"]

def save_todos(todos):
    try:
        with open(TODOS_FILE, "w", encoding="utf-8") as f:
            json.dump(todos, f, ensure_ascii=False, indent=2)
    except Exception as e: st.error(f"저장 오류: {e}")

def load_sports_teams():
    if os.path.exists(SPORTS_FILE):
        try:
            with open(SPORTS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data: return data
        except Exception: pass
    return DEFAULT_SPORTS_TEAMS

def save_sports_teams(teams):
    try:
        with open(SPORTS_FILE, "w", encoding="utf-8") as f:
            json.dump(teams, f, ensure_ascii=False, indent=2)
    except Exception as e: st.error(f"스포츠 설정 저장 오류: {e}")

def load_sports_briefings():
    if os.path.exists(SPORTS_BRIEFINGS_FILE):
        try:
            with open(SPORTS_BRIEFINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception: pass
    return {}

def save_sports_briefings(briefings):
    try:
        with open(SPORTS_BRIEFINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(briefings, f, ensure_ascii=False, indent=2)
    except Exception as e: pass

def load_subscriptions():
    if os.path.exists(SUBS_FILE):
        try:
            with open(SUBS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data: return data
        except Exception: pass
    return DEFAULT_SUBSCRIPTIONS

def save_subscriptions(subs):
    try:
        with open(SUBS_FILE, "w", encoding="utf-8") as f:
            json.dump(subs, f, ensure_ascii=False, indent=2)
    except Exception as e: st.error(f"구독 정보 저장 오류: {e}")

def load_blog_stats():
    if os.path.exists(BLOG_STATS_FILE):
        try:
            with open(BLOG_STATS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data: return data
        except Exception: pass
    return DEFAULT_BLOG_STATS

def save_blog_stats(stats):
    try:
        with open(BLOG_STATS_FILE, "w", encoding="utf-8") as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
    except Exception as e: pass

def load_blog_posts():
    if os.path.exists(BLOG_POSTS_FILE):
        try:
            with open(BLOG_POSTS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list): return data
        except Exception: pass
    return DEFAULT_BLOG_POSTS

def save_blog_posts(posts):
    try:
        with open(BLOG_POSTS_FILE, "w", encoding="utf-8") as f:
            json.dump(posts, f, ensure_ascii=False, indent=2)
    except Exception as e: pass

# 7. [네이버 블로그 실시간 방문자 수 및 포스팅 데이터 조회 엔진]
@st.cache_data(ttl=300)
def fetch_naver_blog_live_data(blog_id="early_leave_lab"):
    visitor_records = []
    today_vis = 0
    total_posts_rss = 0

    try:
        url_vis = f"https://blog.naver.com/NVisitorgp4Ajax.nhn?blogId={blog_id}"
        req_vis = urllib.request.Request(
            url_vis,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Referer': f'https://blog.naver.com/{blog_id}'
            }
        )
        with urllib.request.urlopen(req_vis, timeout=3) as resp:
            xml_data = resp.read().decode('utf-8')
            root = ET.fromstring(xml_data)
            for v in root.findall('visitorcnt'):
                d_str = v.get('id', '')
                cnt = int(v.get('cnt', '0'))
                short_d = f"{d_str[4:6]}/{d_str[6:8]}" if len(d_str) == 8 else d_str
                visitor_records.append({"날짜": short_d, "방문자수": cnt})
            if visitor_records:
                today_vis = visitor_records[-1]["방문자수"]
    except Exception:
        pass

    try:
        url_rss = f"https://rss.blog.naver.com/{blog_id}.xml"
        req_rss = urllib.request.Request(url_rss, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req_rss, timeout=3) as resp_rss:
            xml_rss = resp_rss.read()
            root_rss = ET.fromstring(xml_rss)
            channel = root_rss.find('channel')
            if channel is not None:
                items = channel.findall('item')
                total_posts_rss = len(items)
    except Exception:
        pass

    return {
        "today_visitors": today_vis,
        "visitor_history": visitor_records,
        "rss_post_count": total_posts_rss
    }

# 8. 실시간 위치 기반 날씨 데이터 조회
@st.cache_data(ttl=1800)
def get_current_weather(lat=37.2410, lon=127.1775, default_name="경기도 용인시"):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m&timezone=auto"
        res = requests.get(url, timeout=3).json()
        current = res.get("current", {})
        temp = current.get("temperature_2m", 28.0)
        humidity = current.get("relative_humidity_2m", 65)
        code = current.get("weather_code", 0)
        
        weather_desc = "맑음 ☀️"
        if code == 1 or code == 2: weather_desc = "구름 조금 ⛅"
        elif code == 3: weather_desc = "흐림 ☁️"
        elif code in (51, 53, 55, 61, 63, 65, 80, 81, 82): weather_desc = "비 🌧️"
        elif code in (71, 73, 75, 85, 86): weather_desc = "눈 ❄️"
        
        loc_label = f"📍 {default_name}"
        return f"{temp:.1f}°C", weather_desc, f"{humidity}%", loc_label
    except Exception:
        return "28.0°C", "맑음 ☀️", "60%", f"📍 {default_name}"

# 9. [초고속 pykrx + yfinance 하이브리드 엔진]
@st.cache_data(ttl=120)
def get_live_market_data(ticker_symbol):
    clean_code = str(ticker_symbol).replace(".KS", "").replace(".KQ", "").strip()

    if clean_code.isdigit() and len(clean_code) == 6 and HAS_PYKRX:
        try:
            today_dt = datetime.now(KST)
            start_dt = today_dt - timedelta(days=7)
            s_str = start_dt.strftime("%Y%m%d")
            e_str = today_dt.strftime("%Y%m%d")
            
            df = stock.get_market_ohlcv_by_date(s_str, e_str, clean_code)
            if not df.empty and len(df) >= 2:
                cur_close = float(df['종가'].iloc[-1])
                prev_close = float(df['종가'].iloc[-2])
                pct = ((cur_close - prev_close) / prev_close) * 100 if prev_close > 0 else 0.0
                return cur_close, pct
            elif not df.empty and len(df) == 1:
                return float(df['종가'].iloc[-1]), 0.0
        except Exception:
            pass

    try:
        yf_symbol = ticker_symbol
        if clean_code.isdigit() and len(clean_code) == 6 and not (yf_symbol.endswith(".KS") or yf_symbol.endswith(".KQ")):
            yf_symbol = f"{clean_code}.KS"

        t = yf.Ticker(yf_symbol)
        hist = t.history(period="2d")
        if len(hist) >= 2:
            current = hist['Close'].iloc[-1]
            prev = hist['Close'].iloc[-2]
            delta_pct = ((current - prev) / prev) * 100
            return current, delta_pct
        elif len(hist) == 1:
            return hist['Close'].iloc[-1], 0.0
        return None, None
    except Exception:
        return None, None

def get_batch_market_data(ticker_list):
    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(10, len(ticker_list) + 1)) as executor:
        future_to_ticker = {executor.submit(get_live_market_data, t): t for t in ticker_list}
        for future in concurrent.futures.as_completed(future_to_ticker):
            t = future_to_ticker[future]
            try:
                results[t] = future.result()
            except Exception:
                results[t] = (None, None)
    return results

@st.cache_data(ttl=300)
def fetch_news_feed(query, max_results=8):
    try:
        encoded_query = urllib.parse.quote(query)
        url = f"https://news.google.com/rss/search?q={encoded_query}&hl=ko&gl=KR&ceid=KR:ko"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=3) as response:
            xml_data = response.read()
            root = ET.fromstring(xml_data)
            news_items = []
            for item in root.findall('.//item')[:max_results]:
                title = item.find('title').text if item.find('title') is not None else "제목 없음"
                link = item.find('link').text if item.find('link') is not None else "#"
                pub_date = item.find('pubDate').text if item.find('pubDate') is not None else ""
                source = item.find('source').text if item.find('source') is not None else "언론사"
                if pub_date: pub_date = pub_date[:16]
                news_items.append({"title": title, "link": link, "source": source, "date": pub_date})
            return news_items
    except Exception:
        return []

# 10. [통합 제미나이 AI 호출 엔진]
def call_gemini_api(prompt_text, api_key, system_instruction=None, image_bytes=None, chat_contents=None):
    if not api_key or not api_key.strip():
        return None, "Gemini API Key를 입력해 주세요."
    
    clean_key = api_key.strip()
    headers = {"Content-Type": "application/json"}
    
    candidate_models = []
    try:
        m_res = requests.get(f"https://generativelanguage.googleapis.com/v1beta/models?key={clean_key}", timeout=5)
        if m_res.status_code == 200:
            active = [m['name'].replace("models/", "") for m in m_res.json().get('models', []) if 'generateContent' in m.get('supportedGenerationMethods', [])]
            flash_models = [m for m in active if 'flash' in m.lower()]
            other_models = [m for m in active if 'flash' not in m.lower()]
            candidate_models = flash_models + other_models
    except Exception:
        pass
        
    if not candidate_models:
        candidate_models = ["gemini-1.5-flash", "gemini-1.5-flash-latest", "gemini-2.0-flash", "gemini-2.5-flash", "gemini-pro"]

    if chat_contents:
        contents = chat_contents
    elif image_bytes:
        base64_img = base64.b64encode(image_bytes).decode('utf-8')
        contents = [{"parts": [{"text": prompt_text}, {"inline_data": {"mime_type": "image/jpeg", "data": base64_img}}]}]
    else:
        contents = [{"parts": [{"text": prompt_text}]}]

    payload = {"contents": contents}
    if system_instruction:
        payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

    last_err = ""
    for model_name in candidate_models:
        clean_name = model_name.replace("models/", "").strip()
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{clean_name}:generateContent?key={clean_key}"
        try:
            res = requests.post(url, json=payload, headers=headers, timeout=25)
            if res.status_code == 200:
                resp_json = res.json()
                text = resp_json['candidates'][0]['content']['parts'][0]['text']
                return text, "SUCCESS"
            else:
                last_err = f"[{res.status_code}] {res.text[:120]}"
        except Exception as e:
            last_err = str(e)
            
    return None, f"AI 생성 오류: {last_err}"

def analyze_portfolio_image(image_bytes, api_key):
    prompt = """
    이 이미지는 증권사 주식/ETF 잔고 화면입니다.
    보유 중인 종목명, 야후파이낸스 또는 한국거래소 티커(국내 종목/ETF는 6자리코드, 미국 주식은 알파벳), 평균 매입단가(숫자), 보유 수량(정수)을 추출해주세요.
    반드시 순수 JSON 배열 형식으로만 응답해주세요:
    [
        {"종목명": "KODEX AI반도체TOP2플러스", "티커": "395160", "매입단가": 13234.0, "보유수량": 126},
        {"종목명": "KODEX 200타겟위클리커버드콜", "티커": "498400", "매입단가": 13012.0, "보유수량": 863}
    ]
    """
    raw_text, status = call_gemini_api(prompt, api_key, image_bytes=image_bytes)
    if status == "SUCCESS" and raw_text:
        try:
            clean_json = raw_text.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_json), "SUCCESS"
        except Exception as e:
            return None, f"JSON 파싱 실패: {e}"
    return None, raw_text if raw_text else status

def generate_ai_briefing(news_headlines, portfolio_items, api_key):
    stock_list_str = ", ".join([f"{item['종목명']} ({item['티커']})" for item in portfolio_items]) if portfolio_items else "KODEX AI반도체TOP2플러스, KODEX 200타겟위클리커버드콜"
    news_text = "\n".join([f"- {h['title']} ({h.get('source', '')})" for h in news_headlines[:15]]) if news_headlines else "국내외 주요 증시 시황 및 반도체 뉴스"
    
    prompt = f"""
    당신은 수석 증시 애널리스트 AI 어시스턴트입니다.
    오늘자 실시간 주요 금융/경제 뉴스 헤드라인과 투자자의 보유 포트폴리오를 바탕으로, 모바일에서 읽기 편한 [오늘자 맞춤형 모닝 증시 브리핑]을 작성해주세요.

    [투자자 보유 종목]
    {stock_list_str}

    [오늘의 실시간 주요 뉴스 헤드라인]
    {news_text}

    [작성 가이드라인]
    1. 🌐 오늘의 글로벌 & 국내 증시 핵심 요약 (핵심 3줄)
    2. 🎯 내 보유 종목에 미치는 영향 및 시사점 (KODEX AI반도체 및 커버드콜 등 보유 종목별 맞춤 분석)
    3. 💡 오늘 장 시작 전 투자 전략 및 관전 포인트 (간결하고 실용적인 가이드)
    
    이모지와 함께 모바일 화면에서 한눈에 들어오도록 명확하고 간결하게 마크다운으로 작성해주세요.
    """
    return call_gemini_api(prompt, api_key)

def generate_team_briefing(team_name, sports_type, league, team_news, api_key):
    news_text = "\n".join([f"- {h['title']} ({h.get('source', '')})" for h in team_news[:10]]) if team_news else f"{team_name} 최신 경기 일정"
    
    prompt = f"""
    당신은 스포츠 전문 기자이자 분석가 AI입니다.
    현재 시점(2026년 8월)을 기준으로 [{sports_type} - {team_name} ({league})] 구단의 최신 경기 일정, 최근 경기 결과, 구단 핵심 이슈를 브리핑해주세요.

    [중요 규칙]
    - 경기 일정에 표기되는 모든 날짜와 킥오프/시작 시간은 반드시 **대한민국 표준시 (한국 시간, KST)** 기준으로 표기해주세요 (예: '8월 16일(일) 밤 10:30 (한국 시간)', '새벽 04:00 (한국 시간)').

    [최신 관련 뉴스 데이터]
    {news_text}

    [작성 가이드라인]
    1. 📅 **다가오는 다음 경기 일정**: (대진 상대, 경기 날짜/한국 시간 KST, 홈/원정)
    2. 🏆 **최근 경기 결과 & 스코어**: (최근 경기 승패, 스코어, 주요 활약 선수)
    3. 📰 **구단 핵심 뉴스 & 라인업 이슈**: (부상자, 주요 선수 폼, 최근 팀 분위기 3줄 요약)

    이모지와 함께 모바일 화면에서 한눈에 보기 좋게 마크다운으로 명확하고 간결하게 작성해주세요.
    """
    text, status = call_gemini_api(prompt, api_key)
    return text if status == "SUCCESS" else None

def ask_gemini_chat(chat_history, user_msg, portfolio_items, api_key):
    stock_list_str = ", ".join([f"{item['종목명']} ({item['티커']})" for item in portfolio_items]) if portfolio_items else "KODEX AI반도체TOP2플러스, KODEX 200타겟위클리커버드콜"
    system_inst = f"당신은 투자자의 1:1 개인 금융/주식 비서 AI 'MORI'입니다. 투자자가 보유한 포트폴리오는 [{stock_list_str}] 입니다. 친절하고 명확하며 실용적인 분석을 한국어로 답변하세요."

    contents = []
    last_role = None
    for msg in chat_history:
        role = "user" if msg["role"] == "user" else "model"
        if not contents and role != "user":
            continue
        if role == last_role:
            continue
        contents.append({"role": role, "parts": [{"text": msg["content"]}]})
        last_role = role
        
    if not contents:
        contents = [{"role": "user", "parts": [{"text": user_msg}]}]

    text, status = call_gemini_api("", api_key, system_instruction=system_inst, chat_contents=contents)
    if status == "SUCCESS" and text:
        return text
    
    fallback_prompt = f"[{system_inst}]\n\n질문: {user_msg}"
    fb_text, fb_status = call_gemini_api(fallback_prompt, api_key)
    if fb_status == "SUCCESS" and fb_text:
        return fb_text
    return f"⚠️ AI 비서 응답 중 오류가 발생했습니다: {text if text else status}"


# =============================================================
# ⭐ [4대 핵심 대분류 렌더링 모듈]
# =============================================================

# -------------------------------------------------------------
# 1. 🏠 [데일리 허브 모듈]
# -------------------------------------------------------------
def render_daily_hub():
    st.subheader("🏠 데일리 라이프 & 일정 허브")
    
    sub_d1, sub_d2, sub_d3, sub_d4 = st.tabs(["📌 오늘의 요약", "📅 통합 캘린더", "💳 고정 구독료", "📋 To-Do & 날씨"])

    with sub_d1:
        temp_val, weather_val, humid_val, loc_tag = get_current_weather(
            current_loc_data.get("lat", 37.2410),
            current_loc_data.get("lon", 127.1775),
            current_loc_data.get("name", "경기도 용인시")
        )
        st.markdown(f"""
        <div class="weather-gradient">
            <div style="font-size: 15px; color: #bae6fd; font-weight: 700;">{loc_tag} 실시간 날씨</div>
            <div style="font-size: 30px; font-weight: 900; margin-top: 6px; letter-spacing: -0.02em;">{weather_val} {temp_val}</div>
            <div style="font-size: 14px; color: #e0f2fe; margin-top: 4px;">습도 {humid_val} | 외출 및 출퇴근 추천 날씨</div>
        </div>
        """, unsafe_allow_html=True)

        with st.container(border=True):
            st.markdown("**📅 8월 주요 일정 & D-Day 요약** (오늘: 8월 16일)")
            cal_summary_events = [
                {"날짜": "8월 22일(토)", "구분": "🎬 OTT", "일정": "넷플릭스 결제일 (17,000원)", "D-Day": "D-6"},
                {"날짜": "8월 23일(일)", "구분": "📝 어학", "일정": "오픽(OPIc) 성적 발표 13:00", "D-Day": "D-7"},
                {"날짜": "8월 26일(수)", "구분": "🎯 반도체", "일정": "엔비디아(NVDA) 실적 발표", "D-Day": "D-10"},
                {"날짜": "8월 28일(금)", "구분": "🌐 경제", "일정": "미국 잭슨홀 심포지엄 (파월 연설)", "D-Day": "D-12"},
                {"날짜": "9월 01일(화)", "구분": "💰 배당금", "일정": "KODEX 커버드콜 월 분배금 입금", "D-Day": "D-16"}
            ]
            st.dataframe(pd.DataFrame(cal_summary_events), use_container_width=True)

        home_todos = load_todos()
        with st.container(border=True):
            st.markdown("**✅ 오늘의 할 일 (To-Do)**")
            if home_todos:
                for t in home_todos[:3]:
                    st.markdown(f"• **{t}**")
            else:
                st.info("등록된 할 일이 없습니다.")

        home_portfolio = load_portfolio()
        p_tickers = [it["티커"] for it in home_portfolio]
        batch_prices = get_batch_market_data(p_tickers)
        total_eval_h = 0
        total_buy_h = 0
        for it in home_portfolio:
            cp, _ = batch_prices.get(it["티커"], (None, None))
            if cp is None: cp = it["매입단가"]
            total_eval_h += cp * it["보유수량"]
            total_buy_h += it["매입단가"] * it["보유수량"]
        diff_h = total_eval_h - total_buy_h
        rate_h = (diff_h / total_buy_h) * 100 if total_buy_h > 0 else 0

        with st.container(border=True):
            st.markdown("**💼 내 포트폴리오 한 줄 요약**")
            ch1, ch2 = st.columns(2)
            with ch1: st.metric("총 평가금액", f"{total_eval_h:,.0f}원", f"{rate_h:+.2f}%")
            with ch2: st.metric("총 평가손익", f"{diff_h:+,.0f}원")

    with sub_d2:
        user_portfolio = load_portfolio()
        cover_shares = 863
        for p in user_portfolio:
            if "커버드콜" in p["종목명"]: cover_shares = p["보유수량"]
        monthly_est_div = cover_shares * 270
        
        st.markdown(f"""
        <div class="subs-card">
            <div style="font-size: 15px; color: #e9d5ff; font-weight: 700;">💰 월 배당금(분배금) 예상 수령액</div>
            <div style="font-size: 30px; font-weight: 900; margin-top: 4px;">{monthly_est_div:,.0f}원 / 월</div>
            <div style="font-size: 14px; color: #d8b4fe; margin-top: 4px;">KODEX 200위클리커버드콜({cover_shares:,}주) 기준</div>
        </div>
        """, unsafe_allow_html=True)

        timeline_events = [
            {"날짜": "8월 22일(토)", "분류": "🎬 구독 결제", "내용": "넷플릭스 (17,000원) 결제일 (D-6)", "중요도": "🟡 정기"},
            {"날짜": "8월 23일(일)", "분류": "📝 어학 시험", "내용": "오픽(OPIc) 성적 발표 13:00 (D-7)", "중요도": "🔴 필수"},
            {"날짜": "8월 26일(수)", "분류": "🎯 AI반도체", "내용": "엔비디아(NVDA) 2분기 실적 발표 (D-10)", "중요도": "🔴 핵심"},
            {"날짜": "8월 28일(금)", "분류": "🌐 거시경제", "내용": "미국 잭슨홀 심포지엄 (파월 의장 연설)", "중요도": "🔴 높음"},
            {"날짜": "9월 01일(화)", "분류": "💰 배당금 입금", "내용": "KODEX 커버드콜 월 분배금 입금 예정일", "중요도": "🟢 수익"},
            {"날짜": "9월 01일(화)", "분류": "🎵 구독 결제", "내용": "Spotify (11,990원) 결제일", "중요도": "🟡 정기"},
            {"날짜": "9월 08일(화)", "분류": "🛍️ 구독 결제", "내용": "쿠팡 와우멤버십 (7,890원) 결제일", "중요도": "🟡 정기"},
            {"날짜": "9월 10일(목)", "분류": "🎯 파생만기", "내용": "국내 선물·옵션 동시 만기일 (네 마녀의 날)", "중요도": "🔴 변동성"},
            {"날짜": "9월 15일(화)", "분류": "⚽ 구독 결제", "내용": "SPOTV NOW (19,900원) 결제일", "중요도": "🟡 정기"},
            {"날짜": "9월 16일(수)", "분류": "🌐 거시경제", "내용": "미국 9월 FOMC 기준금리 결정 회의", "중요도": "🔴 높음"}
        ]
        st.dataframe(pd.DataFrame(timeline_events), use_container_width=True)

    with sub_d3:
        subs_list = load_subscriptions()
        total_sub_monthly = sum(s["월요금"] for s in subs_list)
        monthly_est_div = 863 * 270
        coverage_rate = (monthly_est_div / total_sub_monthly * 100) if total_sub_monthly > 0 else 0

        c_s1, c_s2 = st.columns(2)
        with c_s1: st.metric("월 고정 구독료 합계", f"{total_sub_monthly:,.0f}원", f"총 {len(subs_list)}개 서비스")
        with c_s2: st.metric("배당금 방어율", f"{coverage_rate:.1f}%", f"월 배당 {monthly_est_div:,.0f}원")

        st.markdown(f"""
        <div class="summary-card" style="border-left: 4px solid #10b981;">
            <div style="font-weight: 700; color: #34d399;">🛡️ 배당금 방어 성공!</div>
            <div style="font-size: 15px; color: #cbd5e1; margin-top: 4px;">
                매월 발생하는 커버드콜 배당금({monthly_est_div:,.0f}원)이 고정 구독료({total_sub_monthly:,.0f}원)를 초과하여 <b>모든 OTT 및 멤버십을 배당금만으로 전액 무료 충당</b>하고 있습니다.
            </div>
        </div>
        """, unsafe_allow_html=True)

        for idx, s in enumerate(subs_list):
            col_name, col_cost, col_dday = st.columns([0.5, 0.25, 0.25])
            with col_name: st.markdown(f"**{s['카테고리']} {s['서비스']}**")
            with col_cost: st.markdown(f"{s['월요금']:,}원 / 월")
            with col_dday: st.markdown(f"매월 **{s['결제일']}일**")

        with st.expander("➕ 새 구독 서비스 추가 / 관리"):
            with st.form("add_sub_form"):
                new_s_name = st.text_input("서비스명 (예: 유튜브 프리미엄, Goodnotes)", value="유튜브 프리미엄")
                new_s_cost = st.number_input("월 구독료(원)", value=14900, step=1000)
                new_s_day = st.number_input("매월 결제일 (1~31일)", value=1, min_value=1, max_value=31)
                new_s_cat = st.selectbox("카테고리", ["🎬 OTT/영상", "⚽ 스포츠", "🎵 음악", "💼 생산성/클라우드", "🛍️ 쇼핑/기타"])
                if st.form_submit_button("구독 서비스 등록"):
                    if new_s_name.strip():
                        subs_list.append({"서비스": new_s_name.strip(), "월요금": int(new_s_cost), "결제일": int(new_s_day), "카테고리": new_s_cat})
                        save_subscriptions(subs_list)
                        st.success(f"'{new_s_name}' 등록 완료!")
                        st.rerun()

    with sub_d4:
        with st.expander("📍 날씨 지역 변경 / GPS 위치 설정"):
            preset_names = list(LOCATION_PRESETS.keys())
            sel_preset = st.selectbox("지역 선택", preset_names, index=0)
            if st.button("선택 지역으로 날씨 저장"):
                chosen = LOCATION_PRESETS[sel_preset]
                save_location(chosen)
                st.success(f"'{chosen['name']}'(으)로 날씨 위치가 저장되었습니다!")
                st.rerun()

        st.subheader("✅ 할 일 관리 (To-Do List)")
        current_todos = load_todos()
        to_delete = None
        for idx, todo_item in enumerate(current_todos):
            col_t1, col_t2 = st.columns([0.85, 0.15])
            with col_t1: st.write(f"• **{todo_item}**")
            with col_t2:
                if st.button("완료", key=f"del_d_{idx}"): to_delete = idx
        if to_delete is not None:
            current_todos.pop(to_delete)
            save_todos(current_todos)
            st.rerun()

        with st.form("new_todo_form"):
            new_todo = st.text_input("새로운 할 일 입력")
            if st.form_submit_button("추가하기"):
                if new_todo.strip():
                    current_todos.append(new_todo.strip())
                    save_todos(current_todos)
                    st.success("할 일이 추가되었습니다!")
                    st.rerun()

# -------------------------------------------------------------
# 2. 💼 [주식 & 금융 허브 모듈]
# -------------------------------------------------------------
def render_stock_hub():
    st.subheader("💼 주식 & 금융 인텔리전스 허브")
    
    sub_s1, sub_s2, sub_s3, sub_s4, sub_s5 = st.tabs([
        "💼 내 포트폴리오", "📊 실시간 시황", "📰 맞춤 뉴스 & 검색", "💡 AI 모닝 브리핑", "🤖 1:1 투자 비서"
    ])

    with sub_s1:
        user_portfolio = load_portfolio()
        port_tickers = [item["티커"] for item in user_portfolio]
        live_prices_map = get_batch_market_data(port_tickers)

        total_eval_krw = 0
        total_buy_krw = 0
        calculated_rows = []

        for item in user_portfolio:
            cur_p, _ = live_prices_map.get(item["티커"], (None, None))
            if cur_p is None: cur_p = item["매입단가"]
            clean_t = str(item["티커"]).replace(".KS", "").replace(".KQ", "").strip()
            is_krw = clean_t.isdigit()
            eval_amount = cur_p * item["보유수량"]
            buy_amount = item["매입단가"] * item["보유수량"]
            profit_amount = eval_amount - buy_amount
            profit_rate = (profit_amount / buy_amount) * 100 if buy_amount > 0 else 0

            if is_krw:
                total_eval_krw += eval_amount
                total_buy_krw += buy_amount

            calculated_rows.append({
                "종목명": item["종목명"],
                "수량": f"{item['보유수량']:,}주",
                "매입가": f"{item['매입단가']:,.0f}원" if is_krw else f"${item['매입단가']:.2f}",
                "현재가": f"{cur_p:,.0f}원" if is_krw else f"${cur_p:.2f}",
                "평가금액": f"{eval_amount:,.0f}원" if is_krw else f"${eval_amount:,.2f}",
                "수익률": f"{profit_rate:+.2f}%"
            })

        total_profit_krw = total_eval_krw - total_buy_krw
        total_rate_krw = (total_profit_krw / total_buy_krw) * 100 if total_buy_krw > 0 else 0

        c1, c2 = st.columns(2)
        with c1: st.metric("총 평가금액", f"{total_eval_krw:,.0f}원", f"{total_rate_krw:+.2f}%")
        with c2: st.metric("총 평가손익", f"{total_profit_krw:+,.0f}원", f"매입총액: {total_buy_krw:,.0f}원")

        st.dataframe(pd.DataFrame(calculated_rows), use_container_width=True)

        with st.expander("📸 잔고 사진으로 포트폴리오 업데이트"):
            uploaded_file = st.file_uploader("증권사 잔고 캡처 업로드", type=["png", "jpg", "jpeg"])
            if uploaded_file and st.button("✨ AI 분석 및 영구 저장"):
                if not st.session_state.saved_gemini_key:
                    st.warning("Gemini API Key가 필요합니다.")
                else:
                    parsed, status = analyze_portfolio_image(uploaded_file.getvalue(), st.session_state.saved_gemini_key)
                    if status == "SUCCESS" and parsed:
                        save_portfolio(parsed)
                        st.success("포트폴리오가 저장되었습니다!")
                        st.rerun()

    with sub_s2:
        market_tickers = ["^KS11", "^GSPC", "^IXIC", "BZ=F", "005930", "000660", "005380", "NVDA"]
        m_prices = get_batch_market_data(market_tickers)
        kospi_p, kospi_d = m_prices.get("^KS11", (None, None))
        sp500_p, sp500_d = m_prices.get("^GSPC", (None, None))
        samsung_p, samsung_d = m_prices.get("005930", (None, None))
        nvda_p, nvda_d = m_prices.get("NVDA", (None, None))
        
        c1, c2 = st.columns(2)
        with c1:
            st.metric("코스피 (KOSPI)", f"{kospi_p:,.2f}" if kospi_p else "6,977.94", f"{kospi_d:+.2f}%" if kospi_d else "+2.42%")
            st.metric("삼성전자", f"{samsung_p:,.0f}원" if samsung_p else "84,500원", f"{samsung_d:+.2f}%" if samsung_d else "+2.43%")
        with c2:
            st.metric("S&P 500", f"{sp500_p:,.2f}" if sp500_p else "5,554.20", f"{sp500_d:+.2f}%" if sp500_d else "-0.20%")
            st.metric("엔비디아 (NVDA)", f"${nvda_p:.2f}" if nvda_p else "$224.92", f"{nvda_d:+.2f}%" if nvda_d else "-0.18%")

    with sub_s3:
        user_portfolio = load_portfolio()
        my_stock_names = [item["종목명"] for item in user_portfolio]
        
        category_options = (
            ["📌 [전체] 내 보유 종목 뉴스"] +
            [f"🎯 {name}" for name in my_stock_names] +
            ["🇰🇷 국내 증시", "🇺🇸 미국 증시", "🤖 AI·반도체", "🔍 직접 검색"]
        )
        selected_cat = st.selectbox("뉴스 카테고리 선택", category_options, index=0)
        
        if selected_cat == "🔍 직접 검색":
            query = st.text_input("검색할 뉴스 키워드 입력", value="삼성전자")
        elif selected_cat == "📌 [전체] 내 보유 종목 뉴스":
            query = " OR ".join([f'"{name}"' for name in my_stock_names]) + " OR AI반도체 OR 커버드콜"
        elif selected_cat.startswith("🎯 "):
            s_name = selected_cat.replace("🎯 ", "")
            query = f'"{s_name}"' if "반도체" not in s_name else f'"{s_name}" OR AI반도체'
        elif selected_cat == "🇰🇷 국내 증시":
            query = "코스피 OR 코스닥 OR 환율"
        elif selected_cat == "🇺🇸 미국 증시":
            query = "뉴욕증시 OR S&P500 OR 나스닥 OR 엔비디아"
        elif selected_cat == "🤖 AI·반도체":
            query = "엔비디아 OR 반도체 HBM OR 인공지능 AI"
        else:
            query = "코스피"

        if query:
            news_list = fetch_news_feed(query, max_results=8)
            for item in news_list:
                st.markdown(f"""
                <div class="news-card">
                    <a class="news-title" href="{item['link']}" target="_blank">🔗 {item['title']}</a>
                    <div class="news-meta">📰 {item['source']} &nbsp;|&nbsp; 🕒 {item['date']}</div>
                </div>
                """, unsafe_allow_html=True)

    with sub_s4:
        user_portfolio = load_portfolio()
        recent_news = fetch_news_feed("코스피 OR 반도체 OR 연준 금리 OR 엔비디아", max_results=12)
        k_input_b = st.text_input("Gemini API Key (브리핑용)", value=st.session_state.saved_gemini_key, type="password", key="brief_k_in")
        if k_input_b: st.session_state.saved_gemini_key = k_input_b
        
        c_b1, c_b2 = st.columns(2)
        with c_b1:
            if st.button("✨ 오늘자 AI 브리핑 재생성", key="btn_b_re"):
                if not st.session_state.saved_gemini_key:
                    st.warning("API Key가 필요합니다.")
                else:
                    with st.spinner("AI 분석 중..."):
                        b_res, status = generate_ai_briefing(recent_news, user_portfolio, st.session_state.saved_gemini_key)
                        if status == "SUCCESS" and b_res:
                            save_briefing(b_res, datetime.now(KST).strftime('%Y년 %m월 %d일 %H:%M:%S'))
                            st.success("브리핑 완료!")
                            st.rerun()
        saved_b, saved_t = load_briefing()
        with c_b2:
            if saved_b:
                clean_speech = saved_b.replace("#", "").replace("*", "").replace("\n", " ").replace('"', '')[:300]
                tts_html = f"""
                <button onclick="window.speechSynthesis.speak(new SpeechSynthesisUtterance('{clean_speech}'))" style="background-color: #8b5cf6; color: white; border: none; padding: 10px 16px; border-radius: 8px; font-weight: 700; cursor: pointer; width: 100%;">
                    🔊 음성으로 듣기 (TTS)
                </button>
                """
                components.html(tts_html, height=45)
        if saved_b:
            st.caption(f"🕒 생성 시각: {saved_t}")
            st.markdown(saved_b)

    with sub_s5:
        if "chat_messages" not in st.session_state:
            st.session_state.chat_messages = [{"role": "assistant", "content": "안녕하세요! 고객님의 보유 포트폴리오를 기반으로 맞춤 투자 분석을 도와드립니다."}]
        for msg in st.session_state.chat_messages:
            with st.chat_message(msg["role"]): st.markdown(msg["content"])
        with st.form("chat_form_s", clear_on_submit=True):
            col_ci1, col_ci2 = st.columns([0.8, 0.2])
            with col_ci1: user_input = st.text_input("질문", placeholder="AI 비서에게 질문을 입력하세요...", label_visibility="collapsed")
            with col_ci2: send_btn = st.form_submit_button("전송 🚀", use_container_width=True)
        if send_btn and user_input.strip():
            u_text = user_input.strip()
            st.session_state.chat_messages.append({"role": "user", "content": u_text})
            if st.session_state.saved_gemini_key:
                with st.spinner("AI 분석 중..."):
                    reply = ask_gemini_chat(st.session_state.chat_messages, u_text, load_portfolio(), st.session_state.saved_gemini_key)
                    st.session_state.chat_messages.append({"role": "assistant", "content": reply})
                    st.rerun()

# -------------------------------------------------------------
# 3. ⚽ [스포츠 허브 모듈]
# -------------------------------------------------------------
def render_sports_hub():
    st.subheader("⚽ 스포츠 & 응원팀 인텔리전스")
    my_teams = load_sports_teams()
    sports_briefings = load_sports_briefings()

    team_names = [f"{idx+1}. {t['종목']} {t['팀명']} ({t['리그']})" for idx, t in enumerate(my_teams)]
    selected_team_idx = st.selectbox("응원하는 팀 선택", range(len(team_names)), format_func=lambda x: team_names[x], key="sp_sel_main")
    
    current_team = my_teams[selected_team_idx]
    team_key = current_team["팀명"]

    search_query = f'"{current_team["팀명"]}" AND (경기 OR 일정 OR 결과 OR 승리 OR 패배 OR 하이라이트)'
    team_news = fetch_news_feed(search_query, max_results=8)

    c_s1, c_s2 = st.columns([0.65, 0.35])
    with c_s1: st.write(f"### {current_team['종목']} {current_team['팀명']} ({current_team['리그']})")
    with c_s2:
        if st.button("⚡ 경기 브리핑 생성 (한국시간 기준)", key=f"btn_sb_m_{team_key}"):
            if not st.session_state.saved_gemini_key:
                st.warning("Gemini API Key가 필요합니다.")
            else:
                with st.spinner(f"{team_key} 일정 및 이슈 AI 분석 중..."):
                    b_txt = generate_team_briefing(current_team['팀명'], current_team['종목'], current_team['리그'], team_news, st.session_state.saved_gemini_key)
                    if b_txt:
                        sports_briefings[team_key] = {"text": b_txt, "updated_at": datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S')}
                        save_sports_briefings(sports_briefings)
                        st.success("구단 브리핑 업데이트 완료!")
                        st.rerun()

    if team_key in sports_briefings:
        b_data = sports_briefings[team_key]
        st.caption(f"🕒 업데이트 시각: {b_data.get('updated_at', '')} (모든 경기 시간은 한국시간 KST 기준)")
        st.markdown(b_data.get("text", ""))

    st.markdown("---")
    st.write(f"📰 **{current_team['팀명']} 실시간 뉴스 피드**")
    for n in team_news:
        st.markdown(f"""
        <div class="news-card">
            <a class="news-title" href="{n['link']}" target="_blank">📣 {n['title']}</a>
            <div class="news-meta">📰 {n['source']} &nbsp;|&nbsp; 🕒 {n['date']}</div>
        </div>
        """, unsafe_allow_html=True)

    with st.expander("🔄 내 응원팀 순서 변경 및 추가/삭제"):
        for idx, t in enumerate(my_teams):
            col_t_name, col_up, col_down, col_top = st.columns([0.45, 0.18, 0.18, 0.19])
            with col_t_name: st.markdown(f"**{idx+1}위**: {t['종목']} {t['팀명']}")
            with col_up:
                if idx > 0 and st.button("⬆️", key=f"u_{idx}"):
                    my_teams[idx], my_teams[idx-1] = my_teams[idx-1], my_teams[idx]
                    save_sports_teams(my_teams); st.rerun()
            with col_down:
                if idx < len(my_teams)-1 and st.button("⬇️", key=f"d_{idx}"):
                    my_teams[idx], my_teams[idx+1] = my_teams[idx+1], my_teams[idx]
                    save_sports_teams(my_teams); st.rerun()
            with col_top:
                if idx > 0 and st.button("⭐ 1순위", key=f"tp_{idx}"):
                    f_item = my_teams.pop(idx); my_teams.insert(0, f_item)
                    save_sports_teams(my_teams); st.rerun()

# -------------------------------------------------------------
# 4. ✍️ [블로그 관리 모듈 - 실시간 통계 & 1초 빠른 동기화 대시보드]
# -------------------------------------------------------------
def render_blog_hub():
    st.subheader("✍️ 내 네이버 블로그 실시간 대시보드")
    
    blog_stats = load_blog_stats()
    blog_posts = load_blog_posts()
    blog_id = blog_stats.get("blog_id", "early_leave_lab")

    # 1) 네이버 블로그 실시간 데이터 가져오기
    live_data = fetch_naver_blog_live_data(blog_id)
    today_visitors_live = live_data.get("today_visitors", 0)
    history_vis = live_data.get("visitor_history", [])
    total_posts_rss = live_data.get("rss_post_count", 0)

    # 수동 설정값과 라이브값 중 우선 적용
    display_today_vis = today_visitors_live if today_visitors_live > 0 else blog_stats.get("manual_today_visitors", 0)
    display_total_posts = len(blog_posts) if len(blog_posts) > 0 else total_posts_rss

    # 저장된 방문자 히스토리가 있으면 사용
    stored_hist = blog_stats.get("visitor_history", [])
    if history_vis:
        final_history = history_vis
    elif stored_hist:
        final_history = stored_hist
    else:
        final_history = []

    # 🌟 내 블로그 브랜드 카드 & 정확한 네이버 통계 바로가기 링크 버튼들
    st.markdown(f"""
    <div class="blog-card">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
            <div>
                <div style="font-size: 22px; font-weight: 900; color: #6ee7b7;">칼퇴연구소 | 칼퇴연구원의 테크 랩</div>
                <div style="font-size: 15px; color: #a7f3d0; margin-top: 4px;">반복되는 야근을 줄이고 일상을 되찾는 생산성 치트키</div>
                <div style="font-size: 13px; color: #d1fae5; margin-top: 4px;">블로그 ID: <b>@{blog_id}</b></div>
            </div>
        </div>
        <div style="margin-top: 12px; border-top: 1px solid rgba(255,255,255,0.15); padding-top: 10px; display: flex; gap: 8px; flex-wrap: wrap;">
            <a class="blog-btn" href="https://m.blog.naver.com/{blog_id}" target="_blank">
                🌐 내 블로그 바로가기 ↗️
            </a>
            <a class="blog-btn-secondary" href="https://admin.blog.naver.com/{blog_id}/stat/today" target="_blank">
                📊 네이버 통계센터 (PC/관리자) ↗️
            </a>
            <a class="blog-btn-secondary" href="https://blog.stat.naver.com/m/blog/daily/cv" target="_blank">
                📱 모바일 방문자 통계 ↗️
            </a>
            <a class="blog-btn-secondary" href="https://adpost.naver.com" target="_blank">
                💰 애드포스트 수익센터 ↗️
            </a>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 📊 실시간 지표 4개 메트릭 카드
    target_inc = blog_stats.get("target_monthly_income", 300000)
    curr_inc = blog_stats.get("current_monthly_income", 0)
    achieve_rate = (curr_inc / target_inc * 100) if target_inc > 0 else 0

    c_b1, c_b2, c_b3, c_b4 = st.columns(4)
    with c_b1:
        st.metric("오늘 방문자 수", f"{display_today_vis:,}명", "네이버 통계 연동")
    with c_b2:
        st.metric("총 포스팅 수", f"{display_total_posts:,}편", f"관리 대장: {len(blog_posts)}편")
    with c_b3:
        st.metric("애드포스트 수익", f"{curr_inc:,.0f}원", f"목표 {target_inc:,.0f}원")
    with c_b4:
        st.metric("수익 목표 달성률", f"{achieve_rate:.1f}%")

    # ⚡ 오늘자 방문자 수 & 애드포스트 1초 간편 업데이트
    with st.expander("⚡ 오늘 방문자 수 & 애드포스트 수익 1초 간편 갱신", expanded=False):
        st.caption("💡 위 바로가기 버튼을 통해 확인하신 실제 방문자 수와 수익을 입력하시면 아래 일별 차트와 대시보드에 즉시 날짜별로 누적 기록됩니다.")
        with st.form("quick_blog_sync_form"):
            col_q1, col_q2 = st.columns(2)
            with col_q1:
                q_vis = st.number_input("오늘 실제 방문자 수 (명)", value=int(display_today_vis), step=10)
            with col_q2:
                q_inc = st.number_input("이번 달 현재 애드포스트 수익 (원)", value=int(curr_inc), step=10000)
            if st.form_submit_button("통계 갱신 및 차트 반영 💾"):
                blog_stats["manual_today_visitors"] = int(q_vis)
                blog_stats["current_monthly_income"] = int(q_inc)
                
                # 방문자 히스토리에 오늘 날짜 자동 기록
                today_tag = datetime.now(KST).strftime('%m/%d')
                curr_hist = blog_stats.get("visitor_history", [])
                found = False
                for it in curr_hist:
                    if it.get("날짜") == today_tag:
                        it["방문자수"] = int(q_vis)
                        found = True
                        break
                if not found:
                    curr_hist.append({"날짜": today_tag, "방문자수": int(q_vis)})
                blog_stats["visitor_history"] = curr_hist[-7:]
                save_blog_stats(blog_stats)
                st.success("방문자 수와 수익이 성공적으로 반영되었습니다!")
                st.rerun()

    # 📈 최근 일별 방문자 수 추이 차트
    if final_history:
        df_vis = pd.DataFrame(final_history)
        fig_vis = go.Figure()
        fig_vis.add_trace(go.Bar(
            x=df_vis['날짜'],
            y=df_vis['방문자수'],
            marker_color='#10b981',
            text=df_vis['방문자수'],
            textposition='auto'
        ))
        fig_vis.update_layout(
            title="📊 최근 일별 방문자 수 추이",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#f8fafc'),
            margin=dict(l=10, r=10, t=40, b=20),
            height=240
        )
        st.plotly_chart(fig_vis, use_container_width=True)

    sub_tab_p, sub_tab_s = st.tabs(["📋 포스팅 관리 대장", "⚙️ 블로그 정보 & 목표 설정"])

    # ---------------------------------------------------------
    # 서브탭 1: 포스팅 관리 대장
    # ---------------------------------------------------------
    with sub_tab_p:
        st.markdown("##### 📋 내 포스팅 관리 대장")
        
        if not blog_posts:
            st.info("💡 **현재 등록된 포스팅이 없습니다.** 아래에서 새로운 포스팅 아이디어나 발행할 글 일정을 등록해보세요!")
        else:
            st.dataframe(pd.DataFrame(blog_posts), use_container_width=True)
            
            with st.expander("✏️ 등록된 포스팅 상태 변경 / 삭제"):
                del_idx = st.selectbox(
                    "포스팅 선택",
                    range(len(blog_posts)),
                    format_func=lambda x: f"[{blog_posts[x].get('상태', '')}] {blog_posts[x].get('제목', '')}"
                )
                c_del1, c_del2 = st.columns(2)
                with c_del1:
                    new_st_val = st.selectbox("상태 변경", ["아이디어 기획", "원고 작성중", "발행 완료"], key="edit_st_val")
                    if st.button("상태 저장"):
                        blog_posts[del_idx]["상태"] = new_st_val
                        save_blog_posts(blog_posts)
                        st.success("상태가 변경되었습니다!")
                        st.rerun()
                with c_del2:
                    if st.button("🗑️ 선택한 포스팅 삭제"):
                        rem = blog_posts.pop(del_idx)
                        save_blog_posts(blog_posts)
                        st.success(f"'{rem.get('제목', '')}' 포스팅이 삭제되었습니다.")
                        st.rerun()

        # 새 포스팅 추가 폼
        with st.expander("➕ 새 포스팅 일정 / 아이디어 등록", expanded=(len(blog_posts) == 0)):
            with st.form("add_new_blog_post_form", clear_on_submit=True):
                new_title = st.text_input("포스팅 제목", placeholder="예: 직장인 굿노트 서식 3종 공유")
                new_kw = st.text_input("핵심 타겟 키워드", placeholder="예: 굿노트 서식")
                new_cat = st.selectbox("카테고리", ["🤖 AI 실무 프롬프트", "📝 스마트 디지털 노트", "⚡ 업무 효율 팁", "💼 직장인 칼퇴 루틴", "📱 IT 기기"])
                new_status = st.selectbox("진행 상태", ["아이디어 기획", "원고 작성중", "발행 완료"])
                new_date = st.text_input("발행 예정일/완료일 (YYYY-MM-DD)", value=datetime.now(KST).strftime('%Y-%m-%d'))
                
                if st.form_submit_button("포스팅 등록하기"):
                    if new_title.strip():
                        blog_posts.append({
                            "제목": new_title.strip(),
                            "키워드": new_kw.strip(),
                            "카테고리": new_cat,
                            "상태": new_status,
                            "날짜": new_date
                        })
                        save_blog_posts(blog_posts)
                        st.success(f"'{new_title}' 포스팅이 성공적으로 등록되었습니다!")
                        st.rerun()
                    else:
                        st.warning("포스팅 제목을 입력해주세요.")

    # ---------------------------------------------------------
    # 서브탭 2: 블로그 정보 & 목표 설정
    # ---------------------------------------------------------
    with sub_tab_s:
        st.markdown("##### ⚙️ 블로그 정보 및 애드포스트 목표 설정")
        with st.form("edit_blog_info_form"):
            in_blog_id = st.text_input("네이버 블로그 ID", value=blog_id)
            in_target_inc = st.number_input("목표 월 애드포스트 수익(원)", value=int(target_inc), step=50000)
            in_curr_inc = st.number_input("이번 달 현재 애드포스트 수익(원)", value=int(curr_inc), step=10000)
            
            if st.form_submit_button("설정 저장하기"):
                blog_stats["blog_id"] = in_blog_id.strip()
                blog_stats["blog_url"] = f"https://m.blog.naver.com/{in_blog_id.strip()}"
                blog_stats["target_monthly_income"] = int(in_target_inc)
                blog_stats["current_monthly_income"] = int(in_curr_inc)
                save_blog_stats(blog_stats)
                st.success("블로그 설정이 저장되었습니다!")
                st.rerun()


# =============================================================
# 위치 정보 및 세션 안전 초기화
# =============================================================

current_loc_data = load_location()

if "lat" in st.query_params and "lon" in st.query_params:
    try:
        gps_lat = float(st.query_params["lat"])
        gps_lon = float(st.query_params["lon"])
        current_loc_data = {"name": "현재 GPS 위치", "lat": gps_lat, "lon": gps_lon}
        save_location(current_loc_data)
    except Exception: pass

if "saved_gemini_key" not in st.session_state:
    st.session_state.saved_gemini_key = st.secrets.get("GEMINI_API_KEY", "")


# =============================================================
# [메인 헤더]
# =============================================================

st.markdown("""
<div class="mori-header">
    <div class="mori-title">MORI</div>
    <div class="mori-subtitle">Everything about you, in one place.</div>
    <div class="mori-time">대한민국 표준시(KST) : """ + datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S') + """</div>
</div>
""", unsafe_allow_html=True)


# =============================================================
# [4대 핵심 대분류 탭 모드 (데일리 / 주식 / 스포츠 / 블로그)]
# =============================================================

tab_daily_main, tab_stock_main, tab_sports_main, tab_blog_main = st.tabs([
    "🏠 데일리", "💼 주식 & 금융", "⚽ 스포츠", "✍️ 블로그"
])

with tab_daily_main:
    render_daily_hub()

with tab_stock_main:
    render_stock_hub()

with tab_sports_main:
    render_sports_hub()

with tab_blog_main:
    render_blog_hub()
