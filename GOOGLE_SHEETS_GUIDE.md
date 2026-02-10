# Google Sheets 연동 가이드

## 📋 사전 준비

### 1. Google Cloud Console 설정

1. [Google Cloud Console](https://console.cloud.google.com/) 접속
2. 새 프로젝트 생성 또는 기존 프로젝트 선택
3. **API 및 서비스 > 라이브러리**로 이동
4. 다음 API들을 활성화:
   - Google Sheets API
   - Google Drive API

### 2. 서비스 계정 생성

1. **API 및 서비스 > 사용자 인증 정보**로 이동
2. **사용자 인증 정보 만들기 > 서비스 계정** 선택
3. 서비스 계정 이름 입력 (예: `litigation-finance-exporter`)
4. **완료** 클릭

### 3. JSON 키 다운로드

1. 생성된 서비스 계정 클릭
2. **키** 탭으로 이동
3. **키 추가 > 새 키 만들기**
4. **JSON** 선택 후 **만들기**
5. 다운로드된 JSON 파일을 프로젝트 루트에 `credentials.json`으로 저장

```
meotsa_project/
├── credentials.json    # 여기에 저장!
├── app.py
├── ...
```

⚠️ **중요**: `credentials.json`은 절대 Git에 커밋하지 마세요!

## 🚀 사용 방법

### 웹 대시보드에서 내보내기

1. 분석 완료 후 **"📊 Google Sheets로 내보내기"** 버튼 클릭
2. 자동으로 스프레드시트 생성 및 데이터 입력
3. 새 탭에서 Google Sheets 열림

### CLI에서 내보내기

```python
from src.sheets_exporter import SheetsExporter
from src.storage import StorageManager

# 분석 결과 로드
storage = StorageManager()
# ... 분석 결과 로드 로직

# Google Sheets로 내보내기
exporter = SheetsExporter()
url = exporter.export_to_sheets(analyses)
print(f"URL: {url}")
```

## 📊 생성되는 시트

### 1. Sheet1 (분석 결과)
- 등급, 제목, URL, 사건 분야, 상대방
- 피해 금액, 피해자 수, 진행 단계
- 요약, 판단 근거, 충족 조건
- 등급별 색상 구분 (High: 빨강, Medium: 노랑, Low: 초록)

### 2. 요약 (통계)
- 총 분석 건수
- 등급별 개수 및 비율

## 🔐 권한 설정

생성된 스프레드시트는 **누구나 볼 수 있도록** 자동 공유됩니다.

특정 사용자만 접근하게 하려면 `sheets_exporter.py`의 다음 부분을 수정하세요:

```python
# 특정 이메일에만 공유
spreadsheet.share('user@example.com', perm_type='user', role='writer')
```

## ⚠️ 문제 해결

### `credentials.json`을 찾을 수 없습니다
- 파일이 프로젝트 루트에 있는지 확인
- 파일명이 정확히 `credentials.json`인지 확인

### 권한 오류
- Google Cloud Console에서 Sheets API와 Drive API가 활성화되었는지 확인
- 서비스 계정에 충분한 권한이 있는지 확인

### 할당량 초과
- Google Sheets API는 무료 티어에서 일일 제한이 있습니다
- [할당량 페이지](https://console.cloud.google.com/apis/api/sheets.googleapis.com/quotas)에서 확인 가능
