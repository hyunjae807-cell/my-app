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
KAKAO_REST_KEY = (
    os.environ.get("KAKAO_REST_KEY", "") or "98117624d9baa3910b9d03fb295cc27c"
)
KAKAO_AUTH_CODE = (
    os.environ.get("KAKAO_AUTH_CODE", "")
    or "o0-SeFabVjKnUJIl5n0qqqzuFFQITqnDQPptX3BiqBqFP-xjrLzdowAAAAQKFyIgAAABoKy6bXVUdd9ffL_GXA"
)



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
        return []
    try:
        import subprocess
        import sys
        import re

        env = os.environ.copy()
        env["TIMETREE_EMAIL"] = TIMETREE_EMAIL
        env["TIMETREE_PASSWORD"] = TIMETREE_PASSWORD

        ics_path = "timetree.ics"
        cmd = [sys.executable, "-m", "timetree_exporter", "-c", TIMETREE_CALENDAR_CODE, "-o", ics_path]
        res = subprocess.run(cmd, env=env, capture_output=True, text=True)

        extracted = []
        if os.path.exists(ics_path):
            with open(ics_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            events = re.findall(r"BEGIN:VEVENT(.*?)END:VEVENT", content, re.DOTALL)
            for ev in events:
                summary_match = re.search(r"^SUMMARY:(.*)$", ev, re.MULTILINE)
                title = summary_match.group(1).strip() if summary_match else ""

                dt_match = re.search(r"^DTSTART.*?:(\d{4})(\d{2})(\d{2})", ev, re.MULTILINE)
                if dt_match:
                    start_at = f"{dt_match.group(1)}-{dt_match.group(2)}-{dt_match.group(3)}"
                else:
                    start_at = ""

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
                return extracted
    except Exception as e:
        print(f"TimeTree 수집 건너뜀 (오류 또는 라이브러리 부재): {e}")
    return []

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
        url_sox = "https://m.stock.naver.com/front-api/marketIndex/prices?category=worldIndex&reutersCode=.SOX"
        res = requests.get(url_sox, headers={'User-Agent': 'Mozilla/5.0'}, timeout=4).json()
        sox_result = res.get("result", [])
        sox_ratio = float(sox_result[0].get("fluctuationsRatio", 0.0)) if sox_result else 1.5
        
        url_nvda = "https://m.stock.naver.com/api/stock/NVDA.O/basic"
        res_n = requests.get(url_nvda, headers={'User-Agent': 'Mozilla/5.0'}, timeout=4).json()
        nvda_ratio = float(res_n.get("fluctuationsRatio", 2.0)) if res_n else 2.0
        
        return sox_ratio, nvda_ratio
    except Exception:
        return 1.2, 1.8

# 7. 제미나이 고밀도 상세 브리핑 생성 (850~950자)
def generate_detailed_briefing(weather_str, sox_pct, nvda_pct, today_events):
    events_text = "\n".join([f"• {ev.get('title')}" for ev in today_events if ev.get("date") == today_str])
    if not events_text:
        events_text = "오늘 예정된 주요 외부 일정은 없습니다."

    if not GEMINI_API_KEY:
        return f"[MORI 데일리 브리핑] {today_str}({today_weekday})\n\n🌤️ 오늘 날씨: {weather_str}\n📅 오늘의 일정:\n{events_text}\n📈 반도체: SOX {sox_pct:+.2f}%, NVDA {nvda_pct:+.2f}%\n\n좋은 하루 보내세요!"

    prompt = f"""
    당신은 직장인 투자자 이현재 님의 스마트 비서 AI 'MORI'입니다.
    오늘자 아침 카카오톡 브리핑을 공백 포함 **850자 ~ 950자 사이**로 풍부하고 상세하게 작성해주세요. (1,000자 초과 금지)

    [수집 데이터]
    - 오늘 날짜: {today_str} ({today_weekday}요일)
    - 오늘 날씨: {weather_str}
    - 오늘의 TimeTree 일정:
    {events_text}
    - 간밤 증시 지표: 필라델피아 반도체 지수 {sox_pct:+.2f}%, 엔비디아 {nvda_pct:+.2f}%
    - 보유 종목: SK하이닉스, 현대차, 이수페타시스, LS ELECTRIC, 한화에어로스페이스, KODEX 200타겟위클리커버드콜
    - 관심 구단: 맨체스터 유나이티드 (축구)

    [작성 항목]
    [MORI 모닝 인텔리전스] {today_str}({today_weekday})

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
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
        payload = {"contents": [{"role": "user", "parts": [{"text": prompt}]}]}
        headers = {"Content-Type": "application/json"}
        try:
            res = requests.post(url, json=payload, headers=headers, timeout=25)
            if res.status_code == 200:
                candidates = res.json().get('candidates', [])
                if candidates:
                    txt = candidates[0]['content']['parts'][0]['text'].strip()
                    # 1,000자 초과 방지 안전 슬라이싱
                    if len(txt) > 950:
                        txt = txt[:940] + "\n...(자세한 내용은 MORI 앱 참조)"
                    return txt
        except Exception:
            pass

    return f"[MORI 모닝 브리핑] {today_str}({today_weekday})\n\n🌤️ 오늘 날씨: {weather_str}\n📅 오늘의 일정:\n{events_text}"

# 8. 최종 메시지 조립 및 카카오톡 전송
def send_kakao_briefing():
    print("1. 카카오 액세스 토큰 준비 중 (Gist 자동 갱신)...")
    access_token = get_kakao_access_token()
    if not access_token:
        print("❌ 카카오 발송 토큰을 얻지 못했습니다.")
        return

    print("2. 날씨, 증시 및 TimeTree 일정 수집 중...")
    weather_info = get_weather()
    sox_ratio, nvda_ratio = get_market_summary()
    timetree_events = sync_timetree_events() or []

    print("3. 제미나이 상세 브리핑 생성 중...")
    briefing_text = generate_detailed_briefing(weather_info, sox_ratio, nvda_ratio, timetree_events)

    print("4. 카카오톡 메시지 전송 실행...")
    send_url = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    template = {
        "object_type": "text",
        "text": briefing_text,
        "link": {
            "web_url": "https://hj-app.streamlit.app",
            "mobile_web_url": "https://hj-app.streamlit.app"
        },
        "button_title": "📱 MORI 앱 열기"
    }
    
    res = requests.post(send_url, headers=headers, data={"template_object": json.dumps(template)}, timeout=10)
    if res.status_code == 200:
        print("✅ 카카오톡 발송 성공!")
    else:
        print(f"❌ 카카오톡 발송 실패 ({res.status_code}): {res.text}")

if __name__ == "__main__":
    send_kakao_briefing()
