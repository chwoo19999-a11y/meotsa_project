// DOM 요소
const analyzeBtn = document.getElementById('analyzeBtn');
const progressBar = document.getElementById('progressBar');
const progressFill = progressBar.querySelector('.progress-fill');
const progressText = progressBar.querySelector('.progress-text');
const currentArticle = document.getElementById('currentArticle');
const phaseText = document.getElementById('phaseText');
const statsSection = document.getElementById('statsSection');
const filterSection = document.getElementById('filterSection');
const resultsSection = document.getElementById('resultsSection');
const resultsBody = document.getElementById('resultsBody');
const gradeFilter = document.getElementById('gradeFilter');
const detailModal = document.getElementById('detailModal');
const closeModal = document.querySelector('.close');
const exportSheetsBtn = document.getElementById('exportSheetsBtn');
const stopAnalysisBtn = document.getElementById('stopAnalysisBtn');

// 스케줄러 요소
const startSchedulerBtn = document.getElementById('startSchedulerBtn');
const stopSchedulerBtn = document.getElementById('stopSchedulerBtn');
const schedulerStateText = document.getElementById('schedulerStateText');
const collectionProgress = document.getElementById('collectionProgress');
const lastRunText = document.getElementById('lastRunText');
const nextRunText = document.getElementById('nextRunText');

// 수집 진행 바
const collectionBar = document.getElementById('collectionBar');
const collectionFill = collectionBar.querySelector('.progress-fill');
const collectionText = collectionBar.querySelector('.progress-text');

// 통계 요소
const statHigh = document.getElementById('statHigh');
const statMedium = document.getElementById('statMedium');
const statLow = document.getElementById('statLow');

// 상태 타이머
let statusCheckInterval = null;

// 스케줄러 시작
startSchedulerBtn.addEventListener('click', async () => {
    if (confirm('300개 기사 수집을 시작하시겠습니까?\n\n60분 주기로 기사를 모아 300개 달성 시 자동으로 분석 + 시트 내보내기를 실행합니다.')) {
        try {
            const response = await fetch('/api/scheduler/start', { method: 'POST' });
            const data = await response.json();

            if (response.ok) {
                alert(data.message);
                startStatusPolling();
            } else {
                alert(data.message || '스케줄러 시작 실패');
            }
        } catch (error) {
            console.error('Scheduler start error:', error);
            alert('서버 오류가 발생했습니다.');
        }
    }
});

// 스케줄러 중지
stopSchedulerBtn.addEventListener('click', async () => {
    if (confirm('스케줄러를 중지하시겠습니까? 진행 중인 작업도 취소됩니다.')) {
        try {
            const response = await fetch('/api/scheduler/stop', { method: 'POST' });
            const data = await response.json();

            if (response.ok) {
                alert(data.message);
            } else {
                alert(data.message || '스케줄러 중지 실패');
            }
        } catch (error) {
            console.error('Scheduler stop error:', error);
            alert('서버 오류가 발생했습니다.');
        }
    }
});

// 수동 분석 시작
analyzeBtn.addEventListener('click', async () => {
    if (confirm('수집된 기사의 분석을 수동으로 시작하시겠습니까?')) {
        try {
            const response = await fetch('/api/analyze', { method: 'POST' });
            const data = await response.json();

            if (response.ok) {
                alert(data.message);
                startStatusPolling();
            } else {
                alert(data.error || '분석 시작 실패');
            }
        } catch (error) {
            console.error('Error:', error);
            alert('서버 오류가 발생했습니다.');
        }
    }
});

// 분석 중단
stopAnalysisBtn.addEventListener('click', async () => {
    if (confirm('분석을 중단하시겠습니까?\n중단 시점까지의 결과가 Google Sheets로 내보내집니다.')) {
        try {
            const response = await fetch('/api/analyze/stop', { method: 'POST' });
            const data = await response.json();
            alert(data.message);
        } catch (error) {
            console.error('Stop error:', error);
            alert('서버 오류가 발생했습니다.');
        }
    }
});

// 등급 필터
gradeFilter.addEventListener('change', loadResults);

// Google Sheets 내보내기
exportSheetsBtn.addEventListener('click', async () => {
    if (confirm('분석 결과를 Google Sheets로 내보내시겠습니까?')) {
        exportSheetsBtn.disabled = true;
        exportSheetsBtn.textContent = '⏳ 내보내는 중...';

        try {
            const response = await fetch('/api/export-sheets', { method: 'POST' });
            const data = await response.json();

            if (response.ok && data.success) {
                alert(`✅ ${data.exported_count}개 기사를 Google Sheets로 내보냈습니다!`);
                window.open(data.url, '_blank');
            } else {
                alert('❌ 내보내기 실패: ' + (data.error || '알 수 없는 오류'));
            }
        } catch (error) {
            console.error('Export error:', error);
            alert('❌ 서버 오류가 발생했습니다.');
        } finally {
            exportSheetsBtn.disabled = false;
            exportSheetsBtn.textContent = '📊 Google Sheets로 내보내기';
        }
    }
});

// 모달 닫기
closeModal.addEventListener('click', () => {
    detailModal.classList.add('hidden');
});

window.addEventListener('click', (e) => {
    if (e.target === detailModal) {
        detailModal.classList.add('hidden');
    }
});


// ============================================================
// 상태 폴링
// ============================================================

function startStatusPolling() {
    if (statusCheckInterval) return;
    statusCheckInterval = setInterval(updateDashboard, 2000);
}

function stopStatusPolling() {
    if (statusCheckInterval) {
        clearInterval(statusCheckInterval);
        statusCheckInterval = null;
    }
}

async function updateDashboard() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();

        updateSchedulerUI(data);
        updateCollectionUI(data);
        updateAnalysisUI(data);

    } catch (error) {
        console.error('Status update error:', error);
    }
}

function updateSchedulerUI(data) {
    // 스케줄러 활성화 상태
    if (data.scheduler_enabled) {
        startSchedulerBtn.disabled = true;
        stopSchedulerBtn.disabled = false;
    } else {
        startSchedulerBtn.disabled = false;
        stopSchedulerBtn.disabled = false;  // 진행 중인 작업 취소 가능
    }

    // 단계별 상태 표시
    const phaseLabels = {
        'idle': '⚪ 대기 중',
        'collecting': '📰 기사 수집 중...',
        'analyzing': '🤖 AI 분석 중...',
        'exporting': '📊 시트 내보내기 중...',
        'done': '✅ 완료!'
    };
    schedulerStateText.textContent = phaseLabels[data.phase] || '⚪ 대기 중';

    // 수집 진행
    collectionProgress.textContent = `수집: ${data.collection_count} / ${data.target_count} (${data.collection_runs}회 실행)`;

    lastRunText.textContent = `마지막 수집: ${data.last_scheduled_run || '없음'}`;
    nextRunText.textContent = `다음 수집: ${data.next_scheduled_run || '없음'}`;
}

function updateCollectionUI(data) {
    // 수집 진행 바
    if (data.collection_count > 0) {
        collectionBar.classList.remove('hidden');
        const pct = Math.min((data.collection_count / data.target_count) * 100, 100);
        collectionFill.style.width = pct + '%';
        collectionText.textContent = `${data.collection_count} / ${data.target_count}`;
    }
}

function updateAnalysisUI(data) {
    if (data.phase === 'analyzing') {
        analyzeBtn.disabled = true;
        analyzeBtn.textContent = '🔄 분석 중...';
        stopAnalysisBtn.style.display = 'inline-block';
        progressBar.classList.remove('hidden');
        currentArticle.classList.remove('hidden');
        phaseText.classList.remove('hidden');

        if (data.analysis_total > 0) {
            const pct = (data.analysis_progress / data.analysis_total) * 100;
            progressFill.style.width = pct + '%';
            progressText.textContent = `${data.analysis_progress} / ${data.analysis_total}`;
        }

        if (data.current_article) {
            currentArticle.textContent = `분석 중: ${data.current_article.substring(0, 50)}...`;
        }

        phaseText.textContent = `🤖 AI 분석 진행 중 (${data.analysis_progress}/${data.analysis_total})`;

        updateStats(data.stats);
    } else if (data.phase === 'exporting') {
        stopAnalysisBtn.style.display = 'none';
        phaseText.classList.remove('hidden');
        phaseText.textContent = '📊 Google Sheets 내보내기 중...';
    } else if (data.phase === 'done') {
        analyzeBtn.disabled = false;
        analyzeBtn.textContent = '🚀 수동 분석 시작';
        stopAnalysisBtn.style.display = 'none';
        progressBar.classList.add('hidden');
        currentArticle.classList.add('hidden');
        phaseText.classList.remove('hidden');
        phaseText.textContent = '✅ 완료!';

        if (data.sheets_url) {
            phaseText.innerHTML = `✅ 완료! <a href="${data.sheets_url}" target="_blank" style="color: #667eea;">📊 시트 열기</a>`;
        }

        updateStats(data.stats);
        loadResults();

        // 완료 후 폴링 빈도 줄이기
        stopStatusPolling();
    } else {
        analyzeBtn.disabled = false;
        analyzeBtn.textContent = '🚀 수동 분석 시작';
        stopAnalysisBtn.style.display = 'none';
        progressBar.classList.add('hidden');
    }
}

// 통계 업데이트
function updateStats(stats) {
    statHigh.textContent = stats.High || 0;
    statMedium.textContent = stats.Medium || 0;
    statLow.textContent = stats.Low || 0;

    if (stats.High > 0 || stats.Medium > 0 || stats.Low > 0) {
        statsSection.classList.remove('hidden');
    }
}

// 결과 로드
async function loadResults() {
    try {
        const grade = gradeFilter.value;
        const response = await fetch(`/api/results?grade=${grade}`);
        const data = await response.json();

        updateStats(data.stats);
        displayResults(data.results);

        if (data.results.length > 0) {
            filterSection.classList.remove('hidden');
            resultsSection.classList.remove('hidden');
        }
    } catch (error) {
        console.error('Load results error:', error);
    }
}

// 결과 표시
function displayResults(results) {
    resultsBody.innerHTML = '';

    if (results.length === 0) {
        resultsBody.innerHTML = '<tr><td colspan="7" style="text-align:center;">결과가 없습니다.</td></tr>';
        return;
    }

    results.forEach((result, index) => {
        const row = document.createElement('tr');
        const gradeClass = `grade-${result.grade.toLowerCase()}`;

        row.innerHTML = `
            <td><span class="grade-badge ${gradeClass}">${result.grade}</span></td>
            <td style="max-width: 300px;">
                <a href="${result.url}" target="_blank" style="color: #667eea; text-decoration: none;">
                    ${result.title}
                </a>
            </td>
            <td>${result.case_field}</td>
            <td>${result.defendant}</td>
            <td>${result.damage_amount}<br><small>${result.victim_count}명</small></td>
            <td>${result.progress_stage}</td>
            <td><button class="btn-detail" onclick="showDetail(${index})">상세</button></td>
        `;

        resultsBody.appendChild(row);
    });

    window.currentResults = results;
}

// 상세 정보 표시
function showDetail(index) {
    const result = window.currentResults[index];

    const modalTitle = document.getElementById('modalTitle');
    const modalBody = document.getElementById('modalBody');

    modalTitle.textContent = result.title;

    modalBody.innerHTML = `
        <div style="line-height: 1.8;">
            <p><strong>🔗 URL:</strong> <a href="${result.url}" target="_blank">${result.url}</a></p>
            <p><strong>⚖️ 사건 분야:</strong> ${result.case_field}</p>
            <p><strong>👤 상대방:</strong> ${result.defendant}</p>
            <p><strong>💰 피해 규모:</strong> ${result.damage_amount} (${result.victim_count}명)</p>
            <p><strong>📋 진행 단계:</strong> ${result.progress_stage}</p>
            <hr style="margin: 20px 0;">
            <p><strong>📝 요약:</strong></p>
            <p style="background: #f8f9fa; padding: 15px; border-radius: 8px;">${result.summary}</p>
            <hr style="margin: 20px 0;">
            <p><strong>💡 판단 근거:</strong></p>
            <p style="background: #f8f9fa; padding: 15px; border-radius: 8px;">${result.reasoning}</p>
            <hr style="margin: 20px 0;">
            <p><strong>✅ 충족 조건:</strong></p>
            <ul style="margin-left: 20px;">
                ${result.matched_conditions.map(c => `<li>${c}</li>`).join('')}
            </ul>
        </div>
    `;

    detailModal.classList.remove('hidden');
}

// 페이지 로드 시 초기화
window.addEventListener('load', async () => {
    // 기존 결과 로드
    try {
        const response = await fetch('/api/results');
        const data = await response.json();

        if (data.results.length > 0) {
            updateStats(data.stats);
            displayResults(data.results);
            filterSection.classList.remove('hidden');
            resultsSection.classList.remove('hidden');
        }
    } catch (error) {
        console.error('Initial load error:', error);
    }

    // 상태 폴링 시작
    startStatusPolling();
});
