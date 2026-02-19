"""
소송금융 투자 적합도 분석 웹 대시보드
Flask-based web dashboard for litigation finance analysis

파이프라인: 기사 수집(300개 목표) → AI 분석 → Google Sheets 내보내기
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

# 목표 수집 개수
TARGET_ARTICLE_COUNT = 300

# 전체 파이프라인 상태
pipeline_state = {
    # 수집 단계
    'phase': 'idle',  # idle / collecting / analyzing / exporting / done
    'collected_articles': [],  # 수집된 기사 목록 (NewsArticle dict)
    'collected_urls': set(),  # 중복 방지용 URL set
    'collection_count': 0,  # 현재 수집된 기사 수
    'target_count': TARGET_ARTICLE_COUNT,  # 목표 수집 수
    'collection_runs': 0,  # 수집 실행 횟수

    # 분석 단계
    'analysis_progress': 0,
    'analysis_total': 0,
    'current_article': '',
    'results': [],  # 분석 결과
    'stats': {'High': 0, 'Medium': 0, 'Low': 0},

    # 스케줄러
    'scheduler_enabled': False,
    'last_scheduled_run': None,

    # 취소
    'cancel_requested': False,

    # 시트 내보내기 결과
    'sheets_url': None,
}


# ============================================================
# 스케줄러: 주기적 기사 수집 (분석 없이 수집만)
# ============================================================

def scheduled_article_collection():
    """스케줄러에 의해 주기적으로 실행 — 기사 수집만 수행"""
    print(f"\n{'='*60}")
    print(f"⏰ [자동 수집] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    # 이미 분석/내보내기 진행 중이면 스킵
    if pipeline_state['phase'] in ('analyzing', 'exporting'):
        print("⚠️  분석/내보내기 진행 중이므로 이번 수집을 건너뜁니다.")
        return

    if pipeline_state['cancel_requested']:
        print("⚠️  취소가 요청되어 수집을 건너뜁니다.")
        return

    pipeline_state['last_scheduled_run'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # 수집 실행
    thread = threading.Thread(target=run_collection_phase)
    thread.daemon = True
    thread.start()


def run_collection_phase():
    """기사 수집 단계 (분석 없이 수집만, 목표 개수에 도달하면 즉시 중단)"""
    try:
        pipeline_state['phase'] = 'collecting'
        target = pipeline_state['target_count']

        collector = NewsCollector()
        new_count = 0
        target_reached = False

        for keyword in Config.SEARCH_KEYWORDS:
            if pipeline_state['cancel_requested'] or target_reached:
                break

            print(f"🔍 '{keyword}' 검색 중...")
            articles = collector.search_news_paginated(
                keyword,
                display=Config.SEARCH_DISPLAY,
                max_start=Config.SEARCH_MAX_START
            )

            for article in articles:
                if pipeline_state['cancel_requested']:
                    break

                if article.url not in pipeline_state['collected_urls'] and collector._is_domestic_news(article):
                    pipeline_state['collected_articles'].append({
                        'title': article.title,
                        'url': article.url,
                        'description': article.description,
                        'published_date': article.published_date,
                        'source': article.source
                    })
                    pipeline_state['collected_urls'].add(article.url)
                    new_count += 1
                    pipeline_state['collection_count'] = len(pipeline_state['collected_articles'])

                    # 목표 도달 시 즉시 중단
                    if pipeline_state['collection_count'] >= target:
                        print(f"🎯 목표 {target}개 도달! 수집 중단")
                        target_reached = True
                        break

        pipeline_state['collection_count'] = len(pipeline_state['collected_articles'])
        pipeline_state['collection_runs'] += 1

        print(f"📰 수집 완료: 신규 {new_count}개 추가 → 총 {pipeline_state['collection_count']}개")
        print(f"🎯 목표: {target}개")

        # 목표 달성 시 자동으로 분석 → 내보내기
        if pipeline_state['collection_count'] >= pipeline_state['target_count']:
            print(f"\n🎉 목표 {pipeline_state['target_count']}개 달성! 자동 분석을 시작합니다...\n")

            # 스케줄러 중지 (목표 달성했으므로)
            try:
                if pipeline_state['scheduler_enabled']:
                    scheduler.remove_job('article_collection_job')
                    pipeline_state['scheduler_enabled'] = False
                    print("🛑 스케줄러 자동 중지")
            except Exception:
                pass

            # 분석 + 내보내기 실행
            run_analysis_and_export()
        else:
            remaining = pipeline_state['target_count'] - pipeline_state['collection_count']
            print(f"📋 {remaining}개 더 수집 필요. 다음 스케줄러 실행을 기다립니다.")
            pipeline_state['phase'] = 'idle'

    except Exception as e:
        print(f"❌ 수집 오류: {e}")
        pipeline_state['phase'] = 'idle'
        import traceback
        traceback.print_exc()


def run_analysis_and_export():
    """분석 + Google Sheets 내보내기 (수집 완료 후 자동 실행)"""
    try:
        pipeline_state['phase'] = 'analyzing'
        pipeline_state['cancel_requested'] = False

        articles_to_analyze = pipeline_state['collected_articles']
        total = len(articles_to_analyze)
        pipeline_state['analysis_total'] = total
        pipeline_state['analysis_progress'] = 0
        pipeline_state['results'] = []
        pipeline_state['stats'] = {'High': 0, 'Medium': 0, 'Low': 0}

        print(f"\n🤖 AI 분석 시작 ({total}개 기사)...\n")

        from src.models import NewsArticle
        analyzer = AIAnalyzer()
        storage = StorageManager()
        complete_analyses = []

        for i, art_dict in enumerate(articles_to_analyze, 1):
            if pipeline_state['cancel_requested']:
                print(f"\n🛑 분석 취소됨 ({i-1}/{total}개 완료)")
                break

            pipeline_state['current_article'] = art_dict['title']
            pipeline_state['analysis_progress'] = i

            # dict → NewsArticle 변환
            article = NewsArticle(
                title=art_dict['title'],
                url=art_dict['url'],
                description=art_dict['description'],
                published_date=art_dict['published_date'],
                source=art_dict['source']
            )

            # AI 분석
            complete_analysis = analyzer.analyze_article(article)
            complete_analyses.append(complete_analysis)

            # 결과 저장
            grade = complete_analysis.analysis.suitability.grade
            pipeline_state['stats'][grade] = pipeline_state['stats'].get(grade, 0) + 1

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
            pipeline_state['results'].append(result_item)

        # JSON 파일로 저장
        if complete_analyses:
            storage.save_results(complete_analyses)
            storage.save_summary(complete_analyses)

        if pipeline_state['cancel_requested']:
            print(f"\n🛑 분석 중단됨: {len(complete_analyses)}/{total}개 완료")
        else:
            print(f"\n✅ 분석 완료: {len(complete_analyses)}개")

        # Google Sheets 자동 내보내기 (중단된 경우에도 분석된 결과까지 내보내기)
        if complete_analyses:
            pipeline_state['phase'] = 'exporting'
            try:
                label = f"{len(complete_analyses)}개" + (" (중단됨)" if pipeline_state['cancel_requested'] else "")
                print(f"\n📊 Google Sheets로 {label} 기사 내보내기 시작...")
                from src.sheets_exporter import SheetsExporter

                exporter = SheetsExporter()
                url = exporter.export_to_sheets(complete_analyses, spreadsheet_id=Config.GOOGLE_SHEETS_ID)

                if url:
                    pipeline_state['sheets_url'] = url
                    print(f"✅ Google Sheets 내보내기 완료!")
                    print(f"🔗 URL: {url}\n")
                else:
                    print(f"⚠️  Google Sheets 내보내기 실패\n")

            except Exception as e:
                print(f"⚠️  Google Sheets 내보내기 오류: {e}\n")
                import traceback
                traceback.print_exc()

        pipeline_state['phase'] = 'done'

    except Exception as e:
        print(f"❌ 분석/내보내기 오류: {e}")
        pipeline_state['phase'] = 'done'
        import traceback
        traceback.print_exc()


# ============================================================
# API 라우트
# ============================================================

@app.route('/')
def index():
    """메인 대시보드 페이지"""
    return render_template('index.html')


@app.route('/api/status', methods=['GET'])
def get_status():
    """파이프라인 상태 조회"""
    next_run = None
    if pipeline_state['scheduler_enabled'] and scheduler.get_jobs():
        job = scheduler.get_jobs()[0]
        if job.next_run_time:
            next_run = job.next_run_time.strftime('%Y-%m-%d %H:%M:%S')

    return jsonify({
        'phase': pipeline_state['phase'],
        'collection_count': pipeline_state['collection_count'],
        'target_count': pipeline_state['target_count'],
        'collection_runs': pipeline_state['collection_runs'],
        'analysis_progress': pipeline_state['analysis_progress'],
        'analysis_total': pipeline_state['analysis_total'],
        'current_article': pipeline_state['current_article'],
        'stats': pipeline_state['stats'],
        'scheduler_enabled': pipeline_state['scheduler_enabled'],
        'last_scheduled_run': pipeline_state['last_scheduled_run'],
        'next_scheduled_run': next_run,
        'sheets_url': pipeline_state['sheets_url'],
    })


@app.route('/api/results', methods=['GET'])
def get_results():
    """분석 결과 조회"""
    grade_filter = request.args.get('grade', 'all')

    results = pipeline_state['results']
    if grade_filter != 'all':
        results = [r for r in results if r['grade'] == grade_filter]

    return jsonify({
        'total': len(results),
        'results': results,
        'stats': pipeline_state['stats'],
    })


@app.route('/api/scheduler/start', methods=['POST'])
def start_scheduler():
    """300개 수집 스케줄러 시작"""
    if pipeline_state['scheduler_enabled']:
        return jsonify({'message': '스케줄러가 이미 실행 중입니다.'}), 400

    try:
        # 상태 초기화
        pipeline_state['phase'] = 'idle'
        pipeline_state['collected_articles'] = []
        pipeline_state['collected_urls'] = set()
        pipeline_state['collection_count'] = 0
        pipeline_state['collection_runs'] = 0
        pipeline_state['results'] = []
        pipeline_state['stats'] = {'High': 0, 'Medium': 0, 'Low': 0}
        pipeline_state['cancel_requested'] = False
        pipeline_state['sheets_url'] = None
        pipeline_state['analysis_progress'] = 0
        pipeline_state['analysis_total'] = 0

        # 즉시 첫 수집 실행 + 이후 60분마다 반복
        scheduler.add_job(
            func=scheduled_article_collection,
            trigger=IntervalTrigger(minutes=60),
            id='article_collection_job',
            name='자동 기사 수집 (300개 목표)',
            replace_existing=True
        )

        pipeline_state['scheduler_enabled'] = True

        job = scheduler.get_job('article_collection_job')
        next_run = job.next_run_time.strftime('%Y-%m-%d %H:%M:%S') if job.next_run_time else None

        print(f"\n✅ 300개 수집 스케줄러 시작!")
        print(f"📅 다음 실행: {next_run}")
        print(f"🎯 목표: {TARGET_ARTICLE_COUNT}개 수집 → 자동 분석 → 시트 내보내기\n")

        # 즉시 첫 수집 실행
        thread = threading.Thread(target=run_collection_phase)
        thread.daemon = True
        thread.start()

        return jsonify({
            'message': f'300개 수집 스케줄러가 시작되었습니다. 즉시 첫 수집을 실행합니다.',
            'next_run': next_run,
            'target_count': TARGET_ARTICLE_COUNT
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/scheduler/stop', methods=['POST'])
def stop_scheduler():
    """스케줄러 + 진행 중인 작업 취소"""
    try:
        if pipeline_state['scheduler_enabled']:
            scheduler.remove_job('article_collection_job')
            pipeline_state['scheduler_enabled'] = False

        pipeline_state['cancel_requested'] = True

        msg = '스케줄러가 중지되었습니다.'
        if pipeline_state['phase'] in ('collecting', 'analyzing', 'exporting'):
            msg += ' 진행 중인 작업이 취소됩니다.'
            print(f"\n🛑 스케줄러 중지 + 진행 중인 {pipeline_state['phase']} 취소\n")
        else:
            print(f"\n🛑 스케줄러 중지\n")

        return jsonify({'message': msg}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/analyze/stop', methods=['POST'])
def stop_analysis():
    """진행 중인 분석 취소"""
    if pipeline_state['phase'] not in ('collecting', 'analyzing', 'exporting'):
        return jsonify({'message': '진행 중인 작업이 없습니다.'}), 400

    pipeline_state['cancel_requested'] = True
    print(f"\n🛑 작업 취소 요청됨 (현재 단계: {pipeline_state['phase']})\n")
    return jsonify({'message': '취소가 요청되었습니다.'}), 200


@app.route('/api/analyze', methods=['POST'])
def start_analysis():
    """수동 분석 시작 (수집된 기사가 있으면 즉시 분석+내보내기)"""
    if pipeline_state['phase'] in ('analyzing', 'exporting'):
        return jsonify({'error': '이미 분석/내보내기가 진행 중입니다.'}), 400

    if pipeline_state['collection_count'] == 0:
        return jsonify({'error': '수집된 기사가 없습니다. 먼저 스케줄러를 시작하세요.'}), 400

    thread = threading.Thread(target=run_analysis_and_export)
    thread.daemon = True
    thread.start()

    return jsonify({
        'message': f'{pipeline_state["collection_count"]}개 기사 분석을 시작합니다.'
    }), 200


@app.route('/api/export-sheets', methods=['POST'])
def export_to_sheets():
    """수동 Google Sheets 내보내기 (output 폴더의 모든 JSON)"""
    try:
        from src.sheets_exporter import SheetsExporter
        from src.storage import StorageManager
        from src.models import CompleteAnalysis
        import glob

        storage = StorageManager()
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
            return jsonify({'error': '분석 결과가 없습니다.'}), 404

        print(f"📊 {len(all_analyses)}개 기사를 Google Sheets로 내보냅니다...")

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


if __name__ == '__main__':
    if not Config.validate():
        print("\n⚠️  .env 파일을 설정하고 다시 실행하세요.")
        exit(1)

    print("="*60)
    print("🌐 소송금융 투자 적합도 분석 웹 대시보드")
    print("="*60)
    print("\n📍 서버 주소: http://localhost:5000")
    print("⚡ 브라우저에서 위 주소로 접속하세요.")
    print(f"🎯 목표: {TARGET_ARTICLE_COUNT}개 수집 → 자동 분석 → 시트 내보내기\n")

    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)
