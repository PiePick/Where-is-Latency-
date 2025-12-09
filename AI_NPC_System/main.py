import asyncio
import time
import speech_recognition as sr
import sys

# 우리가 만든 모듈들 가져오기
import fast_lane
import slow_lane

# === ⚙️ 전역 설정 ===
INPUT_MODE = 't'  # 기본값 (t: 텍스트 / v: 음성)

# === 🎤 듣기 함수 (STT - 음성 모드용) ===
def get_input_from_mic():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("\n🎤 [대기 중] 말씀하세요... (영어)")
        # 주변 소음 적응 (너무 길면 반응이 느려지니 0.5초로)
        r.adjust_for_ambient_noise(source, duration=0.5)
        
        try:
            # 말할 때까지 최대 5초 대기, 말하기 시작하면 최대 10초까지 녹음
            audio = r.listen(source, timeout=5, phrase_time_limit=10)
            print("⏳ 변환 중...")
            text = r.recognize_google(audio, language='en-US')
            return text
        except sr.WaitTimeoutError:
            return None # 말 안 하고 시간 초과됨
        except sr.UnknownValueError:
            return None # 무슨 말인지 못 알아들음
        except Exception as e:
            print(f"⚠️ 마이크 에러: {e}")
            return None

# === ⌨️ 입력 함수 (타이핑 - 텍스트 모드용) ===
# 비동기 루프 안에서 input()을 쓰면 멈춰버리므로,
# 텍스트 모드일 때는 동기식으로 입력을 받기 위해 별도 처리 없이 바로 input()을 씁니다.

# ★ 전체 워크플로우 실행 (비동기) ★
async def run_cycle():
    print(f"\n🚀 시스템 시작! [{INPUT_MODE.upper()}] 모드로 대기 중입니다.")
    
    while True:
        # 1. 입력 받기 (모드에 따라 분기)
        user_input = None
        
        if INPUT_MODE == 'v':
            # 음성 모드
            user_input = get_input_from_mic()
            if not user_input:
                continue # 인식 실패하거나 말 안 하면 다시 대기
        else:
            # 텍스트 모드 (비동기 루프를 막지 않기 위해 aioconsole을 쓰면 좋지만,
            # 간단한 테스트를 위해 표준 input() 사용. 입력할 때까지 코드가 여기서 멈춤)
            try:
                user_input = input("\n⌨️  User (입력): ").strip()
                if not user_input:
                    continue
            except EOFError:
                break # 종료 처리

        # 사용자 입력 출력
        print(f"👤 User: {user_input}")
        print("-" * 40)
        
        start_time = time.time()
        
        # 2. Fast Lane 실행
        fast_result = fast_lane.analyze_and_react(user_input)
        
        reaction = fast_result['reaction']
        keyword = fast_result['keyword']
        
        # 3. [시각화] Fast Lane 결과 출력
        latency = time.time() - start_time
        print(f"⚡ [Fast Lane] ({latency:.2f}s) 감정: {fast_result['emotion_detail']}")
        print(f"   🔊 리액션: \"{reaction}\"")
        if keyword:
            print(f"   🦜 에코잉: \"{keyword}?\"")
            
        # 4. Slow Lane 요청 (Fast Lane 리액션 정보 전달)
        #print(f"🐢 [Slow Lane] GPT 생각 중...")
        llm_answer = await slow_lane.generate_response(user_input, reaction)
        
        # 5. Slow Lane 결과 출력
        total_time = time.time() - start_time
        print(f"🐢 [Slow Lane] ({total_time:.2f}s) 도착!")
        print(f"   💬 NPC 답변: \"{llm_answer}\"")
        
        print("=" * 40)

# 실행 진입점
if __name__ == "__main__":
    try:
        # 시작할 때 모드 물어보기
        while True:
            choice = input("입력 방식을 선택하세요 (v: 마이크 / t: 키보드): ").strip().lower()
            if choice in ['v', 't']:
                INPUT_MODE = choice
                break
            else:
                print("잘못된 입력입니다. 'v' 또는 't'만 입력해주세요.")

        asyncio.run(run_cycle())
        
    except KeyboardInterrupt:
        print("\n👋 시스템을 종료합니다.")