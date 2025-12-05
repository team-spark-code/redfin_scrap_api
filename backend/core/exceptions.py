# backend/core/exceptions.py
"""커스텀 예외 클래스"""


class RSSException(Exception):
    """기본 RSS 예외"""
    pass


class FeedNotFoundException(RSSException):
    """피드를 찾을 수 없음"""
    pass


class FeedAlreadyExistsException(RSSException):
    """피드가 이미 존재함"""
    pass


class InvalidOPMLError(RSSException):
    """잘못된 OPML 형식"""
    pass

