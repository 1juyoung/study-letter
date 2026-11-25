"""기술 뉴스 레터를 만든다.

흐름
1. RSS 수집: 긱뉴스·블로그(본문 있음)와 한국경제(제목만)
2. 긱뉴스·블로그: AI 요약(JSON, 30개씩) → 검사 → 실패 항목만 1번 재생성 → 그래도 실패면 제외
3. 한국경제: AI가 제목만 보고 PT·토론 이슈 기사를 고름 → 그중 1개만 기사 페이지에서 본문을 가져와 토론 주제 정리 → 검사
4. 마크다운 저장 → TOPICS.md 갱신 → 알림용 출력(GITHUB_OUTPUT)

로컬 테스트 (레포 파일은 건드리지 않고 결과만 out 파일로 저장):
    GEMINI_API_KEY=... python scripts/news/generate.py --out /tmp/news-test.md
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import gemini  # noqa: E402
from fetch import BLOG_SOURCES, Article, collect, fetch_article_text  # noqa: E402
from verify import check_batch, check_debate  # noqa: E402

KST = timezone(timedelta(hours=9))
HERE = Path(__file__).parent
ROOT = HERE.parents[1]
LETTER_DIR = ROOT / "public" / "letters" / "news"
TOPICS_FILE = ROOT / "TOPICS.md"
PROMPT = (HERE / "prompt.md").read_text(encoding="utf-8")
PROMPT_HEADLINES = (HERE / "prompt_headlines.md").read_text(encoding="utf-8")
PROMPT_DEBATE = (HERE / "prompt_debate.md").read_text(encoding="utf-8")
APP_URL = "https://1juyoung.github.io/study-letter/"
BATCH = 30
MAX_PICKS = 10  # 이슈 헤드라인 최대 개수
MAX_WINDOW = timedelta(days=3)  # 며칠 동안 레터가 안 나갔어도 최대 3일치만 정리


# ---------- 기간 ----------

def last_generated_at() -> datetime | None:
    files = sorted(LETTER_DIR.glob("????-??-??.md"))
    if not files:
        return None
    m = re.search(r"^generated_at:\s*(\S+)", files[-1].read_text(encoding="utf-8"), re.M)
    return datetime.fromisoformat(m.group(1)) if m else None


def window(now: datetime) -> tuple[datetime, datetime]:
    since = last_generated_at() or now - timedelta(days=1)
    return max(since, now - MAX_WINDOW), now


# ---------- 긱뉴스·블로그 요약 ----------

def build_prompt(articles: list[Article], feedback: dict[str, list[str]] | None = None) -> str:
    parts = [PROMPT, "\n[원문]"]
    for a in articles:
        parts.append(f"\n[{a.id}] 출처: {a.source}\n제목: {a.title}\n내용: {a.text or '(내용 없음)'}")
    if feedback:
        parts.append("\n[이전 답변에서 어긴 규칙 — 이번에는 반드시 고쳐서 다시 쓴다]")
        for sid, errs in feedback.items():
            parts.append(f"- {sid}: {' / '.join(errs)}")
    return "\n".join(parts)


def summarize(articles: list[Article], api_key: str, models: list[str]) -> tuple[dict[str, dict], dict[str, list[str]]]:
    by_id = {a.id: a for a in articles}
    sources = {a.id: f"{a.title}\n{a.text}" for a in articles}
    passed: dict[str, dict] = {}
    failed: dict[str, list[str]] = {}

    for i in range(0, len(articles), BATCH):
        batch = articles[i:i + BATCH]
        result = gemini.call(build_prompt(batch), gemini.ITEMS_SCHEMA, api_key, models)
        ok, errors = check_batch(result.get("items", []), {a.id: sources[a.id] for a in batch})
        passed.update(ok)

        if errors:  # 실패한 항목만 어긴 규칙을 알려 주고 1번 다시
            for sid, errs in errors.items():
                print(f"  재생성 {sid}: {' / '.join(errs)}", file=sys.stderr)
            retry = [by_id[sid] for sid in errors]
            result = gemini.call(build_prompt(retry, errors), gemini.ITEMS_SCHEMA, api_key, models)
            ok, errors = check_batch(result.get("items", []), {a.id: sources[a.id] for a in retry})
            passed.update(ok)
            failed.update(errors)
            for sid, errs in errors.items():
                print(f"  검사 실패로 제외 {sid} ({by_id[sid].title[:30]}): {' / '.join(errs)}", file=sys.stderr)
    return passed, failed


MAX_BLOG_HIGHLIGHTS = 2


def pick_highlights(articles: list[Article], items: dict[str, dict]) -> list[str]:
    """긱뉴스는 1개(면접 포인트가 있는 글 우선), 블로그 글은 AI가 고른 것 중 최신 2개."""
    geek, blog = [], []
    for a in articles:
        item = items.get(a.id)
        if not item or not item.get("highlight") or item.get("insufficient"):
            continue
        (blog if a.source in BLOG_SOURCES else geek).append(a.id)
    geek.sort(key=lambda sid: not items[sid].get("interview_points"))
    return geek[:1] + blog[-MAX_BLOG_HIGHLIGHTS:]


def refill_geek_highlight(articles: list[Article], items: dict[str, dict], api_key: str, models: list[str]) -> None:
    """긱뉴스에서 고른 글이 검사에 걸려 빠졌으면, 통과한 글 중에서 다시 1개를 골라 자세히 쓰게 한다."""
    if any(items[sid].get("highlight") for sid in items if not sid_is_blog(sid, articles)):
        return
    candidates = [a for a in articles if a.source == "긱뉴스" and a.id in items and not items[a.id].get("insufficient")]
    if not candidates:
        return
    sources = {a.id: f"{a.title}\n{a.text}" for a in candidates}
    note = ("\n[이번 요청] 위 원문 중 기술 면접에 나오거나 공부에 가장 도움 될 글 정확히 1개만 highlight를 true로 하고 "
            "easy_summary, why_it_matters, interview_points를 쓴다. 나머지는 highlight를 false로 한다.")
    for attempt in range(2):
        result = gemini.call(build_prompt(candidates) + note, gemini.ITEMS_SCHEMA, api_key, models)
        ok, _ = check_batch(result.get("items", []), sources)
        picked = [sid for sid, item in ok.items() if item.get("highlight")]
        if picked:
            items[picked[0]] = ok[picked[0]]
            print(f"  자세히 볼 글 다시 고름: {picked[0]}", file=sys.stderr)
            return
        print(f"  자세히 볼 글 다시 고르기 실패({attempt + 1}회)", file=sys.stderr)


def sid_is_blog(sid: str, articles: list[Article]) -> bool:
    return next((a.source in BLOG_SOURCES for a in articles if a.id == sid), False)


# ---------- 한국경제: 이슈 헤드라인 + 토론 주제 ----------

def pick_headlines(headlines: list[Article], api_key: str, models: list[str]) -> tuple[list[str], str]:
    if not headlines:
        return [], ""
    prompt = PROMPT_HEADLINES + "\n[제목]\n" + "\n".join(f"[{h.id}] {h.title}" for h in headlines)
    result = gemini.call(prompt, gemini.HEADLINES_SCHEMA, api_key, models)
    valid = {h.id for h in headlines}
    picks = list(dict.fromkeys(p for p in result.get("picks", []) if p in valid))[:MAX_PICKS]
    debate_pick = result.get("debate_pick", "")
    return picks, debate_pick if debate_pick in valid else ""


def make_debate(article: Article, api_key: str, models: list[str]) -> dict | None:
    body = fetch_article_text(article.link)
    if len(body) < 300:  # 본문을 못 가져왔거나 너무 짧으면 토론 주제 없이 진행
        print("  토론 주제: 기사 본문이 부족해서 건너뛰어요", file=sys.stderr)
        return None
    source_text = f"{article.title}\n{body}"
    prompt = f"{PROMPT_DEBATE}\n[원문]\n제목: {article.title}\n본문: {body}"
    feedback: list[str] = []
    for attempt in range(2):
        full = prompt + (f"\n\n[이전 답변에서 어긴 규칙 — 이번에는 반드시 고친다]\n- " + "\n- ".join(feedback) if feedback else "")
        debate = gemini.call(full, gemini.DEBATE_SCHEMA, api_key, models)
        if debate.get("insufficient"):
            print("  토론 주제: AI가 쟁점이 없다고 판단해서 건너뛰어요", file=sys.stderr)
            return None
        feedback = check_debate(debate, source_text)
        if not feedback:
            return debate
        print(f"  토론 주제 검사 실패({attempt + 1}회): {' / '.join(feedback)}", file=sys.stderr)
    return None


# ---------- 마크다운 ----------

def md_text(text: str) -> str:
    return text.replace("|", "\\|").replace("[", "\\[").replace("]", "\\]").strip()


def tags(a: Article, item: dict) -> str:
    return " ".join(f"`{t}`" for t in [a.source] + list(item.get("categories", [])[1:]))


def render(now: datetime, articles: list[Article], items: dict[str, dict], highlights: list[str],
           failed: dict[str, list[str]], headlines: list[Article], picks: list[str],
           debate_article: Article | None, debate: dict | None) -> tuple[str, str, str]:
    by_id = {a.id: a for a in articles}
    head_by_id = {h.id: h for h in headlines}
    listed = [a for a in articles if a.id in items]

    if debate:
        title = f"오늘의 토론 주제: {debate['issue'].strip()}"
    elif highlights:
        title = f"기술 뉴스: {items[highlights[0]]['one_line'].strip()}"
    else:
        title = "기술 뉴스"
    summary = f"새 글 {len(listed)}개, 이슈 헤드라인 {len(picks)}개" + (", 토론 주제 1개" if debate else "")

    lines = ["---", f"title: {title.replace(chr(10), ' ')}", f"summary: {summary}",
             f"generated_at: {now.isoformat(timespec='seconds')}", "---", ""]

    if debate and debate_article:
        lines += ["## 오늘의 토론 주제", "", f"### {debate['issue'].strip()}", "",
                  f"`{debate_article.source}` {md_text(debate_article.title)}", "",
                  debate["background"].strip(), ""]
        for label, key in (("찬성", "pros"), ("반대", "cons")):
            reasons = [r.strip() for r in debate.get(key) or [] if r.strip()]
            if reasons:
                lines += [f"**{label}**", ""] + [f"- {r}" for r in reasons] + [""]
        general = [r.strip() for r in debate.get("counter_general") or [] if r.strip()]
        if general:
            lines += ["**반대편에서 나올 만한 논리** (AI가 일반적으로 정리한 내용이라 원문 근거가 아니에요)", ""]
            lines += [f"- {r}" for r in general] + [""]
        if debate.get("pt_angle", "").strip():
            lines += ["**PT로 풀어 본다면** (AI가 제안한 관점이라 원문 근거가 아니에요)", "",
                      debate["pt_angle"].strip(), ""]
        lines += [f"[원문 보기]({debate_article.link})", ""]

    if highlights:
        lines += ["## 자세히 볼 글", ""]
        for sid in highlights:
            a, item = by_id[sid], items[sid]
            lines += [f"### {md_text(a.title)}", "", tags(a, item), "", item["easy_summary"].strip(), ""]
            if item.get("why_it_matters"):
                lines += [f"> {item['why_it_matters'].strip()}", ""]
            if item.get("interview_points"):
                lines += ["**면접 포인트** (AI가 일반 개념으로 정리한 내용이라 원문 근거가 아니에요)", ""]
                for p in item["interview_points"]:
                    lines += [f"- **Q.** {p['question'].strip()}", f"  - {p['answer_hint'].strip()}"]
                lines.append("")
            lines += [f"[원문 보기]({a.link})", ""]

    if picks:
        lines += ["## 오늘의 이슈 헤드라인", "", "PT·토론 면접 주제가 될 만한 한국경제 기사예요.", ""]
        lines += [f"- [{md_text(head_by_id[h].title)}]({head_by_id[h].link})" for h in picks] + [""]

    rest = [a for a in listed if a.id not in highlights]
    if rest:
        lines += ["## 한눈에 보기", ""]
        for cat in gemini.CATEGORIES:
            group = [a for a in rest if items[a.id]["categories"][0] == cat]
            if not group:
                continue
            lines += [f"### {cat}", ""]
            for a in group:
                item = items[a.id]
                one = "원문 내용이 짧아 요약하지 않았어요" if item.get("insufficient") else item["one_line"].strip()
                lines.append(f"- [{md_text(a.title)}]({a.link}) — {md_text(one)} {tags(a, item)}")
            lines.append("")

    if failed:
        lines += ["---", "", f"- 원문과 맞는지 검사를 통과하지 못한 글 {len(failed)}개는 요약하지 않았어요."]
        lines += [f"  - [{md_text(by_id[sid].title)}]({by_id[sid].link})" for sid in failed] + [""]

    return "\n".join(lines), title, summary


def update_topics(date: str, debate: dict | None, highlights: list[str], articles: list[Article]) -> None:
    by_id = {a.id: a for a in articles}
    names = [f"토론: {md_text(debate['issue'])}"] if debate else []
    names += [md_text(by_id[sid].title) for sid in highlights]
    text = TOPICS_FILE.read_text(encoding="utf-8")
    marker = re.search(r"<!-- news-topics.*?-->\n\|[^\n]*\|\n\|[-| ]+\|\n", text)
    if not marker:
        print("::warning::TOPICS.md에서 표 위치를 찾지 못했어요", file=sys.stderr)
        return
    row = f"| {date} | {', '.join(names) or '(자세히 본 글 없음)'} |\n"
    TOPICS_FILE.write_text(text[:marker.end()] + row + text[marker.end():], encoding="utf-8")


def write_output(**values: str) -> None:
    path = os.environ.get("GITHUB_OUTPUT")
    if not path:
        return
    with open(path, "a", encoding="utf-8") as f:
        for k, v in values.items():
            f.write(f"{k}={v.replace(chr(10), ' ')}\n")


# ---------- main ----------

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", help="레포 파일 대신 이 경로에만 저장 (로컬 테스트용)")
    args = ap.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        print("GEMINI_API_KEY가 없어요.", file=sys.stderr)
        return 1
    models = gemini.candidate_models(os.environ.get("GEMINI_MODEL"))

    now = datetime.now(KST)
    date = now.strftime("%Y-%m-%d")
    since, until = window(now)
    print(f"기간: {since.isoformat(timespec='minutes')} ~ {until.isoformat(timespec='minutes')}", file=sys.stderr)

    articles, headlines = collect(since, until)
    if not articles and not headlines:
        print("새 글이 없어서 레터를 만들지 않아요.", file=sys.stderr)
        write_output(created="false")
        return 0

    items, failed = summarize(articles, api_key, models) if articles else ({}, {})
    refill_geek_highlight(articles, items, api_key, models)
    highlights = pick_highlights(articles, items)

    picks, debate_pick = pick_headlines(headlines, api_key, models)
    debate_article = next((h for h in headlines if h.id == debate_pick), None)
    debate = make_debate(debate_article, api_key, models) if debate_article else None

    if not items and not picks:
        print("::error::레터에 넣을 글이 하나도 없어요.", file=sys.stderr)
        write_output(created="false", failed="true")
        return 1

    markdown, title, summary = render(now, articles, items, highlights, failed, headlines, picks, debate_article, debate)

    if args.out:
        Path(args.out).write_text(markdown, encoding="utf-8")
        print(f"저장: {args.out} ({summary}, 검사 실패 {len(failed)}개)", file=sys.stderr)
        return 0

    LETTER_DIR.mkdir(parents=True, exist_ok=True)
    (LETTER_DIR / f"{date}.md").write_text(markdown, encoding="utf-8")
    update_topics(date, debate, highlights, articles)
    write_output(created="true", date=date, title=title, body=summary, url=f"{APP_URL}#/letters/news/{date}")
    print(f"저장: public/letters/news/{date}.md ({summary}, 검사 실패 {len(failed)}개)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
