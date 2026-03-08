from typing import Annotated, Literal, TypedDict, List
from langgraph.graph import add_messages
from pydantic import BaseModel
from langchain_core.messages import BaseMessage


# GraphState 정의
class WeatherState(TypedDict):
    # add_messages → langgraph dev가 thread_id 기준으로 자동 누적
    messages: Annotated[List[BaseMessage], add_messages]
    user_message:    str
    intent: Literal["current", "forecast", "unknown"] | None  
    city: str | None
    country: str | None
    city_query: str | None
    retry_count: int
    weather_data: dict | None
    final_response: str | None
    error: str | None
    


# Structured Output 스키마 (Pydantic)

class IntentOutput(BaseModel):
    """의도 분류 결과 스키마"""
    intent: Literal["current", "forecast", "unknown"]

class LocationOutput(BaseModel):
    """도시 + 국가 추출 결과 스키마"""
    city:    str                
    country: str  