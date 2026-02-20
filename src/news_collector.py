"""
네이버 뉴스 수집 모듈
Naver News API integration for collecting litigation-related articles
"""

import re
import json
import os
import time
import requests
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from bs4 import BeautifulSoup
from .models import NewsArticle
from .config import Config


class NewsCollector:
    """네이버 뉴스 검색 및 수집"""
    
    def __init__(self):
        self.client_id = Config.NAVER_CLIENT_ID
        self.client_secret = Config.NAVER_CLIENT_SECRET
        self.base_url = "https://openapi.naver.com/v1/search/news.json"
        self.history_file = os.path.join(Config.OUTPUT_DIR, "collection_history.json")
    
    def search_news(self, keyword: str, display: int = 100, start: int = 1) -> list[NewsArticle]:
        """
        네이버 뉴스 검색
        
        Args:
            keyword: 검색 키워드
            display: 검색 결과 개수 (최대 100)
            start: 검색 시작 위치 (최대 1000)
        
        Returns:
            List[NewsArticle]: 뉴스 기사 리스트
        """
        headers = {
            'X-Naver-Client-Id': self.client_id,
            'X-Naver-Client-Secret': self.client_secret
        }
        
        params = {
            'query': keyword,
            'display': min(display, 100),
            'start': start,
            'sort': Config.SEARCH_SORT
        }
        
        try:
            response = requests.get(self.base_url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            articles = []
            for item in data.get('items', []):
                article = NewsArticle(
                    title=self._clean_html(item['title']),
                    url=item['link'],
                    description=self._clean_html(item['description']),
                    published_date=item['pubDate'][:10].replace('-', ''),  # YYYYMMDD 형식
                    source=self._extract_source(item.get('originallink', item['link']))
                )
                articles.append(article)
            
            return articles
            
        except requests.exceptions.RequestException as e:
            print(f"❌ 네이버 API 호출 실패: {e}")
            return []
    
    def search_news_paginated(self, keyword: str, display: int = 100, max_start: int = 300) -> list[NewsArticle]:
        """
        페이지네이션을 사용하여 키워드당 더 많은 뉴스 수집
        
        Args:
            keyword: 검색 키워드
            display: 페이지당 검색 결과 개수 (최대 100)
            max_start: 최대 시작 위치 (최대 1000)
        
        Returns:
            List[NewsArticle]: 뉴스 기사 리스트
        """
        all_articles = []
        start = 1
        
        while start <= max_start:
            articles = self.search_news(keyword, display=display, start=start)
            
            if not articles:
                break  # 더 이상 결과 없음
            
            all_articles.extend(articles)
            
            # 결과가 display보다 적으면 마지막 페이지
            if len(articles) < display:
                break
            
            start += display
            time.sleep(0.1)  # API rate limit 방지
        
        return all_articles
    
    def search_multiple_keywords(self, keywords: list[str], display: int = 100) -> list[NewsArticle]:
        """
        여러 키워드로 뉴스 검색 (OR 조건) - 페이지네이션 포함
        중복 제거: URL 일치 + 제목 유사도 + 이전 수집 이력
        
        Args:
            keywords: 검색 키워드 리스트
            display: 각 페이지당 검색 결과 개수
        
        Returns:
            List[NewsArticle]: 중복 제거된 뉴스 기사 리스트 (국내 기사만)
        """
        all_articles = []
        seen_urls = set()
        seen_titles = []  # 유사도 비교용 제목 리스트
        
        # 이전 수집 이력 로드
        history = self._load_history()
        history_urls = set(history.get("urls", []))
        history_titles = history.get("titles", [])
        
        # 이전 이력을 seen에 미리 추가
        seen_urls.update(history_urls)
        seen_titles.extend(history_titles)
        
        history_skip_count = 0
        similar_skip_count = 0
        
        for keyword in keywords:
            print(f"🔍 '{keyword}' 검색 중 (페이지네이션)...")
            articles = self.search_news_paginated(
                keyword, 
                display=display, 
                max_start=Config.SEARCH_MAX_START
            )
            
            # 중복 제거 및 국내 기사만 필터링
            new_count = 0
            for article in articles:
                # 1) 국내 기사 필터링
                if not self._is_domestic_news(article):
                    continue
                
                # 2) URL 중복 체크 (이전 이력 포함)
                if article.url in seen_urls:
                    if article.url in history_urls:
                        history_skip_count += 1
                    continue
                
                # 3) 제목 유사도 중복 체크
                normalized_title = self._normalize_title(article.title)
                if self._is_similar_title(normalized_title, seen_titles):
                    similar_skip_count += 1
                    continue
                
                all_articles.append(article)
                seen_urls.add(article.url)
                seen_titles.append(normalized_title)
                new_count += 1
            
            print(f"   → '{keyword}': {len(articles)}개 수집, {new_count}개 신규 추가")
        
        # 중복 제거 통계 출력
        if history_skip_count > 0:
            print(f"🔄 이전 수집 이력 중복 제거: {history_skip_count}개 건너뜀")
        if similar_skip_count > 0:
            print(f"📝 유사 제목 중복 제거: {similar_skip_count}개 건너뜀")
        
        # 수집 이력 저장
        new_urls = [a.url for a in all_articles]
        new_titles = [self._normalize_title(a.title) for a in all_articles]
        self._save_history(new_urls, new_titles)
        
        print(f"✅ 총 {len(all_articles)}개의 국내 뉴스 기사 수집 완료")
        return all_articles
    
    # ──────────────────────────────────────────────
    # 제목 유사도 관련 메서드
    # ──────────────────────────────────────────────
    
    @staticmethod
    def _normalize_title(title: str) -> str:
        """
        제목 정규화 (유사도 비교 정확도 향상)
        - 특수문자, 따옴표, 말줄임표 제거
        - 연속 공백 제거
        """
        # 특수문자 제거 (한글, 영어, 숫자, 공백만 남기기)
        normalized = re.sub(r'[^\w\s가-힣]', '', title)
        # 연속 공백 제거
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        return normalized
    
    @staticmethod
    def _is_similar_title(title: str, existing_titles: list[str], 
                          threshold: float = None) -> bool:
        """
        기존 제목 리스트와 비교하여 유사 기사 판단
        
        Args:
            title: 비교할 제목 (정규화된)
            existing_titles: 기존 제목 리스트
            threshold: 유사도 임계값 (기본: Config 설정값)
        
        Returns:
            bool: 유사한 기사가 있으면 True
        """
        if threshold is None:
            threshold = Config.TITLE_SIMILARITY_THRESHOLD
        
        for existing in existing_titles:
            similarity = SequenceMatcher(None, title, existing).ratio()
            if similarity >= threshold:
                return True
        return False
    
    # ──────────────────────────────────────────────
    # 수집 이력 관리 메서드
    # ──────────────────────────────────────────────
    
    def _load_history(self) -> dict:
        """
        이전 수집 이력 로드
        보관 기한이 지난 이력은 자동 삭제
        
        Returns:
            dict: {"urls": [...], "titles": [...]}
        """
        if not os.path.exists(self.history_file):
            return {"urls": [], "titles": []}
        
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
            
            # 보관 기한 체크
            retention_days = Config.HISTORY_RETENTION_DAYS
            cutoff = (datetime.now() - timedelta(days=retention_days)).strftime("%Y-%m-%d")
            
            # 기한 내의 항목만 유지
            valid_entries = [
                entry for entry in history.get("entries", [])
                if entry.get("collected_at", "") >= cutoff
            ]
            
            # 유효한 URL/제목 집합 생성
            urls = []
            titles = []
            for entry in valid_entries:
                urls.extend(entry.get("urls", []))
                titles.extend(entry.get("titles", []))
            
            expired_count = len(history.get("entries", [])) - len(valid_entries)
            if expired_count > 0:
                print(f"🗑️ 이전 이력 중 {expired_count}개 만료 항목 정리됨")
            
            print(f"📋 이전 수집 이력 로드: URL {len(urls)}개, 제목 {len(titles)}개")
            return {"urls": urls, "titles": titles, "entries": valid_entries}
            
        except (json.JSONDecodeError, KeyError) as e:
            print(f"⚠️ 이력 파일 읽기 실패, 새로 시작합니다: {e}")
            return {"urls": [], "titles": []}
    
    def _save_history(self, new_urls: list[str], new_titles: list[str]):
        """
        수집 이력 저장 (기존 이력에 추가)
        
        Args:
            new_urls: 새로 수집된 URL 리스트
            new_titles: 새로 수집된 제목 리스트 (정규화된)
        """
        # 기존 이력 로드
        existing_entries = []
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    existing_entries = data.get("entries", [])
            except (json.JSONDecodeError, KeyError):
                existing_entries = []
        
        # 보관 기한 체크 - 만료된 항목 제거
        retention_days = Config.HISTORY_RETENTION_DAYS
        cutoff = (datetime.now() - timedelta(days=retention_days)).strftime("%Y-%m-%d")
        valid_entries = [
            entry for entry in existing_entries
            if entry.get("collected_at", "") >= cutoff
        ]
        
        # 새 항목 추가
        new_entry = {
            "collected_at": datetime.now().strftime("%Y-%m-%d"),
            "collected_time": datetime.now().strftime("%Y-%m-%dT%H:%M:%S+09:00"),
            "count": len(new_urls),
            "urls": new_urls,
            "titles": new_titles
        }
        valid_entries.append(new_entry)
        
        # 저장
        history_data = {
            "last_updated": datetime.now().strftime("%Y-%m-%dT%H:%M:%S+09:00"),
            "total_entries": len(valid_entries),
            "entries": valid_entries
        }
        
        # output 디렉토리 확인
        os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
        
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(history_data, f, ensure_ascii=False, indent=2)
        
        print(f"💾 수집 이력 저장: {len(new_urls)}개 기사 기록")
    
    # ──────────────────────────────────────────────
    # 기존 유틸리티 메서드
    # ──────────────────────────────────────────────
    
    @staticmethod
    def _is_domestic_news(article: NewsArticle) -> bool:
        """
        국내 뉴스인지 확인
        
        Args:
            article: 뉴스 기사
        
        Returns:
            bool: 국내 뉴스 여부
        """
        # 한국 도메인 확인 (.kr, .co.kr 등)
        korean_domains = ['.kr', 'naver.com', 'daum.net', 'chosun.com', 'joongang.co', 
                         'donga.com', 'hani.co', 'khan.co', 'mt.co', 'hankyung.com',
                         'mk.co', 'sbs.co', 'kbs.co', 'mbc.co', 'ytn.co', 'jtbc.co']
        
        url_lower = article.url.lower()
        
        # 한국 도메인 중 하나라도 포함되면 국내 뉴스로 판단
        if any(domain in url_lower for domain in korean_domains):
            return True
        
        # 제목이나 내용에 해외 국가명이 많이 포함되어 있으면 해외 뉴스로 판단
        international_keywords = ['미국', '중국', '일본', '유럽', '영국', '프랑스', '독일', 
                                 '러시아', 'USA', 'China', 'Japan', 'Europe', 'UK']
        
        text = (article.title + ' ' + article.description).lower()
        korea_keywords = ['한국', '서울', '부산', '검찰', '법원', '금융감독원', '공정위', 
                         '대법원', '헌재', '국회']
        
        # 한국 관련 키워드가 있으면 국내 뉴스로 판단
        if any(keyword in text for keyword in korea_keywords):
            return True
        
        # 해외 키워드가 많고 한국 키워드가 없으면 제외
        international_count = sum(1 for keyword in international_keywords if keyword.lower() in text)
        if international_count > 2:
            return False
        
        # 기본적으로 포함 (네이버 뉴스는 대부분 국내 뉴스)
        return True
    
    @staticmethod
    def _clean_html(text: str) -> str:
        """HTML 태그 제거"""
        soup = BeautifulSoup(text, 'html.parser')
        return soup.get_text()
    
    @staticmethod
    def _extract_source(url: str) -> str:
        """URL에서 언론사명 추출 (간단한 방식)"""
        # URL에서 도메인 추출
        try:
            domain = url.split('/')[2]
            # news.naver.com 형식은 언론사 정보가 URL에 없을 수 있음
            if 'naver' in domain:
                return "네이버뉴스"
            return domain.replace('www.', '').replace('.com', '').replace('.co.kr', '')
        except:
            return "출처 미상"
