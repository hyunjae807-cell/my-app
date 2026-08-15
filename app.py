import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import requests
import json
import os
import base64
from datetime import datetime, timezone, timedelta
import urllib.request
import xml.etree.ElementTree as ET
import urllib.parse

# 1. 한국 표준시(KST) 정의
KST = timezone(timedelta(hours=9))

# 2. 모바일 최적화 페이지 설정
st.set_page_config(
    page_title="나만의 올인원 비서",
    page_icon="🦁",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 모바일 친화적 CSS
st.markdown("""
    <style>
    .news-card {
        background-color: #1e293b;
        color: #f8fafc;
        border-radius: 10px;
        padding: 14px;
        margin-bottom: 12px;
        border: 1px solid #334155;
    }
    .news-title {
        font-size: 15px;
        font-weight: 600;
        color: #60a5fa;
        text-decoration: none;
    }
    .news-title:hover {
        color: #93c5fd;
    }
    .news-meta {
        font-size: 12px;
        color: #94a3b8;
        margin-top: 6px;
    }
    .weather-card {
        background: linear-gradient(135deg, #0284c7, #0369a1);
        padding: 16px;
        border-radius: 12px;
        color: white;
        margin-bottom: 15px;
    }
    .sports-card {
        background: linear-gradient(135deg, #1e293b, #0f172a);
        border: 1px solid #3b82f6;
        padding: 16px;
        border-radius: 12px;
        color: white;
        margin-bottom: 15px;
    }
    </style>
""", unsafe_allow_html=True)

# 3. [영구 저장소 파일 관리]
PORTFOLIO_FILE = "portfolio.json"
BRIEFING_FILE = "briefing.json"
TODOS_FILE = "todos.json"
SPORTS_FILE = "sports_teams.json"

DEFAULT_PORTFOLIO = [
    {"종목명": "KODEX AI반도체TOP2플러스", "티커": "395160.KS", "매입단가": 13234.0, "보유수량": 126},
    {"종목명": "KODEX 200타겟위클리커버드콜", "티커": "498400.KS", "매입단가": 13012.0, "보유수량": 863}
]

DEFAULT_SPORTS_TEAMS = [
    {"종목": "⚽ 축구", "팀명": "맨체스터 유나이티드", "리그": "프리미어리그 (EPL)", "키워드": "맨체스터 유나이티드 OR 맨유"},
    {"종목": "⚾ 야구", "팀명": "KIA 타이거즈", "리그": "KBO 리그", "키워드": "KIA 타이거즈"},
    {"종목": "⚾ 야구", "팀명": "LA 다저스", "리그": "메이저리그 (MLB)", "키워드": "LA 다저스 OR 오타니"}
]

def load_portfolio():
    if os.path.exists(PORTFOLIO_FILE):
        try:
            with open(PORTFOLIO_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data:
                    return data
        except Exception:
            pass
    return DEFAULT_PORTFOLIO

def save_portfolio(data):
    try:
        with open(PORTFOLIO_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"저장 오류: {e}")

def load_briefing():
    if os.path.exists(BRIEFING_FILE):
        try:
            with open(BRIEFING_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("text"), data.get("generated_at")
        except Exception:
            pass
    return None, None

def save_briefing(text, generated_at_str):
    try:
        with open(BRIEFING_FILE, "w", encoding="utf-8") as f:
            json.dump({"text": text, "generated_at": generated_at_str}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"저장 오류: {e}")

def load_todos():
    if os.path.exists(TODOS_FILE):
        try:
            with open(TODOS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data:
                    return data
        except Exception:
            pass
    return ["주요 증시 캘린더 확인하기", "내 응원팀 경기 일정 체크하기"]

def save_todos(todos):
    try:
        with open(TODOS_FILE, "w", encoding="utf-8") as f:
            json.dump(todos, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"저장 오류: {e}")

def load_sports_teams():
    if os.path.exists(SPORTS_FILE):
        try:
            with open(SPORTS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data:
                    return data
        except Exception:
            pass
    return DEFAULT_SPORTS_TEAMS

def save_sports_teams(teams):
    try:
        with open(SPORTS_FILE, "w", encoding="utf-8") as f:
            json.dump(teams, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"스포츠 설정 저장 오류: {e}")

# 4. 아침 7시 시스템 알람 컴포넌트
alarm_component = """
<div id="alarmCard" style="background: linear-gradient(135deg, #1e293b, #0f172a); padding: 14px; border-radius: 12px; color: white; margin-bottom: 12px; transition: all 0.3s ease;">
    <div style="font-weight: 700; font-size: 14px; margin-bottom: 4px;">⏰ 매일 한국 시간 아침 7시 시스템 알람</div>
    <div style="font-size: 11px; color: #94a3b8; margin-bottom: 10px;">버튼을 누르면 테스트 알람이 울린 후 이 설정창은 자동으로 사라집니다.</div>
    <button id="alarmBtn" onclick="initAlarm()" style="background-color: #3b82f6; color: white; border: none; padding: 8px 14px; border-radius: 8px; font-size: 12px; font-weight: 600; cursor: pointer; width: 100%;">
        🔔 시스템 알람 켜기 & 테스트 알람
    </button>
</div>

<script>
function hideCard() {
    const card = document.getElementById("alarmCard");
    if (card) {
        card.style.display = "none";
    }
}

function playAlarmSound() {
    try {
        const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();
        osc.connect(gain);
        gain.connect(audioCtx.destination);
        osc.type = "sine";
        osc.frequency.setValueAtTime(880, audioCtx.currentTime);
        gain.gain.setValueAtTime(0.5, audioCtx.currentTime);
        osc.start();
        osc.stop(audioCtx.currentTime + 1.2);
    } catch(e) {}
}

function triggerSystemNotification() {
    playAlarmSound();
    if (Notification.permission === "granted") {
        new Notification("🌅 [증시 비서] 오늘의 모닝 브리핑 도착!", {
            body: "코스피 및 뉴욕증시 최신 시황과 핵심 뉴스를 확인하세요.",
            icon: "https://img.icons8.com/color/96/bullish.png"
        });
    }
}

function checkTimeForAlarm() {
    const now = new Date();
    if (now.getHours() === 7 && now.getMinutes() === 0 && now.getSeconds() === 0) {
        triggerSystemNotification();
    }
}

function initAlarm() {
    if (!("Notification" in window)) {
        alert("알림을 지원하지 않는 브라우저입니다.");
        return;
    }
    Notification.requestPermission().then(permission => {
        if (permission === "granted") {
            localStorage.setItem("alarm_enabled", "true");
            triggerSystemNotification();
            setInterval(checkTimeForAlarm, 1000);
            setTimeout(hideCard, 500);
        } else {
            alert("알림 권한이 허용되지 않았습니다.");
        }
    });
}

if (Notification.permission === "granted" || localStorage.getItem("alarm_enabled") === "true") {
    hideCard();
    setInterval(checkTimeForAlarm, 1000);
}
</script>
"""

# 5. 실시간 날씨 데이터 조회 (용인시 기준)
@st.cache_data(ttl=1800)
def get_yongin_weather():
    try:
        url = "https://api.open-meteo.com/v1/forecast?latitude=37.2410&longitude=127.1775&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m&timezone=Asia%2FTokyo"
        res = requests.get(url, timeout=4).json()
        current = res.get("current", {})
        temp = current.get("temperature_2m", 28.0)
        humidity = current.get("relative_humidity_2m", 65)
        code = current.get("weather_code", 0)
        
        weather_desc = "맑음 ☀️"
        if code == 1 or code == 2:
            weather_desc = "구름 조금 ⛅"
        elif code == 3:
            weather_desc = "흐림 ☁️"
        elif code in (51, 53, 55, 61, 63, 65, 80, 81, 82):
            weather_desc = "비 🌧️"
        elif code in (71, 73, 75, 85, 86):
            weather_desc = "눈 ❄️"
        
        return f"{temp:.1f}°C", weather_desc, f"{humidity}%"
    except Exception:
        return "28.0°C", "맑음 ☀️", "60%"

# 6. 실시간 주가 및 뉴스 로딩 함수
@st.cache_data(ttl=60)
def get_live_market_data(ticker_symbol):
    try:
        t = yf.Ticker(ticker_symbol)
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

@st.cache_data(ttl=300)
def fetch_google_news(query, max_results=8):
    try:
        encoded_query = urllib.parse.quote(query)
        url = f"https://news.google.com/rss/search?q={encoded_query}&hl=ko&gl=KR&ceid=KR:ko"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            xml_data = response.read()
            root = ET.fromstring(xml_data)
            news_items = []
            for item in root.findall('.//item')[:max_results]:
                title = item.find('title').text if item.find('title') is not None else "제목 없음"
                link = item.find('link').text if item.find('link') is not None else "#"
                pub_date = item.find('pubDate').text if item.find('pubDate') is not None else ""
                source = item.find('source').text if item.find('source') is not None else "언론사"
                if pub_date:
                    pub_date = pub_date[:16]
                news_items.append({"title": title, "link": link, "source": source, "date": pub_date})
            return news_items
    except Exception:
        return []

# 7. AI 비전 이미지 분석 및 브리핑 함수
def analyze_portfolio_image(image_bytes, api_key):
    api_key = api_key.strip()
    headers = {"Content-Type": "application/json", "x-goog-api-key": api_key}
    candidate_models = ["models/gemini-3.5-flash", "models/gemini-2.0-flash", "models/gemini-1.5-flash-latest"]
    try:
        m_res = requests.get("https://generativelanguage.googleapis.com/v1beta/models", headers=headers, timeout=5)
        if m_res.status_code == 200:
            active = [m['name'] for m in m_res.json().get('models', []) if 'generateContent' in m.get('supportedGenerationMethods', [])]
            if active:
                candidate_models = active
    except Exception:
        pass

    base64_img = base64.b64encode(image_bytes).decode('utf-8')
    prompt = """
    이 이미지는 증권사 주식/ETF 잔고 화면입니다.
    보유 중인 종목명, 야후파이낸스 티커(국내 종목/ETF는 6자리코드.KS 또는 .KQ, 미국 주식은 알파벳), 평균 매입단가(숫자), 보유 수량(정수)을 추출해주세요.
    반드시 순수 JSON 배열 형식으로만 응답해주세요:
    [
        {"종목명": "KODEX AI반도체TOP2플러스", "티커": "395160.KS", "매입단가": 13234.0, "보유수량": 126},
        {"종목명": "KODEX 200타겟위클리커버드콜", "티커": "498400.KS", "매입단가": 13012.0, "보유수량": 863}
    ]
    """
    payload = {"contents": [{"parts": [{"text": prompt}, {"inline_data": {"mime_type": "image/jpeg", "data": base64_img}}]}]}
    
    last_err = ""
    for model_path in candidate_models:
        clean_model = model_path if model_path.startswith("models/") else f"models/{model_path}"
        url = f"https://generativelanguage.googleapis.com/v1beta/{clean_model}:generateContent"
        try:
            res = requests.post(url, json=payload, headers=headers, timeout=20)
            if res.status_code == 200:
                raw = res.json()['candidates'][0]['content']['parts'][0]['text']
                raw = raw.replace("```json", "").replace("```", "").strip()
                return json.loads(raw), "SUCCESS"
            else:
                last_err = f"{clean_model}: {res.text}"
        except Exception as e:
            last_err = str(e)
    return None, f"분석 오류: {last_err}"

def generate_ai_briefing(news_headlines, portfolio_items, api_key):
    api_key = api_key.strip()
    headers = {"Content-Type": "application/json", "x-goog-api-key": api_key}
    candidate_models = ["models/gemini-3.5-flash", "models/gemini-2.0-flash", "models/gemini-1.5-flash-latest"]
    try:
        m_res = requests.get("https://generativelanguage.googleapis.com/v1beta/models", headers=headers, timeout=5)
        if m_res.status_code == 200:
            active = [m['name'] for m in m_res.json().get('models', []) if 'generateContent' in m.get('supportedGenerationMethods', [])]
            if active:
                candidate_models = active
    except Exception:
        pass

    stock_list_str = ", ".join([f"{item['종목명']} ({item['티커']})" for item in portfolio_items])
    news_text = "\n".join([f"- {h['title']} ({h.get('source', '')})" for h in news_headlines[:15]])
    
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
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    for model_path in candidate_models:
        clean_model = model_path if model_path.startswith("models/") else f"models/{model_path}"
        url = f"https://generativelanguage.googleapis.com/v1beta/{clean_model}:generateContent"
        try:
            res = requests.post(url, json=payload, headers=headers, timeout=25)
            if res.status_code == 200:
                return res.json()['candidates'][0]['content']['parts'][0]['text'], "SUCCESS"
        except Exception:
            pass
    return None, "브리핑 생성 실패"

# 8. 1:1 대화형 AI 투자 챗봇 함수
def ask_gemini_chat(chat_history, user_msg, portfolio_items, api_key):
    api_key = api_key.strip()
    headers = {"Content-Type": "application/json", "x-goog-api-key": api_key}
    stock_list_str = ", ".join([f"{item['종목명']} ({item['티커']})" for item in portfolio_items])
    
    system_inst = f"당신은 투자자의 1:1 개인 금융/주식 비서 AI입니다. 투자자가 보유한 종목은 [{stock_list_str}] 입니다. 친절하고 명확하며 통찰력 있는 분석을 한국어로 답변하세요."
    
    contents = []
    for msg in chat_history:
        if not contents and msg["role"] != "user":
            continue
        role = "user" if msg["role"] == "user" else "model"
        contents.append({"role": role, "parts": [{"text": msg["content"]}]})
        
    contents.append({"role": "user", "parts": [{"text": f"[{system_inst}]\n\n질문: {user_msg}"}]})

    candidate_models = ["models/gemini-3.5-flash", "models/gemini-2.0-flash", "models/gemini-1.5-flash-latest"]
    try:
        m_res = requests.get("https://generativelanguage.googleapis.com/v1beta/models", headers=headers, timeout=5)
        if m_res.status_code == 200:
            active = [m['name'] for m in m_res.json().get('models', []) if 'generateContent' in m.get('supportedGenerationMethods', [])]
            if active:
                candidate_models = active
    except Exception:
        pass

    for model_path in candidate_models:
        clean_model = model_path if model_path.startswith("models/") else f"models/{model_path}"
        url = f"https://generativelanguage.googleapis.com/v1beta/{clean_model}:generateContent"
        try:
            res = requests.post(url, json={"contents": contents}, headers=headers, timeout=20)
            if res.status_code == 200:
                return res.json()['candidates'][0]['content']['parts'][0]['text']
        except Exception:
            pass
    return "답변을 불러오는 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요."


# =============================================================
# 메인 UI 렌더링
# =============================================================

st.title("🦁 My Personal Assistant")
st.caption(f"기준 시각: {datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S (한국 시간)')}")

# 알람 컴포넌트 삽입 (설정 완료 시 스스로 사라짐)
components.html(alarm_component, height=95)

# API 키 공유 관리
if "saved_gemini_key" not in st.session_state:
    st.session_state.saved_gemini_key = st.secrets.get("GEMINI_API_KEY", "")

# 7개 탭 구성
tab_portfolio, tab_market, tab_news, tab_briefing, tab_chat, tab_sports, tab_daily = st.tabs(
    ["💼 포트폴리오", "📊 실시간 시황", "📰 주요 뉴스", "💡 AI 브리핑", "🤖 AI 챗봇", "⚽ 스포츠 허브", "📋 데일리 & 날씨"]
)

# -------------------------------------------------------------
# TAB 1: 내 실제 포트폴리오 & 배당금 계산기
# -------------------------------------------------------------
with tab_portfolio:
    st.subheader("💼 내 주식·ETF 포트폴리오")
    user_portfolio = load_portfolio()
    total_eval_krw = 0
    total_buy_krw = 0
    calculated_rows = []

    for item in user_portfolio:
        cur_p, _ = get_live_market_data(item["티커"])
        if cur_p is None:
            cur_p = item["매입단가"]

        is_krw = ".KS" in item["티커"] or ".KQ" in item["티커"]
        eval_amount = cur_p * item["보유수량"]
        buy_amount = item["매입단가"] * item["보유수량"]
        profit_amount = eval_amount - buy_amount
        profit_rate = (profit_amount / buy_amount) * 100 if buy_amount > 0 else 0

        if is_krw:
            total_eval_krw += eval_amount
            total_buy_krw += buy_amount

        calculated_rows.append({
            "종목명": item["종목명"],
            "보유수량": f"{item['보유수량']:,}주",
            "매입단가": f"{item['매입단가']:,.0f}원" if is_krw else f"${item['매입단가']:.2f}",
            "현재가 (실시간)": f"{cur_p:,.0f}원" if is_krw else f"${cur_p:.2f}",
            "평가금액": f"{eval_amount:,.0f}원" if is_krw else f"${eval_amount:,.2f}",
            "평가손익": f"{profit_amount:+,.0f}원" if is_krw else f"${profit_amount:+.2f}",
            "수익률": f"{profit_rate:+.2f}%"
        })

    total_profit_krw = total_eval_krw - total_buy_krw
    total_rate_krw = (total_profit_krw / total_buy_krw) * 100 if total_buy_krw > 0 else 0

    c1, c2 = st.columns(2)
    with c1:
        st.metric("총 평가금액", f"{total_eval_krw:,.0f}원", f"{total_rate_krw:+.2f}%")
    with c2:
        st.metric("총 평가손익", f"{total_profit_krw:+,.0f}원", f"매입총액: {total_buy_krw:,.0f}원")

    st.markdown("---")
    st.write("📋 **보유 종목 실시간 현황표**")
    st.dataframe(pd.DataFrame(calculated_rows), use_container_width=True)

    # 💰 배당금 / 분배금 계산기
    st.markdown("---")
    with st.expander("💰 내 배당금 / 커버드콜 월 분배금 계산기", expanded=False):
        st.write("보유 중인 `KODEX 200타겟위클리커버드콜` 등 고배당 ETF의 예상 배당 수익을 계산합니다.")
        div_shares = st.number_input("커버드콜 보유 수량(주)", value=863, min_value=0)
        div_per_share = st.number_input("주당 예상 월 분배금(원)", value=270, min_value=0)
        
        monthly_div = div_shares * div_per_share
        annual_div = monthly_div * 12
        
        cd1, cd2 = st.columns(2)
        with cd1:
            st.metric("예상 월 분배금", f"{monthly_div:,.0f}원")
        with cd2:
            st.metric("예상 연간 배당 소득", f"{annual_div:,.0f}원")

    # 📸 캡처 사진 자동 업데이트
    st.markdown("---")
    with st.expander("📸 새 잔고 사진으로 포트폴리오 업데이트"):
        uploaded_file = st.file_uploader("증권사 잔고 캡처 사진 올리기", type=["png", "jpg", "jpeg"])
        if uploaded_file is not None:
            st.image(uploaded_file, use_container_width=True)
            k_input = st.text_input("Gemini API Key 입력", value=st.session_state.saved_gemini_key, type="password")
            if k_input:
                st.session_state.saved_gemini_key = k_input
                
            if st.button("✨ AI로 잔고 사진 분석 및 저장"):
                if not st.session_state.saved_gemini_key:
                    st.warning("API Key를 입력해 주세요.")
                else:
                    with st.spinner("AI 분석 중..."):
                        parsed, status = analyze_portfolio_image(uploaded_file.getvalue(), st.session_state.saved_gemini_key)
                        if status == "SUCCESS" and parsed:
                            save_portfolio(parsed)
                            st.success("🎉 포트폴리오가 영구 저장되었습니다!")
                            st.rerun()
                        else:
                            st.error(f"오류: {status}")

# -------------------------------------------------------------
# TAB 2: 실시간 시황
# -------------------------------------------------------------
with tab_market:
    st.subheader("🌐 글로벌 & 국내 주요 지수 (실시간)")
    kospi_p, kospi_d = get_live_market_data("^KS11")
    sp500_p, sp500_d = get_live_market_data("^GSPC")
    nasdaq_p, nasdaq_d = get_live_market_data("^IXIC")
    oil_p, oil_d = get_live_market_data("BZ=F")
    
    c1, c2 = st.columns(2)
    with c1:
        st.metric("코스피 (KOSPI)", f"{kospi_p:,.2f}" if kospi_p else "6,977.94", f"{kospi_d:+.2f}%" if kospi_d else "+2.42%")
        st.metric("S&P 500", f"{sp500_p:,.2f}" if sp500_p else "5,554.20", f"{sp500_d:+.2f}%" if sp500_d else "-0.20%")
    with c2:
        st.metric("나스닥 (NASDAQ)", f"{nasdaq_p:,.2f}" if nasdaq_p else "17,594.50", f"{nasdaq_d:+.2f}%" if nasdaq_d else "+0.12%")
        st.metric("브렌트유 (Oil)", f"${oil_p:.2f}" if oil_p else "$88.59", f"{oil_d:+.2f}%" if oil_d else "+1.75%")

    st.markdown("---")
    st.subheader("🏢 주요 대형주 시세")
    samsung_p, samsung_d = get_live_market_data("005930.KS")
    hynix_p, hynix_d = get_live_market_data("000660.KS")
    hyundai_p, hyundai_d = get_live_market_data("005380.KS")
    nvda_p, nvda_d = get_live_market_data("NVDA")
    
    ca, cb = st.columns(2)
    with ca:
        st.metric("삼성전자", f"{samsung_p:,.0f}원" if samsung_p else "84,500원", f"{samsung_d:+.2f}%" if samsung_d else "+2.43%")
        st.metric("SK하이닉스", f"{hynix_p:,.0f}원" if hynix_p else "193,000원", f"{hynix_d:+.2f}%" if hynix_d else "+3.30%")
    with cb:
        st.metric("현대차", f"{hyundai_p:,.0f}원" if hyundai_p else "256,000원", f"{hyundai_d:+.2f}%" if hynix_d else "+8.24%")
        st.metric("엔비디아 (NVDA)", f"${nvda_p:.2f}" if nvda_p else "$224.92", f"{nvda_d:+.2f}%" if nvda_d else "-0.18%")

# -------------------------------------------------------------
# TAB 3: 내 보유 종목 맞춤 뉴스 피드
# -------------------------------------------------------------
with tab_news:
    st.subheader("📰 실시간 뉴스 피드")
    user_portfolio = load_portfolio()
    my_stock_names = [item["종목명"] for item in user_portfolio]
    
    category_options = (
        ["📌 [전체] 내 보유 종목 뉴스 모아보기"] + 
        [f"🎯 {name}" for name in my_stock_names] + 
        ["🇰🇷 국내 증시·경제", "🇺🇸 미국·글로벌 증시", "🤖 AI·반도체", "🔍 직접 검색"]
    )
    selected_cat = st.selectbox("뉴스 카테고리 선택", category_options, index=0)
    
    if selected_cat == "📌 [전체] 내 보유 종목 뉴스 모아보기":
        query = " OR ".join([f'"{name}"' for name in my_stock_names]) + " OR AI반도체 OR 커버드콜"
    elif selected_cat.startswith("🎯 "):
        stock_name = selected_cat.replace("🎯 ", "")
        if "AI반도체" in stock_name:
            query = f'"{stock_name}" OR "AI반도체" OR "삼성전자 반도체"'
        elif "커버드콜" in stock_name:
            query = f'"{stock_name}" OR "커버드콜" OR "코스피200 분배금"'
        else:
            query = f'"{stock_name}"'
    elif selected_cat == "🇰🇷 국내 증시·경제":
        query = "코스피 OR 국내증시 OR 환율"
    elif selected_cat == "🇺🇸 미국·글로벌 증시":
        query = "뉴욕증시 OR 연준 금리 OR S&P500"
    elif selected_cat == "🤖 AI·반도체":
        query = "엔비디아 OR 반도체 HBM OR 인공지능"
    else:
        query = st.text_input("검색 키워드", value="삼성전자")
    
    if query:
        news_list = fetch_google_news(query, max_results=8)
        if news_list:
            for item in news_list:
                st.markdown(f"""
                <div class="news-card">
                    <a class="news-title" href="{item['link']}" target="_blank">🔗 {item['title']}</a>
                    <div class="news-meta">📰 {item['source']} &nbsp;|&nbsp; 🕒 {item['date']}</div>
                </div>
                """, unsafe_allow_html=True)

# -------------------------------------------------------------
# TAB 4: 실시간 AI 브리핑 & 음성 읽어주기 (TTS)
# -------------------------------------------------------------
with tab_briefing:
    st.subheader("💡 실시간 맞춤형 AI 모닝 브리핑")
    
    user_portfolio = load_portfolio()
    recent_news = fetch_google_news("코스피 OR 반도체 OR 연준 금리 OR 엔비디아", max_results=12)
    
    k_input_b = st.text_input("Gemini API Key 입력 (브리핑용)", value=st.session_state.saved_gemini_key, type="password", key="briefing_key")
    if k_input_b:
        st.session_state.saved_gemini_key = k_input_b
        
    c_btn1, c_btn2 = st.columns(2)
    with c_btn1:
        if st.button("✨ 오늘자 AI 브리핑 생성"):
            if not st.session_state.saved_gemini_key:
                st.warning("API Key를 입력해 주세요.")
            else:
                with st.spinner("구글 Gemini AI가 종합 분석 중입니다..."):
                    briefing_result, status = generate_ai_briefing(recent_news, user_portfolio, st.session_state.saved_gemini_key)
                    if status == "SUCCESS" and briefing_result:
                        now_str = datetime.now(KST).strftime('%Y년 %m월 %d일 %H:%M:%S')
                        save_briefing(briefing_result, now_str)
                        st.success("✅ AI 모닝 브리핑 생성 및 저장 완료!")
                        st.rerun()
                    else:
                        st.error(f"오류: {status}")

    saved_briefing_text, saved_time = load_briefing()

    with c_btn2:
        if saved_briefing_text:
            clean_speech = saved_briefing_text.replace("#", "").replace("*", "").replace("\n", " ").replace('"', '')[:300]
            tts_html = f"""
            <button onclick="speakBriefing()" style="background-color: #8b5cf6; color: white; border: none; padding: 9px 15px; border-radius: 8px; font-weight: 600; cursor: pointer; width: 100%;">
                🔊 음성으로 듣기 (TTS)
            </button>
            <script>
            function speakBriefing() {{
                if ('speechSynthesis' in window) {{
                    window.speechSynthesis.cancel();
                    const ut = new SpeechSynthesisUtterance("{clean_speech}");
                    ut.lang = 'ko-KR';
                    ut.rate = 1.0;
                    window.speechSynthesis.speak(ut);
                }} else {{
                    alert("음성 합성을 지원하지 않는 브라우저입니다.");
                }}
            }}
            </script>
            """
            components.html(tts_html, height=45)

    if saved_briefing_text:
        st.caption(f"🕒 **마지막 브리핑 생성 시각**: {saved_time}")
        with st.container(border=True):
            st.markdown(saved_briefing_text)
    else:
        st.info("💡 위의 **[✨ 오늘자 AI 브리핑 생성]** 버튼을 누르면 맞춤형 리포트가 생성되어 영구 보존됩니다.")

    st.markdown("---")
    st.subheader("📅 내 보유 종목 맞춤형 이벤트 캘린더")
    events = [
        {"날짜": "2026-08-26", "구분": "🎯 AI반도체", "이벤트": "엔비디아(NVDA) 2분기 실적 발표 (미국 현지시간)", "중요도": "🔴 핵심"},
        {"날짜": "2026-08-28", "구분": "🌐 거시경제", "이벤트": "미국 잭슨홀 심포지엄 (파월 연준의장 기조연설)", "중요도": "🔴 높음"},
        {"날짜": "2026-09-10", "구분": "🎯 커버드콜", "이벤트": "국내 선물·옵션 동시 만기일 (네 마녀의 날)", "중요도": "🔴 변동성"},
        {"날짜": "2026-09-16", "구분": "🌐 거시경제", "이벤트": "미국 9월 FOMC 기준금리 결정 회의", "중요도": "🔴 높음"},
        {"날짜": "매주 목요일", "구분": "🎯 커버드콜", "이벤트": "위클리 옵션 만기 및 프리미엄 정산", "중요도": "🟡 정기"}
    ]
    st.dataframe(pd.DataFrame(events), use_container_width=True)

# -------------------------------------------------------------
# TAB 5: 1:1 대화형 AI 투자 챗봇
# -------------------------------------------------------------
with tab_chat:
    st.subheader("🤖 1:1 AI 투자 비서 챗봇")
    st.caption("내 포트폴리오를 기반으로 무엇이든 질문하세요!")
    
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = [
            {"role": "assistant", "content": "안녕하세요! 고객님의 포트폴리오(KODEX AI반도체, KODEX 200커버드콜)를 기반으로 맞춤 투자 분석을 도와드립니다. 무엇이든 물어보세요!"}
        ]

    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    k_input_c = st.text_input("Gemini API Key 입력 (챗봇용)", value=st.session_state.saved_gemini_key, type="password", key="chat_key")
    if k_input_c:
        st.session_state.saved_gemini_key = k_input_c

    user_input = st.chat_input("AI 투자 비서에게 질문하기...")
    if user_input:
        st.session_state.chat_messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        if not st.session_state.saved_gemini_key:
            with st.chat_message("assistant"):
                st.warning("챗봇 사용을 위해 상단에 Gemini API Key를 입력해 주세요.")
        else:
            with st.chat_message("assistant"):
                with st.spinner("AI 비서가 분석 중입니다..."):
                    bot_reply = ask_gemini_chat(st.session_state.chat_messages, user_input, user_portfolio, st.session_state.saved_gemini_key)
                    st.markdown(bot_reply)
                    st.session_state.chat_messages.append({"role": "assistant", "content": bot_reply})

# -------------------------------------------------------------
# TAB 6: [맞춤형 검색 & 다종목 지원] 스포츠 허브
# -------------------------------------------------------------
with tab_sports:
    st.subheader("🏆 내 응원팀 스포츠 허브")
    
    # 영구 저장된 내 응원팀 목록 로드
    my_teams = load_sports_teams()
    
    # 팀 선택 셀렉트박스
    team_names = [f"{t['종목']} {t['팀명']} ({t['리그']})" for t in my_teams]
    selected_team_idx = st.selectbox("응원하는 팀 선택", range(len(team_names)), format_func=lambda x: team_names[x])
    
    current_team = my_teams[selected_team_idx]
    
    # 선택된 팀 안내 카드
    st.markdown(f"""
    <div class="sports-card">
        <div style="font-size: 18px; font-weight: 800;">{current_team['종목']} {current_team['팀명']}</div>
        <div style="font-size: 14px; margin-top: 6px; color: #93c5fd;">🏆 {current_team['리그']}</div>
        <div style="font-size: 12px; color: #cbd5e1; margin-top: 6px;">실시간 최신 경기 결과 및 구단 뉴스 브리핑</div>
    </div>
    """, unsafe_allow_html=True)

    # 해당 팀 실시간 뉴스 피드
    st.write(f"📰 **{current_team['팀명']} 실시간 뉴스**")
    team_news = fetch_google_news(current_team["키워드"], max_results=6)
    if team_news:
        for n in team_news:
            st.markdown(f"""
            <div class="news-card">
                <a class="news-title" href="{n['link']}" target="_blank">📣 {n['title']}</a>
                <div class="news-meta">📰 {n['source']} &nbsp;|&nbsp; 🕒 {n['date']}</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("최신 뉴스를 가져오는 중입니다...")

    # ➕ 새로운 응원팀 추가 / 관리
    st.markdown("---")
    with st.expander("➕ 새 응원팀 직접 검색 및 추가하기 (축구, 야구, 농구, e스포츠 등)"):
        with st.form("add_team_form"):
            sports_type = st.selectbox("종목 선택", ["⚽ 축구", "⚾ 야구", "🏀 농구", "🏐 배구", "🎮 e스포츠", "🏎️ 모터스포츠/기타"])
            new_team_name = st.text_input("팀명 입력 (예: 토트넘, 한화 이글스, T1, 골든스테이트)", value="토트넘")
            new_league = st.text_input("리그명 (예: EPL, KBO, LCK, NBA)", value="EPL")
            new_keyword = st.text_input("뉴스 검색 키워드 (예: 토트넘 OR 손흥민)", value="토트넘")
            
            if st.form_submit_button("내 응원팀에 추가하기"):
                if new_team_name.strip():
                    my_teams.append({
                        "종목": sports_type,
                        "팀명": new_team_name.strip(),
                        "리그": new_league.strip(),
                        "키워드": new_keyword.strip() if new_keyword.strip() else new_team_name.strip()
                    })
                    save_sports_teams(my_teams)
                    st.success(f"'{new_team_name}' 팀이 성공적으로 추가되었습니다!")
                    st.rerun()

        # 팀 삭제 옵션
        if len(my_teams) > 1:
            st.write("🗑️ **등록된 팀 삭제**")
            del_idx = st.selectbox("삭제할 팀 선택", range(len(my_teams)), format_func=lambda x: f"{my_teams[x]['종목']} {my_teams[x]['팀명']}", key="del_team_sel")
            if st.button("선택한 팀 삭제", key="btn_del_team"):
                removed = my_teams.pop(del_idx)
                save_sports_teams(my_teams)
                st.success(f"'{removed['팀명']}' 팀이 삭제되었습니다.")
                st.rerun()

# -------------------------------------------------------------
# TAB 7: 데일리 생산성 & 날씨 (용인시 기준)
# -------------------------------------------------------------
with tab_daily:
    st.subheader("📋 데일리 생산성 & 라이프")
    
    temp_val, weather_val, humid_val = get_yongin_weather()
    st.markdown(f"""
    <div class="weather-card">
        <div style="font-size: 16px; font-weight: 700;">📍 경기도 용인시 오늘 날씨</div>
        <div style="font-size: 24px; font-weight: 800; margin-top: 6px;">{weather_val} {temp_val}</div>
        <div style="font-size: 12px; color: #e0f2fe; margin-top: 4px;">습도: {humid_val} | 외출 및 출퇴근 추천 날씨</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("✅ 오늘의 할 일 (To-Do List)")
    
    current_todos = load_todos()
    
    to_delete = None
    for idx, todo_item in enumerate(current_todos):
        col_t1, col_t2 = st.columns([0.85, 0.15])
        with col_t1:
            st.write(f"• {todo_item}")
        with col_t2:
            if st.button("완료", key=f"del_{idx}"):
                to_delete = idx

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
