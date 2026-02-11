# Google Sheets 내보내기 오류 해결 가이드

## 🔴 현재 문제

에러: `'Worksheet' object has no attribute 'set_column_width'`

## ✅ 해결 방법

코드는 이미 수정되었습니다. **Flask 웹 서버를 재시작**해야 변경사항이 적용됩니다.

### 1. 현재 실행 중인 서버 중지

터미널에서 `Ctrl + C` 키를 눌러 서버를 중지하세요.

### 2. 서버 재시작

```bash
python app.py
```

### 3. 브라우저 새로고침

- 브라우저에서 `F5` 또는 `Ctrl + R`로 페이지 새로고침
- 캐시 완전 삭제: `Ctrl + Shift + R`

### 4. 다시 내보내기

**"📊 Google Sheets로 내보내기"** 버튼 클릭

---

## 📌 주요 변경사항

- ❌ 제거: `worksheet.set_column_width()` (존재하지 않는 메서드)
- ✅ 추가: `spreadsheet.batch_update()` (올바른 API)

이제 다음과 같은 개선사항이 적용됩니다:
- 열 너비 자동 최적화
- 텍스트 자동 줄바꿈
- 폰트 크기 10pt
- 컴팩트한 레이아웃

---

## ⚠️ 주의사항

Flask는 `debug=True`로 실행해도 모듈 변경 시 자동 리로드가 안 될 수 있습니다.
항상 **서버를 수동으로 재시작**하세요!
