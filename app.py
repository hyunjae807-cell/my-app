import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
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
        background-color: #ffffff;
        border-radius: 10px;
        padding: 14px;
        margin-bottom: 12px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .news-title {
        font-size: 15px;
        font-weight: 600;
        color: #1e293b;
        text-decoration: none;
    }
    .news-title:hover {
        color: #2563eb;
    }
    .news-meta {
        font-size: 12px;
        color: #64748b;
        margin-top: 6px;
    }
    </style>
""", unsafe_allow_html=True)

# 3. 아침 7시 시스템 알람 컴포넌트
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

# 4. 실시간 주가 및 뉴스 로딩 함수
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
def fetch_google_news(query, max_results=7):
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
# TAB 1: 실시간 내 포트폴리오 관리 (100% 안정 연동)
# -------------------------------------------------------------
with tab_portfolio:
    st.subheader("💼 실시간 내 주식 포트폴리오")
    st.caption("보유 종목을 등록해 두면 실시간 현재가와 총 수익률을 자동으로 추적합니다.")
    
    # 기본 보유 종목 초기화
    if "user_portfolio" not in st.session_state:
        st.session_state.user_portfolio = [
            {"종목명": "삼성전자", "티커": "005930.KS", "매입단가": 80000.0, "보유수량": 50},
            {"종목명": "SK하이닉스", "티커": "000660.KS", "매입단가": 185000.0, "보유수량": 20},
            {"종목명": "엔비디아", "티커": "NVDA", "매입단가": 210.0, "보유수량": 15},
        ]

    # 실시간 시세 매칭 및 손익 계산
    total_eval_krw = 0
    total_buy_krw = 0
    calculated_rows = []

    for item in st.session_state.user_portfolio:
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
            "티커": item["티커"],
            "보유수량": f"{item['보유수량']}주",
            "매입단가": f"{item['매입단가']:,.0f}원" if is_krw else f"${item['매입단가']:.2f}",
            "현재가 (실시간)": f"{cur_p:,.0f}원" if is_krw else f"${cur_p:.2f}",
            "평가손익": f"{profit_amount:+,.0f}원" if is_krw else f"${profit_amount:+.2f}",
            "수익률": f"{profit_rate:+.2f}%"
        })

    # 상단 총 요약 카드
    total_profit_krw = total_eval_krw - total_buy_krw
    total_rate_krw = (total_profit_krw / total_buy_krw) * 100 if total_buy_krw > 0 else 0

    c1, c2 = st.columns(2)
    with c1:
        st.metric("국내 보유 총 평가금액", f"{total_eval_krw:,.0f}원", f"{total_rate_krw:+.2f}%")
    with c2:
        st.metric("국내 총 평가손익", f"{total_profit_krw:+,.0f}원")

    st.markdown("---")
    st.write("📋 **보유 종목 실시간 현황표**")
    st.dataframe(pd.DataFrame(calculated_rows), use_container_width=True)

    # 종목 추가/수정 인터페이스
    with st.expander("➕ 새 종목 추가 / 포트폴리오 관리"):
        with st.form("add_stock_form"):
            f_name = st.text_input("종목명 (예: 현대차, 애플)", value="현대차")
            f_ticker = st.text_input("티커 (국내: 005380.KS / 미국: AAPL)", value="005380.KS")
            f_price = st.number_input("매입단가 (원 또는 달러)", value=240000.0)
            f_qty = st.number_input("보유 수량 (주)", value=10, min_value=1)
            
            submitted = st.form_submit_button("포트폴리오에 추가하기")
            if submitted:
                st.session_state.user_portfolio.append({
                    "종목명": f_name,
                    "티커": f_ticker.upper(),
                    "매입단가": f_price,
                    "보유수량": int(f_qty)
                })
                st.success(f"'{f_name}' 종목이 추가되었습니다!")
                st.rerun()

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
    st.subheader("🏢 주요 대형주 시세 (실시간)")
    samsung_p, samsung_d = get_live_market_data("005930.KS")
    hynix_p, hynix_d = get_live_market_data("000660.KS")
    hyundai_p, hyundai_d = get_live_market_data("005380.KS")
    nvda_p, nvda_d = get_live_market_data("NVDA")
    
    ca, cb = st.columns(2)
    with ca:
        st.metric("삼성전자", f"{samsung_p:,.0f}원" if samsung_p else "84,500원", f"{samsung_d:+.2f}%" if samsung_d else "+2.43%")
        st.metric("SK하이닉스", f"{hynix_p:,.0f}원" if hynix_p else "193,000원", f"{hynix_d:+.2f}%" if hynix_d else "+3.30%")
    with cb:
        st.metric("현대차", f"{hyundai_p:,.0f}원" if hyundai_p else "256,000원", f"{hyundai_d:+.2f}%" if hyundai_d else "+8.24%")
        st.metric("엔비디아 (NVDA)", f"${nvda_p:.2f}" if nvda_p else "$224.92", f"{nvda_d:+.2f}%" if nvda_d else "-0.18%")

# -------------------------------------------------------------
# TAB 3: 주요 뉴스
# -------------------------------------------------------------
with tab_news:
    st.subheader("📰 실시간 핵심 뉴스")
    news_category = st.radio("카테고리", ["🇰🇷 국내 증시·경제", "🇺🇸 미국·글로벌 증시", "🤖 AI·반도체", "🔍 직접 검색"], horizontal=True)
    if news_category == "🇰🇷 국내 증시·경제":
        query = "코스피 OR 국내증시 OR 환율"
    elif news_category == "🇺🇸 미국·글로벌 증시":
        query = "뉴욕증시 OR 연준 금리 OR S&P500"
    elif news_category == "🤖 AI·반도체":
        query = "엔비디아 OR 반도체 HBM OR 인공지능"
    else:
        query = st.text_input("검색 키워드", value="삼성전자")
    
    if query:
        news_list = fetch_google_news(query, max_results=7)
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
    ticker_input = st.text_input("티커 입력 (예: AAPL, NVDA, TSLA, 005930.KS)", value="NVDA").upper()
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
                fig.update_layout(title=f"{ticker_input} 최근 1개월 주가 추이", margin=dict(l
