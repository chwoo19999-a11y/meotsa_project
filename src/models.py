"""
데이터 모델 정의
Data models for news articles and analysis results
"""

from datetime import datetime
from pydantic import BaseModel, Field


class NewsArticle(BaseModel):
    """뉴스 기사 데이터 모델"""
    title: str = Field(..., description="기사 제목")
    url: str = Field(..., description="기사 URL")
    description: str = Field(..., description="기사 요약/본문")
    published_date: str = Field(..., description="발행일 (YYYYMMDD)")
    source: str = Field(..., description="언론사명")


class DamageScale(BaseModel):
    """피해 규모"""
    amount: str = Field(..., description="피해 금액 또는 '추정 불가'")
    victim_count: str = Field(..., description="피해자 수 또는 '추정 불가'")


class SuitabilityEvaluation(BaseModel):
    """적합도 평가"""
    grade: str = Field(..., description="High|Medium|Low")
    reasoning: str = Field(..., description="판단 근거")
    matched_conditions: list[str] = Field(default_factory=list, description="충족된 적합 조건")
    unmatched_conditions: list[str] = Field(default_factory=list, description="미충족 조건")


class AnalysisResult(BaseModel):
    """분석 결과"""
    suitability: SuitabilityEvaluation
    case_field: str = Field(..., description="사건 분야")
    defendant: str = Field(..., description="상대방")
    damage_scale: DamageScale
    progress_stage: str = Field(..., description="피해 발생|관련 절차 진행|소송중|판결 선고|종결")
    progress_detail: str = Field(..., description="진행 단계 상세")
    summary: str = Field(..., description="2-3문장 요약")


class AnalysisMetadata(BaseModel):
    """분석 메타데이터"""
    analyzed_at: str = Field(..., description="분석 일시")
    analyzer_version: str = Field(default="1.0", description="분석기 버전")


class CompleteAnalysis(BaseModel):
    """완전한 분석 결과 (뉴스 + 분석)"""
    title: str
    url: str
    published_date: str
    source: str
    analysis: AnalysisResult
    metadata: AnalysisMetadata

    class Config:
        json_schema_extra = {
            "example": {
                "title": "개인정보 1만건 유출 ○○카드, 금감원 제재…피해자 집단소송 추진",
                "url": "https://news.naver.com/...",
                "published_date": "2026-02-09",
                "source": "○○일보",
                "analysis": {
                    "suitability": {
                        "grade": "High",
                        "reasoning": "대기업 상대, 집단 피해, 명확한 증거",
                        "matched_conditions": ["상대방 책임이 비교적 명확함"],
                        "unmatched_conditions": []
                    },
                    "case_field": "개인정보",
                    "defendant": "○○카드",
                    "damage_scale": {
                        "amount": "100억원",
                        "victim_count": "10000"
                    },
                    "progress_stage": "관련 절차 진행",
                    "progress_detail": "금감원 과징금 부과",
                    "summary": "개인정보 유출 사건"
                },
                "metadata": {
                    "analyzed_at": "2026-02-09T22:52:00+09:00",
                    "analyzer_version": "1.0"
                }
            }
        }
