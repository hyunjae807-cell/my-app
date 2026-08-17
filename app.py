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

# 3. 프리미엄 미니멀 MORI 앱 아이콘 생성
def get_mori_app_icon():
    size = 256
    img = Image.new("RGBA", (size, size), (255, 255, 255, 0))
    mask = Image.new("L", (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle([(0, 0), (size, size)], radius=56, fill=255)

    base = Image.new("RGBA", (size, size), (11, 15, 25, 255))
    base_draw = ImageDraw.Draw(base)
    
    points = [(65, 180), (65, 90), (128, 145), (191, 90), (191, 180)]
    for i in range(len(points)-1):
        base_draw.line([points[i], points[i+1]], fill=(255, 255, 255, 255), width=16)

    icon_img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    icon_img.paste(base, (0, 0), mask=mask)
    return icon_img

mori_icon_image = get_mori_app_icon()

# 4. 페이지 설정
st.set_page_config(
    page_title="MORI",
    page_icon=mori_icon_image,
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 5. [최고급 모던 핀테크 & 네이버 감성 프리미엄 CSS] - 상단 짤림 완벽 해결 및 정교한 벤토 그리드
st.markdown("""
<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css');

:root {
    --bg-dark: #0b0f19;
    --card-bg: #131b2e;
    --card-border: rgba(255, 255, 255, 0.08);
    --card-hover: rgba(255, 255, 255, 0.12);
    --accent-blue: #3b82f6;
    --accent-green: #10b981;
    --accent-red: #ef4444;
    --text-primary: #f8fafc;
    --text-secondary: #94a3b8;
    --text-muted: #64748b;
}

* {
    font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif !important;
    letter-spacing: -0.02em !important;
}

/* 상단 짤림 방지 및 모바일 여백 정밀 조정 */
.block-container {
    padding-top: 4.2rem !important;
    padding-bottom: 3.5rem !important;
    padding-left: 1rem !important;
    padding-right: 1rem !important;
    max-width: 1200px !important;
    margin: 0 auto !important;
}

/* 상단 네비게이션 헤더 바 */
.mori-navbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 6px 0 16px 0;
    margin-bottom: 12px;
    border-bottom: 1px solid var(--card-border);
}
.mori-brand-box {
    display: flex;
    align-items: baseline;
    gap: 8px;
}
.mori-logo {
    font-size: 28px !important;
    font-weight: 900 !important;
    color: var(--text-primary);
    letter-spacing: -0.04em !important;
}
.mori-desc {
    font-size: 13px !important;
    color: var(--text-muted);
    font-weight: 600;
}
.mori-badge-time {
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid var(--card-border);
    padding: 6px 12px;
    border-radius: 20px;
    font-size: 12px !important;
    font-weight: 700;
    color: var(--text-secondary);
}

/* 상단 4단 위젯 스트립 (네이버/토스 스타일) */
.widget-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 10px;
    margin-bottom: 20px;
}
@media (max-width: 768px) {
    .widget-grid {
        grid-template-columns: repeat(2, 1fr);
    }
}
.widget-card {
    background: var(--card-bg);
    border: 1px solid var(--card-border);
    border-radius: 16px;
    padding: 14px 16px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    min-height: 84px;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
    transition: transform 0.2s ease, border-color 0.2s ease;
}
.widget-card:hover {
    border-color: rgba(96, 165, 250, 0.3);
    transform: translateY(-2px);
}
.widget-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 12px;
    font-weight: 600;
    color: var(--text-muted);
}
.widget-main {
    font-size: 19px;
    font-weight: 900;
    color: var(--text-primary);
    margin: 4px 0 2px 0;
    line-height: 1.2;
}
.widget-footer {
    font-size: 12px;
    font-weight: 700;
}
.pill-up {
    color: #f87171;
    display: inline-flex;
    align-items: center;
    gap: 2px;
}
.pill-down {
    color: #60a5fa;
    display: inline-flex;
    align-items: center;
    gap: 2px;
}

/* 메인 카드 스타일 */
.bento-card {
    background: var(--card-bg);
    border: 1px solid var(--card-border);
    border-radius: 20px;
    padding: 22px;
    margin-bottom: 16px;
    color: var(--text-primary);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.25);
}
.bento-title {
    font-size: 18px;
    font-weight: 800;
    color: var(--text-primary);
    margin-bottom: 14px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

/* 버튼 스타일 */
.btn-action-primary {
    display: inline-block;
    background: #2563eb;
    color: #ffffff !important;
    text-decoration: none;
    font-weight: 700;
    padding: 9px 18px;
    border-radius: 12px;
    font-size: 14px;
    border: none;
    box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
    transition: all 0.2s ease;
}
.btn-action-primary:hover {
    background: #1d4ed8;
    transform: translateY(-1px);
}
.btn-action-secondary {
    display: inline-block;
    background: rgba(255, 255, 255, 0.06);
    color: #e2e8f0 !important;
    text-decoration: none;
    font-weight: 600;
    padding: 9px 16px;
    border-radius: 12px;
    font-size: 14px;
    border: 1px solid rgba(255, 255, 255, 0.1);
    transition: all 0.2s ease;
}
.btn-action-secondary:hover {
    background: rgba(255, 255, 255, 0.12);
    border-color: rgba(255, 255, 255, 0.2);
}

/* 뉴스 피드 아이템 */
.news-row {
    background: rgba(255, 255, 255, 0.02);
    border: 1px solid var(--card-border);
    border-radius: 14px;
    padding: 14px 18px;
    margin-bottom: 10px;
    transition: all 0.2s ease;
}
.news-row:hover {
    background: rgba(255, 255, 255, 0.05);
    border-color: rgba(96, 165, 250, 0.3);
}
.news-heading {
    font-size: 16px !important;
    font-weight: 700 !important;
    color: var(--text-primary);
    text-decoration: none;
    line-height: 1.45;
    display: block;
}
.news-heading:hover {
    color: #60a5fa;
}
.news-info {
    font-size: 12px !important;
    color: var(--text-muted);
    margin-top: 6px;
}

/* 세그먼트 탭 스타일 */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
    background: rgba(255, 255, 255, 0.03);
    padding: 4px;
    border-radius: 14px;
    border: 1px solid var(--card-border);
    margin-bottom: 16px;
}
.stTabs [data-baseweb="tab"] {
    height: 40px !important;
    border-radius: 10px;
    padding: 6px 18px !important;
    font-size: 15px !important;
    font-weight: 700 !important;
    color: var(--text-secondary);
    background: transparent;
    border: none;
    transition: all 0.2s ease;
}
.stTabs [aria-selected="true"] {
    background: #2563eb !important;
    color: #ffffff !important;
    box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
}

/* 메트릭 스타일 */
[data-testid="stMetricValue"] {
    font-size: 26px !important;
    font-weight: 900 !important;
    letter-spacing: -0.03em !important;
    color: #f8fafc !important;
}
[data-testid="stMetricLabel"] {
    font-size: 13px !important;
    font-weight: 600 !important;
    color: #94a3b8 !important;
}

button {
    font-size: 15px !important;
    font-weight: 700 !important;
    border-radius: 12px !important;
}
input, select, textarea {
    font-size: 15px !important;
    border-radius: 10px !important;
}
</style>
""", unsafe_allow_html=True)

# 6. 영구 저장소 파일 관리
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
    {"종목": "축구", "팀명": "맨체스터 유나이티드", "리그": "프리미어리그 (EPL)", "키워드": "맨체스터 유나이티드 OR 맨유"},
    {"종목": "야구", "팀명": "KIA 타이거즈", "리그": "KBO 리그", "키워드": "KIA 타이거즈"},
    {"종목": "야구", "팀명": "LA 다저스", "리그": "메이저리그 (MLB)", "키워드": "LA 다저스 OR 오타니"}
]

DEFAULT_SUBSCRIPTIONS = [
    {"서비스": "SPOTV NOW", "월요금": 19900, "결제일": 15, "카테고리": "스포츠"},
    {"서비스": "넷플릭스 (Netflix)", "월요금": 17000, "결제일": 22, "카테고리": "OTT"},
    {"서비스": "쿠팡 와우멤버십", "월요금": 7890, "결제일": 8, "카테고리": "쇼핑·OTT"},
    {"서비스": "Spotify (스포티파이)", "월요금": 11990, "결제일": 1, "카테고리": "음악"}
]

DEFAULT_BLOG_STATS = {
    "blog_url": "https://m.blog.naver.com/early_leave_lab",
    "blog_id": "early_leave_lab",
    "blog_name": "칼퇴연구소 | 테크·생산성 랩",
    "blog_slogan": "반복되는 야근을 줄이고 일상을 되찾는 생산성 솔루션",
    "target_monthly_income": 300000,
    "current_monthly_income": 0,
    "manual_today_visitors": 0,
    "visitor_history": []
}

DEFAULT_BLOG_POSTS = []

DEFAULT_LOCATION = {
    "name": "용인시",
    "lat": 37.2410,
    "lon": 127.1775
}

LOCATION_PRESETS = {
    "경기도 용인시": {"lat": 37.2410, "lon": 127.1775, "name": "용인시"},
    "경기도 성남시 (분당/판교)": {"lat": 37.4200, "lon": 127.1265, "name": "성남시"},
    "서울특별시 강남구": {"lat": 37.4979, "lon": 127.0276, "name": "서울 강남"},
    "서울특별시 종로/중구": {"lat": 37.5636, "lon": 126.9976, "name": "서울 종로"},
    "인천광역시": {"lat": 37.4563, "lon": 126.7052, "name": "인천"},
    "부산광역시": {"lat": 35.1796, "lon": 129.0756, "name": "부산"},
    "대전광역시": {"lat": 36.3504, "lon": 127.3845, "name": "대전"},
    "대구광역시": {"lat": 35.8714, "lon": 128.6014, "name": "대구"},
    "광주광역시": {"lat": 35.1595, "lon": 126.8526, "name": "광주"}
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
    return ["주요 증시 캘린더 확인", "응원팀 경기 일정 체크"]

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

# 7. 네이버 블로그 방문자 수 및 RSS 조회
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
def get_current_weather(lat=37.2410, lon=127.1775, default_name="용인시"):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m&timezone=auto"
        res = requests.get(url, timeout=3).json()
        current = res.get("current", {})
        temp = current.get("temperature_2m", 26.2)
        humidity = current.get("relative_humidity_2m", 82)
        code = current.get("weather_code", 0)
        
        weather_desc = "맑음"
        if code in (1, 2): weather_desc = "구름 조금"
        elif code == 3: weather_desc = "흐림"
        elif code in (51, 53, 55, 61, 63, 65, 80, 81, 82): weather_desc = "비"
        elif code in (71, 73, 75, 85, 86): weather_desc = "눈"
        
        return f"{temp:.1f}°C", weather_desc, f"{humidity}%", default_name
    except Exception:
        return "26.2°C", "구름 조금", "82%", default_name

# 9. 초고속 pykrx + yfinance 하이브리드 엔진
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

# 10. AI 호출 엔진
def call_gemini_api(prompt_text, api_key, system_instruction=None, image_bytes=None, chat_contents=None):
    if not api_key or not api_key.strip():
        return None, "Gemini API Key를 입력해 주세요."
    
    clean_key = api_key.strip()
    headers = {"Content-Type": "application/json"}
    
    candidate_models = ["gemini-1.5-flash", "gemini-1.5-flash-latest", "gemini-2.0-flash", "gemini-pro"]

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
    오늘자 실시간 주요 금융/경제 뉴스 헤드라인과 투자자의 보유 포트폴리오를 바탕으로, 불필요한 미사여구 없이 간결하고 명확한 [모닝 증시 브리핑]을 작성해주세요.

    [투자자 보유 종목]
    {stock_list_str}

    [오늘의 실시간 주요 뉴스 헤드라인]
    {news_text}

    [작성 가이드라인]
    1. 글로벌 & 국내 증시 핵심 요약 (3줄)
    2. 보유 종목 영향 및 시사점 (KODEX AI반도체, 커버드콜 맞춤 분석)
    3. 금일 투자 전략 및 체크포인트

    이모지는 배제하고, 가독성 높은 마크다운 형식으로 작성해주세요.
    """
    return call_gemini_api(prompt, api_key)

def generate_team_briefing(team_name, sports_type, league, team_news, api_key):
    news_text = "\n".join([f"- {h['title']} ({h.get('source', '')})" for h in team_news[:10]]) if team_news else f"{team_name} 최신 경기 일정"
    
    prompt = f"""
    당신은 스포츠 전문 분석가 AI입니다.
    현재 시점(2026년 8월)을 기준으로 [{sports_type} - {team_name} ({league})] 구단의 최신 경기 일정, 최근 경기 결과, 핵심 이슈를 간결하게 정리해주세요.

    [규칙]
    - 모든 경기 일정 및 시간은 대한민국 표준시 (한국 시간, KST) 기준으로 표기해주세요.
    - 불필요한 이모지를 남발하지 말고, 군더더기 없는 문장으로 요약해주세요.

    [최신 뉴스 데이터]
    {news_text}

    [작성 항목]
    1. 다음 경기 일정: (상대팀, 한국 시간 KST, 홈/원정)
    2. 최근 경기 결과: (스코어, 주요 기록)
    3. 구단 핵심 이슈: (부상자, 주요 라인업 3줄 요약)
    """
    text, status = call_gemini_api(prompt, api_key)
    return text if status == "SUCCESS" else None

def ask_gemini_chat(chat_history, user_msg, portfolio_items, api_key):
    stock_list_str = ", ".join([f"{item['종목명']} ({item['티커']})" for item in portfolio_items]) if portfolio_items else "KODEX AI반도체TOP2플러스, KODEX 200타겟위클리커버드콜"
    system_inst = f"당신은 투자자의 1:1 금융/자산 분석 비서 AI 'MORI'입니다. 투자자가 보유한 포트폴리오는 [{stock_list_str}] 입니다. 이모지를 최소화하고 전문적이며 명확하게 답변하세요."

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
    return f"AI 응답 오류: {text if text else status}"


# =============================================================
# ⭐ [4대 핵심 대분류 렌더링 모듈 - 벤토 그리드 모던 UI]
# =============================================================

# -------------------------------------------------------------
# 1. [데일리 허브 모듈]
# -------------------------------------------------------------
def render_daily_hub():
    sub_d1, sub_d2, sub_d3, sub_d4 = st.tabs(["오늘 요약", "통합 캘린더", "고정 구독료", "할 일 관리"])

    with sub_d1:
        temp_val, weather_val, humid_val, loc_tag = get_current_weather(
            current_loc_data.get("lat", 37.2410),
            current_loc_data.get("lon", 127.1775),
            current_loc_data.get("name", "용인시")
        )

        with st.container(border=True):
            st.markdown(f"**{loc_tag} 실시간 날씨** : {weather_val} **{temp_val}** (습도 {humid_val})")

        with st.container(border=True):
            st.markdown("**8월 주요 일정 및 D-Day**")
            cal_summary_events = [
                {"날짜": "8월 22일(토)", "구분": "OTT", "내용": "넷플릭스 결제일 (17,000원)", "D-Day": "D-6"},
                {"날짜": "8월 23일(일)", "구분": "어학", "내용": "오픽(OPIc) 성적 발표 13:00", "D-Day": "D-7"},
                {"날짜": "8월 26일(수)", "구분": "반도체", "내용": "엔비디아(NVDA) 실적 발표", "D-Day": "D-10"},
                {"날짜": "8월 28일(금)", "구분": "경제", "내용": "미국 잭슨홀 심포지엄 (파월 연설)", "D-Day": "D-12"},
                {"날짜": "9월 01일(화)", "구분": "배당", "내용": "KODEX 커버드콜 월 분배금 입금", "D-Day": "D-16"}
            ]
            st.dataframe(pd.DataFrame(cal_summary_events), use_container_width=True)

        home_todos = load_todos()
        with st.container(border=True):
            st.markdown("**오늘의 할 일**")
            if home_todos:
                for t in home_todos[:3]:
                    st.markdown(f"• {t}")
            else:
                st.caption("등록된 할 일이 없습니다.")

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
            st.markdown("**내 포트폴리오 요약**")
            ch1, ch2 = st.columns(2)
            with ch1: st.metric("총 평가금액", f"{total_eval_h:,.0f}원", f"{rate_h:+.2f}%")
            with ch2: st.metric("총 평가손익", f"{diff_h:+,.0f}원")

    with sub_d2:
        user_portfolio = load_portfolio()
        cover_shares = 863
        for p in user_portfolio:
            if "커버드콜" in p["종목명"]: cover_shares = p["보유수량"]
        monthly_est_div = cover_shares * 270

        with st.container(border=True):
            st.markdown(f"**월 배당(분배금) 예상 수령액** : **{monthly_est_div:,.0f}원** (KODEX 200위클리커버드콜 {cover_shares:,}주 기준)")

        timeline_events = [
            {"날짜": "8월 22일(토)", "구분": "구독 결제", "내용": "넷플릭스 (17,000원) 결제일 (D-6)"},
            {"날짜": "8월 23일(일)", "구분": "어학 시험", "내용": "오픽(OPIc) 성적 발표 13:00 (D-7)"},
            {"날짜": "8월 26일(수)", "구분": "실적 발표", "내용": "엔비디아(NVDA) 2분기 실적 발표 (D-10)"},
            {"날짜": "8월 28일(금)", "구분": "거시경제", "내용": "미국 잭슨홀 심포지엄 (파월 연설)"},
            {"날짜": "9월 01일(화)", "구분": "배당 입금", "내용": "KODEX 커버드콜 월 분배금 입금 예정일"},
            {"날짜": "9월 01일(화)", "구분": "구독 결제", "내용": "Spotify (11,990원) 결제일"},
            {"날짜": "9월 08일(화)", "구분": "구독 결제", "내용": "쿠팡 와우멤버십 (7,890원) 결제일"},
            {"날짜": "9월 10일(목)", "구분": "파생만기", "내용": "국내 선물·옵션 동시 만기일"},
            {"날짜": "9월 15일(화)", "구분": "구독 결제", "내용": "SPOTV NOW (19,900원) 결제일"},
            {"날짜": "9월 16일(수)", "구분": "거시경제", "내용": "미국 9월 FOMC 기준금리 결정 회의"}
        ]
        st.dataframe(pd.DataFrame(timeline_events), use_container_width=True)

    with sub_d3:
        subs_list = load_subscriptions()
        total_sub_monthly = sum(s["월요금"] for s in subs_list)
        monthly_est_div = 863 * 270
        coverage_rate = (monthly_est_div / total_sub_monthly * 100) if total_sub_monthly > 0 else 0

        c_s1, c_s2 = st.columns(2)
        with c_s1: st.metric("월 고정 구독료", f"{total_sub_monthly:,.0f}원", f"총 {len(subs_list)}개 서비스")
        with c_s2: st.metric("배당금 방어율", f"{coverage_rate:.1f}%", f"월 배당 {monthly_est_div:,.0f}원")

        for s in subs_list:
            col_name, col_cost, col_dday = st.columns([0.5, 0.25, 0.25])
            with col_name: st.markdown(f"**{s['서비스']}** ({s['카테고리']})")
            with col_cost: st.markdown(f"{s['월요금']:,}원 / 월")
            with col_dday: st.markdown(f"매월 **{s['결제일']}일**")

        with st.expander("구독 서비스 추가"):
            with st.form("add_sub_form"):
                new_s_name = st.text_input("서비스명", value="유튜브 프리미엄")
                new_s_cost = st.number_input("월 구독료(원)", value=14900, step=1000)
                new_s_day = st.number_input("결제일 (1~31일)", value=1, min_value=1, max_value=31)
                new_s_cat = st.selectbox("카테고리", ["OTT·영상", "스포츠", "음악", "생산성", "쇼핑·기타"])
                if st.form_submit_button("등록"):
                    if new_s_name.strip():
                        subs_list.append({"서비스": new_s_name.strip(), "월요금": int(new_s_cost), "결제일": int(new_s_day), "카테고리": new_s_cat})
                        save_subscriptions(subs_list)
                        st.success("등록 완료되었습니다.")
                        st.rerun()

    with sub_d4:
        with st.expander("날씨 지역 설정"):
            preset_names = list(LOCATION_PRESETS.keys())
            sel_preset = st.selectbox("지역 선택", preset_names, index=0)
            if st.button("지역 저장"):
                chosen = LOCATION_PRESETS[sel_preset]
                save_location(chosen)
                st.success("저장되었습니다.")
                st.rerun()

        st.markdown("##### 할 일 목록 (To-Do)")
        current_todos = load_todos()
        to_delete = None
        for idx, todo_item in enumerate(current_todos):
            col_t1, col_t2 = st.columns([0.85, 0.15])
            with col_t1: st.write(f"• {todo_item}")
            with col_t2:
                if st.button("완료", key=f"del_d_{idx}"): to_delete = idx
        if to_delete is not None:
            current_todos.pop(to_delete)
            save_todos(current_todos)
            st.rerun()

        with st.form("new_todo_form"):
            new_todo = st.text_input("새로운 할 일 입력")
            if st.form_submit_button("추가"):
                if new_todo.strip():
                    current_todos.append(new_todo.strip())
                    save_todos(current_todos)
                    st.rerun()

# -------------------------------------------------------------
# 2. [주식 & 금융 허브 모듈]
# -------------------------------------------------------------
def render_stock_hub():
    sub_s1, sub_s2, sub_s3, sub_s4, sub_s5 = st.tabs([
        "내 포트폴리오", "실시간 시황", "맞춤 뉴스", "모닝 브리핑", "AI 투자 비서"
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
        with c2: st.metric("총 평가손익", f"{total_profit_krw:+,.0f}원", f"매입원금: {total_buy_krw:,.0f}원")

        st.dataframe(pd.DataFrame(calculated_rows), use_container_width=True)

        with st.expander("잔고 캡처 이미지로 포트폴리오 업데이트"):
            uploaded_file = st.file_uploader("증권사 잔고 캡처 업로드", type=["png", "jpg", "jpeg"])
            if uploaded_file and st.button("AI 분석 및 저장"):
                if not st.session_state.saved_gemini_key:
                    st.warning("Gemini API Key가 필요합니다.")
                else:
                    parsed, status = analyze_portfolio_image(uploaded_file.getvalue(), st.session_state.saved_gemini_key)
                    if status == "SUCCESS" and parsed:
                        save_portfolio(parsed)
                        st.success("포트폴리오가 업데이트되었습니다.")
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
            ["[전체] 내 보유 종목 뉴스"] +
            [f"{name}" for name in my_stock_names] +
            ["국내 증시", "미국 증시", "AI·반도체", "직접 검색"]
        )
        selected_cat = st.selectbox("뉴스 카테고리", category_options, index=0)
        
        if selected_cat == "직접 검색":
            query = st.text_input("검색어 입력", value="삼성전자")
        elif selected_cat == "[전체] 내 보유 종목 뉴스":
            query = " OR ".join([f'"{name}"' for name in my_stock_names]) + " OR AI반도체 OR 커버드콜"
        elif selected_cat in my_stock_names:
            query = f'"{selected_cat}"' if "반도체" not in selected_cat else f'"{selected_cat}" OR AI반도체'
        elif selected_cat == "국내 증시":
            query = "코스피 OR 코스닥 OR 환율"
        elif selected_cat == "미국 증시":
            query = "뉴욕증시 OR S&P500 OR 나스닥 OR 엔비디아"
        elif selected_cat == "AI·반도체":
            query = "엔비디아 OR 반도체 HBM OR 인공지능 AI"
        else:
            query = "코스피"

        if query:
            news_list = fetch_news_feed(query, max_results=8)
            for item in news_list:
                st.markdown(f"""
                <div class="news-row">
                    <a class="news-heading" href="{item['link']}" target="_blank">{item['title']}</a>
                    <div class="news-info">{item['source']} | {item['date']}</div>
                </div>
                """, unsafe_allow_html=True)

    with sub_s4:
        user_portfolio = load_portfolio()
        recent_news = fetch_news_feed("코스피 OR 반도체 OR 연준 금리 OR 엔비디아", max_results=12)
        k_input_b = st.text_input("Gemini API Key", value=st.session_state.saved_gemini_key, type="password", key="brief_k_in")
        if k_input_b: st.session_state.saved_gemini_key = k_input_b
        
        c_b1, c_b2 = st.columns(2)
        with c_b1:
            if st.button("오늘자 AI 브리핑 생성", key="btn_b_re"):
                if not st.session_state.saved_gemini_key:
                    st.warning("API Key를 입력해주세요.")
                else:
                    with st.spinner("증시 브리핑 작성 중..."):
                        b_res, status = generate_ai_briefing(recent_news, user_portfolio, st.session_state.saved_gemini_key)
                        if status == "SUCCESS" and b_res:
                            save_briefing(b_res, datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S'))
                            st.rerun()
        saved_b, saved_t = load_briefing()
        with c_b2:
            if saved_b:
                clean_speech = saved_b.replace("#", "").replace("*", "").replace("\n", " ").replace('"', '')[:300]
                tts_html = f"""
                <button onclick="window.speechSynthesis.speak(new SpeechSynthesisUtterance('{clean_speech}'))" style="background-color: #334155; color: white; border: none; padding: 9px 16px; border-radius: 10px; font-weight: 700; cursor: pointer; width: 100%;">
                    음성 듣기 (TTS)
                </button>
                """
                components.html(tts_html, height=42)
        if saved_b:
            st.caption(f"생성 시각: {saved_t}")
            st.markdown(saved_b)

    with sub_s5:
        if "chat_messages" not in st.session_state:
            st.session_state.chat_messages = [{"role": "assistant", "content": "보유 포트폴리오를 기반으로 전문적인 금융·투자 분석을 제공해 드립니다."}]
        for msg in st.session_state.chat_messages:
            with st.chat_message(msg["role"]): st.markdown(msg["content"])
        with st.form("chat_form_s", clear_on_submit=True):
            col_ci1, col_ci2 = st.columns([0.82, 0.18])
            with col_ci1: user_input = st.text_input("질문", placeholder="질문을 입력하세요...", label_visibility="collapsed")
            with col_ci2: send_btn = st.form_submit_button("전송", use_container_width=True)
        if send_btn and user_input.strip():
            u_text = user_input.strip()
            st.session_state.chat_messages.append({"role": "user", "content": u_text})
            if st.session_state.saved_gemini_key:
                with st.spinner("분석 중..."):
                    reply = ask_gemini_chat(st.session_state.chat_messages, u_text, load_portfolio(), st.session_state.saved_gemini_key)
                    st.session_state.chat_messages.append({"role": "assistant", "content": reply})
                    st.rerun()

# -------------------------------------------------------------
# 3. [스포츠 허브 모듈]
# -------------------------------------------------------------
def render_sports_hub():
    my_teams = load_sports_teams()
    sports_briefings = load_sports_briefings()

    team_names = [f"{t['팀명']} ({t['리그']})" for t in my_teams]
    selected_team_idx = st.selectbox("응원팀 선택", range(len(team_names)), format_func=lambda x: team_names[x], key="sp_sel_main")
    
    current_team = my_teams[selected_team_idx]
    team_key = current_team["팀명"]

    search_query = f'"{current_team["팀명"]}" AND (경기 OR 일정 OR 결과 OR 승리 OR 패배 OR 하이라이트)'
    team_news = fetch_news_feed(search_query, max_results=8)

    c_s1, c_s2 = st.columns([0.7, 0.3])
    with c_s1: st.markdown(f"#### {current_team['팀명']} ({current_team['리그']})")
    with c_s2:
        if st.button("구단 브리핑 생성", key=f"btn_sb_m_{team_key}"):
            if not st.session_state.saved_gemini_key:
                st.warning("Gemini API Key가 필요합니다.")
            else:
                with st.spinner(f"{team_key} 분석 중..."):
                    b_txt = generate_team_briefing(current_team['팀명'], current_team['종목'], current_team['리그'], team_news, st.session_state.saved_gemini_key)
                    if b_txt:
                        sports_briefings[team_key] = {"text": b_txt, "updated_at": datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S')}
                        save_sports_briefings(sports_briefings)
                        st.rerun()

    if team_key in sports_briefings:
        b_data = sports_briefings[team_key]
        st.caption(f"업데이트: {b_data.get('updated_at', '')} (한국 시간 KST 기준)")
        st.markdown(b_data.get("text", ""))

    st.markdown("---")
    st.markdown(f"**{current_team['팀명']} 실시간 뉴스**")
    for n in team_news:
        st.markdown(f"""
        <div class="news-row">
            <a class="news-heading" href="{n['link']}" target="_blank">{n['title']}</a>
            <div class="news-info">{n['source']} | {n['date']}</div>
        </div>
        """, unsafe_allow_html=True)

    with st.expander("응원팀 순서 및 목록 설정"):
        for idx, t in enumerate(my_teams):
            col_t_name, col_up, col_down = st.columns([0.6, 0.2, 0.2])
            with col_t_name: st.markdown(f"**{idx+1}위**: {t['팀명']} ({t['리그']})")
            with col_up:
                if idx > 0 and st.button("위로", key=f"u_{idx}"):
                    my_teams[idx], my_teams[idx-1] = my_teams[idx-1], my_teams[idx]
                    save_sports_teams(my_teams); st.rerun()
            with col_down:
                if idx < len(my_teams)-1 and st.button("아래로", key=f"d_{idx}"):
                    my_teams[idx], my_teams[idx+1] = my_teams[idx+1], my_teams[idx]
                    save_sports_teams(my_teams); st.rerun()

# -------------------------------------------------------------
# 4. [블로그 관리 모듈 - 정교한 벤토 그리드]
# -------------------------------------------------------------
def render_blog_hub():
    blog_stats = load_blog_stats()
    blog_posts = load_blog_posts()
    blog_id = blog_stats.get("blog_id", "early_leave_lab")

    live_data = fetch_naver_blog_live_data(blog_id)
    today_visitors_live = live_data.get("today_visitors", 0)
    history_vis = live_data.get("visitor_history", [])
    total_posts_rss = live_data.get("rss_post_count", 0)

    display_today_vis = today_visitors_live if today_visitors_live > 0 else blog_stats.get("manual_today_visitors", 0)
    display_total_posts = len(blog_posts) if len(blog_posts) > 0 else total_posts_rss

    stored_hist = blog_stats.get("visitor_history", [])
    final_history = history_vis if history_vis else stored_hist

    # 메인 채널 벤토 카드
    st.markdown(f"""
    <div class="bento-card">
        <div class="bento-title">
            <span>칼퇴연구소 | 테크·생산성 랩</span>
            <span style="font-size: 13px; font-weight: 600; color: #94a3b8;">@{blog_id}</span>
        </div>
        <div style="font-size: 14px; color: #94a3b8; margin-bottom: 14px;">
            반복되는 야근을 줄이고 일상을 되찾는 실무 AI & 생산성 치트키
        </div>
        <div style="display: flex; gap: 8px; flex-wrap: wrap;">
            <a class="btn-action-primary" href="https://m.blog.naver.com/{blog_id}" target="_blank">
                블로그 바로가기 ↗
            </a>
            <a class="btn-action-secondary" href="https://admin.blog.naver.com/{blog_id}/stat/today" target="_blank">
                통계센터 (관리자)
            </a>
            <a class="btn-action-secondary" href="https://blog.stat.naver.com/m/blog/daily/cv" target="_blank">
                모바일 통계
            </a>
            <a class="btn-action-secondary" href="https://adpost.naver.com" target="_blank">
                애드포스트 센터
            </a>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 4대 핵심 지표
    target_inc = blog_stats.get("target_monthly_income", 300000)
    curr_inc = blog_stats.get("current_monthly_income", 0)
    achieve_rate = (curr_inc / target_inc * 100) if target_inc > 0 else 0

    c_b1, c_b2, c_b3, c_b4 = st.columns(4)
    with c_b1: st.metric("오늘 방문자", f"{display_today_vis:,}명")
    with c_b2: st.metric("총 포스팅", f"{display_total_posts:,}편")
    with c_b3: st.metric("애드포스트 수익", f"{curr_inc:,.0f}원")
    with c_b4: st.metric("목표 달성률", f"{achieve_rate:.1f}%", f"목표 {target_inc:,.0f}원")

    # 오늘 방문자/수익 빠른 갱신
    with st.expander("방문자 수 및 수익 갱신"):
        with st.form("quick_blog_sync_form"):
            col_q1, col_q2 = st.columns(2)
            with col_q1: q_vis = st.number_input("오늘 실제 방문자 수 (명)", value=int(display_today_vis), step=10)
            with col_q2: q_inc = st.number_input("이번 달 애드포스트 수익 (원)", value=int(curr_inc), step=10000)
            if st.form_submit_button("저장"):
                blog_stats["manual_today_visitors"] = int(q_vis)
                blog_stats["current_monthly_income"] = int(q_inc)
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
                st.success("반영되었습니다.")
                st.rerun()

    # 최근 방문자 추이 차트
    if final_history:
        df_vis = pd.DataFrame(final_history)
        fig_vis = go.Figure()
        fig_vis.add_trace(go.Bar(
            x=df_vis['날짜'],
            y=df_vis['방문자수'],
            marker=dict(
                color='#3b82f6',
                line=dict(color='#60a5fa', width=1)
            ),
            text=df_vis['방문자수'],
            textposition='auto'
        ))
        fig_vis.update_layout(
            title="일별 방문자 수 추이",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#94a3b8', family='Pretendard'),
            margin=dict(l=10, r=10, t=35, b=20),
            height=220,
            xaxis=dict(gridcolor='rgba(255,255,255,0.05)'),
            yaxis=dict(gridcolor='rgba(255,255,255,0.05)')
        )
        st.plotly_chart(fig_vis, use_container_width=True)

    sub_tab_p, sub_tab_s = st.tabs(["포스팅 관리 대장", "블로그 설정"])

    with sub_tab_p:
        if not blog_posts:
            st.info("등록된 포스팅이 없습니다.")
        else:
            st.dataframe(pd.DataFrame(blog_posts), use_container_width=True)
            
            with st.expander("상태 변경 및 삭제"):
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
                        st.success("수정되었습니다.")
                        st.rerun()
                with c_del2:
                    if st.button("선택 삭제"):
                        rem = blog_posts.pop(del_idx)
                        save_blog_posts(blog_posts)
                        st.success("삭제되었습니다.")
                        st.rerun()

        with st.expander("새 포스팅 일정 등록", expanded=(len(blog_posts) == 0)):
            with st.form("add_new_blog_post_form", clear_on_submit=True):
                new_title = st.text_input("제목", placeholder="예: 직장인을 위한 굿노트 서식 3종")
                new_kw = st.text_input("키워드", placeholder="예: 굿노트 서식")
                new_cat = st.selectbox("카테고리", ["AI 실무", "스마트 노트", "업무 효율", "직장인 루틴", "IT 기기"])
                new_status = st.selectbox("진행 상태", ["아이디어 기획", "원고 작성중", "발행 완료"])
                new_date = st.text_input("날짜 (YYYY-MM-DD)", value=datetime.now(KST).strftime('%Y-%m-%d'))
                
                if st.form_submit_button("등록"):
                    if new_title.strip():
                        blog_posts.append({
                            "제목": new_title.strip(),
                            "키워드": new_kw.strip(),
                            "카테고리": new_cat,
                            "상태": new_status,
                            "날짜": new_date
                        })
                        save_blog_posts(blog_posts)
                        st.success("등록되었습니다.")
                        st.rerun()

    with sub_tab_s:
        with st.form("edit_blog_info_form"):
            in_blog_id = st.text_input("블로그 ID", value=blog_id)
            in_target_inc = st.number_input("목표 월 수익(원)", value=int(target_inc), step=50000)
            in_curr_inc = st.number_input("이번 달 수익(원)", value=int(curr_inc), step=10000)
            
            if st.form_submit_button("설정 저장"):
                blog_stats["blog_id"] = in_blog_id.strip()
                blog_stats["blog_url"] = f"https://m.blog.naver.com/{in_blog_id.strip()}"
                blog_stats["target_monthly_income"] = int(in_target_inc)
                blog_stats["current_monthly_income"] = int(in_curr_inc)
                save_blog_stats(blog_stats)
                st.success("저장되었습니다.")
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
# [상단 헤더 네비게이션 & 4단 위젯 스트립]
# =============================================================

# 1) 헤더 바 (상단 짤림 없는 안전 여백 적용)
st.markdown("""
<div class="mori-navbar">
    <div class="mori-brand-box">
        <span class="mori-logo">MORI</span>
        <span class="mori-desc">Daily & Asset Intelligence</span>
    </div>
    <div class="mori-badge-time">""" + datetime.now(KST).strftime('%m.%d %H:%M') + """ KST</div>
</div>
""", unsafe_allow_html=True)

# 2) 네이버/토스 스타일 상단 4단 위젯 스트립
w_temp, w_desc, w_hum, w_loc = get_current_weather(
    current_loc_data.get("lat", 37.2410),
    current_loc_data.get("lon", 127.1775),
    current_loc_data.get("name", "용인시")
)
m_prices_top = get_batch_market_data(["^KS11", "^IXIC", "395160"])
kospi_val, kospi_del = m_prices_top.get("^KS11", (None, None))
nasdaq_val, nasdaq_del = m_prices_top.get("^IXIC", (None, None))

kospi_txt = f"{kospi_val:,.1f}" if kospi_val else "6,977.9"
kospi_d_txt = f"{kospi_del:+.2f}%" if kospi_del else "+2.42%"
nasdaq_txt = f"{nasdaq_val:,.1f}" if nasdaq_val else "26,729.2"
nasdaq_d_txt = f"{nasdaq_del:+.2f}%" if nasdaq_del else "-0.28%"

st.markdown(f"""
<div class="widget-grid">
    <div class="widget-card">
        <div class="widget-header"><span>날씨</span><span>{w_loc}</span></div>
        <div class="widget-main">{w_desc} {w_temp}</div>
        <div class="widget-footer" style="color: #94a3b8;">습도 {w_hum}</div>
    </div>
    <div class="widget-card">
        <div class="widget-header"><span>코스피</span><span>KOSPI</span></div>
        <div class="widget-main">{kospi_txt}</div>
        <div class="widget-footer"><span class="{'pill-up' if '+' in kospi_d_txt else 'pill-down'}">{kospi_d_txt}</span></div>
    </div>
    <div class="widget-card">
        <div class="widget-header"><span>나스닥 종합</span><span>NASDAQ</span></div>
        <div class="widget-main">{nasdaq_txt}</div>
        <div class="widget-footer"><span class="{'pill-up' if '+' in nasdaq_d_txt else 'pill-down'}">{nasdaq_d_txt}</span></div>
    </div>
    <div class="widget-card">
        <div class="widget-header"><span>주요 D-Day</span><span>어학</span></div>
        <div class="widget-main">오픽 D-7</div>
        <div class="widget-footer" style="color: #94a3b8;">8.23 13:00 발표</div>
    </div>
</div>
""", unsafe_allow_html=True)


# =============================================================
# [4대 핵심 대분류 탭 - 세그먼트 캡슐형 탭]
# =============================================================

tab_daily, tab_stock, tab_sports, tab_blog = st.tabs([
    "데일리", "주식·금융", "스포츠", "블로그"
])

with tab_daily:
    render_daily_hub()

with tab_stock:
    render_stock_hub()

with tab_sports:
    render_sports_hub()

with tab_blog:
    render_blog_hub()
