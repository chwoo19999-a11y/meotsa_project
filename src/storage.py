"""
분석 결과 저장 관리 모듈
Storage manager for analysis results
"""

import json
import os
from datetime import datetime
from .models import CompleteAnalysis
from .config import Config


class StorageManager:
    """분석 결과 저장 및 관리"""
    
    def __init__(self, output_dir: str = None):
        self.output_dir = output_dir or Config.OUTPUT_DIR
        self._ensure_output_dir()
    
    def _ensure_output_dir(self):
        """출력 디렉토리 생성"""
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            print(f"📁 출력 디렉토리 생성: {self.output_dir}")
    
    def save_results(self, analyses: list[CompleteAnalysis], filename: str = None) -> str:
        """
        분석 결과 저장
        
        Args:
            analyses: 분석 결과 리스트
            filename: 파일명 (None일 경우 타임스탬프 사용)
        
        Returns:
            str: 저장된 파일 경로
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"analysis_results_{timestamp}.json"
        
        filepath = os.path.join(self.output_dir, filename)
        
        # Pydantic 모델을 dict로 변환
        data = {
            "total_count": len(analyses),
            "analyzed_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S+09:00"),
            "results": [analysis.model_dump() for analysis in analyses]
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"💾 결과 저장 완료: {filepath}")
        return filepath
    
    def save_summary(self, analyses: list[CompleteAnalysis], filename: str = None) -> str:
        """
        분석 요약 저장 (등급별 통계)
        
        Args:
            analyses: 분석 결과 리스트
            filename: 파일명
        
        Returns:
            str: 저장된 파일 경로
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"analysis_summary_{timestamp}.json"
        
        filepath = os.path.join(self.output_dir, filename)
        
        # 등급별 통계
        grade_stats = {"High": 0, "Medium": 0, "Low": 0}
        high_cases = []
        
        for analysis in analyses:
            grade = analysis.analysis.suitability.grade
            grade_stats[grade] = grade_stats.get(grade, 0) + 1
            
            if grade == "High":
                high_cases.append({
                    "title": analysis.title,
                    "url": analysis.url,
                    "defendant": analysis.analysis.defendant,
                    "case_field": analysis.analysis.case_field,
                    "damage_amount": analysis.analysis.damage_scale.amount
                })
        
        summary = {
            "total_count": len(analyses),
            "analyzed_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S+09:00"),
            "grade_statistics": grade_stats,
            "high_priority_cases": high_cases
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        print(f"📊 요약 저장 완료: {filepath}")
        return filepath
    
    def print_summary(self, analyses: list[CompleteAnalysis]):
        """
        분석 결과 요약 출력
        
        Args:
            analyses: 분석 결과 리스트
        """
        print("\n" + "="*60)
        print("📊 분석 결과 요약")
        print("="*60)
        
        # 등급별 통계
        grade_stats = {"High": 0, "Medium": 0, "Low": 0}
        for analysis in analyses:
            grade = analysis.analysis.suitability.grade
            grade_stats[grade] = grade_stats.get(grade, 0) + 1
        
        print(f"\n총 분석 건수: {len(analyses)}개")
        print(f"  🔴 High:   {grade_stats['High']:2d}개 ({grade_stats['High']/len(analyses)*100:.1f}%)")
        print(f"  🟡 Medium: {grade_stats['Medium']:2d}개 ({grade_stats['Medium']/len(analyses)*100:.1f}%)")
        print(f"  🟢 Low:    {grade_stats['Low']:2d}개 ({grade_stats['Low']/len(analyses)*100:.1f}%)")
        
        # High 등급 케이스 출력
        high_cases = [a for a in analyses if a.analysis.suitability.grade == "High"]
        if high_cases:
            print(f"\n🔴 High 등급 케이스 ({len(high_cases)}개):")
            print("-" * 60)
            for i, case in enumerate(high_cases, 1):
                print(f"{i}. {case.title[:50]}...")
                print(f"   상대방: {case.analysis.defendant}")
                print(f"   분야: {case.analysis.case_field}")
                print(f"   피해규모: {case.analysis.damage_scale.amount}")
                print(f"   URL: {case.url}")
                print()
        
        print("="*60 + "\n")
