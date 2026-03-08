"""
weather_bot
===========
LangGraph 기반 날씨 조회 엔진

설치:
    pip install langgraph langchain-openai langchain-core requests python-dotenv

환경변수 (.env):
    OPENAI_API_KEY=sk-...
    WEATHER_API_KEY=...    (https://openweathermap.org 무료 가입)

사용:
    from weather_bot import run_weather_graph

    answer, messages = run_weather_graph("서울 날씨 알려줘")
    answer, messages = run_weather_graph("거기 내일은?", messages)
"""

from graph import run_weather_graph

__all__ = ["run_weather_graph"]