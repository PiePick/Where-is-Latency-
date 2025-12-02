# main.py
import asyncio
import time
import speech_recognition as sr

# 우리가 만든 모듈들 가져오기
import fast_lane
import slow_lane

# 듣기 함수 (STT)
def listen_from_mic():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("\n[대기 중] 말씀하세요... (영어)")
        r.adjust_for_ambient_noise(source, duration=0.5)
        try:
            audio = r.listen(source, timeout=5, phrase_time_limit=10)
            print("변환 중...")
            text = r.recognize_google(audio, language='en-US')
            return text
        except:
            return None

# ★ 전체 워크플로우 실행 (비동기) ★
async def run_cycle():
    while True:
        # 1. 듣기 (동기 - 듣는 동안은 멈춤)
        user_input = listen_from_mic()
        
        if not user_input:
            continue
            
        print(f"👤 User: {user_input}")
        print("-" * 40)
        
        start_time = time.time()
        
        # 2. Fast Lane 실행 (CPU 작업이라 await 없이 즉시 실행)
        # 이 부분은 아주 빨라서(0.1초) 그냥 동기로 처리해도 무방합니다.
        fast_result = fast_lane.analyze_and_react(user_input)
        
        reaction = fast_result['reaction']
        keyword = fast_result['keyword']
        
        # 3. [시각화] Fast Lane 결과 즉시 출력 (스피커 재생 시점)
        latency = time.time() - start_time
        
        # [수정] fast_lane.py에서 반환하는 키 이름은 'emotion_label' 입니다.
        print(f"⚡ [Fast Lane] ({latency:.2f}s) 감정: {fast_result['emotion_label']}")
        print(f"   🔊 오디오 재생: \"{reaction}\"")
        if keyword:
            print(f"   🦜 에코잉 재생: \"{keyword}?\"")
            
        # 4. Slow Lane 요청 (Fast Lane 리액션을 정보로 넘김)
        # 여기서 create_task를 쓰거나 바로 await를 해도 되지만,
        # 이미 Fast Lane이 끝났으므로 순차적으로 요청합니다.
        
        print(f"[Slow Lane] GPT 생각 중...")
        llm_answer = await slow_lane.generate_response(user_input, reaction)
        
        # 5. Slow Lane 결과 출력
        total_time = time.time() - start_time
        print(f"[Slow Lane] ({total_time:.2f}s) 도착!")
        print(f"   NPC 답변: \"{llm_answer}\"")
        
        print("=" * 40)

# 실행 진입점
if __name__ == "__main__":
    try:
        asyncio.run(run_cycle())
    except KeyboardInterrupt:
        print("\n시스템 종료")