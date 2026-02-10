"""
소송금융 투자 적합도 분석 프로그램 메인 실행 파일
Litigation Finance Suitability Analysis - Main Application
"""

import sys
from src.config import Config
from src.news_collector import NewsCollector
from src.ai_analyzer import AIAnalyzer
from src.storage import StorageManager


def main():
    """메인 실행 함수"""
    print("="*60)
    print("소송금융 투자 적합도 분석 프로그램")
    print("Litigation Finance Suitability Analyzer")
    print("="*60 + "\n")
    
    # 1. 설정 검증
    print("⚙️  설정 검증 중...")
    if not Config.validate():
        print("\n💡 설정 방법:")
        print("   1. .env 파일을 생성하세요 (.env.example 참고)")
        print("   2. 네이버 개발자 센터에서 Client ID와 Secret 발급")
        print("   3. Google AI Studio에서 Gemini API 키 발급")
        sys.exit(1)
    print("✅ 설정 완료\n")
    
    # 2. 뉴스 수집
    print("📰 뉴스 수집 시작...")
    collector = NewsCollector()
    articles = collector.search_multiple_keywords(
        Config.SEARCH_KEYWORDS,
        display=Config.SEARCH_DISPLAY
    )
    
    if not articles:
        print("❌ 수집된 뉴스가 없습니다.")
        sys.exit(1)
    
    print(f"✅ {len(articles)}개 뉴스 수집 완료\n")
    
    # 3. 분석 시작
    print("🤖 AI 분석 시작...")
    analyzer = AIAnalyzer()
    analyses = []
    
    for i, article in enumerate(articles, 1):
        print(f"[{i}/{len(articles)}] 분석 중: {article.title[:40]}...")
        analysis = analyzer.analyze_article(article)
        analyses.append(analysis)
        
        # 진행 상황 표시
        grade = analysis.analysis.suitability.grade
        grade_emoji = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}
        print(f"    → {grade_emoji.get(grade, '⚪')} {grade} | {analysis.analysis.case_field} | {analysis.analysis.defendant}")
    
    print(f"\n✅ {len(analyses)}개 분석 완료\n")
    
    # 4. 결과 저장
    print("💾 결과 저장 중...")
    storage = StorageManager()
    storage.save_results(analyses)
    storage.save_summary(analyses)
    
    # 5. 요약 출력
    storage.print_summary(analyses)
    
    print("✅ 프로그램 종료\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  사용자에 의해 중단되었습니다.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
