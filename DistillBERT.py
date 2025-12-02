# 필수 라이브러리 설치 필요: pip install transformers torch

from transformers import pipeline

def analyze_emotion(text):
    """
    DistilBERT 모델을 사용하여 텍스트의 세부 감정을 분석하는 함수
    """
    # 1. Hugging Face의 파이프라인 로드 (GoEmotions로 학습된 DistilBERT 모델 지정)
    # top_k=None으로 설정하면 모든 감정 라벨에 대한 점수를 반환합니다.
    emotion_classifier = pipeline(
        "text-classification", 
        model="joeddav/distilbert-base-uncased-go-emotions-student", 
        top_k=None
    )
    
    # 2. 모델 추론 실행
    results = emotion_classifier(text)
    
    # 3. 결과 정리 및 출력 (점수가 높은 순으로 정렬되어 반환됨)
    print(f"입력 텍스트: '{text}'\n")
    print("=== 감정 분석 결과 (상위 5개) ===")
    
    # results는 리스트의 리스트 형태이므로 첫 번째 요소를 가져옵니다.
    scores = results[0]
    
    # 보기 좋게 상위 5개만 출력
    for i, emotion in enumerate(scores[:5]):
        label = emotion['label']
        score = emotion['score']
        print(f"{i+1}. {label:<15}: {score:.4f} ({score*100:.1f}%)")

if __name__ == "__main__":
    # 테스트할 문장 (영어)
    # 번역: "이 패키지가 정말 빨리 도착해서 너무 기뻐! 정말 고마워."
    test_text = "I am so happy that this package arrived early! Thanks a lot."
    
    analyze_emotion(test_text)