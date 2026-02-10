"""
사용 가능한 Gemini 모델 목록 확인 스크립트
"""
import google.generativeai as genai
from src.config import Config

genai.configure(api_key=Config.GEMINI_API_KEY)

print("🔍 사용 가능한 Gemini 모델 목록:\n")
print("=" * 70)

for model in genai.list_models():
    if 'generateContent' in model.supported_generation_methods:
        print(f"✅ {model.name}")
        print(f"   지원 메소드: {', '.join(model.supported_generation_methods)}")
        print()

print("=" * 70)
