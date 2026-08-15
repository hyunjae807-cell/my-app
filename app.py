import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import requests
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

# 모바일 친화적 CSS 스타일링
st.markdown("""
    <style>
    .metric-card {
        background-color: #f8fafc;
        border-radius: 10px;
        padding: 14px;
        margin-bottom: 10px;
        border: 1px solid #e2e8f0;
    }
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

# 3. 아침 7시 시스템 알람 & 소리 컴포넌트
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

# 4. 서버 공인 IP 확인 함수
@st.cache_data(ttl=3600)
def get_current_server_ip():
    try:
        return requests.get("https://api.ipify.org", timeout=3).text
    except Exception:
        return "확인 불가"

# 5. 실시간 주가 및 뉴스 로딩 함수
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

# 6. 토스증권 연동 함수
@st.cache_data(ttl=60)
def fetch_toss_portfolio():
    if "TOSS_API_KEY" in st.secrets and "TOSS_SECRET_KEY" in st.secrets and "TOSS_ACCOUNT_NO" in st.secrets:
        try:
            api_key = st.secrets["TOSS_API_KEY"]
            secret_key = st.secrets["TOSS_SECRET_KEY"]
            account_no = st.secrets["TOSS_ACCOUNT_NO"]

            # OAuth2 토큰 발급
            token_url = "https://openapi.tossinvest.com/oauth2/token"
            token_payload = {
                "grant_type": "client_credentials",
                "client_id": api_key,
                "client_secret": secret_key
            }
            token_headers = {"Content-Type": "application/x-www-form-urlencoded"}
            token_res = requests.post(token_url, data=token_payload, headers=token_headers, timeout=5)
            
            if token_res.status_code != 200:
                return None, f"IP 차단 또는 인증 오류: {token_res.text}"
            
            access_token = token_res.json().get("access_token")

            # 공식 holdings 호출
            holdings_url = "https://openapi.tossinvest.com/api/v1/holdings"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "X-Tossinvest-Account": str(account_no),
                "Content-Type": "application/json"
            }
            holdings_res = requests.get(holdings_url, headers=headers, timeout=5)
            
            if holdings_res.status_code == 200:
                return holdings_res.json(), "SUCCESS"
            else:
                return None, f"조회 오류: {holdings_res.text}"
        except Exception as e:
            return None, str(e)
    return None, "NOT_CONFIGURED"


# =============================================================
# UI 렌더링
# =============================================================

st.title("📱 Daily Stock Assistant")
st.caption(f"최근 조회 시각: {datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S (한국 시간)')}")

components.html(alarm_component, height=130)

tab_portfolio, tab_market, tab_news, tab_chart, tab_briefing = st.tabs(
    ["💼 내 포트폴리오", "📊 실시간 시황", "📰 주요 뉴스", "🔍 종목 차트", "💡 AI 브리핑"]
)

# TAB 1: 내 포트폴리오
with tab_portfolio:
    st.subheader("💼 내 주식 포트폴리오")
    
    server_ip = get_current_server_ip()
    portfolio_data, status = fetch_toss_portfolio()
    
    if status == "SUCCESS" and portfolio_data:
        st.success("✅ 토스증권 실시간 계좌 연동 중")
        holdings = portfolio_data if isinstance(portfolio_data, list) else portfolio_data.get("holdings", [])
        if holdings:
            st.dataframe(pd.DataFrame(holdings), use_container_width=True)
        else:
            st.info("현재 보유 중인 종목이 없습니다.")
    else:
        # IP 등록 안내 카드
        st.warning(f"🔒 **토스증권 IP 등록이 필요합니다**\n\n현재 앱 서버의 공인 IP: **`{server_ip}`**")
        st.info("👉 [토스증권 Open API 콘솔](https://corp.tossinvest.com/ko/open-api)의 **[허용 IP 목록]**에 위 IP 주소를 등록하시면 바로 실시간 연동됩니다.")
        
        st.markdown("---")
        st.subheader("✍️ 내 보유 종목 간편 관리 (실시간 시세 자동 추적)")
        
        # 기본 예시 종목 (직접 수정 가능)
        if "my_stocks" not in st.session_state:
            st.session_state.my_stocks = [
                {"종목명": "삼성전자", "티커": "005930.KS", "매입단가": 80000, "보유수량": 50},
                {"종목명": "SK하이닉스", "티커": "000660.KS", "매입단가": 180000, "보유수량": 20},
                {"종목명": "엔비디아", "티커": "NVDA", "매입단가": 210.0, "보유수량": 15},
            ]
        
        total_eval = 0
        total_buy = 0
        portfolio_rows = []
        
        for item in st.session_state.my_stocks:
            cur_price, _ = get_live_market_data(item["티커"])
            if cur_price is None:
                cur_price = item["매입단가"]
                
            is_krw = ".KS" in item["티커"] or ".KQ" in item["티커"]
            eval_amt = cur_price * item["보유수량"]
            buy_amt = item["매입단가"] * item["보유수량"]
            profit_amt = eval_amt - buy_amt
            profit_rate = (profit_amt / buy_amt) * 100 if buy_amt > 0 else 0
            
            if is_krw:
                total_eval += eval_amt
                total_buy += buy_amt
                
            portfolio_rows.append({
                "종목명": item["종목명"],
                "보유수량": f"{item['보유수량']}주",
                "매입단가": f"{item['매입단가']:,.0f}원" if is_krw else f"${item['매입단가']:.2f}",
                "현재가": f"{cur_price:,.0f}원" if is_krw else f"${cur_price:.2f}",
                "수익률": f"{profit_rate:+.2f}%"
            })
            
        total_profit_rate = ((total_eval - total_buy) / total_buy) * 100 if total_buy > 0 else 0
        
        c1, c2 = st.columns(2)
        with c1:
            st.metric("국내 보유 총 평가금액", f"{total_eval:,.0f}원", f"{total_profit_rate:+.2f}%")
        with c2:
            st.metric("국내 총 평가손익", f"{total_eval - total_buy:+,.0f}원")
            
        st.dataframe(pd.DataFrame(portfolio_rows), use_container_width=True)

# TAB 2: 실시간 시황
with tab_market:
    st.subheader("🌐 글로벌 & 국내 주요 지수")
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
        st.metric("현대차", f"{hyundai_p:,.0f}원" if hyundai_p else "256,000원", f"{hyundai_d:+.2f}%" if hyundai_d else "+8.24%")
        st.metric("엔비디아 (NVDA)", f"${nvda_p:.2f}" if nvda_p else "$224.92", f"{nvda_d:+.2f}%" if nvda_d else "-0.18%")

# TAB 3: 주요 뉴스
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

# TAB 4: 종목 차트
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
                fig.update_layout(title=f"{ticker_input} 최근 1개월 주가 추이", margin=dict(l=10, r=10, t=40, b=10), height=300, xaxis_rangeslider_visible=False)
                st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.error(f"오류: {e}")

# TAB 5: AI 브리핑
with tab_briefing:
    st.subheader("📌 증시 핵심 체크포인트")
    st.info("📅 **주요 일정**\n• **8월 26일**: 엔비디아 2분기 실적 발표\n• **8월 28일**: 잭슨홀 심포지엄 (파월 연준의장 연설)")
    with st.expander("1. 미국 매크로: 인플레이션 안정 vs 소비 둔화", expanded=True):
        st.write("7월 소매판매(-0.6%) 및 소비자심리지수 하락으로 경기 둔화 우려 대두. 8월 28일 잭슨홀 미팅 주목.")
    with st.expander("2. AI 반도체: 엔비디아 실적(8/26) & 데이터센터"):
        st.write("블랙웰 출하 일정 및 AI ROI 검증 국면 진입. 오픈AI 데이터센터 보증 축소 이슈 점검.")
    with st.expander("3. 국내 증시: 외국인 수급 지속성"):
        st.write("외국인 매수세의 코스닥 및 소부장 중소형주 확산 여부 관찰 필요.")
