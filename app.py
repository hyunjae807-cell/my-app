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

# 2. 실시간 구글 뉴스 RSS 파싱 함수 (외부 라이브러리 추가 불필요)
@st.cache_data(ttl=600)  # 10분 캐싱
def fetch_google_news(query, max_results=6):
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
                
                # 날짜 간소화
                if pub_date:
                    pub_date = pub_date[:16]

                news_items.append({
                    "title": title,
                    "link": link,
                    "source": source,
                    "date": pub_date
                })
            return news_items
    except Exception as e:
        return []

# 헤더
st.title("📱 Daily Stock Assistant")
st.caption(f"기준 시각: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

# 4개 탭 구성
tab1, tab2, tab3, tab4 = st.tabs(["📊 시장 요약", "📰 주요 뉴스", "🔍 종목 조회", "💡 AI 브리핑"])

# -------------------------------------------------------------
# TAB 1: 주요 지수 및 대형주 시황
# -------------------------------------------------------------
with tab1:
    st.subheader("🌐 글로벌 & 국내 주요 지수")
    c1, c2 = st.columns(2)
    with c1:
        st.metric(label="코스피 (KOSPI)", value="6,977.94", delta="+2.42%")
        st.metric(label="S&P 500", value="5,554.20", delta="-0.20%")
    with c2:
        st.metric(label="나스닥 (NASDAQ)", value="17,594.50", delta="+0.12%")
        st.metric(label="브렌트유 (Oil)", value="$88.59", delta="+1.75%")

    st.markdown("---")
    st.subheader("🏢 주요 대형주 시세")
    ca, cb = st.columns(2)
    with ca:
        st.metric(label="삼성전자 (005930)", value="84,500원", delta="+2.43%")
        st.metric(label="SK하이닉스 (000660)", value="193,000원", delta="+3.30%")
    with cb:
        st.metric(label="현대차 (005380)", value="256,000원", delta="+8.24%")
        st.metric(label="엔비디아 (NVDA)", value="$224.92", delta="-0.18%")

# -------------------------------------------------------------
# TAB 2: [신규] 실시간 주요 뉴스 확인란
# -------------------------------------------------------------
with tab2:
    st.subheader("📰 실시간 핵심 뉴스 피드")
    
    # 뉴스 카테고리 선택
    news_category = st.radio(
        "카테고리 선택", 
        ["🇰🇷 국내 증시·경제", "🇺🇸 미국·글로벌 증시", "🤖 AI·반도체", "🔍 직접 검색"], 
        horizontal=True
    )
    
    if news_category == "🇰🇷 국내 증시·경제":
        query = "코스피 OR 국내증시 OR 한국은행 환율"
    elif news_category == "🇺🇸 미국·글로벌 증시":
        query = "미국증시 OR 뉴욕증시 OR 연준 금리 S&P500"
    elif news_category == "🤖 AI·반도체":
        query = "엔비디아 OR 반도체 HBM OR 인공지능 빅테크"
    else:
        query = st.text_input("검색할 뉴스 키워드를 입력하세요", value="삼성전자")
    
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
            st.info("최신 뉴스를 불러오는 중입니다. 잠시 후 다시 확인해 주세요.")

# -------------------------------------------------------------
# TAB 3: 종목 실시간 차트 & 시세 조회
# -------------------------------------------------------------
with tab3:
    st.subheader("🔍 미국/글로벌 주식 차트")
    ticker_input = st.text_input("티커(Ticker) 입력 (예: AAPL, NVDA, TSLA)", value="NVDA").upper()
    
    if st.button("조회하기"):
        try:
            stock = yf.Ticker(ticker_input)
            hist = stock.history(period="1mo")
            
            if not hist.empty:
                current_price = hist['Close'].iloc[-1]
                prev_price = hist['Close'].iloc[-2]
                change_pct = ((current_price - prev_price) / prev_price) * 100
                
                st.metric(
                    label=f"{ticker_input} 최근 종가", 
                    value=f"${current_price:.2f}", 
                    delta=f"{change_pct:.2f}%"
                )
                
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=hist.index, 
                    y=hist['Close'], 
                    mode='lines+markers',
                    name='Close Price',
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
                st.warning("데이터를 불러올 수 없습니다. 티커를 다시 확인해 주세요.")
        except Exception as e:
            st.error(f"조회 중 오류 발생: {e}")

# -------------------------------------------------------------
# TAB 4: 핵심 요약 & 캘린더 브리핑
# -------------------------------------------------------------
with tab4:
    st.subheader("📌 시장 핵심 이슈 브리핑")
    with st.expander("1. 미국 매크로: 인플레이션 안정 vs 소비 둔화", expanded=True):
        st.write("7월 소매판매(-0.6%) 및 소비자심리지수 하락으로 경기 둔화 우려 대두. 8월 28일 잭슨홀 미팅 주목.")
    with st.expander("2. AI 반도체: 엔비디아 실적(8/26) & 데이터센터", expanded=True):
        st.write("블랙웰 출하 일정 및 AI ROI 검증 국면 진입. 오픈AI 데이터센터 보증 축소 이슈 점검.")
    with st.expander("3. 국내 증시: 외국인 3조 원 순매수"):
        st.write("반도체·자동차 대형주 중심 수급 유입. 코스피 7,000선 안착 시도.")
    
    st.markdown("---")
    st.info("📅 **주요 일정**\n• **8월 26일**: 엔비디아 실적 발표\n• **8월 28일**: 잭슨홀 심포지엄 (파월 연준의장 연설)")
st.caption(f"기준 시각: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

# 탭 구성
tab1, tab2, tab3 = st.tabs(["📊 시장 요약", "📰 핵심 브리핑", "🔍 종목 조회"])

# TAB 1: 주요 지수 및 대형주 시황
with tab1:
    st.subheader("🌐 글로벌 & 국내 주요 지수")
    c1, c2 = st.columns(2)
    with c1:
        st.metric(label="코스피 (KOSPI)", value="6,977.94", delta="+2.42%")
        st.metric(label="S&P 500", value="5,554.20", delta="-0.20%")
    with c2:
        st.metric(label="나스닥 (NASDAQ)", value="17,594.50", delta="+0.12%")
        st.metric(label="브렌트유 (Oil)", value="$88.59", delta="+1.75%")

    st.markdown("---")
    st.subheader("🏢 주요 대형주 시세")
    ca, cb = st.columns(2)
    with ca:
        st.metric(label="삼성전자 (005930)", value="84,500원", delta="+2.43%")
        st.metric(label="SK하이닉스 (000660)", value="193,000원", delta="+3.30%")
    with cb:
        st.metric(label="현대차 (005380)", value="256,000원", delta="+8.24%")
        st.metric(label="엔비디아 (NVDA)", value="$224.92", delta="-0.18%")

# TAB 2: 오늘자 핵심 뉴스 & AI 브리핑
with tab2:
    st.subheader("📌 오늘의 3대 핵심 이슈")
    
    with st.expander("1. 🇺🇸 미국 매크로: 인플레이션 안정 vs 소비 둔화", expanded=True):
        st.write("""
        * **현황**: 7월 CPI·PPI 둔화로 물가 압력은 완화되었으나, 7월 소매판매(-0.6%)와 8월 미시간대 소비자심리지수(51.0)가 동반 하락하며 소비 둔화 우려 부각.
        * **관전 포인트**: 8월 28일 잭슨홀 심포지엄에서 제롬 파월 의장의 9월 금리 정책 가이던스에 주목.
        """)

    with st.expander("2. 🤖 AI 반도체: 엔비디아 실적 대기 & 데이터센터 보증 이슈", expanded=True):
        st.write("""
        * **현황**: 엔비디아 2분기 실적 발표(8월 26일)를 앞두고 차세대 블랙웰 칩 납품 일정과 빅테크 CAPEX 지속성 점검.
        * **이슈**: 오픈AI 오하이오 데이터센터 채무 보증 축소 협의로 AI 산업의 실질적 수익성(ROI) 검증 국면 진입.
        """)

    with st.expander("3. 🇰🇷 국내 증시: 외국인 3조 원 폭풍 매수 & 7천피 안착 시도"):
        st.write("""
        * **현황**: 외국인이 반도체(삼성전자·SK하이닉스)와 현대차를 집중 매수하며 코스피 지수를 5거래일 연속 견인.
        * **전략**: 대형주 수급이 코스닥 및 소부장 중소형주로 확산되는지 여부 관찰 필요.
        """)

    st.markdown("---")
    st.subheader("📅 주요 일정 캘린더")
    st.info("• **8월 26일**: 엔비디아 2분기 실적 발표 (미국 현지시간)\n• **8월 28일**: 잭슨홀 심포지엄 (파월 의장 연설)")

# TAB 3: 실시간 종목 차트 및 시세 검색
with tab3:
    st.subheader("🔍 미국/글로벌 주식 검색")
    ticker_input = st.text_input("티커(Ticker) 입력 (예: AAPL, NVDA, TSLA)", value="NVDA").upper()
    
    if st.button("조회하기"):
        try:
            stock = yf.Ticker(ticker_input)
            hist = stock.history(period="1mo")
            
            if not hist.empty:
                current_price = hist['Close'].iloc[-1]
                prev_price = hist['Close'].iloc[-2]
                change_pct = ((current_price - prev_price) / prev_price) * 100
                
                st.metric(
                    label=f"{ticker_input} 최근 종가", 
                    value=f"${current_price:.2f}", 
                    delta=f"{change_pct:.2f}%"
                )
                
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=hist.index, 
                    y=hist['Close'], 
                    mode='lines+markers',
                    name='Close Price',
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
                st.warning("데이터를 불러올 수 없습니다. 티커를 다시 확인해 주세요.")
        except Exception as e:
            st.error(f"조회 중 오류 발생: {e}")
