"""AI가 만든 글이 원문에 근거하는지 코드로 검사한다.

검사 규칙
1. source_id가 넘긴 번호인지, 빠지거나 겹친 항목이 없는지
2. categories가 정해진 목록 안에 있고 1~3개인지
3. 모든 글에 URL·도메인이 없는지
4. 숫자(%, 원, 억, 년, 버전 포함)가 원문(제목+본문)에 그대로 있는지
5. 영문 고유명사·약어가 원문에 있는지 (요약·토론 정리만, 면접 포인트는 일반 개념이라 제외)
6. 날짜·시점 표현이 원문에 있는지
"""

from __future__ import annotations

import re

from gemini import CATEGORIES

URL_RE = re.compile(r"https?://|www\.|\b[\w-]+\.(?:com|net|org|io|kr|dev|ai|co|app)\b", re.I)
NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)*")
LATIN_RE = re.compile(r"[A-Za-z][A-Za-z0-9.+#'-]*[A-Za-z0-9+#]|[A-Za-z]")
TIME_RE = re.compile(r"지난\s?(?:주|달|해)|어제|그제|내일|올해|작년|내년|이번\s?(?:주|달)|다음\s?(?:주|달)|최근")

# 원문에 없어도 설명용으로 흔히 쓰는 일반 용어 (고유명사가 아님)
GENERIC_TERMS = {
    "ai", "api", "ui", "ux", "os", "db", "sql", "http", "https", "cpu", "gpu", "it", "js", "css", "html",
    "cs", "llm", "sdk", "cli", "ide", "pc", "app", "web", "dom", "tcp", "udp", "ip", "dns", "json", "xml",
    "rest", "saas", "cloud", "ml", "pt", "a", "i",
}


def _numbers_in(text: str) -> set[str]:
    return {n.replace(",", "") for n in NUMBER_RE.findall(text)}


def check_text(strict: str, loose: str, source_text: str) -> list[str]:
    """strict: 원문 근거여야 하는 글(요약 등), loose: 일반 개념 설명(면접 포인트 등)."""
    errors: list[str] = []
    everything = f"{strict} {loose}"
    source_lower = re.sub(r"\s+", " ", source_text).lower()

    if URL_RE.search(everything):
        errors.append("링크·URL·도메인을 쓰면 안 돼요")

    source_numbers = _numbers_in(source_text)
    missing_numbers = sorted(n for n in _numbers_in(everything) if n not in source_numbers)
    if missing_numbers:
        errors.append(f"원문에 없는 숫자가 있어요: {', '.join(missing_numbers)}")

    missing_names = sorted({
        w for w in LATIN_RE.findall(strict)
        if w.lower() not in GENERIC_TERMS and w.lower() not in source_lower
    })
    if missing_names:
        errors.append(f"원문에 없는 영문 이름이 있어요: {', '.join(missing_names)}")

    missing_times = sorted({t for t in TIME_RE.findall(everything) if t not in source_text})
    if missing_times:
        errors.append(f"원문에 없는 시점 표현이 있어요: {', '.join(missing_times)}")
    return errors


def check_item(item: dict, source_text: str) -> list[str]:
    errors: list[str] = []
    cats = item.get("categories") or []
    if not 1 <= len(cats) <= 3 or any(c not in CATEGORIES for c in cats):
        errors.append(f"categories는 {', '.join(CATEGORIES)} 중 1~3개여야 해요 (받은 값: {cats})")

    strict = " ".join(str(item.get(f) or "") for f in ("one_line", "easy_summary", "why_it_matters"))
    loose = " ".join(f"{p.get('question', '')} {p.get('answer_hint', '')}" for p in item.get("interview_points") or [])
    errors += check_text(strict, loose, source_text)

    if item.get("highlight") and not (item.get("easy_summary") or "").strip():
        errors.append("highlight가 true면 easy_summary를 써야 해요")
    return errors


def check_batch(items: list[dict], sources: dict[str, str]) -> tuple[dict[str, dict], dict[str, list[str]]]:
    """통과한 항목과 항목별 에러를 돌려준다. 빠진 원문도 에러로 표시한다."""
    passed: dict[str, dict] = {}
    errors: dict[str, list[str]] = {}
    seen: set[str] = set()
    for item in items:
        sid = item.get("source_id", "")
        if sid not in sources or sid in seen:
            continue  # 넘기지 않은 번호와 중복은 버린다
        seen.add(sid)
        item_errors = check_item(item, sources[sid])
        if item_errors:
            errors[sid] = item_errors
        else:
            passed[sid] = item
    for sid in sources:
        if sid not in seen:
            errors[sid] = ["이 원문에 대한 항목이 빠졌어요"]
    return passed, errors


def check_debate(debate: dict, source_text: str) -> list[str]:
    if debate.get("insufficient"):
        return []
    errors: list[str] = []
    if not debate.get("issue", "").strip() or not debate.get("background", "").strip():
        errors.append("issue와 background를 써야 해요")
    strict = " ".join([debate.get("background", ""), debate.get("issue", "")]
                      + list(debate.get("pros") or []) + list(debate.get("cons") or []))
    loose = " ".join([debate.get("pt_angle", "")] + list(debate.get("counter_general") or []))
    errors += check_text(strict, loose, source_text)
    return errors
