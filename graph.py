from typing import List
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from Config import MAX_HISTORY
from state import WeatherState
from nodes import (
    classify_intent_node,
    extract_location_node,
    validate_city_node,
    fetch_weather_node,
    format_response_node,
    handle_error_node,
)
from routers import (
    route_after_intent,
    route_after_extract,
    route_after_validate,
    route_after_fetch,
)



# ================================================================
# 그래프 조립 
# ================================================================

graph = StateGraph(WeatherState)

# ── 노드 등록 ──────────────────────────────
graph.add_node("classify_intent",  classify_intent_node)
graph.add_node("extract_location", extract_location_node)
graph.add_node("validate_city",    validate_city_node)
graph.add_node("fetch_weather",    fetch_weather_node)
graph.add_node("format_response",  format_response_node)
graph.add_node("handle_error",     handle_error_node)

# ── 시작점 설정 ────────────────────────────
graph.add_edge(START, "classify_intent")


# ── 조건부 엣지 연결 ───────────────────────
graph.add_conditional_edges("classify_intent",  route_after_intent)
graph.add_conditional_edges("extract_location", route_after_extract)
graph.add_conditional_edges("validate_city",    route_after_validate)
graph.add_conditional_edges("fetch_weather",    route_after_fetch)


# ── 종료 엣지 ──────────────────────────────
graph.add_edge("format_response", END)
graph.add_edge("handle_error",    END)

workflow = graph.compile() # 그래프에 저장소 연결


