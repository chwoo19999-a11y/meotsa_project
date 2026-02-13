// DOM 요소
const analyzeBtn = document.getElementById('analyzeBtn');
const progressBar = document.getElementById('progressBar');
const progressFill = progressBar.querySelector('.progress-fill');
const progressText = progressBar.querySelector('.progress-text');
const currentArticle = document.getElementById('currentArticle');
const statsSection = document.getElementById('statsSection');
const filterSection = document.getElementById('filterSection');
const resultsSection = document.getElementById('resultsSection');
const resultsBody = document.getElementById('resultsBody');
const gradeFilter = document.getElementById('gradeFilter');
const detailModal = document.getElementById('detailModal');
const closeModal = document.querySelector('.close');
const exportSheetsBtn = document.getElementById('exportSheetsBtn');

// 스케줄러 요소
const startSchedulerBtn = document.getElementById('startSchedulerBtn');
const stopSchedulerBtn = document.getElementById('stopSchedulerBtn');
const schedulerStateText = document.getElementById('schedulerStateText');
const lastRunText = document.getElementById('lastRunText');
const nextRunText = document.getElementById('nextRunText');

// 통계 요소
const statHigh = document.getElementById('statHigh');
const statMedium = document.getElementById('statMedium');
const statLow = document.getElementById('statLow');

// 상태 체크 타이머
let statusCheckInterval = null;
let schedulerStatusInterval = null;

// 분석 시작
analyzeBtn.addEventListener('click', async () => {
    if (confirm('분석을 시작하시겠습니까? (시간이 소요될 수 있습니다)')) {
        try {
            const response = await fetch('/api/analyze', {
                method: 'POST'
            });

            if (response.ok) {
                analyzeBtn.disabled = true;
                analyzeBtn.textContent = '🔄 분석 중...';
                progressBar.classList.remove('hidden');
                currentArticle.classList.remove('hidden');

                // 상태 체크 시작
                startStatusCheck();
            } else {
                const data = await response.json();
                alert(data.error || '분석 시작 실패');
            }
        } catch (error) {
            console.error('Error:', error);
            alert('서버 오류가 발생했습니다.');
        }
    }
});

// 스케줄러 시작
startSchedulerBtn.addEventListener('click', async () => {
    if (confirm('자동 수집 스케줄러를 시작하시겠습니까?')) {
        try {
            const response = await fetch('/api/scheduler/start', { method: 'POST' });
            const data = await response.json();

            if (response.ok) {
                alert(data.message);
                updateSchedulerStatus();
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
    if (confirm('자동 수집 스케줄러를 중지하시겠습니까?')) {
        try {
            const response = await fetch('/api/scheduler/stop', { method: 'POST' });
            const data = await response.json();

            if (response.ok) {
                alert(data.message);
                updateSchedulerStatus();
            } else {
                alert(data.message || '스케줄러 중지 실패');
            }
        } catch (error) {
            console.error('Scheduler stop error:', error);
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
            const response = await fetch('/api/export-sheets', {
                method: 'POST'
            });

            const data = await response.json();

            if (response.ok && data.success) {
                alert('✅ Google Sheets로 내보내기 완료!');
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

// 상태 체크 시작
function startStatusCheck() {
    statusCheckInterval = setInterval(async () => {
        try {
            const response = await fetch('/api/status');
            const data = await response.json();

            updateProgress(data);

            if (!data.is_running && data.total > 0) {
                // 분석 완료
                stopStatusCheck();
                analyzeBtn.disabled = false;
                analyzeBtn.textContent = '🚀 분석 시작';
                progressBar.classList.add('hidden');
                currentArticle.classList.add('hidden');

                // 결과 로드
                loadResults();

                alert('분석이 완료되었습니다!');
            }
        } catch (error) {
            console.error('Status check error:', error);
        }
    }, 1000);
}

// 상태 체크 중지
function stopStatusCheck() {
    if (statusCheckInterval) {
        clearInterval(statusCheckInterval);
        statusCheckInterval = null;
    }
}

// 진행 상황 업데이트
function updateProgress(data) {
    if (data.total > 0) {
        const percentage = (data.progress / data.total) * 100;
        progressFill.style.width = percentage + '%';
        progressText.textContent = `${data.progress} / ${data.total}`;

        if (data.current_article) {
            currentArticle.textContent = `분석 중: ${data.current_article.substring(0, 50)}...`;
        }

        // 통계 업데이트
        updateStats(data.stats);
    }
}

// 스케줄러 상태 업데이트
async function updateSchedulerStatus() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();

        // 스케줄러 활성화 상태
        if (data.scheduler_enabled) {
            startSchedulerBtn.disabled = true;
            stopSchedulerBtn.disabled = false;

            // 수집 중인지 확인
            if (data.is_running) {
                schedulerStateText.textContent = '🔄 수집 중...';
                schedulerStateText.className = 'collecting';
            } else {
                schedulerStateText.textContent = '🟢 실행 중';
                schedulerStateText.className = 'active';
            }
        } else {
            startSchedulerBtn.disabled = false;
            stopSchedulerBtn.disabled = true;
            schedulerStateText.textContent = '⚪ 대기 중';
            schedulerStateText.className = '';
        }

        // 마지막 실행 시간
        lastRunText.textContent = `마지막 실행: ${data.last_scheduled_run || '없음'}`;

        // 다음 실행 시간
        nextRunText.textContent = `다음 실행: ${data.next_scheduled_run || '없음'}`;

    } catch (error) {
        console.error('Scheduler status update error:', error);
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

    // 전역으로 results 저장 (상세보기용)
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

// 페이지 로드 시 기존 결과가 있으면 표시
window.addEventListener('load', async () => {
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

    // 스케줄러 상태 초기 업데이트 및 주기적 체크
    updateSchedulerStatus();
    schedulerStatusInterval = setInterval(updateSchedulerStatus, 3000);
});
