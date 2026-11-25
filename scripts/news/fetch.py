"""RSS에서 지난 레터 이후 올라온 글을 모으고, 토론 주제로 고른 기사 하나의 본문을 가져온다."""

from __future__ import annotations

import html
import re
import sys
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import feedparser

# 요약하는 소스 (RSS에 본문이 들어 있는 곳)
SUMMARY_SOURCES = [
    ("긱뉴스", "https://news.hada.io/rss/news"),
    ("토스", "https://toss.tech/rss.xml"),
    ("카카오", "https://tech.kakao.com/feed/"),
    ("네이버 D2", "https://d2.naver.com/d2.atom"),
    ("당근", "https://medium.com/feed/daangn"),
    ("SW마에스트로", "https://rss.blog.naver.com/sw_maestro.xml"),
]
# 우아한형제들 기술블로그는 프로그램 접근을 403으로 막고 있어서 뺐다 (우회하지 않음)
# 제목만 쓰는 소스 (RSS에 본문이 거의 없음). 토론 주제로 고른 기사 1개만 페이지에서 본문을 가져온다.
HEADLINE_SOURCES = [
    ("한국경제", "https://www.hankyung.com/feed/it"),
    ("한국경제", "https://www.hankyung.com/feed/finance"),
]
BLOG_SOURCES = {"토스", "카카오", "네이버 D2", "당근", "SW마에스트로"}

# PT·토론 면접과 거리가 먼 시황·주가 기사는 제목으로 먼저 거른다 (AI에 넘기지 않음)
MARKET_NOISE = ["특징주", "코스피", "코스닥", "마감", "급등", "급락", "폭락", "목표주가", "목표가", "환율", "시황",
                "상한가", "하한가", "주가", "증시", "장중", "개장", "순매수", "순매도", "사이드카", "종목", "랠리"]
MAX_HEADLINES = 40  # 거르고 남은 한국경제 제목 중 최신순 최대 개수 (AI는 제목만 읽으므로 가벼움)
MAX_TEXT = 2000  # 요약용 원문 길이
MAX_ARTICLE_TEXT = 6000  # 토론 주제용 기사 본문 길이
USER_AGENT = "study-letter/1.0 (+https://github.com/1juyoung/study-letter)"


@dataclass
class Article:
    id: str  # 요약 소스는 N1, N2 … / 제목 소스는 H1, H2 …
    source: str
    title: str
    link: str
    published: datetime
    text: str  # AI에 넘기는 원문(제목 제외). 제목 소스는 비어 있음


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def html_to_text(raw: str) -> str:
    parser = _TextExtractor()
    parser.feed(raw or "")
    text = html.unescape(" ".join(parser.parts))
    return re.sub(r"\s+", " ", text).strip()


def clean_link(url: str) -> str:
    """utm_ 같은 추적용 파라미터를 뗀다."""
    parts = urlsplit(url)
    query = [(k, v) for k, v in parse_qsl(parts.query) if not k.startswith("utm_")]
    return urlunsplit(parts._replace(query=urlencode(query)))


def _published(entry) -> datetime | None:
    for key in ("published_parsed", "updated_parsed"):
        value = entry.get(key)
        if value:
            return datetime(*value[:6], tzinfo=timezone.utc)
    return None


def _read_feeds(sources, since: datetime, until: datetime, with_text: bool) -> list[Article]:
    seen: set[str] = set()
    articles: list[Article] = []
    for source, url in sources:
        feed = feedparser.parse(url, agent=USER_AGENT)
        if feed.get("bozo") and not feed.entries:
            print(f"::warning::{source} RSS를 읽지 못했어요: {url} ({feed.get('bozo_exception')})", file=sys.stderr)
            continue
        count = 0
        for entry in feed.entries:
            link = clean_link(entry.get("link", "").strip())
            published = _published(entry)
            if not link or link in seen or published is None or not (since <= published < until):
                continue
            body = ""
            if with_text:
                if entry.get("content"):
                    body = entry.content[0].get("value", "")
                body = html_to_text(body or entry.get("summary", ""))[:MAX_TEXT]
            seen.add(link)
            articles.append(Article("", source, html_to_text(entry.get("title", "")), link, published, body))
            count += 1
        print(f"{source}: {count}개 ({url})", file=sys.stderr)
    return articles


def collect(since: datetime, until: datetime) -> tuple[list[Article], list[Article]]:
    """(요약할 글, 한국경제 제목) 두 묶음을 돌려준다."""
    articles = sorted(_read_feeds(SUMMARY_SOURCES, since, until, with_text=True), key=lambda a: a.published)
    for i, a in enumerate(articles, 1):
        a.id = f"N{i}"

    headlines = _read_feeds(HEADLINE_SOURCES, since, until, with_text=False)
    noise = [h for h in headlines if any(w in h.title for w in MARKET_NOISE)]
    headlines = sorted((h for h in headlines if h not in noise), key=lambda a: a.published, reverse=True)[:MAX_HEADLINES]
    for i, h in enumerate(headlines, 1):
        h.id = f"H{i}"
    print(f"한국경제: 시황 기사 {len(noise)}개 제외, 제목 {len(headlines)}개 사용", file=sys.stderr)
    return articles, headlines


class _ArticleBody(HTMLParser):
    """기사 페이지에서 본문 영역(id/class에 article 본문 표시가 있는 div)의 글자만 모은다."""

    BODY_MARKERS = ("articletxt", "article-body", "article_body", "articlebody")
    SKIP_TAGS = {"script", "style", "figcaption", "button"}

    def __init__(self) -> None:
        super().__init__()
        self.depth = 0  # 본문 div 안에 있을 때 1 이상
        self.skip = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        marker = f"{attrs.get('id', '')} {attrs.get('class', '')}".lower()
        if self.depth:
            if tag == "div":
                self.depth += 1
            if tag in self.SKIP_TAGS:
                self.skip += 1
        elif tag == "div" and any(m in marker for m in self.BODY_MARKERS):
            self.depth = 1

    def handle_endtag(self, tag):
        if not self.depth:
            return
        if tag in self.SKIP_TAGS and self.skip:
            self.skip -= 1
        if tag == "div":
            self.depth -= 1

    def handle_data(self, data):
        if self.depth and not self.skip:
            self.parts.append(data)


def fetch_article_text(url: str) -> str:
    """기사 페이지 하나에서 본문을 가져온다. 못 가져오면 빈 문자열."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=30) as res:
            raw = res.read().decode(res.headers.get_content_charset() or "utf-8", errors="replace")
    except Exception as e:  # noqa: BLE001 - 어떤 이유든 본문 없이 진행
        print(f"::warning::기사 본문을 가져오지 못했어요: {url} ({e})", file=sys.stderr)
        return ""
    parser = _ArticleBody()
    parser.feed(raw)
    text = re.sub(r"\s+", " ", html.unescape(" ".join(parser.parts))).strip()
    print(f"기사 본문 {len(text)}자: {url}", file=sys.stderr)
    return text[:MAX_ARTICLE_TEXT]
