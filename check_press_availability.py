"""
네이버 뉴스 검색 API에서 제공하는 언론사 확인 스크립트
- 목표 언론사 목록을 대상으로 네이버 API 검색 결과에 나오는지 확인
- 결과: API로 가져올 수 있는 언론사 / RSS로 따로 가져와야 할 언론사 분류
"""

import requests
import time
import json
import os
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("NAVER_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET", "")

# 확인 대상 언론사 목록과 알려진 도메인 매핑
TARGET_PRESS = {
    # 종합일간지
    "경향신문": ["khan.co.kr"],
    "국민일보": ["kmib.co.kr"],
    "동아일보": ["donga.com"],
    "문화일보": ["munhwa.com"],
    "서울신문": ["seoul.co.kr"],
    "세계일보": ["segye.com"],
    "조선일보": ["chosun.com"],
    "중앙일보": ["joongang.co.kr"],
    "한겨레": ["hani.co.kr"],
    "한국일보": ["hankookilbo.com"],

    # 통신·방송
    "뉴스1": ["news1.kr"],
    "뉴시스": ["newsis.com"],
    "연합뉴스": ["yna.co.kr"],
    "연합뉴스TV": ["yonhapnewstv.co.kr"],
    "채널A": ["ichannela.com"],
    "한국경제TV": ["wowtv.co.kr"],
    "JTBC": ["jtbc.co.kr", "jtbc.joins.com"],
    "KBS": ["kbs.co.kr"],
    "MBC": ["imnews.imbc.com", "mbc.co.kr"],
    "MBN": ["mbn.co.kr"],
    "SBS": ["sbs.co.kr"],
    "SBS Biz": ["sbsbiz.co.kr", "biz.sbs.co.kr"],
    "TV조선": ["tvchosun.com"],
    "YTN": ["ytn.co.kr"],

    # 경제지
    "매일경제": ["mk.co.kr"],
    "머니투데이": ["mt.co.kr"],
    "비즈워치": ["bizwatch.co.kr"],
    "서울경제": ["sedaily.com"],
    "아시아경제": ["asiae.co.kr"],
    "이데일리": ["edaily.co.kr"],
    "조선비즈": ["biz.chosun.com"],
    "조세일보": ["joseilbo.com"],
    "파이낸셜뉴스": ["fnnews.com"],
    "한국경제": ["hankyung.com"],
    "헤럴드경제": ["heraldcorp.com"],

    # 인터넷·뉴미디어
    "노컷뉴스": ["nocutnews.co.kr"],
    "더팩트": ["tf.co.kr", "thefact.co.kr"],
    "데일리안": ["dailian.co.kr"],
    "머니S": ["moneys.mt.co.kr"],
    "미디어오늘": ["mediatoday.co.kr"],
    "아이뉴스24": ["inews24.com"],
    "오마이뉴스": ["ohmynews.com"],
    "프레시안": ["pressian.com"],

    # IT 전문
    "디지털데일리": ["ddaily.co.kr"],
    "디지털타임스": ["dt.co.kr"],
    "블로터": ["bloter.net"],
    "전자신문": ["etnews.com"],
    "지디넷코리아": ["zdnet.co.kr"],

    # 시사·잡지
    "더스쿠프": ["thescoop.co.kr"],
    "레이디경향": ["lady.khan.co.kr"],
    "매경이코노미": ["mk.co.kr"],  # 매일경제 하위
    "시사IN": ["sisain.co.kr"],
    "시사저널": ["sisajournal.com"],
    "신동아": ["donga.com"],  # 동아 하위
    "월간 산": ["san.chosun.com"],
    "이코노미스트": ["economist.co.kr"],
    "주간경향": ["weekly.khan.co.kr"],
    "주간동아": ["weekly.donga.com"],
    "주간조선": ["weekly.chosun.com"],
    "중앙SUNDAY": ["joongang.co.kr"],  # 중앙 하위
    "한겨레21": ["h21.hani.co.kr"],
    "한경비즈니스": ["hankyung.com"],  # 한경 하위

    # 전문·특수
    "기자협회보": ["journalist.or.kr"],
    "농민신문": ["nongmin.com"],
    "뉴스타파": ["newstapa.org"],
    "동아사이언스": ["dongascience.com"],
    "여성신문": ["womennews.co.kr"],
    "일다": ["ildaro.com"],
    "코리아중앙데일리": ["koreajoongangdaily.joins.com"],
    "코리아헤럴드": ["koreaherald.com"],
    "코메디닷컴": ["kormedi.com"],
    "헬스조선": ["health.chosun.com"],

    # 지역
    "강원도민일보": ["kado.net"],
    "강원일보": ["kwnews.co.kr"],
    "경기일보": ["kyeonggi.com"],
    "국제신문": ["kookje.co.kr"],
    "대구MBC": ["dgmbc.co.kr"],
    "대전일보": ["daejonilbo.com"],
    "매일신문": ["imaeil.com"],
    "부산일보": ["busan.com"],
    "전주MBC": ["jmbc.co.kr"],
    "CJB청주방송": ["cjb.co.kr"],
    "JIBS": ["jibs.co.kr"],
    "KBC광주방송": ["ikbc.co.kr"],
}


def search_naver_news(query: str, display: int = 100, start: int = 1) -> dict:
    """네이버 뉴스 검색 API 호출"""
    url = "https://openapi.naver.com/v1/search/news.json"
    headers = {
        "X-Naver-Client-Id": CLIENT_ID,
        "X-Naver-Client-Secret": CLIENT_SECRET,
    }
    params = {
        "query": query,
        "display": display,
        "start": start,
        "sort": "date",
    }
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()


def extract_domain(url: str) -> str:
    """URL에서 도메인 추출"""
    try:
        domain = url.split("/")[2].lower()
        domain = domain.replace("www.", "")
        return domain
    except (IndexError, AttributeError):
        return ""


def check_press_availability():
    """각 언론사가 네이버 API 검색 결과에 나오는지 확인"""

    if not CLIENT_ID or not CLIENT_SECRET:
        print("오류: .env 파일에 NAVER_CLIENT_ID, NAVER_CLIENT_SECRET을 설정하세요.")
        return

    print("=" * 70)
    print("네이버 뉴스 검색 API 언론사 확인")
    print("=" * 70)

    # 1단계: 다양한 키워드로 검색해서 API에 나오는 전체 도메인 수집
    print("\n[1단계] 다양한 키워드로 API 검색 결과의 도메인 수집 중...\n")

    search_keywords = [
        "소송", "판결", "경제", "정치", "사회", "사건", "사고",
        "기업", "부동산", "금융", "주식", "환경", "노동",
        "IT", "과학", "건강", "지역", "강원", "부산", "대구", "광주", "대전",
    ]

    api_domains = set()
    total_articles = 0

    for keyword in search_keywords:
        for start in [1, 101, 201]:  # 키워드당 최대 300건
            try:
                data = search_naver_news(keyword, display=100, start=start)
                items = data.get("items", [])
                total_articles += len(items)

                for item in items:
                    original = item.get("originallink", "")
                    link = item.get("link", "")

                    for url in [original, link]:
                        domain = extract_domain(url)
                        if domain:
                            api_domains.add(domain)

                time.sleep(0.1)  # API 호출 간격

            except Exception as e:
                print(f"  검색 실패 ({keyword}, start={start}): {e}")
                time.sleep(1)

        print(f"  '{keyword}' 검색 완료 (누적 도메인: {len(api_domains)}개)")

    print(f"\n총 검색 기사: {total_articles}건")
    print(f"수집된 고유 도메인: {len(api_domains)}개\n")

    # 2단계: 각 언론사 이름으로 직접 검색해서 추가 확인
    print("[2단계] 각 언론사 이름으로 직접 검색 중...\n")

    direct_found = {}  # 직접 검색으로 찾은 언론사

    for press_name, known_domains in TARGET_PRESS.items():
        try:
            data = search_naver_news(press_name, display=10)
            items = data.get("items", [])

            for item in items:
                original = item.get("originallink", "")
                link = item.get("link", "")

                for url in [original, link]:
                    domain = extract_domain(url)
                    if domain:
                        api_domains.add(domain)
                        for kd in known_domains:
                            if kd in domain or domain in kd:
                                direct_found[press_name] = domain
                                break

            time.sleep(0.1)

        except Exception as e:
            print(f"  '{press_name}' 검색 실패: {e}")
            time.sleep(1)

    # 3단계: 도메인 매칭으로 분류
    print("[3단계] 결과 분류 중...\n")

    available_via_api = {}   # 네이버 API로 가져올 수 있는 언론사
    need_rss = {}            # RSS로 따로 가져와야 할 언론사

    for press_name, known_domains in TARGET_PRESS.items():
        found = False
        matched_domain = ""

        # 직접 검색에서 찾은 경우
        if press_name in direct_found:
            found = True
            matched_domain = direct_found[press_name]
        else:
            # 도메인 매칭으로 확인
            for kd in known_domains:
                for api_domain in api_domains:
                    if kd in api_domain or api_domain.endswith(kd):
                        found = True
                        matched_domain = api_domain
                        break
                if found:
                    break

        if found:
            available_via_api[press_name] = matched_domain
        else:
            need_rss[press_name] = known_domains

    # 결과 출력
    print("=" * 70)
    print(f"네이버 API로 가져올 수 있는 언론사: {len(available_via_api)}개")
    print("=" * 70)
    for press, domain in sorted(available_via_api.items()):
        print(f"  [O] {press:<20s} ({domain})")

    print()
    print("=" * 70)
    print(f"RSS로 따로 가져와야 할 언론사: {len(need_rss)}개")
    print("=" * 70)
    for press, domains in sorted(need_rss.items()):
        print(f"  [X] {press:<20s} (도메인: {', '.join(domains)})")

    print()
    print("=" * 70)
    print("요약")
    print("=" * 70)
    total = len(TARGET_PRESS)
    api_count = len(available_via_api)
    rss_count = len(need_rss)
    print(f"  전체 대상:      {total}개")
    print(f"  네이버 API:     {api_count}개 ({api_count/total*100:.1f}%)")
    print(f"  RSS 필요:       {rss_count}개 ({rss_count/total*100:.1f}%)")

    # 결과를 JSON 파일로 저장
    result = {
        "total_target": total,
        "available_via_api": {
            "count": api_count,
            "press_list": available_via_api,
        },
        "need_rss": {
            "count": rss_count,
            "press_list": {name: domains for name, domains in need_rss.items()},
        },
        "all_api_domains": sorted(api_domains),
    }

    output_path = "press_availability_result.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n상세 결과 저장: {output_path}")


if __name__ == "__main__":
    check_press_availability()
