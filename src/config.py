"""
설정 관리
Configuration management for API keys and search parameters
"""

import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()


class Config:
    """애플리케이션 설정"""
    
    # 네이버 API 설정
    NAVER_CLIENT_ID: str = os.getenv("NAVER_CLIENT_ID", "")
    NAVER_CLIENT_SECRET: str = os.getenv("NAVER_CLIENT_SECRET", "")
    
    # Gemini API 설정
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    
    # Google Sheets ID (선택사항)
    GOOGLE_SHEETS_ID: str = os.getenv("GOOGLE_SHEETS_ID", "")
    
    # 검색 키워드 (OR 조건)
    SEARCH_KEYWORDS: list[str] = [
        "소송",
        "손해배상",
        "집단소송",
        "공동소송",
        "피해자",
        "피해보상",
        "피해구제"
    ]
    
    # 검색 옵션
    SEARCH_DISPLAY: int = 100  # 검색 결과 개수 (최대 100)
    SEARCH_MAX_START: int = 300  # 페이지네이션 최대 시작 위치 (최대 1000)
    SEARCH_SORT: str = "date"  # 정렬 방식 (date: 최신순, sim: 관련도순)
    
    # 출력 디렉토리
    OUTPUT_DIR: str = "output"
    
    # 중복 판단 설정
    TITLE_SIMILARITY_THRESHOLD: float = 0.8  # 제목 유사도 임계값 (0.0~1.0)
    HISTORY_RETENTION_DAYS: int = 7  # 수집 이력 보관 일수
    
    # 분석기 버전
    ANALYZER_VERSION: str = "1.0"
    
    @classmethod
    def validate(cls) -> bool:
        """API 키 검증"""
        if not cls.NAVER_CLIENT_ID or not cls.NAVER_CLIENT_SECRET:
            print("❌ 네이버 API 키가 설정되지 않았습니다.")
            print("   .env 파일에 NAVER_CLIENT_ID와 NAVER_CLIENT_SECRET을 설정하세요.")
            return False
        
        if not cls.GEMINI_API_KEY:
            print("❌ Gemini API 키가 설정되지 않았습니다.")
            print("   .env 파일에 GEMINI_API_KEY를 설정하세요.")
            return False
        
        return True
