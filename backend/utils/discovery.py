# backend/utils/discovery.py
"""
RSS 피드 발견 유틸리티

웹 페이지에서 RSS 피드를 찾는 로직을 담당합니다.
단일 책임 원칙(SRP)에 따라 FeedService와 분리되었습니다.
"""
import logging
from typing import List

import requests
from bs4 import BeautifulSoup
from feedsearch import search as fs_search

logger = logging.getLogger(__name__)


def discover_rss_feeds(url: str, top_k: int = 3) -> List[str]:
    """
    URL에서 RSS 피드를 발견합니다.
    
    Args:
        url: 탐색할 URL
        top_k: 최대 반환할 피드 수
        
    Returns:
        발견된 RSS 피드 URL 목록
    """
    candidates = []
    
    # 1. feedsearch 라이브러리 사용 (가장 신뢰성 높음)
    try:
        res = fs_search(url, max_urls=20, timeout=10)
        candidates = [x.url for x in res][:top_k]
        if candidates:
            logger.debug(f"feedsearch로 {len(candidates)}개 피드 발견: {url}")
            return candidates
    except Exception as e:
        logger.debug(f"feedsearch 실패 ({url}): {str(e)}")
    
    # 2. HTML <link> 태그에서 RSS 링크 찾기 (fallback)
    try:
        html = requests.get(url, timeout=10).text
        soup = BeautifulSoup(html, "lxml")
        links = []
        for link in soup.find_all("link"):
            link_type = (link.get("type") or "").lower()
            if "rss" in link_type or "atom" in link_type or "xml" in link_type:
                href = link.get("href")
                if href:
                    links.append(href)
        candidates = links[:top_k]
        if candidates:
            logger.debug(f"HTML 파싱으로 {len(candidates)}개 피드 발견: {url}")
            return candidates
    except Exception as e:
        logger.debug(f"HTML 파싱 실패 ({url}): {str(e)}")
    
    logger.warning(f"피드를 발견하지 못함: {url}")
    return []

