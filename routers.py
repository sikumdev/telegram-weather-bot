from typing_extensions import Literal
from Config import MAX_RETRY
from state import WeatherState

def route_after_intent(state: WeatherState) -> Literal["extract_location", "handle_error"]:
    """
    unknown → handle_error    (날씨 질문이 아닌 경우)
    나머지  → extract_location (정상 흐름 계속)
    """
    if state["intent"] == "unknown":
        return "handle_error"
    return "extract_location"


def route_after_extract(state: WeatherState) -> Literal["validate_city", "handle_error"]:
    """
    city=None → handle_error  (위치 특정 불가)
    city 있음 → validate_city (Geocoding 검증으로 이동)
    """
    if state["city"] is None:
        return "handle_error"
    return "validate_city"


def route_after_validate(state: WeatherState) -> Literal["fetch_weather", "handle_error"]:
    """
    city=None → handle_error  (존재하지 않는 도시)
    city 있음 → fetch_weather (날씨 API 호출)
    """
    if state["city"] is None:
        return "handle_error"
    return "fetch_weather"

def route_after_fetch(state: WeatherState) -> Literal["format_response", "fetch_weather", "handle_error"]:
    """
    성공                      → format_response  (정상 흐름)
    실패 + retry_count < MAX  → fetch_weather    (재시도 루프 ↩)
    실패 + retry_count >= MAX → handle_error     (재시도 포기)
    """
    if state["weather_data"] is not None:
        return "format_response"
    if state["retry_count"] < MAX_RETRY:
        return "fetch_weather"
    return "handle_error"

