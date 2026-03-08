# 🌤️ 날씨 텔레그램 봇

텔레그램에서 날씨를 물어보면 AI가 답변해주는 봇입니다.  
LangGraph로 대화 흐름을 설계하고, OpenWeatherMap API로 실시간 날씨 데이터를 가져옵니다.

---

## 📌 주요 기능

- 현재 날씨 및 5일 예보 조회 (current, forecast)
- 대화 히스토리 유지 (이전 대화 맥락 참고)
- "거기 날씨는?", "내일은?" 같은 자연스러운 대화 지원
- 존재하지 않는 도시, API 오류 등 에러 처리 (validate_city_node, fetch_weather_node)
- 날씨 API 실패 시 최대 3회 자동 재시도

---

## 🛠️ 기술 스택

| 분류 | 기술 |
|------|------|
| AI 프레임워크 | LangGraph, LangChain |
| LLM | GPT-4.1-mini, GPT-4o |
| 날씨 API | OpenWeatherMap |
| 웹 서버 | FastAPI |
| 메신저 연동 | Telegram Bot API |
| 터널링 | ngrok |
| 언어 | Python 3.13 |

---

## 🏗️ 아키텍처 흐름도

### 전체 요청 흐름
```
유저 (텔레그램)
    ↓ 메시지 전송
텔레그램 서버
    ↓ 웹훅 (HTTP POST)
ngrok (로컬 터널링)
    ↓
LangGraph Dev 서버 (localhost:2024)
    ↓ FastAPI → LangGraph SDK
LangGraph 그래프 실행 + 히스토리 저장
    ↓
텔레그램 API로 답변 전송
    ↓
유저 (텔레그램)
```

### LangGraph 그래프 흐름
```
START
  ↓
classify_intent       # 의도 분류 (current / forecast / unknown)
  ↓
extract_location      # 도시 + 국가 추출
  ↓
validate_city         # 도시 실존 검증 (Geocoding API)
  ↓
fetch_weather         # 날씨 API 호출 (실패 시 최대 3회 재시도)
  ↓
format_response       # LLM으로 답변 포맷팅
  ↓
END

* 각 단계에서 오류 발생 시 → handle_error로 이동
```

---

## 📁 프로젝트 구조

```
├── webapp.py        # FastAPI 웹훅 엔드포인트
├── graph.py         # LangGraph 그래프 조립
├── nodes.py         # 각 노드 구현
├── routers.py       # 조건부 엣지 (라우터)
├── state.py         # WeatherState 정의
├── Config.py        # 환경변수 및 LLM 설정
└── langgraph.json   # LangGraph Dev 설정
```

---


## 💡 배운 점 / 회고

**LangGraph**
- 단순한 LLM 호출이 아닌 노드와 엣지로 대화 흐름을 설계하는 방법을 배웠다.
- 조건부 엣지(라우터)로 상황에 따라 다른 노드로 분기하는 구조를 구현했다.
- `workflow.ainvoke()` 직접 호출과 LangGraph SDK를 통한 호출의 차이를 직접 겪으며 이해했다.

**FastAPI**
- 인터넷 요청을 파이썬 함수로 연결하는 웹 서버의 역할을 이해했다.
- 동기/비동기(`async`, `await`)의 개념과 왜 필요한지 배웠다.

**삽질한 것들**
- `messages: []`를 매번 초기화해서 히스토리가 쌓이지 않던 문제
- `MemorySaver`를 직접 넣으면 LangGraph Dev와 충돌하는 문제
- `workflow.ainvoke()` 직접 호출 시 LangGraph persistence가 작동하지 않는 문제
  → LangGraph SDK의 `client.runs.create()`로 해결

---

## 💬 사용 예시

```
유저: 서울 오늘 날씨 알려줘
봇:   ☀️ 서울 오늘 맑음, 기온 8°C

유저: 내일은?
봇:   🌤️ 서울 내일 구름 조금, 최고 10°C
```