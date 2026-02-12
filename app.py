"""
소송금융 투자 적합도 분석 웹 대시보드
Flask-based web dashboard for litigation finance analysis
"""

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import threading
import json
import os
from datetime import datetime

from src.config import Config
from src.news_collector import NewsCollector
from src.ai_analyzer import AIAnalyzer
from src.storage import StorageManager

app = Flask(__name__)
CORS(app)

# 분석 상태 저장
analysis_state = {
    'is_running': False,
    'progress': 0,
    'total': 0,
    'current_article': '',
    'results': [],
    'stats': {'High': 0, 'Medium': 0, 'Low': 0}
}


@app.route('/')
def index():
    """메인 대시보드 페이지"""
    return render_template('index.html')


@app.route('/api/analyze', methods=['POST'])
def start_analysis():
    """분석 시작 API"""
    if analysis_state['is_running']:
        return jsonify({'error': '이미 분석이 진행 중입니다.'}), 400
    
    # 백그라운드에서 분석 실행
    thread = threading.Thread(target=run_analysis)
    thread.daemon = True
    thread.start()
    
    return jsonify({'message': '분석이 시작되었습니다.'}), 200


@app.route('/api/status', methods=['GET'])
def get_status():
    """분석 진행 상황 조회 API"""
    return jsonify({
        'is_running': analysis_state['is_running'],
        'progress': analysis_state['progress'],
        'total': analysis_state['total'],
        'current_article': analysis_state['current_article'],
        'stats': analysis_state['stats']
    })


@app.route('/api/results', methods=['GET'])
def get_results():
    """분석 결과 조회 API"""
    # 등급 필터링
    grade_filter = request.args.get('grade', 'all')
    
    results = analysis_state['results']
    if grade_filter != 'all':
        results = [r for r in results if r['grade'] == grade_filter]
    
    return jsonify({
        'total': len(results),
        'results': results,
        'stats': analysis_state['stats']
    })


@app.route('/api/export-sheets', methods=['POST'])
def export_to_sheets():
    """Google Sheets로 내보내기 API"""
    try:
        from src.sheets_exporter import SheetsExporter
        from src.storage import StorageManager
        
        # 최신 분석 결과 로드
        storage = StorageManager()
        
        # output 디렉토리에서 가장 최근 결과 파일 찾기
        import glob
        result_files = glob.glob(os.path.join(storage.output_dir, 'analysis_results_*.json'))
        
        if not result_files:
            return jsonify({'error': '분석 결과가 없습니다.'}), 404
        
        # 가장 최근 파일 선택
        latest_file = max(result_files, key=os.path.getctime)
        
        # JSON 파일 로드
        with open(latest_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # CompleteAnalysis 객체로 변환
        from src.models import CompleteAnalysis
        analyses = [CompleteAnalysis(**result) for result in data['results']]
        
        # Google Sheets로 내보내기
        exporter = SheetsExporter()
        url = exporter.export_to_sheets(analyses, spreadsheet_id=Config.GOOGLE_SHEETS_ID)
        
        if url:
            return jsonify({'success': True, 'url': url}), 200
        else:
            return jsonify({'error': 'Google Sheets 내보내기 실패'}), 500
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


def run_analysis():
    """분석 실행 함수 (백그라운드)"""
    global analysis_state
    
    try:
        analysis_state['is_running'] = True
        analysis_state['progress'] = 0
        analysis_state['results'] = []
        analysis_state['stats'] = {'High': 0, 'Medium': 0, 'Low': 0}
        
        # 1. 뉴스 수집
        collector = NewsCollector()
        articles = collector.search_multiple_keywords(
            Config.SEARCH_KEYWORDS,
            display=Config.SEARCH_DISPLAY
        )
        
        analysis_state['total'] = len(articles)
        
        # 2. 분석
        analyzer = AIAnalyzer()
        storage = StorageManager()
        
        complete_analyses = []
        
        for i, article in enumerate(articles, 1):
            analysis_state['current_article'] = article.title
            analysis_state['progress'] = i
            
            # AI 분석
            complete_analysis = analyzer.analyze_article(article)
            complete_analyses.append(complete_analysis)
            
            # 결과 저장 (웹용)
            grade = complete_analysis.analysis.suitability.grade
            analysis_state['stats'][grade] = analysis_state['stats'].get(grade, 0) + 1
            
            result_item = {
                'title': complete_analysis.title,
                'url': complete_analysis.url,
                'grade': grade,
                'case_field': complete_analysis.analysis.case_field,
                'defendant': complete_analysis.analysis.defendant,
                'damage_amount': complete_analysis.analysis.damage_scale.amount,
                'victim_count': complete_analysis.analysis.damage_scale.victim_count,
                'progress_stage': complete_analysis.analysis.progress_stage,
                'summary': complete_analysis.analysis.summary,
                'reasoning': complete_analysis.analysis.suitability.reasoning,
                'matched_conditions': complete_analysis.analysis.suitability.matched_conditions
            }
            
            analysis_state['results'].append(result_item)
        
        # 3. JSON 파일로 저장
        storage.save_results(complete_analyses)
        storage.save_summary(complete_analyses)
        
        analysis_state['is_running'] = False
        
    except Exception as e:
        print(f"분석 오류: {e}")
        analysis_state['is_running'] = False
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    # API 키 검증
    if not Config.validate():
        print("\n⚠️  .env 파일을 설정하고 다시 실행하세요.")
        exit(1)
    
    print("="*60)
    print("🌐 소송금융 투자 적합도 분석 웹 대시보드")
    print("="*60)
    print("\n📍 서버 주소: http://localhost:5000")
    print("⚡ 브라우저에서 위 주소로 접속하세요.\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)
