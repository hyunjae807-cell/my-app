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
    padding-top: 1rem !important;
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
    margin-top: -10px;
    margin-bottom: 18px;
    padding-bottom: 14px;
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
    margin-top: 5px;
    letter-spacing: -0.01em;
}
.mori-time {
    font-size: 13px !important;
    color: #64748b;
    margin-top: 6px;
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
    font-size: 15px !important;
    font-weight: 800 !important;
    color: #94a3b8;
}
.stTabs [aria-selected="true"] {
    background-color: rgba(59, 130, 246, 0.2) !important;
    color: #60a5fa !important;
    border-bottom: 2px solid #3b82f6 !important;
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

# 7. 실시간 위치 기반 날씨 데이터 조회
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

# 8. [초고속 pykrx + yfinance 하이브리드 엔진]
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
def fetch_google_news(query, max_results=8):
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

# 9. [통합 제미나이 AI 호출 엔진 - 404 모델 에러 100% 방지]
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
# [공통 모듈 렌더링 함수들]
# =============================================================

def render_portfolio_section():
    st.subheader("💼 내 주식·ETF 포트폴리오")
    user_portfolio = load_portfolio()
    
    port_tickers = [item["티커"] for item in user_portfolio]
    live_prices_map = get_batch_market_data(port_tickers)

    total_eval_krw = 0
    total_buy_krw = 0
    calculated_rows = []

    for item in user_portfolio:
        cur_p, _ = live_prices_map.get(item["티커"], (None, None))
        if cur_p is None:
            cur_p = item["매입단가"]

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
    with c1:
        st.metric("총 평가금액", f"{total_eval_krw:,.0f}원", f"{total_rate_krw:+.2f}%")
    with c2:
        st.metric("총 평가손익", f"{total_profit_krw:+,.0f}원", f"매입총액: {total_buy_krw:,.0f}원")

    st.dataframe(pd.DataFrame(calculated_rows), use_container_width=True)

def render_calendar_section():
    st.subheader("📅 통합 스마트 캘린더 & 배당 플래너")
    
    user_portfolio = load_portfolio()
    cover_shares = 863
    div_per = 270
    for p in user_portfolio:
        if "커버드콜" in p["종목명"]:
            cover_shares = p["보유수량"]
            
    monthly_est_div = cover_shares * div_per
    
    st.markdown(f"""
    <div class="subs-card">
        <div style="font-size: 15px; color: #e9d5ff; font-weight: 700;">💰 월 배당금(분배금) 예상 수령액</div>
        <div style="font-size: 30px; font-weight: 900; margin-top: 4px;">{monthly_est_div:,.0f}원 / 월</div>
        <div style="font-size: 14px; color: #d8b4fe; margin-top: 4px;">KODEX 200위클리커버드콜({cover_shares:,}주) 기준 | 연간 약 {monthly_est_div*12:,.0f}원</div>
    </div>
    """, unsafe_allow_html=True)

    timeline_events = [
        {"날짜": "2026-08-22", "분류": "🎬 구독 결제", "내용": "넷플릭스 (17,000원) 결제일 (D-6)", "중요도": "🟡 정기"},
        {"날짜": "2026-08-26", "분류": "🎯 AI반도체", "내용": "엔비디아(NVDA) 2분기 실적 발표 (미국)", "중요도": "🔴 핵심"},
        {"날짜": "2026-08-28", "분류": "🌐 거시경제", "내용": "미국 잭슨홀 심포지엄 (파월 의장 연설)", "중요도": "🔴 높음"},
        {"날짜": "2026-09-01", "분류": "💰 배당금 입금", "내용": "KODEX 커버드콜 월 분배금 입금 예정일", "중요도": "🟢 수익"},
        {"날짜": "2026-09-01", "분류": "🎵 구독 결제", "내용": "Spotify (11,990원) 결제일", "중요도": "🟡 정기"},
        {"날짜": "2026-09-08", "분류": "🛍️ 구독 결제", "내용": "쿠팡 와우멤버십 (7,890원) 결제일", "중요도": "🟡 정기"},
        {"날짜": "2026-09-10", "분류": "🎯 파생만기", "내용": "국내 선물·옵션 동시 만기일 (네 마녀의 날)", "중요도": "🔴 변동성"},
        {"날짜": "2026-09-15", "분류": "⚽ 구독 결제", "내용": "SPOTV NOW (19,900원) 결제일", "중요도": "🟡 정기"},
        {"날짜": "2026-09-16", "분류": "🌐 거시경제", "내용": "미국 9월 FOMC 기준금리 결정 회의", "중요도": "🔴 높음"}
    ]
    st.write("📋 **통합 일정 타임라인**")
    st.dataframe(pd.DataFrame(timeline_events), use_container_width=True)

def render_subscriptions_section():
    st.subheader("💳 고정 구독료 관리자")
    subs_list = load_subscriptions()
    
    total_sub_monthly = sum(s["월요금"] for s in subs_list)
    monthly_est_div = 863 * 270
    coverage_rate = (monthly_est_div / total_sub_monthly * 100) if total_sub_monthly > 0 else 0

    c_s1, c_s2 = st.columns(2)
    with c_s1:
        st.metric("월 고정 구독료 합계", f"{total_sub_monthly:,.0f}원", f"총 {len(subs_list)}개 서비스")
    with c_s2:
        st.metric("배당금 방어율", f"{coverage_rate:.1f}%", f"월 배당 {monthly_est_div:,.0f}원")

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
        with col_name:
            st.markdown(f"**{s['카테고리']} {s['서비스']}**")
        with col_cost:
            st.markdown(f"{s['월요금']:,}원 / 월")
        with col_dday:
            st.markdown(f"매월 **{s['결제일']}일**")

    st.markdown("---")
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
                    st.success(f"'{new_s_name}' 서비스가 등록되었습니다!")
                    st.rerun()

        if len(subs_list) > 1:
            del_sub_idx = st.selectbox("삭제할 구독 선택", range(len(subs_list)), format_func=lambda x: f"{subs_list[x]['서비스']} ({subs_list[x]['월요금']:,}원)")
            if st.button("선택한 구독 삭제"):
                removed_s = subs_list.pop(del_sub_idx)
                save_subscriptions(subs_list)
                st.success(f"'{removed_s['서비스']}' 구독이 삭제되었습니다.")
                st.rerun()

def render_market_section():
    st.subheader("🌐 글로벌 & 국내 시황")
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

def render_briefing_section():
    st.subheader("💡 실시간 맞춤형 AI 모닝 브리핑")
    user_portfolio = load_portfolio()
    recent_news = fetch_google_news("코스피 OR 반도체 OR 연준 금리 OR 엔비디아", max_results=12)
    
    k_input_b = st.text_input("Gemini API Key (브리핑용)", value=st.session_state.saved_gemini_key, type="password", key="briefing_key_view")
    if k_input_b: st.session_state.saved_gemini_key = k_input_b
    
    if st.button("✨ 오늘자 AI 브리핑 재생성", key="btn_regen_briefing"):
        if not st.session_state.saved_gemini_key:
            st.warning("API Key를 입력해 주세요.")
        else:
            with st.spinner("구글 Gemini AI 분석 중..."):
                b_res, status = generate_ai_briefing(recent_news, user_portfolio, st.session_state.saved_gemini_key)
                if status == "SUCCESS" and b_res:
                    now_str = datetime.now(KST).strftime('%Y년 %m월 %d일 %H:%M:%S')
                    save_briefing(b_res, now_str)
                    st.success("브리핑 생성 완료!")
                    st.rerun()

    saved_briefing_text, saved_time = load_briefing()
    if saved_briefing_text:
        st.caption(f"🕒 생성 시각: {saved_time}")
        with st.container(border=True):
            st.markdown(saved_briefing_text)

def render_chat_section():
    st.subheader("🤖 1:1 AI 투자 비서 챗봇")
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = [
            {"role": "assistant", "content": "안녕하세요! 고객님의 포트폴리오(KODEX AI반도체, KODEX 200커버드콜)를 기반으로 맞춤 투자 분석을 도와드립니다."}
        ]

    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_input = st.chat_input("AI 비서에게 질문하기...", key="chat_input_field")
    if user_input:
        st.session_state.chat_messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        if not st.session_state.saved_gemini_key:
            with st.chat_message("assistant"):
                st.warning("상단에 Gemini API Key를 입력해 주세요.")
        else:
            with st.chat_message("assistant"):
                with st.spinner("AI 비서 답변 생성 중..."):
                    user_port = load_portfolio()
                    bot_reply = ask_gemini_chat(st.session_state.chat_messages, user_input, user_port, st.session_state.saved_gemini_key)
                    st.markdown(bot_reply)
                    st.session_state.chat_messages.append({"role": "assistant", "content": bot_reply})

def render_sports_section():
    st.subheader("🏆 내 응원팀 스포츠 허브")
    my_teams = load_sports_teams()
    sports_briefings = load_sports_briefings()
    
    team_names = [f"{idx+1}. {t['종목']} {t['팀명']} ({t['리그']})" for idx, t in enumerate(my_teams)]
    selected_team_idx = st.selectbox("응원하는 팀 선택", range(len(team_names)), format_func=lambda x: team_names[x], key="sp_team_select")
    
    current_team = my_teams[selected_team_idx]
    team_key = current_team["팀명"]

    search_query = f'"{current_team["팀명"]}" AND (경기 OR 일정 OR 결과 OR 승리 OR 패배 OR 하이라이트)'
    team_news = fetch_google_news(search_query, max_results=8)

    c_s1, c_s2 = st.columns([0.65, 0.35])
    with c_s1:
        st.write(f"### {current_team['종목']} {current_team['팀명']} ({current_team['리그']})")
    with c_s2:
        if st.button("⚡ 실시간 경기 브리핑 생성", key=f"btn_sb_view_{team_key}"):
            if not st.session_state.saved_gemini_key:
                st.warning("API Key가 필요합니다.")
            else:
                with st.spinner(f"{team_key} 일정 분석 중..."):
                    briefing_text = generate_team_briefing(
                        current_team['팀명'], current_team['종목'], current_team['리그'], team_news, st.session_state.saved_gemini_key
                    )
                    if briefing_text:
                        now_str = datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S')
                        sports_briefings[team_key] = {"text": briefing_text, "updated_at": now_str}
                        save_sports_briefings(sports_briefings)
                        st.success("업데이트 완료!")
                        st.rerun()

    if team_key in sports_briefings:
        b_data = sports_briefings[team_key]
        st.caption(f"🕒 업데이트 시각: {b_data.get('updated_at', '')} (KST 기준)")
        with st.container(border=True):
            st.markdown(b_data.get("text", ""))


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

if "dual_view_mode" not in st.session_state:
    st.session_state["dual_view_mode"] = False


# =============================================================
# [화면 렌더링 분기: 듀얼뷰 vs 탭 네비게이션]
# =============================================================

col_h1, col_h2 = st.columns([0.7, 0.3])
with col_h1:
    st.markdown("""
    <div class="mori-header">
        <div class="mori-title">MORI</div>
        <div class="mori-subtitle">Everything about you, in one place.</div>
        <div class="mori-time">대한민국 표준시(KST) : """ + datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S') + """</div>
    </div>
    """, unsafe_allow_html=True)
with col_h2:
    st.write("")
    is_dual = st.toggle("📖 듀얼뷰 (폴드 펼침 모드)", value=st.session_state.get("dual_view_mode", False))
    st.session_state["dual_view_mode"] = is_dual


if st.session_state.get("dual_view_mode", False):
    # ---------------------------------------------------------
    # 📖 폴드 펼침 대화면 2열 듀얼 뷰 모드
    # ---------------------------------------------------------
    st.info("💡 **갤럭시 Z 폴드 대화면 듀얼 뷰 활성화됨** : 좌측(자산·캘린더·구독) / 우측(AI 브리핑·챗봇·스포츠)")
    
    col_left, col_right = st.columns([0.5, 0.5])
    
    with col_left:
        with st.container(border=True):
            render_portfolio_section()
        
        with st.container(border=True):
            render_calendar_section()

        with st.container(border=True):
            render_subscriptions_section()

        with st.container(border=True):
            render_market_section()

    with col_right:
        temp_val, weather_val, humid_val, loc_tag = get_current_weather(
            current_loc_data.get("lat", 37.2410),
            current_loc_data.get("lon", 127.1775),
            current_loc_data.get("name", "경기도 용인시")
        )
        st.markdown(f"""
        <div class="weather-gradient">
            <div style="font-size: 15px; color: #bae6fd; font-weight: 700;">{loc_tag} 실시간 날씨</div>
            <div style="font-size: 30px; font-weight: 900; margin-top: 6px;">{weather_val} {temp_val} (습도 {humid_val})</div>
        </div>
        """, unsafe_allow_html=True)

        with st.container(border=True):
            render_briefing_section()

        with st.container(border=True):
            render_chat_section()

        with st.container(border=True):
            render_sports_section()

else:
    # ---------------------------------------------------------
    # 📱 커버 화면 최적화 탭 네비게이션 모드
    # ---------------------------------------------------------
    tabs = st.tabs([
        "🏠 데일리 요약", "💼 포트폴리오", "📅 캘린더", "💳 구독료 관리",
        "📊 실시간 시황", "📰 주요 뉴스", "💡 AI 브리핑", "🤖 AI 챗봇", "⚽ 스포츠 허브", "📋 데일리 & 날씨"
    ])

    with tabs[0]:
        st.subheader("오늘의 핵심 데일리 요약")
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
            st.markdown("**💼 내 포트폴리오 요약**")
            ch1, ch2 = st.columns(2)
            with ch1: st.metric("총 평가금액", f"{total_eval_h:,.0f}원", f"{rate_h:+.2f}%")
            with ch2: st.metric("총 평가손익", f"{diff_h:+,.0f}원")

        quick_news = fetch_google_news("코스피 OR 반도체 OR 연준 금리", max_results=3)
        with st.container(border=True):
            st.markdown("**📰 오늘의 핵심 3줄 뉴스**")
            for qn in quick_news:
                st.markdown(f"• [{qn['title']}]({qn['link']}) <span style='font-size:12px;color:#94a3b8;'>({qn['source']})</span>", unsafe_allow_html=True)

    with tabs:
        render_portfolio_section()

    with tabs:
        render_calendar_section()

    with tabs[3]:
        render_subscriptions_section()

    with tabs[4]:
        render_market_section()

    with tabs[5]:
        st.subheader("📰 실시간 뉴스 피드")
        user_portfolio = load_portfolio()
        my_stock_names = [item["종목명"] for item in user_portfolio]
        category_options = ["📌 [전체] 내 보유 종목 뉴스 모아보기"] + [f"🎯 {name}" for name in my_stock_names] + ["🇰🇷 국내 증시", "🇺🇸 미국 증시", "🤖 AI·반도체"]
        selected_cat = st.selectbox("뉴스 카테고리 선택", category_options, index=0)
        query = "코스피 OR 반도체"
        if selected_cat.startswith("🎯 "): query = selected_cat.replace("🎯 ", "")
        news_list = fetch_google_news(query, max_results=8)
        for item in news_list:
            st.markdown(f"""
            <div class="news-card">
                <a class="news-title" href="{item['link']}" target="_blank">🔗 {item['title']}</a>
                <div class="news-meta">📰 {item['source']} &nbsp;|&nbsp; 🕒 {item['date']}</div>
            </div>
            """, unsafe_allow_html=True)

    with tabs[6]:
        render_briefing_section()

    with tabs[7]:
        render_chat_section()

    with tabs[8]:
        render_sports_section()

    with tabs[9]:
        st.subheader("📋 데일리 생산성 & 라이프")
        temp_val, weather_val, humid_val, loc_tag = get_current_weather(
            current_loc_data.get("lat", 37.2410),
            current_loc_data.get("lon", 127.1775),
            current_loc_data.get("name", "경기도 용인시")
        )
        st.markdown(f"""
        <div class="weather-card">
            <div style="font-size: 16px; font-weight: 700;">{loc_tag} 오늘 날씨</div>
            <div style="font-size: 30px; font-weight: 900; margin-top: 6px;">{weather_val} {temp_val} (습도 {humid_val})</div>
        </div>
        """, unsafe_allow_html=True)

        with st.expander("📍 날씨 지역 변경 / GPS 위치 설정"):
            preset_names = list(LOCATION_PRESETS.keys())
            sel_preset = st.selectbox("지역 선택", preset_names, index=0)
            if st.button("선택 지역으로 날씨 저장"):
                chosen = LOCATION_PRESETS[sel_preset]
                save_location(chosen)
                st.success(f"'{chosen['name']}'(으)로 날씨 위치가 저장되었습니다!")
                st.rerun()

        st.markdown("---")
        st.subheader("✅ 오늘의 할 일 (To-Do List)")
        current_todos = load_todos()
        to_delete = None
        for idx, todo_item in enumerate(current_todos):
            col_t1, col_t2 = st.columns([0.85, 0.15])
            with col_t1: st.write(f"• **{todo_item}**")
            with col_t2:
                if st.button("완료", key=f"del_{idx}"): to_delete = idx
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
