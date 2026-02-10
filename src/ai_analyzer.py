"""
AI 기반 적합도 분석 모듈
Gemini AI-based litigation finance suitability analyzer
"""

import json
import google.generativeai as genai
from datetime import datetime
from .models import NewsArticle, CompleteAnalysis, AnalysisResult, AnalysisMetadata
from .config import Config


class AIAnalyzer:
    """Gemini AI를 사용한 소송금융 적합도 분석"""
    
    def __init__(self):
        genai.configure(api_key=Config.GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
    
    def analyze_article(self, article: NewsArticle) -> CompleteAnalysis:
        """
        뉴스 기사 분석
        
        Args:
            article: 분석할 뉴스 기사
        
        Returns:
            CompleteAnalysis: 분석 결과
        """
        prompt = self._create_analysis_prompt(article)
        
        try:
            response = self.model.generate_content(prompt)
            analysis_text = response.text
            
            # JSON 추출 (```json ... ``` 형식 처리)
            json_text = self._extract_json(analysis_text)
            analysis_data = json.loads(json_text)
            
            # AnalysisResult 객체 생성
            analysis_result = AnalysisResult(**analysis_data)
            
            # CompleteAnalysis 객체 생성
            complete_analysis = CompleteAnalysis(
                title=article.title,
                url=article.url,
                published_date=self._format_date(article.published_date),
                source=article.source,
                analysis=analysis_result,
                metadata=AnalysisMetadata(
                    analyzed_at=datetime.now().strftime("%Y-%m-%dT%H:%M:%S+09:00"),
                    analyzer_version=Config.ANALYZER_VERSION
                )
            )
            
            return complete_analysis
            
        except Exception as e:
            print(f"❌ 분석 실패: {article.title[:30]}... - {e}")
            # 실패 시 기본값 반환
            return self._create_fallback_analysis(article, str(e))
    
    def _create_analysis_prompt(self, article: NewsArticle) -> str:
        """분석 프롬프트 생성"""
        prompt = f"""당신은 소송금융 투자를 검토하는 심사역입니다. 다음 뉴스 기사를 분석하여 소송금융 투자 적합도를 판단하세요.

# 뉴스 기사
**제목**: {article.title}
**내용**: {article.description}
**발행일**: {article.published_date}

# 분석 기준

## 적합 조건 (6가지)
1. 상대방 책임이 비교적 명확함
2. 상대방에게 자력이 충분함 (대기업, 금융기관, 상장회사, 공공기관 등)
3. 집단적 피해 (수십 명 이상)
4. 피해 규모가 큼 (수억 원 이상 또는 수만 명 이상)
5. 증거가 있거나 확보 가능함 (공식 조사, 정부 발표 등)
6. 이미 공적 절차가 진행 중임 (검찰 수사, 정부 조사, 행정처분 등)

## 부적합 조건 (1가지)
1. 이미 종결된 사건 (합의 완료, 판결 확정)

## 등급 판정
- **High**: 적합 조건 4개 이상, 부적합 조건 없음
- **Medium**: 적합 조건 2~3개, 부적합 조건 없음
- **Low**: 적합 조건 1개 이하 또는 부적합 조건 1개 이상

## 사건 분야 분류
제조물책임, 산업재해, 환경, 소비자분쟁, 노동, 개인정보, 행정, 건설·부동산, 지식재산권 등

## 진행 단계
피해 발생, 관련 절차 진행, 소송중, 판결 선고, 종결

# 출력 형식

**반드시 다음 JSON 형식으로만 출력하세요. 설명이나 추가 텍스트 없이 JSON만 출력하세요:**

{{
  "suitability": {{
    "grade": "High|Medium|Low",
    "reasoning": "판단 근거를 구체적으로 작성",
    "matched_conditions": ["충족된 조건1", "충족된 조건2"],
    "unmatched_conditions": ["미충족 조건1"]
  }},
  "case_field": "사건 분야",
  "defendant": "상대방 (기업명, 기관명 등)",
  "damage_scale": {{
    "amount": "피해 금액 또는 '추정 불가'",
    "victim_count": "피해자 수 또는 '추정 불가'"
  }},
  "progress_stage": "피해 발생|관련 절차 진행|소송중|판결 선고|종결",
  "progress_detail": "진행 단계 상세 내용",
  "summary": "2-3문장으로 사건 요약"
}}
"""
        return prompt
    
    @staticmethod
    def _extract_json(text: str) -> str:
        """텍스트에서 JSON 추출"""
        # ```json ... ``` 형식 처리
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            return text[start:end].strip()
        elif "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            return text[start:end].strip()
        else:
            return text.strip()
    
    @staticmethod
    def _format_date(date_str: str) -> str:
        """날짜 형식 변환: YYYYMMDD -> YYYY-MM-DD"""
        if len(date_str) == 8:
            return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
        return date_str
    
    def _create_fallback_analysis(self, article: NewsArticle, error_msg: str) -> CompleteAnalysis:
        """분석 실패 시 기본 응답 생성"""
        from .models import SuitabilityEvaluation, DamageScale
        
        return CompleteAnalysis(
            title=article.title,
            url=article.url,
            published_date=self._format_date(article.published_date),
            source=article.source,
            analysis=AnalysisResult(
                suitability=SuitabilityEvaluation(
                    grade="Low",
                    reasoning=f"분석 실패: {error_msg}",
                    matched_conditions=[],
                    unmatched_conditions=[]
                ),
                case_field="미분류",
                defendant="미상",
                damage_scale=DamageScale(
                    amount="추정 불가",
                    victim_count="추정 불가"
                ),
                progress_stage="피해 발생",
                progress_detail="분석 실패",
                summary=article.description[:100]
            ),
            metadata=AnalysisMetadata(
                analyzed_at=datetime.now().strftime("%Y-%m-%dT%H:%M:%S+09:00"),
                analyzer_version=Config.ANALYZER_VERSION
            )
        )
