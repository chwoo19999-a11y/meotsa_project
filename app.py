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
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import atexit

from src.config import Config
from src.news_collector import NewsCollector
from src.ai_analyzer import AIAnalyzer
from src.storage import StorageManager

app = Flask(__name__)
CORS(app)

# 스케줄러 초기화
scheduler = BackgroundScheduler()
scheduler.start()

# 앱 종료 시 스케줄러도 종료
atexit.register(lambda: scheduler.shutdown())

# 분석 상태 저장
analysis_state = {
    'is_running': False,
    'progress': 0,
    'total': 0,
    'current_article': '',
    'results': [],
    'accumulated_results': [],  # 모든 실행에서 누적된 결과
    'accumulated_urls': set(),  # 누적 결과의 URL (중복 방지)
    'stats': {'High': 0, 'Medium': 0, 'Low': 0},
    'accumulated_stats': {'High': 0, 'Medium': 0, 'Low': 0},  # 누적 통계
    'scheduler_enabled': False,
    'last_scheduled_run': None,
    'next_scheduled_run': None,
    'run_count': 0,  # 실행 횟수
    'cancel_requested': False  # 분석 취소 요청
}


def scheduled_news_collection():
    """스케줄러에 의해 60분마다 자동 실행되는 뉴스 수집 함수"""
    print(f"\n{'='*60}")
    print(f"⏰ [자동 수집] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")
    
    # 이미 분석이 진행 중이면 스킵
    if analysis_state['is_running']:
        print("⚠️  이미 분석이 진행 중이므로 이번 수집을 건너뜁니다.")
        return
    
    # 마지막 실행 시간 기록
    analysis_state['last_scheduled_run'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # 백그라운드에서 분석 실행 (Google Sheets 자동 내보내기 활성화)
    thread = threading.Thread(target=run_analysis, kwargs={'auto_export_to_sheets': True})
    thread.daemon = True
    thread.start()


@app.route('/')
def index():
    """메인 대시보드 페이지"""
    return render_template('index.html')


@app.route('/api/analyze', methods=['POST'])
def start_analysis():
    """분석 시작 API"""
    if analysis_state['is_running']:
        return jsonify({'error': '이미 분석이 진행 중입니다.'}), 400
    
    # 백그라운드에서 분석 실행 (Google Sheets 자동 내보내기 활성화)
    thread = threading.Thread(target=run_analysis, kwargs={'auto_export_to_sheets': True})
    thread.daemon = True
    thread.start()
    
    return jsonify({'message': '분석이 시작되었습니다. 완료 후 자동으로 Google Sheets에 내보냅니다.'}), 200


@app.route('/api/status', methods=['GET'])
def get_status():
    """분석 진행 상황 조회 API"""
    # 다음 실행 시간 계산
    next_run = None
    if analysis_state['scheduler_enabled'] and scheduler.get_jobs():
        job = scheduler.get_jobs()[0]
        if job.next_run_time:
            next_run = job.next_run_time.strftime('%Y-%m-%d %H:%M:%S')
    
    return jsonify({
        'is_running': analysis_state['is_running'],
        'progress': analysis_state['progress'],
        'total': analysis_state['total'],
        'current_article': analysis_state['current_article'],
        'stats': analysis_state['stats'],
        'scheduler_enabled': analysis_state['scheduler_enabled'],
        'last_scheduled_run': analysis_state['last_scheduled_run'],
        'next_scheduled_run': next_run
    })


@app.route('/api/results', methods=['GET'])
def get_results():
    """분석 결과 조회 API (누적 결과 반환)"""
    # 등급 필터링
    grade_filter = request.args.get('grade', 'all')
    
    # 누적 결과 반환
    results = analysis_state['accumulated_results']
    if grade_filter != 'all':
        results = [r for r in results if r['grade'] == grade_filter]
    
    return jsonify({
        'total': len(results),
        'results': results,
        'stats': analysis_state['accumulated_stats'],
        'run_count': analysis_state['run_count']
    })


@app.route('/api/scheduler/start', methods=['POST'])
def start_scheduler():
    """자동 수집 스케줄러 시작 API"""
    if analysis_state['scheduler_enabled']:
        return jsonify({'message': '스케줄러가 이미 실행 중입니다.'}), 400
    
    try:
        # 60분마다 실행되는 작업 추가
        scheduler.add_job(
            func=scheduled_news_collection,
            trigger=IntervalTrigger(minutes=60),
            id='news_collection_job',
            name='자동 뉴스 수집',
            replace_existing=True
        )
        
        analysis_state['scheduler_enabled'] = True
        
        # 다음 실행 시간
        job = scheduler.get_job('news_collection_job')
        next_run = job.next_run_time.strftime('%Y-%m-%d %H:%M:%S') if job.next_run_time else None
        
        print(f"\n✅ 자동 수집 스케줄러가 시작되었습니다.")
        print(f"📅 다음 실행 시간: {next_run}\n")
        
        return jsonify({
            'message': '자동 수집 스케줄러가 시작되었습니다.',
            'next_run': next_run
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/scheduler/stop', methods=['POST'])
def stop_scheduler():
    """자동 수집 스케줄러 중지 API + 진행 중인 분석도 취소"""
    try:
        if analysis_state['scheduler_enabled']:
            scheduler.remove_job('news_collection_job')
            analysis_state['scheduler_enabled'] = False
            analysis_state['next_scheduled_run'] = None
        
        # 진행 중인 분석도 취소
        if analysis_state['is_running']:
            analysis_state['cancel_requested'] = True
            print(f"\n🛑 자동 수집 스케줄러가 중지되고 진행 중인 분석이 취소됩니다.\n")
            return jsonify({'message': '스케줄러가 중지되고 진행 중인 분석이 취소됩니다.'}), 200
        
        print(f"\n🛑 자동 수집 스케줄러가 중지되었습니다.\n")
        return jsonify({'message': '자동 수집 스케줄러가 중지되었습니다.'}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/analyze/stop', methods=['POST'])
def stop_analysis():
    """진행 중인 분석 취소 API"""
    if not analysis_state['is_running']:
        return jsonify({'message': '진행 중인 분석이 없습니다.'}), 400
    
    analysis_state['cancel_requested'] = True
    print(f"\n🛑 분석 취소가 요청되었습니다.\n")
    return jsonify({'message': '분석 취소가 요청되었습니다. 현재 기사 분석 후 중단됩니다.'}), 200


@app.route('/api/export-sheets', methods=['POST'])
def export_to_sheets():
    """Google Sheets로 내보내기 API — 누적된 전체 기사 내보내기"""
    try:
        from src.sheets_exporter import SheetsExporter
        from src.storage import StorageManager
        from src.models import CompleteAnalysis
        
        accumulated = analysis_state['accumulated_results']
        
        if not accumulated:
            return jsonify({'error': '누적된 분석 결과가 없습니다.'}), 404
        
        # 누적된 모든 결과 파일을 로드하여 CompleteAnalysis 객체로 변환
        storage = StorageManager()
        import glob
        result_files = sorted(
            glob.glob(os.path.join(storage.output_dir, 'analysis_results_*.json')),
            key=os.path.getctime
        )
        
        all_analyses = []
        seen_urls = set()
        
        for result_file in result_files:
            with open(result_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            for result in data.get('results', []):
                url = result.get('url', '')
                if url not in seen_urls:
                    all_analyses.append(CompleteAnalysis(**result))
                    seen_urls.add(url)
        
        if not all_analyses:
            return jsonify({'error': '분석 결과 파일을 불러올 수 없습니다.'}), 404
        
        print(f"📊 누적 {len(all_analyses)}개 기사를 Google Sheets로 내보냅니다...")
        
        # Google Sheets로 내보내기
        exporter = SheetsExporter()
        url = exporter.export_to_sheets(all_analyses, spreadsheet_id=Config.GOOGLE_SHEETS_ID)
        
        if url:
            return jsonify({
                'success': True, 
                'url': url,
                'exported_count': len(all_analyses)
            }), 200
        else:
            return jsonify({'error': 'Google Sheets 내보내기 실패'}), 500
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


def run_analysis(auto_export_to_sheets=False):
    """분석 실행 함수 (백그라운드)
    
    Args:
        auto_export_to_sheets: True이면 분석 완료 후 자동으로 Google Sheets로 내보내기
    """
    global analysis_state
    
    try:
        analysis_state['is_running'] = True
        analysis_state['cancel_requested'] = False
        analysis_state['progress'] = 0
        analysis_state['results'] = []  # 현재 실행 결과 (리셋)
        analysis_state['stats'] = {'High': 0, 'Medium': 0, 'Low': 0}
        analysis_state['run_count'] += 1
        
        # 1. 뉴스 수집 (페이지네이션 포함)
        collector = NewsCollector()
        articles = collector.search_multiple_keywords(
            Config.SEARCH_KEYWORDS,
            display=Config.SEARCH_DISPLAY
        )
        
        # 이미 누적된 URL은 제외하여 분석 대상에서 제외
        new_articles = [
            a for a in articles 
            if a.url not in analysis_state['accumulated_urls']
        ]
        
        print(f"📰 총 {len(articles)}개 수집, 신규 {len(new_articles)}개 (기존 누적 {len(analysis_state['accumulated_results'])}개)")
        
        analysis_state['total'] = len(new_articles)
        
        # 2. 신규 기사만 분석
        analyzer = AIAnalyzer()
        storage = StorageManager()
        
        complete_analyses = []
        
        for i, article in enumerate(new_articles, 1):
            # 취소 요청 확인
            if analysis_state['cancel_requested']:
                print(f"\n🛑 분석이 취소되었습니다. ({i-1}/{len(new_articles)}개 완료)")
                break
            
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
            
            # 누적 결과에도 추가
            analysis_state['accumulated_results'].append(result_item)
            analysis_state['accumulated_urls'].add(complete_analysis.url)
            analysis_state['accumulated_stats'][grade] = analysis_state['accumulated_stats'].get(grade, 0) + 1
        
        # 3. JSON 파일로 저장 (이번 실행분)
        if complete_analyses:
            storage.save_results(complete_analyses)
            storage.save_summary(complete_analyses)
        
        print(f"\n📊 이번 실행: {len(complete_analyses)}개 분석 | 누적 총: {len(analysis_state['accumulated_results'])}개")
        
        # 4. Google Sheets 자동 내보내기 (옵션) — output 폴더의 모든 JSON 파일에서 로드
        if auto_export_to_sheets:
            try:
                print(f"\n📊 Google Sheets로 누적 전체 기사 자동 내보내기 시작...")
                from src.sheets_exporter import SheetsExporter
                from src.models import CompleteAnalysis
                import glob
                
                # 모든 결과 파일에서 로드
                result_files = sorted(
                    glob.glob(os.path.join(storage.output_dir, 'analysis_results_*.json')),
                    key=os.path.getctime
                )
                
                all_analyses = []
                seen_urls = set()
                
                for result_file in result_files:
                    with open(result_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    for result in data.get('results', []):
                        url = result.get('url', '')
                        if url not in seen_urls:
                            all_analyses.append(CompleteAnalysis(**result))
                            seen_urls.add(url)
                
                if all_analyses:
                    exporter = SheetsExporter()
                    url = exporter.export_to_sheets(all_analyses, spreadsheet_id=Config.GOOGLE_SHEETS_ID)
                    
                    if url:
                        print(f"✅ Google Sheets로 누적 {len(all_analyses)}개 기사 내보내기 완료!")
                        print(f"🔗 URL: {url}\n")
                    else:
                        print(f"⚠️  Google Sheets 내보내기 실패\n")
                    
            except Exception as e:
                print(f"⚠️  Google Sheets 내보내기 오류: {e}\n")
                import traceback
                traceback.print_exc()
        
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
