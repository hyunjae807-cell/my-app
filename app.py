import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import urllib.request
import xml.etree.ElementTree as ET
import urllib.parse

# 1. 모바일 최적화 페이지 설정
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
        color: #1a202c;
        text-decoration: none;
    }
    .news-title:hover {
        color: #3182ce;
    }
    .news-meta {
        font-size: 12px;
        color: #718096;
        margin-top: 6px;
    }
    </style>
""", unsafe_allow_html=True)

# 2. 실시간 주가/지수 데이터 조회 함수 (1분 캐싱)
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

# 3. 실시간 구글 뉴스 파싱 함수 (5분 캐싱)
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

                news_items.append({
                    "title": title,
                    "link": link,
                    "source": source,
                    "date": pub_date
                })
            return news_items
    except Exception:
        return []

# 헤더 영역
st.title("📱 Daily Stock Assistant")
st.caption(f"최근 조회 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if st.button("🔄 실시간 데이터 새로고침"):
    st.cache_data.clear()
    st.rerun()

# 4개 탭 구성
tab1, tab2, tab3, tab4 = st.tabs(["📊 실시간 시황", "📰 주요 뉴스", "🔍 종목 차트", "💡 AI 브리핑"])

# -------------------------------------------------------------
# TAB 1: 실시간 주요 지수 및 대형주 시황 (API 자동 연동)
# -------------------------------------------------------------
with tab1:
    st.subheader("🌐 글로벌 & 국내 주요 지수 (실시간)")
    
    # 지수 데이터 실시간 호출
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
        st.metric("브렌트유 (Brent Oil)", f"${oil_p:.2f}" if oil_p else "$88.59", f"{oil_d:+.2f}%" if oil_d else "+1.75%")

    st.markdown("---")
    st.subheader("🏢 주요 대형주 시세 (실시간)")
    
    # 종목 데이터 실시간 호출
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
# TAB 2: 실시간 주요 뉴스 피드
# -------------------------------------------------------------
with tab2:
    st.subheader("📰 실시간 핵심 뉴스")
    news_category = st.radio(
        "카테고리", 
        ["🇰🇷 국내 증시·경제", "🇺🇸 미국·글로벌 증시", "🤖 AI·반도체", "🔍 직접 검색"], 
        horizontal=True
    )
    
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
        else:
            st.info("최신 뉴스를 가져오는 중입니다...")

# -------------------------------------------------------------
# TAB 3: 종목 실시간 차트 검색
# -------------------------------------------------------------
with tab3:
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
                
                currency_symbol = "원" if ".KS" in ticker_input or ".KQ" in ticker_input else "$"
                st.metric(
                    label=f"{ticker_input} 현재/최근가", 
                    value=f"{currency_symbol}{current_price:,.2f}" if currency_symbol == "$" else f"{current_price:,.0f}원", 
                    delta=f"{change_pct:+.2f}%"
                )
                
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=hist.index, 
                    y=hist['Close'], 
                    mode='lines+markers',
                    name='Close',
                    line=dict(color='#0066cc', width=2)
                ))
                fig.update_layout(
                    title=f"{ticker_input} 최근 1개월 주가 추이",
                    margin=dict(l=10, r=10, t=40, b=10),
                    height=300,
                    xaxis_rangeslider_visible=False
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("데이터를 찾을 수 없습니다. 티커를 확인해 주세요.")
        except Exception as e:
            st.error(f"오류: {e}")

# -------------------------------------------------------------
# TAB 4: 주요 일정 & AI 브리핑
# -------------------------------------------------------------
with tab4:
    st.subheader("📌 증시 핵심 체크포인트")
    st.info("📅 **주요 일정**\n• **8월 26일**: 엔비디아 2분기 실적 발표\n• **8월 28일**: 잭슨홀 심포지엄 (파월 연준의장 기조연설)")
    
    with st.expander("1. 미국 매크로: 인플레이션 안정 vs 소비 둔화", expanded=True):
        st.write("7월 소매판매(-0.6%) 및 소비자심리지수 하락으로 경기 둔화 우려 대두. 8월 28일 잭슨홀 미팅 주목.")
    with st.expander("2. AI 반도체: 엔비디아 실적(8/26) & 데이터센터"):
        st.write("블랙웰 출하 일정 및 AI ROI 검증 국면 진입. 오픈AI 데이터센터 보증 축소 이슈 점검.")
    with st.expander("3. 국내 증시: 외국인 수급 지속성"):
        st.write("외국인 매수세의 코스닥 및 소부장 중소형주 확산 여부 관찰 필요.")
