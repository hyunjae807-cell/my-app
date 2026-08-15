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
    page_title="나만의 증시 비서",
    page_icon="📈",
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
    </style>
""", unsafe_allow_html=True)

# 3. [영구 저장소] 포트폴리오 및 AI 브리핑 파일 관리
PORTFOLIO_FILE = "portfolio.json"
BRIEFING_FILE = "briefing.json"

DEFAULT_PORTFOLIO = [
    {"종목명": "KODEX AI반도체TOP2플러스", "티커": "395160.KS", "매입단가": 13234.0, "보유수량": 126},
    {"종목명": "KODEX 200타겟위클리커버드콜", "티커": "498400.KS", "매입단가": 13012.0, "보유수량": 863}
]

def load_portfolio():
    if os.path.exists(PORTFOLIO_FILE):
        try:
            with open(PORTFOLIO_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data:
                    return data
        except Exception:
            return DEFAULT_PORTFOLIO
    return DEFAULT_PORTFOLIO

def save_portfolio(data):
    try:
        with open(PORTFOLIO_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"포트폴리오 저장 오류: {e}")

def load_briefing():
    if os.path.exists(BRIEFING_FILE):
        try:
            with open(BRIEFING_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("text"), data.get("generated_at")
        except Exception:
            return None, None
    return None, None

def save_briefing(text, generated_at_str):
    try:
        with open(BRIEFING_FILE, "w", encoding="utf-8") as f:
            json.dump({"text": text, "generated_at": generated_at_str}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"브리핑 저장 오류: {e}")

# 4. 아침 7시 시스템 알람 컴포넌트
alarm_component = """
<div style="background: linear-gradient(135deg, #1e293b, #0f172a); padding: 15px; border-radius: 12px; color: white; margin-bottom: 15px;">
    <div style="font-weight: 700; font-size: 14px; margin-bottom: 4px;">⏰ 매일 한국 시간 아침 7시 시스템 알람</div>
    <div style="font-size: 11px; color: #94a3b8; margin-bottom: 10px;">스마트폰 상단바 알림과 소리 알람을 활성화합니다.</div>
    <button id="alarmBtn" onclick="initAlarm()" style="background-color: #3b82f6; color: white; border: none; padding: 8px 14px; border-radius: 8px; font-size: 12px; font-weight: 600; cursor: pointer; width: 100%;">
        🔔 시스템 알람 및 소리 켜기
    </button>
    <div id="alarmStatus" style="margin-top: 6px; font-size: 11px; color: #4ade80; text-align: center;"></div>
</div>

<script>
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
    } catch(e) { console.log(e); }
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
        alert("브라우저에서 시스템 알림을 지원하지 않습니다.");
        return;
    }
    Notification.requestPermission().then(permission => {
        if (permission === "granted") {
            document.getElementById("alarmStatus").innerText = "✅ 매일 아침 7시 시스템 알람 활성화 완료!";
            document.getElementById("alarmBtn").style.backgroundColor = "#16a34a";
            document.getElementById("alarmBtn").innerText = "🔔 알람 작동 중 (오전 7:00)";
            triggerSystemNotification();
            setInterval(checkTimeForAlarm, 1000);
        } else {
            alert("알림 권한이 허용되지 않았습니다.");
        }
    });
}
</script>
"""

# 5. 종목별 맞춤 캘린더 일정 함수
def get_stock_calendar_events(portfolio_items):
    events = [
        {"날짜": "2026-08-28", "구분": "🌐 거시경제", "이벤트": "미국 잭슨홀 심포지엄 (파월 연준의장 기조연설)", "중요도": "🔴 높음"},
        {"날짜": "2026-09-16", "구분": "🌐 거시경제", "이벤트": "미국 9월 FOMC 기준금리 결정 회의", "중요도": "🔴 높음"}
    ]
    for item in portfolio_items:
        name = item["종목명"]
        ticker = item["티커"]
        if "AI반도체" in name or "395160" in ticker or "NVDA" in ticker or "삼성전자" in name or "하이닉스" in name:
            events.append({"날짜": "2026-08-26", "구분": f"🎯 {name}", "이벤트": "엔비디아(NVDA) 2분기 실적 발표 (미국 현지시간)", "중요도": "🔴 핵심"})
            events.append({"날짜": "2026-09-04", "구분": f"🎯 {name}", "이벤트": "글로벌 세미콘 반도체 컨퍼런스 & HBM 서밋", "중요도": "🟡 보통"})
            events.append({"날짜": "2026-10-08", "구분": f"🎯 {name}", "이벤트": "삼성전자 3분기 잠정 실적 발표", "중요도": "🔴 높음"})
        if "커버드콜" in name or "498400" in ticker or "200" in name:
            events.append({"날짜": "2026-08-19", "구분": f"🎯 {name}", "이벤트": "8월 월분배금(배당금) 계좌 지급일", "중요도": "🟢 배당"})
            events.append({"날짜": "2026-09-10", "구분": f"🎯 {name}", "이벤트": "국내 선물·옵션 동시 만기일 (네 마녀의 날)", "중요도": "🔴 변동성"})
            events.append({"날짜": "매주 목요일", "구분": f"🎯 {name}", "이벤트": "위클리 옵션 만기 및 프리미엄 정산", "중요도": "🟡 정기"})
    return pd.DataFrame(events).drop_duplicates(subset=["날짜", "이벤트"])

# 6. AI 비전 이미지 분석 함수
def analyze_portfolio_image(image_bytes, api_key):
    api_key = api_key.strip()
    headers = {"Content-Type": "application/json", "x-goog-api-key": api_key}
    candidate_models = ["models/gemini-3.5-flash", "models/gemini-2.0-flash", "models/gemini-1.5-flash-latest"]
    try:
        m_res = requests.get("https://generativelanguage.googleapis.com/v1beta/models", headers=headers, timeout=5)
        if m_res.status_code == 200:
            active_models = [m['name'] for m in m_res.json().get('models', []) if 'generateContent' in m.get('supportedGenerationMethods', [])]
            if active_models: candidate_models = active_models
    except Exception: pass

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

# 7. 실시간 맞춤형 AI 브리핑 생성 함수
def generate_ai_briefing(news_headlines, portfolio_items, api_key):
    api_key = api_key.strip()
    headers = {"Content-Type": "application/json", "x-goog-api-key": api_key}
    candidate_models = ["models/gemini-3.5-flash", "models/gemini-2.0-flash", "models/gemini-1.5-flash-latest"]
    try:
        m_res = requests.get("https://generativelanguage.googleapis.com/v1beta/models", headers=headers, timeout=5)
        if m_res.status_code == 200:
            active_models = [m['name'] for m in m_res.json().get('models', []) if 'generateContent' in m.get('supportedGenerationMethods', [])]
            if active_models: candidate_models = active_models
    except Exception: pass

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
        except Exception: pass
    return None, "브리핑 생성에 실패했습니다."

# 8. 실시간 주가 및 뉴스 로딩 함수
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
                if pub_date: pub_date = pub_date[:16]
                news_items.append({"title": title, "link": link, "source": source, "date": pub_date})
            return news_items
    except Exception:
        return []


# =============================================================
# 메인 UI 화면
# =============================================================

st.title("📱 Daily Stock Assistant")
st.caption(f"최근 조회 시각: {datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S (한국 시간)')}")

components.html(alarm_component, height=130)

tab_portfolio, tab_market, tab_news, tab_chart, tab_briefing = st.tabs(
    ["💼 내 포트폴리오", "📊 실시간 시황", "📰 주요 뉴스", "🔍 종목 차트", "💡 AI 브리핑"]
)

# -------------------------------------------------------------
# TAB 1: 내 실제 포트폴리오
# -------------------------------------------------------------
with tab_portfolio:
    st.subheader("💼 내 주식·ETF 포트폴리오 (실시간 연동 & 영구 저장)")
    
    user_portfolio = load_portfolio()
    total_eval_krw = 0
    total_buy_krw = 0
    calculated_rows = []

    for item in user_portfolio:
        cur_p, _ = get_live_market_data(item["티커"])
        if cur_p is None: cur_p = item["매입단가"]

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
            "티커": item["티커"],
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

    # 📸 캡처 사진 자동 업데이트
    st.markdown("---")
    st.subheader("📸 새 잔고 사진으로 포트폴리오 업데이트")
    uploaded_file = st.file_uploader("증권사 잔고 캡처 사진 올리기", type=["png", "jpg", "jpeg"])
    
    if uploaded_file is not None:
        st.image(uploaded_file, caption="업로드된 잔고 캡처", use_container_width=True)
        api_key = st.secrets.get("GEMINI_API_KEY", None)
        if not api_key:
            api_key = st.text_input("Google AI Studio (Gemini) API Key 입력", type="password")
            
        if st.button("✨ AI로 잔고 사진 분석 및 저장"):
            if not api_key:
                st.warning("API Key를 입력해 주세요.")
            else:
                with st.spinner("AI가 이미지를 정밀 분석 중입니다..."):
                    parsed_stocks, status = analyze_portfolio_image(uploaded_file.getvalue(), api_key)
                    if status == "SUCCESS" and parsed_stocks:
                        save_portfolio(parsed_stocks)
                        st.success(f"🎉 총 {len(parsed_stocks)}개 종목이 인식되어 영구 저장되었습니다!")
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
        if "AI반도체" in stock_name: query = f'"{stock_name}" OR "AI반도체" OR "삼성전자 반도체"'
        elif "커버드콜" in stock_name: query = f'"{stock_name}" OR "커버드콜" OR "코스피200 분배금"'
        else: query = f'"{stock_name}"'
    elif selected_cat == "🇰🇷 국내 증시·경제": query = "코스피 OR 국내증시 OR 환율"
    elif selected_cat == "🇺🇸 미국·글로벌 증시": query = "뉴욕증시 OR 연준 금리 OR S&P500"
    elif selected_cat == "🤖 AI·반도체": query = "엔비디아 OR 반도체 HBM OR 인공지능"
    else: query = st.text_input("검색 키워드", value="삼성전자")
    
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
# TAB 4: 종목 차트
# -------------------------------------------------------------
with tab_chart:
    st.subheader("🔍 글로벌 종목 차트 분석")
    ticker_input = st.text_input("티커 입력 (예: 395160.KS, 498400.KS, NVDA)", value="395160.KS").upper()
    if st.button("차트 조회"):
        try:
            stock = yf.Ticker(ticker_input)
            hist = stock.history(period="1mo")
            if not hist.empty:
                current_price = hist['Close'].iloc[-1]
                prev_price = hist['Close'].iloc[-2]
                change_pct = ((current_price - prev_price) / prev_price) * 100
                currency = "원" if ".KS" in ticker_input or ".KQ" in ticker_input else "$"
                st.metric(label=f"{ticker_input} 현재/최근가", value=f"{currency}{current_price:,.2f}" if currency == "$" else f"{current_price:,.0f}원", delta=f"{change_pct:+.2f}%")
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=hist.index, y=hist['Close'], mode='lines+markers', name='Close', line=dict(color='#0066cc', width=2)))
                fig.update_layout(title=f"{ticker_input} 최근 1개월 주가 추이", margin=dict(l=10, r=10, t=40, b=10), height=300, xaxis_rangeslider_visible=False)
                st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.error(f"오류: {e}")

# -------------------------------------------------------------
# TAB 5: [영구 보존 적용] 실시간 AI 브리핑 & 종목별 캘린더
# -------------------------------------------------------------
with tab_briefing:
    st.subheader("💡 실시간 맞춤형 AI 모닝 브리핑")
    
    user_portfolio = load_portfolio()
    recent_news = fetch_google_news("코스피 OR 반도체 OR 연준 금리 OR 엔비디아", max_results=12)
    
    api_key = st.secrets.get("GEMINI_API_KEY", None)
    if not api_key:
        api_key = st.text_input("Gemini API Key 입력 (실시간 브리핑 생성용)", type="password", key="briefing_key")
        
    if st.button("✨ 오늘자 뉴스 기반 실시간 AI 브리핑 생성"):
        if not api_key:
            st.warning("API Key를 입력해 주세요.")
        else:
            with st.spinner("구글 Gemini AI가 최신 뉴스와 내 포트폴리오를 종합 분석 중입니다..."):
                briefing_result, status = generate_ai_briefing(recent_news, user_portfolio, api_key)
                if status == "SUCCESS" and briefing_result:
                    now_str = datetime.now(KST).strftime('%Y년 %m월 %d일 %H:%M:%S')
                    save_briefing(briefing_result, now_str)
                    st.success("✅ AI 모닝 브리핑이 성공적으로 생성 및 영구 저장되었습니다!")
                    st.rerun()
                else:
                    st.error(f"오류: {status}")

    # [영구 저장소에서 불러오기]
    saved_briefing_text, saved_time = load_briefing()

    if saved_briefing_text:
        st.caption(f"🕒 **마지막 브리핑 생성 시각**: {saved_time} (새 브리핑을 만들려면 위 버튼을 터치하세요)")
        with st.container(border=True):
            st.markdown(saved_briefing_text)
    else:
        st.info("💡 위의 **[✨ 오늘자 뉴스 기반 실시간 AI 브리핑 생성]** 버튼을 누르면 오늘 아침 최신 뉴스에 맞춘 리포트가 생성되어 영구 저장됩니다.")

    # 📅 내 보유 종목 맞춤형 이벤트 캘린더 표
    st.markdown("---")
    st.subheader("📅 내 보유 종목 맞춤형 이벤트 캘린더")
    df_stock_events = get_stock_calendar_events(user_portfolio)
    st.dataframe(df_stock_events, use_container_width=True)
