# 소송금융 뉴스 분석 프로젝트

네이버 뉴스 검색 API를 활용하여 소송금융 투자 적합성을 판단하는 자동화된 뉴스 분석 시스템입니다.

## 📋 프로젝트 개요

이 프로젝트는 소송금융 투자를 검토하는 심사역의 관점에서 뉴스 기사를 자동으로 수집하고 분석하여 투자 적합도를 판단합니다.

### 주요 기능

- **자동 뉴스 수집**: 네이버 뉴스 검색 API를 통한 키워드 기반 기사 수집
- **소송금융 적합도 분석**: High/Medium/Low 3단계 등급 판단
- **상세 정보 추출**: 사건 분야, 상대방, 피해 규모, 진행 단계 등 핵심 정보 자동 추출
- **구조화된 결과**: JSON 형식의 분석 결과 제공

## 🎯 수집 키워드

- 소송
- 손해배상
- 집단소송
- 공동소송
- 피해자
- 피해보상
- 피해구제

## 📊 분석 항목

| 번호 | 항목 | 설명 |
|------|------|------|
| 1 | **소송금융 적합도** | High / Medium / Low + 판단 근거 |
| 2 | **사건 분야** | 제조물책임, 개인정보, 환경, 노동 등 |
| 3 | **상대방** | 소송 가능한 대상 (기업명, 기관명) |
| 4 | **피해 규모** | 금액 추정 및 피해자 수 |
| 5-1 | **진행 단계** | 피해 발생 / 관련 절차 진행 / 소송중 / 판결 선고 / 종결 |
| 5-2 | **진행 단계 상세** | 구체적인 진행 상황 |
| 6 | **요약** | 2-3문장 요약 |

## 🚀 시작하기

### 필수 요구사항

- Python 3.12 이상
# 소송금융 투자 적합도 분석 프로그램

네이버 뉴스 API와 Gemini AI를 활용하여 소송금융 투자 적합성을 자동으로 분석하는 프로그램입니다.

## 🎯 주요 기능

- **자동 뉴스 수집**: 네이버 뉴스 API를 통해 소송 관련 뉴스 자동 수집
- **AI 기반 분석**: Gemini AI를 활용한 투자 적합도 평가 (High/Medium/Low)
- **구조화된 정보 추출**: 사건 분야, 상대방, 피해 규모, 진행 단계 자동 추출
- **결과 저장**: JSON 형식으로 분석 결과 및 통계 저장

## 📋 분석 기준

### 적합 조건 (6가지)
1. 상대방 책임이 비교적 명확함
2. 상대방에게 자력이 충분함 (대기업, 금융기관, 공공기관 등)
3. 집단적 피해 (수십 명 이상)
4. 피해 규모가 큼 (수억 원 이상 또는 수만 명 이상)
5. 증거가 있거나 확보 가능함
6. 이미 공적 절차가 진행 중임

### 등급 판정
- **High**: 적합 조건 4개 이상, 부적합 조건 없음
- **Medium**: 적합 조건 2~3개, 부적합 조건 없음
- **Low**: 적합 조건 1개 이하 또는 부적합 조건 있음

## 🚀 설치 및 설정

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

### 2. API 키 발급

#### 네이버 뉴스 검색 API
1. [네이버 개발자 센터](https://developers.naver.com/) 접속
2. 애플리케이션 등록: [앱 등록 페이지](https://developers.naver.com/apps/#/register)
3. 검색 API 선택 후 `Client ID`와 `Client Secret` 발급

#### Google Gemini API
1. [Google AI Studio](https://aistudio.google.com/app/apikey) 접속
2. API 키 발급

### 3. 환경변수 설정

`.env.example` 파일을 `.env`로 복사하고 API 키를 입력하세요:

```bash
# Windows
copy .env.example .env

# Linux/Mac
cp .env.example .env
```

`.env` 파일 내용:
```
NAVER_CLIENT_ID=your_naver_client_id_here
NAVER_CLIENT_SECRET=your_naver_client_secret_here
GEMINI_API_KEY=your_gemini_api_key_here
```

### 네이버 API 키 발급 방법

1. [네이버 개발자 센터](https://developers.naver.com/main/) 접속
2. 로그인 후 "Application > 애플리케이션 등록" 선택
3. "검색" API 선택
4. Client ID와 Client Secret 발급받기

## 💻 사용 방법

### 기본 실행

```bash
python main.py
```

### 특정 키워드로 검색

```bash
python main.py --keyword "집단소송"
```

### 검색 결과 수 조정

```bash
python main.py --display 50
```

### 결과 저장

```bash
python main.py --output results.json
```

## 📁 프로젝트 구조

```
meotsa_project/
├── README.md
├── requirements.txt
├── .env
├── main.py                      # 메인 실행 파일
├── src/
│   ├── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── naver_news.py       # 네이버 뉴스 API 클라이언트
│   ├── analyzer/
│   │   ├── __init__.py
│   │   ├── suitability.py      # 적합도 판단 로직
│   │   └── extractor.py        # 정보 추출 로직
│   └── utils/
│       ├── __init__.py
│       └── helpers.py          # 유틸리티 함수
├── data/
│   ├── raw/                    # 원본 뉴스 데이터
│   └── processed/              # 분석 결과
└── tests/
    ├── __init__.py
    ├── test_api.py
    └── test_analyzer.py
```

## 🔍 적합도 판단 기준

### High (높음)
- 적합 조건 4개 이상 충족
- 부적합 조건 해당 없음
- 대기업 상대, 집단 피해, 명확한 증거 등

### Medium (중간)
- 적합 조건 2-3개 충족
- 부적합 조건 해당 없음

### Low (낮음)
- 적합 조건 1개 이하
- 부적합 조건 1개 이상 해당
- 이미 종결된 사건 등

### 적합 조건
1. ✅ 상대방 책임이 비교적 명확함
2. ✅ 상대방에게 자력이 충분함 (대기업, 금융기관 등)
3. ✅ 집단적 피해 (수십 명 이상)
4. ✅ 피해 규모가 큼 (수억 원 이상 또는 수만 명 이상)
5. ✅ 증거가 있거나 확보 가능함
6. ✅ 이미 공적 절차가 진행 중임 (검찰 수사, 정부 조사 등)

### 부적합 조건
1. ❌ 이미 종결된 사건 (합의 완료, 판결 확정)

## 🎭 페르소나

**"소송금융 투자를 검토하는 심사역"**
- 원칙적인 법률 전문가의 관점
- 공격적으로 수임 기회를 포착하는 비즈니스 전략가의 관점

## 📝 결과 예시

```json
{
  "title": "개인정보 유출 피해자 1만명, ○○기업 상대 집단소송 추진",
  "url": "https://...",
  "published_date": "2026-02-09",
  "analysis": {
    "suitability": {
      "grade": "High",
      "reasoning": "대기업 상대, 집단 피해(1만명), 명확한 증거(개인정보보호위원회 조사 결과), 피해 규모 큼"
    },
    "case_field": "개인정보",
    "defendant": "○○기업",
    "damage_scale": {
      "amount": "추정 100억원",
      "victim_count": 10000
    },
    "progress_stage": "관련 절차 진행",
    "progress_detail": "개인정보보호위원회 조사 완료, 과징금 부과",
    "summary": "○○기업의 개인정보 유출로 1만명의 피해자가 발생했으며, 개인정보보호위원회의 조사 결과 위법 사실이 확인되었다. 피해자들은 집단소송을 추진 중이며, 총 피해액은 100억원으로 추정된다."
  }
}
```

## 🛠️ 로컬 개발

### 테스트 실행

```bash
pytest tests/
```

### 코드 포맷팅

```bash
black src/
flake8 src/
```

> **Note**: 이 프로젝트는 로컬 환경 전용으로 설계되었으며, 별도의 배포 과정은 필요하지 않습니다.