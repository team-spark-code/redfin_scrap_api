# backend/utils/url_norm.py
from __future__ import annotations
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode
import re
import html


def normalize_url(u: str) -> str:
    if not u:
        return u
    u = html.unescape(u.strip())             # "&amp;" -> "&"
    pr = urlparse(u)

    scheme = (pr.scheme or "http").lower()
    netloc = pr.hostname.lower() if pr.hostname else ""
    if pr.port:
        # 기본 포트는 제거
        if not ((scheme == "http" and pr.port == 80) or (scheme == "https" and pr.port == 443)):
            netloc = f"{netloc}:{pr.port}"

    # path: // -> /, 트레일링 슬래시는 존중(피드마다 의미 다를 수 있어 보존)
    path = pr.path or "/"

    # query: 정렬 + 중복 제거
    q = urlencode(sorted(dict(parse_qsl(pr.query, keep_blank_values=True)).items()), doseq=True)

    # fragment 제거
    frag = ""

    return urlunparse((scheme, netloc, path, "", q, frag))


# OPML 업로드 시 잘못된 '&'를 고쳐주는 최소 sanitizer
_amp_re = re.compile(r'&(?!amp;|#\d+;|#x[0-9A-Fa-f]+;)')
def sanitize_opml_bytes(raw: bytes) -> bytes:
    try:
        txt = raw.decode("utf-8")
    except UnicodeDecodeError:
        txt = raw.decode("latin-1")
    # xmlUrl="...": 속성값 안의 맨홀(&)만 우선 교정
    def _fix_attr(m):
        val = m.group(1)
        return f'xmlUrl="{_amp_re.sub("&amp;", val)}"'
    txt = re.sub(r'xmlUrl="([^"]+)"', _fix_attr, txt)
    # <title>…</title> 등 본문에 남은 맨홀도 최소 교정
    txt = re.sub(r'>([^<]*&[^<]*)<', lambda m: ">" + _amp_re.sub("&amp;", m.group(1)) + "<", txt)
    return txt.encode("utf-8")

