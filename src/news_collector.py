"""
네이버 뉴스 수집 모듈
Naver News API integration for collecting litigation-related articles
"""

import requests
from typing import List
from bs4 import BeautifulSoup
from .models import NewsArticle
from .config import Config


class NewsCollector:
    """네이버 뉴스 검색 및 수집"""
    
    def __init__(self):
        self.client_id = Config.NAVER_CLIENT_ID
        self.client_secret = Config.NAVER_CLIENT_SECRET
        self.base_url = "https://openapi.naver.com/v1/search/news.json"
    
    def search_news(self, keyword: str, display: int = 10) -> List[NewsArticle]:
        """
        네이버 뉴스 검색
        
        Args:
            keyword: 검색 키워드
            display: 검색 결과 개수 (최대 100)
        
        Returns:
            List[NewsArticle]: 뉴스 기사 리스트
        """
        headers = {
            'X-Naver-Client-Id': self.client_id,
            'X-Naver-Client-Secret': self.client_secret
        }
        
        params = {
            'query': keyword,
            'display': display,
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
    
    def search_multiple_keywords(self, keywords: List[str], display: int = 10) -> List[NewsArticle]:
        """
        여러 키워드로 뉴스 검색 (OR 조건)
        
        Args:
            keywords: 검색 키워드 리스트
            display: 각 키워드당 검색 결과 개수
        
        Returns:
            List[NewsArticle]: 중복 제거된 뉴스 기사 리스트
        """
        all_articles = []
        seen_urls = set()
        
        for keyword in keywords:
            print(f"🔍 '{keyword}' 검색 중...")
            articles = self.search_news(keyword, display)
            
            # 중복 제거
            for article in articles:
                if article.url not in seen_urls:
                    all_articles.append(article)
                    seen_urls.add(article.url)
        
        print(f"✅ 총 {len(all_articles)}개의 뉴스 기사 수집 완료")
        return all_articles
    
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
