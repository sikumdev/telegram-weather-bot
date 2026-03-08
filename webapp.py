import os
import uuid
import aiohttp
from fastapi import FastAPI, Request
from dotenv import load_dotenv
from langgraph_sdk import get_client

load_dotenv()

# ================================================================
# 설정
# ================================================================
TELEGRAM_TOKEN   = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# ================================================================
# FastAPI 앱
# ================================================================

app = FastAPI()

# "localhost:2024에 있는 LangGraph Dev 서버랑 연결할게" -> langgraph_sdk import get_client
# langgraph SDK -> FastAPI가 LangGraph 서버한테 쉽게 요청 보낼 수 있게 해주는 도구 (langgraph 입장에서는 fastapi가 client임)
# LangGraph 서버 주소를 기억하고, 복잡한 HTTP 요청을 대신 처리 
# client.메서드 -> langgraph 서버에서 제공하는 기능들을 쓸 수 있음
client = get_client(url="http://localhost:2024")

# ================================================================
# 유틸 함수 
# ================================================================

async def send_telegram_message(chat_id: int, text: str):
    """텔레그램으로 메시지 전송"""
    # aiohttp.ClientSession() -> HTTP 요청을 보낼때 쓰이는 객체
    async with aiohttp.ClientSession() as session:
        await session.post(
            f"{TELEGRAM_API_URL}/sendMessage",
            json={
                "chat_id":    chat_id,
                "text":       text,
                "parse_mode": "Markdown",
            }
        )

# ================================================================
# 웹훅 엔드포인트

"""
    텔레그램 웹훅 수신

    텔레그램이 보내는 JSON 구조:
    {
        "message": {
            "chat": {"id": 12345},
            "text": "서울 날씨 알려줘"
        }
    }
    """

# ================================================================


@app.post("/telegram/webhook")
async def telegram_webhook(request: Request): # request는 텔레그램에서 보내는 데이터
    payload = await request.json()

    # 메시지 자체가 없는 요청 무시 (봇 채널 추가 / 봇을 그룹에서 삭제 등 메시지 외 알림) -> 참고) 웹훅 수신 시 응답하지 않으면 계속 재시도해서 응답값 return
    message = payload.get("message")
    if not message:
        return {"ok": True}

    chat_id      = message["chat"]["id"]
    user_message = message.get("text", "")

    # 텍스트 메시지가 아니면 무시 (사진, 동영상 등)
    if not user_message:
        return {"ok": True}

    # thread_id = chat_id를 UUID로 변환 (같은 chat_id → 항상 같은 UUID)
    # langgraph SDK는 thread를 UUID 형식으로만 받음
                  # 12345 → 2f596f7d-f345-5317-8b0a-82e65487a88d
    thread_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, str(chat_id)))

    # thread 가져오거나 없으면 새로 생성
    try:
        await client.threads.get(thread_id)
    except Exception:
        await client.threads.create(thread_id=thread_id)

    # LangGraph API를 통해 실행 → persistence 자동 관리
    # langgraph 서버한테 이 thread 에서 그래프 실행하라고 요청
    run = await client.runs.create(
        thread_id=thread_id,
        assistant_id="workflow",
        # 그래프한테 넘길 초기 데이터
        input={"user_message": user_message, "retry_count": 0},
    )

    # 실행 완료될 때까지 대기 -> 비동기라서 실행 요청 후 결과 나올때까지 기다려야함
    # 참고) run_id는 runs.create()에서 반환힌 실행 id
    await client.runs.join(thread_id=thread_id, run_id=run["run_id"])

    # thread state에서 결과 읽기 -> 이 thread에서 실행한 그래프의 결과값 가져와서 send_telegram_message(chat_id, answer)
    state = await client.threads.get_state(thread_id=thread_id)
    # state["values"] -> WeatherState 전체
    answer = state["values"].get("final_response") or "응답을 생성할 수 없어요 😢"
    await send_telegram_message(chat_id, answer)

    return {"ok": True}