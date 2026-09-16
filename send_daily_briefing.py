import os
import json
import requests
from datetime import datetime, timezone, timedelta

# 한국 표준시(KST) 정의
KST = timezone(timedelta(hours=9))

# ==========================================
# 1. Gist 스마트 자동 탐색 및 카카오 토큰 갱신
# ==========================================
def get_kakao_access_token(kakao_rest_key, gist_id, gist_token, kakao_auth_code=""):
    gist_headers = {
        "Authorization": f"token {gist_token}",
        "User-Agent": "MORI-App",
        "Accept": "application/vnd.github.v3+json"
    }
    gist_url = f"https://api.github.com/gists/{gist_id}"
    
    files = {}
    try:
        r = requests.get(gist_url, headers=gist_headers, timeout=6)
        if r.status_code == 200:
            files = r.json().get("files", {})
            print(f"🔍 Gist 연결 성공! 보관된 파일 목록: {list(files.keys())}")
        else:
            print(f"❌ Gist 조회 실패 (상태 코드 {r.status_code}): {r.text}")
            return None
    except Exception as e:
        print(f"❌ Gist 네트워크 통신 오류: {e}")
        return None

    target_filename = None
    file_content_json = {}
    tokens = {}

    # 🌟 Gist 내 모든 파일을 검사하여 카카오 토큰이 들어있는 파일 자동 탐지
    for fname, finfo in files.items():
        try:
            content = json.loads(finfo.get("content", "{}"))
            if isinstance(content, dict):
                if "refresh_token" in content or "access_token" in content:
                    target_filename = fname
                    file_content_json = content
                    tokens = content
                    break
                elif "kakao_tokens" in content:
                    target_filename = fname
                    file_content_json = content
                    tokens = content["kakao_tokens"]
                    break
        except Exception:
            pass

    if not target_filename:
        print("❌ Gist 파일들 속에서 카카오 토큰(refresh_token)을 찾지 못했습니다.")
        return None

    print(f"🔑 카카오 토큰 파일 발견: [{target_filename}]")
    refresh_token = tokens.get("refresh_token")
    access_token = tokens.get("access_token")

    # 🌟 리프레시 토큰으로 새 액세스 토큰 갱신
    if refresh_token and kakao_rest_key:
        print("🔄 카카오 리프레시 토큰으로 최신 액세스 토큰 갱신 중...")
        token_url = "https://kauth.kakao.com/oauth/token"
        data = {
            "grant_type": "refresh_token",
            "client_id": kakao_rest_key,
            "refresh_token": refresh_token
        }
        res = requests.post(token_url, data=data, timeout=10)
        if res.status_code == 200:
            token_res = res.json()
            new_access_token = token_res.get("access_token")
            new_refresh_token = token_res.get("refresh_token")
            
            # 토큰 정보 업데이트
            tokens["access_token"] = new_access_token
            if new_refresh_token:
                tokens["refresh_token"] = new_refresh_token
                
            if "kakao_tokens" in file_content_json:
                file_content_json["kakao_tokens"] = tokens
            else:
                file_content_json.update(tokens)
                
            # Gist에 최신 갱신 토큰 저장
            try:
                payload = {
                    "files": {
                        target_filename: {
                            "content": json.dumps(file_content_json, ensure_ascii=False, indent=2)
                        }
                    }
                }
                requests.patch(gist_url, json=payload, headers=gist_headers, timeout=6)
                print("💾 최신 토큰을 Gist에 성공적으로 업데이트했습니다.")
            except Exception as e:
                print(f"Gist 저장 경고: {e}")
                
            print("✅ 새 카카오 액세스 토큰 발급 완료!")
            return new_access_token
        else:
            print(f"❌ 카카오 리프레시 갱신 실패 ({res.status_code}): {res.text}")

    return access_token

# ==========================================
# 2. 날씨 정보 수집 (용인시 기준)
# ==========================================
def get_weather(lat=37.2410, lon=127.1775):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,weather_code&timezone=Asia%2FSeoul"
        res = requests.get(url, timeout=5).json()
        cur = res.get("current", {})
        temp = cur.get("temperature_2m", 22.0)
        hum = cur.get("relative_humidity_2m", 70)
        code = cur.get("weather_code", 0)
        
        desc = "맑음"
        if code in (1, 2): desc = "구름 조금"
        elif code == 3: desc = "흐림"
        elif code in (51, 53, 55, 61, 63, 65, 80, 81, 82): desc = "비"
        elif code in (71, 73, 75, 85, 86): desc = "눈"
        
        return f"용인시 {desc}, 기온 {temp:.1f}°C, 습도 {hum}%"
    except Exception:
        return "용인시 맑음, 약 22°C"

# ==========================================
# 3. TimeTree 일정 가져오기
# ==========================================
def get_timetree_today(email, password, calendar_code):
    if not email or not password:
        return "TimeTree 계정 정보 미등록"
        
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json"
    })
    
    today_str = datetime.now(KST).strftime('%Y-%m-%d')
    events_text = []
    
    try:
        login_url = "https://timetreeapp.com/api/v1/session"
        login_payload = {"session": {"email": email, "password": password}}
        r = session.post(login_url, json=login_payload, timeout=8)
        
        if r.status_code in (200, 201):
            cal_url = f"https://timetreeapp.com/api/v1/calendars/{calendar_code}/upcoming_events"
            cr = session.get(cal_url, timeout=8)
            if cr.status_code == 200:
                data = cr.json().get("events", [])
                for ev in data:
                    start_at = ev.get("start_at", "")
                    title = ev.get("title", "일정")
                    if start_at.startswith(today_str):
                        t_str = start_at[11:16] if len(start_at) >= 16 else "종일"
                        events_text.append(f"• [{t_str}] {title}")
    except Exception as e:
        print(f"TimeTree 수집 오류: {e}")

    return "\n".join(events_text) if events_text else "오늘 예정된 주요 일정이 없습니다."

# ==========================================
# 4. Gemini 고밀도 상세 브리핑 작성 (850~950자)
# ==========================================
def make_ai_briefing(weather_str, timetree_events_str, api_key):
    today_kst = datetime.now(KST).strftime('%Y년 %m월 %d일')
    weekday_kr = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"][datetime.now(KST).weekday()]
    
    if not api_key:
        return f"[MORI 모닝 브리핑] {today_kst}\n\n🌤️ 날씨: {weather_str}\n📅 오늘의 일정:\n{timetree_events_str}\n\n좋은 하루 보내세요!"

    prompt = f"""
    당신은 직장인 투자자 이현재 님의 스마트 비서 AI 'MORI'입니다.
    오늘자 아침 카카오톡 브리핑을 작성해주세요.

    [분량 및 스타일 규칙 - 매우 중요]
    - 전체 분량은 반드시 공백 포함 850자 ~ 950자 사이로 풍부하고 상세하게 작성할 것 (1,000자 초과 금지).
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

    for model_name in ["gemini-2.5-flash", "gemini-3.5-flash", "gemini-3.1-flash-lite"]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
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
        except Exception:
            pass
            
    return f"[MORI 모닝 브리핑] {today_kst}\n🌤️ 날씨: {weather_str}\n📅 오늘의 일정:\n{timetree_events_str}"

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
    res = requests.post(send_url, headers=headers, data={"template_object": json.dumps(template)}, timeout=10)
    if res.status_code == 200:
        print("✅ 카카오톡 발송 성공!")
        return True
    else:
        print(f"❌ 카카오톡 발송 실패 ({res.status_code}): {res.text}")
        return False

# ==========================================
# 메인 실행부
# ==========================================
if __name__ == "__main__":
    KAKAO_REST_KEY = os.environ.get("KAKAO_REST_KEY")
    KAKAO_AUTH_CODE = os.environ.get("KAKAO_AUTH_CODE", "")
    GIST_ID = os.environ.get("GIST_ID")
    GIST_TOKEN = os.environ.get("GIST_TOKEN")
    
    TIMETREE_EMAIL = os.environ.get("TIMETREE_EMAIL", "")
    TIMETREE_PASSWORD = os.environ.get("TIMETREE_PASSWORD", "")
    TIMETREE_CALENDAR_CODE = os.environ.get("TIMETREE_CALENDAR_CODE", "")
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

    print("1. 카카오 액세스 토큰 준비 중 (Gist 스마트 연동)...")
    access_token = get_kakao_access_token(KAKAO_REST_KEY, GIST_ID, GIST_TOKEN, KAKAO_AUTH_CODE)
    if not access_token:
        print("❌ 카카오 발송 토큰을 얻지 못했습니다.")
        exit(1)

    print("2. 날씨 및 TimeTree 일정 수집 중...")
    weather_info = get_weather()
    timetree_info = get_timetree_today(TIMETREE_EMAIL, TIMETREE_PASSWORD, TIMETREE_CALENDAR_CODE)

    print("3. Gemini 고밀도 상세 브리핑 작성 중...")
    briefing_text = make_ai_briefing(weather_info, timetree_info, GEMINI_API_KEY)

    print("4. 카카오톡 메시지 전송 실행...")
    send_kakao_briefing(briefing_text, access_token)
