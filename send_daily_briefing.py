import os
import json
import requests
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))

# ==========================================
# 1. 카카오톡 액세스 토큰 갱신
# ==========================================
def refresh_kakao_token(client_id, client_secret, refresh_token):
    url = "https://kauth.kakao.com/oauth/token"
    data = {
        "grant_type": "refresh_token",
        "client_id": client_id,
        "refresh_token": refresh_token
    }
    if client_secret:
        data["client_secret"] = client_secret
        
    res = requests.post(url, data=data, timeout=10)
    if res.status_code == 200:
        token_data = res.json()
        return token_data.get("access_token")
    else:
        print(f"카카오 토큰 갱신 실패: {res.status_code} - {res.text}")
        return None

# ==========================================
# 2. 날씨 정보 수집 (용인시 기준)
# ==========================================
def get_weather(lat=37.2410, lon=127.1775):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,weather_code&timezone=Asia%2FSeoul"
        res = requests.get(url, timeout=5).json()
        cur = res.get("current", {})
        temp = cur.get("temperature_2m", 20.0)
        hum = cur.get("relative_humidity_2m", 70)
        code = cur.get("weather_code", 0)
        
        desc = "맑음"
        if code in (1, 2): desc = "구름 조금"
        elif code == 3: desc = "흐림"
        elif code in (51, 53, 55, 61, 63, 65, 80, 81, 82): desc = "비"
        elif code in (71, 73, 75, 85, 86): desc = "눈"
        
        return f"용인시 {desc}, 현재 {temp:.1f}°C, 습도 {hum}%"
    except Exception:
        return "용인시 맑음, 약 22°C"

# ==========================================
# 3. TimeTree 일정 가져오기
# ==========================================
def get_timetree_today(timetree_token, calendar_id):
    today_str = datetime.now(KST).strftime('%Y-%m-%d')
    events = []
    if not timetree_token or not calendar_id:
        return "TimeTree 설정 미등록"
        
    try:
        url = f"https://timetreeapis.com/calendars/{calendar_id}/upcoming_events?timezone=Asia/Seoul&days=1"
        headers = {
            "Accept": "application/vnd.timetree.v1+json",
            "Authorization": f"Bearer {timetree_token}"
        }
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            data = res.json().get("data", [])
            for item in data:
                attr = item.get("attributes", {})
                start_at = attr.get("start_at", "")
                if start_at.startswith(today_str):
                    t_str = start_at[11:16] if len(start_at) >= 16 else "종일"
                    events.append(f"• [{t_str}] {attr.get('title')}")
    except Exception as e:
        print(f"TimeTree 수집 에러: {e}")
        
    if events:
        return "\n".join(events)
    return "오늘 예정된 주요 일정이 없습니다."

# ==========================================
# 4. Gemini를 통한 고밀도 상세 브리핑 작성 (850~950자)
# ==========================================
def make_ai_briefing(weather_str, timetree_events_str, api_key):
    today_kst = datetime.now(KST).strftime('%Y년 %m월 %d일')
    weekday_kr = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"][datetime.now(KST).weekday()]
    
    prompt = f"""
    당신은 직장인 투자자 이현재 님의 스마트 비서 AI 'MORI'입니다.
    오늘자 실시간 아침 브리핑을 작성해주세요.

    [분량 및 스타일 규칙 - 매우 중요]
    - 전체 분량은 반드시 공백 포함 **850자 ~ 950자 사이**로 풍부하고 상세하게 작성할 것 (1,000자 초과 금지).
    - 전문적이고 정중한 어조로 작성하되, 가독성을 위해 항목별로 구분할 것.

    [데이터]
    - 날짜: {today_kst} ({weekday_kr})
    - 오늘 날씨: {weather_str}
    - 오늘의 TimeTree 일정:
    {timetree_events_str}
    - 사용자 보유 종목: SK하이닉스, 현대차, 이수페타시스, LS ELECTRIC, 한화에어로스페이스, KODEX 200타겟위클리커버드콜
    - 관심 스포츠 팀: 맨체스터 유나이티드 (축구)

    [작성 항목]
    [MORI 모닝 인텔리전스] {today_kst}({weekday_kr})

    🌤️ 오늘 날씨 & 출근길 가이드
    (기온, 날씨 특성, 권장 옷차림 상세 조언)

    📅 오늘의 TimeTree 일정
    (제공된 일정 요약 또는 개인 루틴 점검)

    📈 글로벌 증시 마감 & 보유 종목 핵심 분석
    (뉴욕 증시 및 반도체 지수 마감 총평)
    - SK하이닉스 & 반도체: AI HBM 수요 및 외인 수급 관점
    - 현대차 & 방산/전력: 원/달러 환율과 수출 수주 모멘텀
    - 커버드콜/고배당주: 배당 방어력 및 월 분배금 흐름

    ⚽ 맨체스터 유나이티드 소식
    (다음 경기 일정 KST 시간 표기 및 최근 구단 핵심 이슈 1~2줄)

    💡 상세 포트폴리오 분석 리포트는 아래 앱에서 확인하실 수 있습니다.
    """

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    payload = {"contents": [{"role": "user", "parts": [{"text": prompt}]}]}
    headers = {"Content-Type": "application/json"}
    
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=25)
        if res.status_code == 200:
            candidates = res.json().get('candidates', [])
            if candidates:
                text = candidates[0]['content']['parts'][0]['text'].strip()
                if len(text) > 950:
                    text = text[:940] + "\n...(자세한 내용은 MORI 앱 참조)"
                return text
    except Exception as e:
        print(f"Gemini API 에러: {e}")
        
    return f"[MORI 모닝 브리핑]\n오늘 날씨: {weather_str}\n\n오늘의 일정:\n{timetree_events_str}\n\n좋은 하루 보내세요!"

# ==========================================
# 5. 카카오톡 '나에게 보내기' 발송 (버튼 탑재)
# ==========================================
def send_kakao_briefing(final_text, access_token):
    send_url = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    template = {
        "object_type": "text",
        "text": final_text,
        "link": {
            "web_url": "https://hj-app.streamlit.app",
            "mobile_web_url": "https://hj-app.streamlit.app"
        },
        "buttons": [
            {
                "title": "📱 MORI 앱 열기",
                "link": {
                    "web_url": "https://hj-app.streamlit.app",
                    "mobile_web_url": "https://hj-app.streamlit.app"
                }
            }
        ]
    }
    
    res = requests.post(send_url, headers=headers, data={"template_object": json.dumps(template)})
    if res.status_code == 200:
        print("✅ 카카오톡 발송 완료!")
    else:
        print(f"❌ 카카오톡 발송 실패: {res.status_code} - {res.text}")

# ==========================================
# 메인 실행부
# ==========================================
if __name__ == "__main__":
    # 🌟 어떤 이름으로 등록되어 있어도 자동으로 찾아오도록 보완
    KAKAO_CLIENT_ID = (
        os.environ.get("KAKAO_CLIENT_ID")
        or os.environ.get("KAKAO_REST_API_KEY")
        or os.environ.get("REST_API_KEY")
        or os.environ.get("KAKAO_API_KEY")
    )
    KAKAO_CLIENT_SECRET = os.environ.get("KAKAO_CLIENT_SECRET", "")
    KAKAO_REFRESH_TOKEN = (
        os.environ.get("KAKAO_REFRESH_TOKEN")
        or os.environ.get("REFRESH_TOKEN")
    )
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
    TIMETREE_TOKEN = os.environ.get("TIMETREE_TOKEN", "")
    TIMETREE_CALENDAR_ID = os.environ.get("TIMETREE_CALENDAR_ID", "")

    if not KAKAO_CLIENT_ID:
        print("❌ KAKAO_CLIENT_ID(REST API 키)를 찾을 수 없습니다. GitHub Secrets 설정을 확인해주세요.")
        exit(1)


    print("2. 날씨 및 TimeTree 일정 수집 중...")
    weather_info = get_weather()
    timetree_info = get_timetree_today(TIMETREE_TOKEN, TIMETREE_CALENDAR_ID)

    print("3. Gemini 고밀도 상세 브리핑 생성 중...")
    briefing_text = make_ai_briefing(weather_info, timetree_info, GEMINI_API_KEY)

    print("4. 카카오톡 전송 실행...")
    send_kakao_briefing(briefing_text, access_token)
