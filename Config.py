"""상수, 환경변수, LLM 설정"""

import os
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model

load_dotenv() 

# llm 설정
llm = init_chat_model('gpt-4.1-mini')
llm_strong = init_chat_model('gpt-4o')

# 날씨 API 재시도 최대 횟수 -> 네트워크 불안정 등으로 API 호출 실패 시 최대 3회까지 자동 재시도
MAX_RETRY = 3

# 대화 히스토리 최대 유지 턴 수 -> 너무 길면 토큰 낭비, 너무 짧으면 맥락 손실
MAX_HISTORY = 20

# 프롬프트에 넘길 히스토리 최대 턴 수 ( 전체 히스토리(MAX_HISTORY)보다 적게 유지 → 토큰 절약 )
MAX_HISTORY_FOR_PROMPT = 6


# OpenWeatherMap API 설정
WEATHER_API_KEY = os.environ["WEATHER_API_KEY"]
BASE_URL        = "https://api.openweathermap.org/data/2.5"
GEO_URL         = "http://api.openweathermap.org/geo/1.0/direct"