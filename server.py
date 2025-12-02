# server.py
import asyncio
import json
import time
import fast_lane  # 감정 분석 모듈
import slow_lane  # LLM (OpenAI) 모듈

# 서버 설정
HOST = '127.0.0.1'
PORT = 5000

async def handle_client(reader, writer):
    """
    Unity 클라이언트 하나가 접속했을 때 처리하는 비동기 함수
    """
    addr = writer.get_extra_info('peername')
    print(f"[Server] 클라이언트 접속: {addr}")

    try:
        while True:
            # 1. 데이터 수신 (비동기 대기)
            # Unity에서 보낸 데이터를 읽습니다. (최대 1024바이트)
            data = await reader.read(1024)
            if not data:
                break
            
            user_text = data.decode('utf-8').strip()
            if not user_text:
                continue

            print(f"\n👤 User Input: {user_text}")
            
            # ---------------------------------------------------------
            # Path 1: Fast Lane (CPU 작업 - 동기 실행)
            # ---------------------------------------------------------
            start_time = time.time()
            
            # 감정 분석 및 리액션 추출
            fast_result = fast_lane.analyze_and_react(user_text)
            latency = time.time() - start_time
            
            # Fast Lane 결과 패킷 생성
            fast_packet = {
                "type": "fast",
                "emotion": fast_result['emotion_label'],
                "reaction": fast_result['reaction'],
                "keyword": fast_result['keyword'],
                "latency": f"{latency:.4f}s"
            }
            
            # Unity로 즉시 전송
            await send_json(writer, fast_packet)
            print(f"⚡ [Fast Sent] {fast_result['reaction']} ({latency:.4f}s)")
            
            # ---------------------------------------------------------
            # Path 2: Slow Lane (IO 작업 - 비동기 실행)
            # ---------------------------------------------------------
            print("[Slow Lane] LLM 생각 중...")
            
            # ★ 여기서 await를 하므로, LLM 응답이 올 때까지 
            # 이 함수는 대기 상태가 되지만, 서버 전체는 멈추지 않습니다.
            llm_reply = await slow_lane.generate_response(
                user_text, 
                fast_result['reaction']
            )
            
            # Slow Lane 결과 패킷 생성
            slow_packet = {
                "type": "slow",
                "npc_reply": llm_reply
            }
            
            # Unity로 전송
            await send_json(writer, slow_packet)
            print(f"[Slow Sent] {llm_reply}")

    except asyncio.IncompleteReadError:
        print("연결이 끊어졌습니다.")
    except ConnectionResetError:
        print("클라이언트가 강제로 연결을 종료했습니다.")
    except Exception as e:
        print(f"서버 에러: {e}")
    finally:
        print(f"클라이언트 접속 종료: {addr}")
        writer.close()
        await writer.wait_closed()

async def send_json(writer, data_dict):
    """딕셔너리를 JSON으로 바꿔 전송하는 헬퍼 (비동기)"""
    message = json.dumps(data_dict) + "\n"  # 패킷 구분자 \n
    writer.write(message.encode('utf-8'))
    await writer.drain()  # 버퍼 비우기 (전송 완료 대기)

async def main():
    # 비동기 서버 시작
    server = await asyncio.start_server(handle_client, HOST, PORT)
    
    addr = server.sockets[0].getsockname()
    print(f"[Async Server] AI 두뇌 가동 중... {addr}")
    print("   Unity 접속을 기다립니다.")

    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    try:
        # 윈도우의 경우 이벤트 루프 정책 설정이 필요할 수 있음
        if hasattr(asyncio, 'WindowsSelectorEventLoopPolicy'):
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n서버를 종료합니다.")