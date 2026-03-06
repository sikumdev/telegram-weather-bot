# 최소 조건

1. 텔레그램 봇과 대화 시작
2. 날씨를 물어봄
    1. ngrok 서버로 webhook 날라감
    2. ngrok  -> langgraph dev 서버로 요청 보냄
    3. langgraph dev 서버가 llm으로 답변 생성
    4. telegram API로 메시지 전송
3. 날씨를 알려줌