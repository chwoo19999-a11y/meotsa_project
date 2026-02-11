"""
Google Sheets 내보내기 모듈
Export analysis results to Google Sheets
"""

import gspread
from google.oauth2.service_account import Credentials
from typing import List
from datetime import datetime
from .models import CompleteAnalysis


class SheetsExporter:
    """Google Sheets로 분석 결과 내보내기"""
    
    def __init__(self, credentials_file: str = None):
        """
        Args:
            credentials_file: Google 서비스 계정 JSON 파일 경로
        """
        self.credentials_file = credentials_file or 'credentials.json'
        self.client = None
    
    def authenticate(self):
        """Google Sheets API 인증"""
        try:
            scopes = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
            
            creds = Credentials.from_service_account_file(
                self.credentials_file, 
                scopes=scopes
            )
            self.client = gspread.authorize(creds)
            return True
            
        except FileNotFoundError:
            print(f"❌ 인증 파일을 찾을 수 없습니다: {self.credentials_file}")
            print("💡 Google Cloud Console에서 서비스 계정을 생성하고 JSON 키를 다운로드하세요.")
            return False
        except Exception as e:
            print(f"❌ 인증 실패: {e}")
            return False
    
    def export_to_sheets(self, analyses: List[CompleteAnalysis], spreadsheet_id: str = None) -> str:
        """
        분석 결과를 Google Sheets로 내보내기
        
        Args:
            analyses: 분석 결과 리스트
            spreadsheet_id: 기존 스프레드시트 ID (None일 경우 새로 생성)
        
        Returns:
            str: 스프레드시트 URL
        """
        if not self.authenticate():
            return None
        
        try:
            # 기존 스프레드시트 열기 또는 새로 생성
            if spreadsheet_id:
                try:
                    spreadsheet = self.client.open_by_key(spreadsheet_id)
                    print(f"📂 기존 스프레드시트 열기: {spreadsheet.title}")
                    
                    # 새 시트 추가 (타임스탬프로 구분)
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    sheet_name = f"분석_{timestamp}"
                    worksheet = spreadsheet.add_worksheet(title=sheet_name, rows="1000", cols="20")
                    
                except Exception as e:
                    print(f"⚠️  기존 스프레드시트를 열 수 없습니다: {e}")
                    print("💡 새 스프레드시트를 생성합니다.")
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    spreadsheet = self.client.create(f"소송금융_분석결과_{timestamp}")
                    worksheet = spreadsheet.sheet1
            else:
                # 새 스프레드시트 생성
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                spreadsheet = self.client.create(f"소송금융_분석결과_{timestamp}")
                worksheet = spreadsheet.sheet1
            
            # 헤더 작성
            headers = [
                '등급', '제목', 'URL', '사건 분야', '상대방', 
                '피해 금액', '피해자 수', '진행 단계', '진행 상세',
                '요약', '판단 근거', '충족 조건', '분석 일시'
            ]
            worksheet.update('A1:M1', [headers])
            
            # 헤더 스타일 적용
            worksheet.format('A1:M1', {
                'backgroundColor': {'red': 0.4, 'green': 0.5, 'blue': 0.9},
                'textFormat': {'bold': True, 'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}},
                'horizontalAlignment': 'CENTER'
            })
            
            # 데이터 작성
            rows = []
            for analysis in analyses:
                grade = analysis.analysis.suitability.grade
                matched_conditions = '\n'.join(analysis.analysis.suitability.matched_conditions)
                
                row = [
                    grade,
                    analysis.title,
                    analysis.url,
                    analysis.analysis.case_field,
                    analysis.analysis.defendant,
                    analysis.analysis.damage_scale.amount,
                    analysis.analysis.damage_scale.victim_count,
                    analysis.analysis.progress_stage,
                    analysis.analysis.progress_detail,
                    analysis.analysis.summary,
                    analysis.analysis.suitability.reasoning,
                    matched_conditions,
                    analysis.metadata.analyzed_at
                ]
                rows.append(row)
            
            # 데이터 일괄 업데이트
            if rows:
                worksheet.update(f'A2:M{len(rows)+1}', rows)
                
                # 등급별 색상을 배치로 적용 (API 호출 최소화)
                format_requests = []
                
                for i, analysis in enumerate(analyses, start=2):
                    grade = analysis.analysis.suitability.grade
                    
                    if grade == 'High':
                        color = {'red': 1, 'green': 0.9, 'blue': 0.9}
                    elif grade == 'Medium':
                        color = {'red': 1, 'green': 0.96, 'blue': 0.9}
                    else:  # Low
                        color = {'red': 0.9, 'green': 0.97, 'blue': 0.9}
                    
                    format_requests.append({
                        'range': f'A{i}:M{i}',
                        'format': {'backgroundColor': color}
                    })
                
                # 한 번에 모든 포맷 적용 (배치 처리)
                if format_requests:
                    worksheet.batch_format(format_requests)
                
                # 텍스트 래핑 및 셀 크기 최적화
                # 전체 데이터 범위에 텍스트 줄바꿈 적용
                worksheet.format(f'A1:M{len(rows)+1}', {
                    'wrapStrategy': 'WRAP',
                    'verticalAlignment': 'TOP',
                    'textFormat': {'fontSize': 10}
                })
                
                # 열 너비 설정 (batch_update 사용)
                column_widths = [
                    (0, 80),    # A: 등급
                    (1, 300),   # B: 제목
                    (2, 80),    # C: URL
                    (3, 100),   # D: 사건 분야
                    (4, 120),   # E: 상대방
                    (5, 100),   # F: 피해 금액
                    (6, 100),   # G: 피해자 수
                    (7, 100),   # H: 진행 단계
                    (8, 150),   # I: 진행 상세
                    (9, 250),   # J: 요약
                    (10, 200),  # K: 판단 근거
                    (11, 180),  # L: 충족 조건
                    (12, 120),  # M: 분석 일시
                ]
                
                requests = []
                for col_index, width in column_widths:
                    requests.append({
                        'updateDimensionProperties': {
                            'range': {
                                'sheetId': worksheet.id,
                                'dimension': 'COLUMNS',
                                'startIndex': col_index,
                                'endIndex': col_index + 1
                            },
                            'properties': {
                                'pixelSize': width
                            },
                            'fields': 'pixelSize'
                        }
                    })
                
                # 배치로 열 너비 적용
                if requests:
                    spreadsheet.batch_update({'requests': requests})
            
            # 공유 설정 (누구나 볼 수 있게)
            spreadsheet.share('', perm_type='anyone', role='reader')
            
            url = spreadsheet.url
            print(f"✅ Google Sheets 내보내기 완료!")
            print(f"📊 URL: {url}")
            
            return url
            
        except Exception as e:
            print(f"❌ Google Sheets 내보내기 실패: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def export_summary(self, analyses: List[CompleteAnalysis], spreadsheet_url: str):
        """
        기존 스프레드시트에 요약 시트 추가
        
        Args:
            analyses: 분석 결과 리스트
            spreadsheet_url: 스프레드시트 URL
        """
        try:
            spreadsheet = self.client.open_by_url(spreadsheet_url)
            
            # 요약 시트 이름 생성 (중복 방지)
            summary_sheet_name = "요약"
            existing_sheets = [ws.title for ws in spreadsheet.worksheets()]
            
            # 이미 "요약" 시트가 있으면 타임스탬프 추가
            if summary_sheet_name in existing_sheets:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                summary_sheet_name = f"요약_{timestamp}"
            
            # 요약 시트 생성
            summary_sheet = spreadsheet.add_worksheet(title=summary_sheet_name, rows="100", cols="10")
            
            # 등급별 통계
            stats = {'High': 0, 'Medium': 0, 'Low': 0}
            for analysis in analyses:
                grade = analysis.analysis.suitability.grade
                stats[grade] = stats.get(grade, 0) + 1
            
            total = len(analyses)
            
            # 요약 데이터 작성
            summary_data = [
                ['📊 분석 요약', ''],
                ['', ''],
                ['총 분석 건수', total],
                ['', ''],
                ['🔴 High 등급', f"{stats['High']}건 ({stats['High']/total*100:.1f}%)"],
                ['🟡 Medium 등급', f"{stats['Medium']}건 ({stats['Medium']/total*100:.1f}%)"],
                ['🟢 Low 등급', f"{stats['Low']}건 ({stats['Low']/total*100:.1f}%)"],
            ]
            
            summary_sheet.update('A1:B7', summary_data)
            
            # 스타일 적용
            summary_sheet.format('A1:B1', {
                'textFormat': {'bold': True, 'fontSize': 16},
                'horizontalAlignment': 'CENTER'
            })
            
            print(f"✅ 요약 시트 추가 완료! (시트명: {summary_sheet_name})")
            
        except Exception as e:
            print(f"❌ 요약 시트 추가 실패: {e}")
