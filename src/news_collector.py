"""
네이버 뉴스 수집 모듈
Naver News API integration for collecting litigation-related articles
"""

import time
import requests
from bs4 import BeautifulSoup
from .models import NewsArticle
from .config import Config


class NewsCollector:
    """네이버 뉴스 검색 및 수집"""
    
    def __init__(self):
        self.client_id = Config.NAVER_CLIENT_ID
        self.client_secret = Config.NAVER_CLIENT_SECRET
        self.base_url = "https://openapi.naver.com/v1/search/news.json"
    
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
        
        Args:
            keywords: 검색 키워드 리스트
            display: 각 페이지당 검색 결과 개수
        
        Returns:
            List[NewsArticle]: 중복 제거된 뉴스 기사 리스트 (국내 기사만)
        """
        all_articles = []
        seen_urls = set()
        
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
                if article.url not in seen_urls and self._is_domestic_news(article):
                    all_articles.append(article)
                    seen_urls.add(article.url)
                    new_count += 1
            
            print(f"   → '{keyword}': {len(articles)}개 수집, {new_count}개 신규 추가")
        
        print(f"✅ 총 {len(all_articles)}개의 국내 뉴스 기사 수집 완료")
        return all_articles
    
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
