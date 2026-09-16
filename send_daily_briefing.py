import os
import json
import requests
from datetime import datetime, timezone, timedelta

# 1. 한국 표준시(KST) 정의
KST = timezone(timedelta(hours=9))
today_now = datetime.now(KST)
today_str = today_now.strftime("%Y-%m-%d")
weekdays_kr = ["월", "화", "수", "목", "금", "토", "일"]
today_weekday = weekdays_kr[today_now.weekday()]

# 2. 환경변수(Secrets) 불러오기
GIST_ID = os.environ.get("GIST_ID", "")
GIST_TOKEN = os.environ.get("GIST_TOKEN", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
KAKAO_REST_KEY = os.environ.get("KAKAO_REST_KEY", "")
KAKAO_AUTH_CODE = os.environ.get("KAKAO_AUTH_CODE", "")

TIMETREE_EMAIL = os.environ.get("TIMETREE_EMAIL", "")
TIMETREE_PASSWORD = os.environ.get("TIMETREE_PASSWORD", "")
TIMETREE_CALENDAR_CODE = os.environ.get("TIMETREE_CALENDAR_CODE", "")

# 3. Gist 데이터 읽기/쓰기 유틸리티
def get_gist_data():
    if not GIST_ID or not GIST_TOKEN:
        return {}
    url = f"https://api.github.com/gists/{GIST_ID}"
    headers = {"Authorization": f"token {GIST_TOKEN}", "User-Agent": "MORI-Bot"}
    try:
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            files = res.json().get("files", {})
            if "mori_data.json" in files:
                return json.loads(files["mori_data.json"].get("content", "{}"))
    except Exception as e:
        print(f"Gist 읽기 실패: {e}")
    return {}

def save_gist_key(key, val):
    if not GIST_ID or not GIST_TOKEN:
        return
    data = get_gist_data()
    data[key] = val
    url = f"https://api.github.com/gists/{GIST_ID}"
    headers = {
        "Authorization": f"token {GIST_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "MORI-Bot"
    }
    payload = {
        "files": {
            "mori_data.json": {
                "content": json.dumps(data, ensure_ascii=False, indent=2)
            }
        }
    }
    try:
        requests.patch(url, json=payload, headers=headers, timeout=5)
    except Exception as e:
        print(f"Gist 저장 실패: {e}")

# 4. 카카오 토큰 무한 자동 갱신 엔진
def get_kakao_access_token():
    gist_data = get_gist_data()
    saved_refresh_token = gist_data.get("kakao_refresh_token")
    
    # 1) 기존 리프레시 토큰으로 액세스 토큰 갱신
    if saved_refresh_token:
        url = "https://kauth.kakao.com/oauth/token"
        data = {
            "grant_type": "refresh_token",
            "client_id": KAKAO_REST_KEY,
            "refresh_token": saved_refresh_token
        }
        res = requests.post(url, data=data, timeout=5).json()
        if "access_token" in res:
            # 새 리프레시 토큰이 같이 오면 Gist에 업데이트
            if "refresh_token" in res:
                save_gist_key("kakao_refresh_token", res["refresh_token"])
            return res["access_token"]
        print(f"리프레시 토큰 갱신 실패: {res}")

    # 2) 최초 실행 시 KAKAO_AUTH_CODE로 최초 발급
    if KAKAO_AUTH_CODE:
        url = "https://kauth.kakao.com/oauth/token"
        data = {
            "grant_type": "authorization_code",
            "client_id": KAKAO_REST_KEY,
            "redirect_uri": "https://hj-app.streamlit.app",
            "code": KAKAO_AUTH_CODE
        }
        res = requests.post(url, data=data, timeout=5).json()
        if "access_token" in res and "refresh_token" in res:
            save_gist_key("kakao_refresh_token", res["refresh_token"])
            print("최초 카카오 리프레시 토큰 획득 및 Gist 영구 보관 성공!")
            return res["access_token"]
        print(f"최초 토큰 발급 실패: {res}")
        
    return None

# 5. TimeTree 웹 자동 수집 엔진
def sync_timetree_events():
    if not TIMETREE_EMAIL or not TIMETREE_PASSWORD or not TIMETREE_CALENDAR_CODE:
        return
    try:
        from timetree_exporter.timetree import TimeTreeClient
        client = TimeTreeClient(TIMETREE_EMAIL, TIMETREE_PASSWORD)
        cal_data = client.get_calendar_events(TIMETREE_CALENDAR_CODE)
        
        extracted = []
        for ev in cal_data:
            start_at = ev.get("start_at", "")[:10]
            title = ev.get("title", "")
            if start_at and title:
                extracted.append({
                    "id": f"tt_{start_at}_{title}",
                    "date": start_at,
                    "type": "가족 일정",
                    "title": title,
                    "auto_stock": "-"
                })
        if extracted:
            save_gist_key("timetree_events", extracted)
            print(f"TimeTree 일정 {len(extracted)}건 수집 완료")
    except Exception as e:
        print(f"TimeTree 수집 건너뜀 (오류 또는 라이브러리 부재): {e}")

# 6. 실시간 날씨 및 간밤 증시 데이터 수집
def get_weather():
    try:
        url = "https://api.open-meteo.com/v1/forecast?latitude=37.2410&longitude=127.1775&current=temperature_2m,weather_code&daily=temperature_2m_max,temperature_2m_min&timezone=auto"
        res = requests.get(url, timeout=4).json()
        cur = res.get("current", {})
        temp = cur.get("temperature_2m", 21.0)
        code = cur.get("weather_code", 0)
        desc = "맑음"
        rain_tag = "우산 X"
        if code in (1, 2): desc = "구름조금"
        elif code == 3: desc = "흐림"
        elif code in (51, 53, 55, 61, 63, 65, 80, 81, 82):
            desc = "비"; rain_tag = "우산 필수 ☔"
        return f"{desc} {temp:.0f}°C ({rain_tag})"
    except Exception:
        return "맑음 21°C (우산 X)"

def get_market_summary():
    try:
        # 네이버 금융 증시 지표
        url_sox = "https://m.stock.naver.com/front-api/marketIndex/prices?category=worldIndex&reutersCode=.SOX"
        res = requests.get(url_sox, headers={'User-Agent': 'Mozilla/5.0'}, timeout=4).json()
        sox_result = res.get("result", [])
        sox_ratio = float(sox_result[0].get("fluctuationsRatio", 0.0)) if sox_result else 1.5
        
        # 엔비디아 시세
        url_nvda = "https://m.stock.naver.com/api/stock/NVDA.O/basic"
        res_n = requests.get(url_nvda, headers={'User-Agent': 'Mozilla/5.0'}, timeout=4).json()
        nvda_ratio = float(res_n.get("fluctuationsRatio", 2.0)) if res_n else 2.0
        
        return sox_ratio, nvda_ratio
    except Exception:
        return 1.2, 1.8

# 7. 제미나이 1줄 시그널 생성 (30자 엄수)
def generate_ai_signal(sox_pct, nvda_pct):
    if not GEMINI_API_KEY:
        return "반도체 견조한 흐름 예상 ☀️"
    prompt = f"""
    당신은 수석 반도체 애널리스트입니다.
    간밤 필라델피아 반도체 지수는 {sox_pct:+.2f}%, 엔비디아는 {nvda_pct:+.2f}% 마감했습니다.
    오늘 한국 반도체 주식(SK하이닉스, 이수페타시스 등)의 개장 전 분위기를 30자 이내의 한 문장(이모지 1개 포함)으로 요약해주세요.
    반드시 마침표나 미사여구 없이 문장만 출력하세요.
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    try:
        res = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=6).json()
        txt = res['candidates'][0]['content']['parts'][0]['text'].strip()
        return txt[:32]
    except Exception:
        return "반도체 맑음 ☀️ (하이닉스 긍정)"

# 8. 최종 메시지 조립 및 카카오톡 전송
def send_kakao_briefing():
    access_token = get_kakao_access_token()
    if not access_token:
        print("카카오 토큰이 없어 발송을 중단합니다.")
        return

    sync_timetree_events()
    weather_txt = get_weather()
    sox_r, nvda_r = get_market_summary()
    market_signal = generate_ai_signal(sox_r, nvda_r)
    
    # 오늘 일정 추출 (TimeTree + Gist 고정 일정)
    gist_data = get_gist_data()
    all_events = gist_data.get("calendar_events", []) + gist_data.get("timetree_events", [])
    today_events = [e.get("title") for e in all_events if e.get("date") == today_str]
    
    # 중복 제거 및 최대 3개 선별
    seen = set()
    filtered_events = []
    for t in today_events:
        if t not in seen:
            seen.add(t)
            filtered_events.append(t)
            
    if filtered_events:
        event_str = ", ".join(filtered_events[:3])
        if len(filtered_events) > 3:
            event_str += f" 외 {len(filtered_events)-3}건"
    else:
        event_str = "오늘 예정된 주요 일정 없음"

    # 요일별 스포츠 한줄
    sports_str = "오늘 밤 맨유 경기 없음"
    if today_weekday in ["토", "일"]:
        sports_str = "주말 매치데이 (맨유·KBO 일정 확인)"

    # 완결형 텍스트 구성 (스크롤 없이 15초 완독)
    msg_lines = [
        f"[MORI 모닝 브리프] {today_now.month}.{today_now.day}({today_weekday})",
        f"📈 {market_signal}",
        f"• 필반도 {sox_r:+.1f}%, NVDA {nvda_r:+.1f}%",
        "",
        f"📍 경기 용인: {weather_txt}",
        f"⏰ 오늘 일정: {event_str}",
        f"⚽ 스포츠: {sports_str}"
    ]
    final_text = "\n".join(msg_lines)

    # 카카오 '나에게 보내기' API 호출
    send_url = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
    headers = {"Authorization": f"Bearer {access_token}"}
    template = {
        "object_type": "text",
        "text": final_text,
        "link": {
            "web_url": "https://hj-app.streamlit.app",
            "mobile_web_url": "https://hj-app.streamlit.app"
        },
        "button_title": "📱 MORI 앱 열기"
    }
    
    res = requests.post(send_url, headers=headers, data={"template_object": json.dumps(template)}, timeout=6)
    if res.status_code == 200:
        print("카카오톡 모닝 브리프 전송 성공! 🎉")
    else:
        print(f"카카오톡 전송 실패: {res.text}")

if __name__ == "__main__":
    send_kakao_briefing()
