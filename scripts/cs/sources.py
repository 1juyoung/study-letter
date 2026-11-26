"""커리큘럼의 근거 자료(sources)를 GitHub 원문에서 가져온다."""

from __future__ import annotations

import re
import sys
import urllib.parse
import urllib.request

USER_AGENT = "study-letter/1.0 (+https://github.com/1juyoung/study-letter)"
MAX_SOURCE_TEXT = 8000  # 자료 하나당 AI에 넘기는 최대 길이

REPOS = {
    "gy": ("gyoogle/tech-interview-for-developer", "master", "gyoogle/tech-interview-for-developer"),
    "fe": ("Esoolgnah/Frontend-Interview-Questions", "main", "Esoolgnah/Frontend-Interview-Questions"),
    "pf": ("junh0328/prepare_frontend_interview", "main", "junh0328/prepare_frontend_interview"),
}


def _quote(path: str) -> str:
    return "/".join(urllib.parse.quote(p) for p in path.split("/"))


def resolve(source: str) -> tuple[str, str, str]:
    """'gy:경로' → (원문 raw 주소, 사람이 보는 주소, 표시 이름)"""
    prefix, path = source.split(":", 1)
    if prefix == "mdn":
        slug = path.strip("/")
        raw = f"https://raw.githubusercontent.com/mdn/content/main/files/en-us/{slug.lower()}/index.md"
        return raw, f"https://developer.mozilla.org/ko/docs/{slug}", f"MDN: {slug.split('/')[-1]}"
    repo, branch, label = REPOS[prefix]
    raw = f"https://raw.githubusercontent.com/{repo}/{branch}/{_quote(path)}"
    page = f"https://github.com/{repo}/blob/{branch}/{_quote(path)}"
    return raw, page, f"{label.split('/')[0]}: {path.rsplit('/', 1)[-1].removesuffix('.md')}"


def _clean(text: str) -> str:
    text = re.sub(r"^---\n.*?\n---\n", "", text, flags=re.S)  # MDN front matter
    text = re.sub(r"\{\{[^}]*\}\}", "", text)  # MDN 매크로
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)  # 이미지
    text = re.sub(r"<img[^>]*>", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _section(text: str, keyword: str) -> str:
    """제목에 keyword가 들어간 절만 잘라 낸다 (같은 수준 이상의 다음 제목 전까지)."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        m = re.match(r"^(#+)\s", line)
        if m and keyword in line:
            level = len(m.group(1))
            end = next((j for j in range(i + 1, len(lines))
                        if (n := re.match(r"^(#+)\s", lines[j])) and len(n.group(1)) <= level), len(lines))
            return "\n".join(lines[i:end])
    return text


def fetch(source: str) -> dict | None:
    source, _, section = source.partition("#")
    raw, page, label = resolve(source)
    try:
        req = urllib.request.Request(raw, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=30) as res:
            text = res.read().decode("utf-8", errors="replace")
    except Exception as e:  # noqa: BLE001
        print(f"::warning::근거 자료를 가져오지 못했어요: {source} ({e})", file=sys.stderr)
        return None
    text = _clean(text)
    if section:
        text = _section(text, section)
    print(f"  근거 자료 {len(text)}자: {label}", file=sys.stderr)
    return {"source": source, "label": label, "url": page, "text": text[:MAX_SOURCE_TEXT],
            "official": source.startswith("mdn:")}
