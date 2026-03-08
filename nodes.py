import json
import requests
from datetime import date
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage



from Config import (
    WEATHER_API_KEY, BASE_URL, GEO_URL,
    MAX_RETRY, MAX_HISTORY_FOR_PROMPT,
    llm, llm_strong,
)

from state import WeatherState, IntentOutput, LocationOutput

# ────────────────────────────────────────────
# 노드 1: 의도 분류 Node
# ────────────────────────────────────────────

def classify_intent_node(state: WeatherState) -> dict:
    structured_llm = llm.with_structured_output(IntentOutput)


    prompt = """사용자 메시지의 의도를 분류하세요.
                분류 기준:
                - 현재/지금/오늘 날씨 질문 → current
                - 내일/이따가/이번주/예보 질문 → forecast
                - 날씨와 무관한 질문 → unknown
                - 히스토리를 참고해서 "거기", "부산은?", "도쿄는?" 같이 도시명만 말해도 날씨 질문이면 current로 분류
                - 날씨 관련 맥락이 있으면 최대한 current나 forecast로 분류
                - 명백하게 날씨와 무관한 경우에만 unknown"""
    result = structured_llm.invoke(
        [SystemMessage(content=prompt),*state["messages"][-6:],
         HumanMessage(content=state["user_message"]) ]              
        )
    return {"intent": result.intent}

# ────────────────────────────────────────────
# 노드 2: 위치 추출 (도시 + 국가) Node
# ────────────────────────────────────────────

def extract_location_node(state: WeatherState) -> dict:

    print("=== 히스토리 확인 ===", state["messages"]) 

    structured_llm = llm.with_structured_output(LocationOutput)

    prompt = f"""
                메시지에서 날씨를 물어보는 위치를 추출하세요.메시지: 
                규칙:
                - city: 도시명을 OpenWeatherMap이 인식하는 영어로 변환 (서울→Seoul, 부산→Busan, 도쿄→Tokyo, 뉴욕→New York, 파리→Paris)
                - country: ISO 3166-1 alpha-2 국가코드 (KR, JP, US, FR, GB ...)
                - 도시 없이 나라만 언급한 경우 → 해당 나라 수도를 city로 반환(한국/Korea → Seoul, 일본/Japan → Tokyo, 미국/America → Washington D.C.)
                - 나라도 불분명하면 city와 country 모두 빈 문자열("")로 반환
                - 히스토리에서도 위치를 못 찾으면 city와 country 모두 빈 문자열("")로 반환
                """
    result = structured_llm.invoke(
        [SystemMessage(content=prompt),*state["messages"][-6:],
         HumanMessage(content=state["user_message"]) ]              
        )

    # city나 country가 비어있으면 위치 특정 불가 → 에러
    if not result.city or not result.country:
        return {
                "city":    None,
                "country": None,
                "error":   "어느 도시 날씨가 궁금하신가요? 🏙️\n예) *서울 날씨*, *도쿄 내일 날씨*",
            }

    # city, country 분리 저장                                                "Seoul" + "KR" → "Seoul,KR"
    return {"city": result.city, "country": result.country, "city_query": f"{result.city},{result.country}", "error": None}


# ────────────────────────────────────────────
# 노드 3: 도시 실존 검증 Node
# ────────────────────────────────────────────
def validate_city_node(state: WeatherState) -> dict:

    # "Seoul,KR"
    city_query = state["city_query"]
   

    try:
        resp = requests.get(
            GEO_URL, 
            params={"q": city_query, "limit": 1, "appid": WEATHER_API_KEY},
            timeout=5,
        )
        resp.raise_for_status()

        # 빈 배열 = 존재하지 않는 도시
        if not resp.json():
            return {
                "city":  None,
                "error": f"*{state['city']}* 도시를 찾을 수 없어요. 도시 이름을 다시 확인해주세요 🗺️",
            }
        
    except requests.HTTPError:
        if resp.status_code == 401:
            # API 키 문제 → fetch_weather도 똑같이 실패할 게 확실
            # 미리 잡아서 즉시 에러로 보냄
            return {
                "city":  None,
                "error": "날씨 API 키가 유효하지 않아요. 관리자에게 문의해주세요 🔑",
            }
        # 429, 500 등 → fetch_weather에서 처리
        pass

    except Exception:
        pass

    # 검증 통과 → error 초기화 (city, country는 그대로 유지)
    return {"error": None}


# ────────────────────────────────────────────
# 노드 4: 날씨 API 호출
# ────────────────────────────────────────────


def fetch_weather_node(state: WeatherState) -> dict:
    """
    OpenWeatherMap API를 호출해서 날씨 데이터를 가져옵니다.

    intent에 따라 다른 엔드포인트 사용:
        "current"  → /weather   (현재 날씨)
        "forecast" → /forecast  (5일 예보, 3시간 간격)

    실패 시 retry_count를 올려서 반환
    → route_after_fetch 라우터가 재시도 or 에러 처리 결정
    """

    city    = state["city"]
    country = state["country"]
    intent  = state["intent"]

    # "Seoul,KR"
    city_query = state["city_query"]

    # intent에 따라 호출할 API 엔드포인트 결정
    endpoint = "/weather" if intent == "current" else "/forecast"

    params = {
        "q":      city_query,
        "appid":  WEATHER_API_KEY,
        "units":  "metric",  # 섭씨 온도
        "lang":   "kr",      # 날씨 설명 한국어
    }

    try:
        resp = requests.get(f"{BASE_URL}{endpoint}", params=params, timeout=5)
        resp.raise_for_status()

        # 성공 → weather_data 저장, error 초기화
        return {"weather_data": resp.json(), "error": None}

    except requests.HTTPError:
        # 404: 도시 없음 → 재시도해도 의미 없으니 retry_count를 MAX로 설정 -> 즉시 handle_error
        if resp.status_code == 404:
            return {
                "weather_data": None,
                "error": f"*{city}* 날씨 정보를 찾을 수 없어요 🗺️",
                "retry_count": MAX_RETRY,  
            }
        # 기타 서버 오류 → retry_count 증가 (재시도 가능)
        return {
            "weather_data": None,
            "error": f"날씨 서버 오류 (HTTP {resp.status_code})",
            "retry_count": state["retry_count"] + 1,
        }

    except requests.Timeout:
        # 타임아웃 5초 초과 → 재시도 가능
        return {
            "weather_data": None,
            "error": "날씨 서버 응답 시간 초과",
            "retry_count": state["retry_count"] + 1,
        }

    except Exception as e:
        # 기타 예외 → 재시도 가능
        return {
            "weather_data": None,
            "error": f"네트워크 오류: {str(e)}",
            "retry_count": state["retry_count"] + 1,
        }


# ────────────────────────────────────────────
# 노드 5: 답변 포맷팅
# ────────────────────────────────────────────

def format_response_node(state: WeatherState) -> dict:
    # weather_data JSON 그대로 전달 -> GPT가 current/forecast 구조 알아서 파악
    # indent=2로 가독성 향상 → GPT 응답 품질도 올라감
    raw_data = json.dumps(state["weather_data"], ensure_ascii=False, indent=2)

    weekday = ["월", "화", "수", "목", "금", "토", "일"][date.today().weekday()]
    today   = f"{date.today()} ({weekday}요일)"

    system_prompt = f"""다음 날씨 데이터를 텔레그램 메시지로 변환하세요.
                작성 규칙:
                - 사용자가 물어본 시점(내일/모레/수요일 등)에 해당하는 데이터만 사용
                - 날씨 상태에 맞는 이모지 사용 (☀️ 🌤️ ⛅ 🌧️ ❄️ 🌩️ 🌨️ 🌫️)
                - 기온은 소수점 없이 정수로 반올림
                - 친근하고 간결한 한국어
                - 텔레그램 마크다운 사용 가능 (*굵게*, _기울임_)
                - 5줄 이내로 간결하게 """
    
    user_prompt = f"""  오늘 날짜: {today}
                        사용자 질문: {state['user_message']}
                        날씨 데이터:{raw_data}"""

    response = llm_strong.invoke(
        [SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),]
        )

    print("=== format_response 저장 messages ===", [
        HumanMessage(content=state["user_message"]),
        AIMessage(content=response.content),
    ])


    return {"final_response": response.content, "messages": [                                    # ← 이거 추가!
            HumanMessage(content=state["user_message"]),
            AIMessage(content=response.content),
        ]}


# ────────────────────────────────────────────
# 노드 6: 에러 처리
# ────────────────────────────────────────────

def handle_error_node(state: WeatherState) -> dict:

    if state.get("intent") == "unknown":
        return {
            "final_response": (
                "저는 날씨 전문 봇이에요! 🌤️\n\n"
                "이렇게 물어봐주세요:\n"
                "• *서울 지금 날씨 어때?*\n"
                "• *내일 부산 비 와?*\n"
                "• *제주도 이번 주 날씨*"
            )
        }

    if state.get("retry_count", 0) >= MAX_RETRY:
        return {
            "final_response": (
                "⚠️ 날씨 서버에 일시적인 문제가 있어요.\n"
                "잠시 후 다시 시도해주세요!"
            )
        }
    
    else: 
        error_msg = state.get("error", "알 수 없는 오류가 발생했어요.")
        final = f"❌ {error_msg}"

    return { "final_response": final,
        "messages": [
            HumanMessage(content=state["user_message"]),
            AIMessage(content=final),
        ]}



# class a (TypedDict):
#     pass

# agent = create_agent(
#     llm,
#     tools = [],
#     system_prompt= 'f'
# )

# graph = StateGraph(MessagesState)
# graph.add_edge(START,END)
# workflow =graph.compile()