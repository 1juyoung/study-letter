"""CS 면접 레터를 만든다.

흐름
1. 주제 고르기: 오늘 요일의 분야에서 아직 안 보낸 첫 주제. 그 분야가 끝났으면 남은 주제가 가장 많은 분야에서.
   전부 끝났으면 복습 레터(지난 객관식 모음).
2. 근거 자료 가져오기 (gyoogle, Esoolgnah, prepare_frontend_interview, MDN)
3. 검수: 자료끼리·공식 문서와 다른 설명, 오래된 내용, 틀린 설명을 찾아 메모로 남김 (자동으로 고치지 않음)
4. 레터 생성(JSON) → 원문 대조 검사 → 실패하면 1번 재생성
5. 마크다운 저장 → README 진도표 갱신 → 객관식 모음(quiz-bank.json)에 추가 → 알림용 출력

로컬 테스트 (레포 파일은 건드리지 않고 결과만 out 파일로 저장):
    GEMINI_API_KEY=... python scripts/cs/generate.py --out /tmp/cs-test.md
    특정 주제로 테스트: --topic "클로저"
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "news"))

import gemini  # noqa: E402  (scripts/news/gemini.py)
from sources import fetch  # noqa: E402
from verify import check_text  # noqa: E402  (scripts/news/verify.py)

KST = timezone(timedelta(hours=9))
ROOT = HERE.parents[1]
LETTER_DIR = ROOT / "public" / "letters" / "cs"
README = ROOT / "README.md"
QUIZ_BANK = HERE / "quiz-bank.json"
CURRICULUM = yaml.safe_load((HERE / "curriculum.yml").read_text(encoding="utf-8"))
PROMPT_REVIEW = (HERE / "prompt_review.md").read_text(encoding="utf-8")
PROMPT_LETTER = (HERE / "prompt_letter.md").read_text(encoding="utf-8")
APP_URL = "https://1juyoung.github.io/study-letter/"
WEEKDAYS = "월화수목금토일"
REVIEW_COUNT = 5

_S = {"type": "STRING"}
REVIEW_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "notes": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {"source_id": _S, "problem": _S, "correction": _S, "basis": _S},
                "required": ["source_id", "problem", "correction", "basis"],
            },
        },
    },
    "required": ["notes"],
}
LETTER_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "concept": _S,
        "key_points": {"type": "ARRAY", "items": _S},
        "interview_question": _S,
        "model_answer": _S,
        "follow_ups": {
            "type": "ARRAY",
            "items": {"type": "OBJECT", "properties": {"question": _S, "answer_hint": _S},
                      "required": ["question", "answer_hint"]},
        },
        "quiz": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {"question": _S, "code": _S, "options": {"type": "ARRAY", "items": _S},
                               "answer_index": {"type": "INTEGER"}, "explanation": _S},
                "required": ["question", "code", "options", "answer_index", "explanation"],
            },
        },
    },
    "required": ["concept", "key_points", "interview_question", "model_answer", "follow_ups", "quiz"],
}


# ---------- 주제 고르기 ----------

def sent_topics() -> set[str]:
    done = set()
    for f in LETTER_DIR.glob("????-??-??.md"):
        m = re.search(r"^topic:\s*(.+)$", f.read_text(encoding="utf-8"), re.M)
        if m:
            done.add(m.group(1).strip())
    return done


def pick_topic(now: datetime, forced: str | None = None) -> tuple[str, dict] | None:
    """(분야 키, 주제) 또는 None(전부 끝남 → 복습)"""
    areas = CURRICULUM["areas"]
    if forced:
        for key, area in areas.items():
            for t in area["topics"]:
                if t["title"] == forced:
                    return key, t
        raise SystemExit(f"커리큘럼에 없는 주제예요: {forced}")

    done = sent_topics()
    remaining = {k: [t for t in a["topics"] if t["title"] not in done] for k, a in areas.items()}
    today_area = CURRICULUM["schedule"][WEEKDAYS[now.weekday()]]
    if remaining[today_area]:
        return today_area, remaining[today_area][0]
    # 오늘 분야가 끝났으면 남은 주제가 가장 많은 분야에서 (같으면 커리큘럼 순서)
    key = max(remaining, key=lambda k: len(remaining[k]))
    if remaining[key]:
        return key, remaining[key][0]
    return None


# ---------- 생성 ----------

def source_block(docs: list[dict]) -> str:
    parts = []
    for i, d in enumerate(docs, 1):
        kind = "공식 문서" if d["official"] else "개인 정리 자료"
        parts.append(f"[S{i}] {d['label']} ({kind})\n{d['text']}")
    return "\n\n".join(parts)


def review(topic: str, docs: list[dict], api_key: str, models: list[str]) -> list[dict]:
    prompt = f"{PROMPT_REVIEW}\n\n[주제] {topic}\n\n{source_block(docs)}"
    notes = gemini.call(prompt, REVIEW_SCHEMA, api_key, models).get("notes", [])
    valid = {f"S{i}" for i in range(1, len(docs) + 1)}
    notes = [n for n in notes if n.get("source_id") in valid and n.get("problem", "").strip()]
    print(f"  검수 메모 {len(notes)}개", file=sys.stderr)
    return notes


def check_letter(letter: dict, source_text: str) -> list[str]:
    errors: list[str] = []
    strict = " ".join([letter.get("concept", ""), " ".join(letter.get("key_points") or []),
                       letter.get("model_answer", "")])
    loose = " ".join([letter.get("interview_question", "")]
                     + [f"{f.get('question', '')} {f.get('answer_hint', '')}" for f in letter.get("follow_ups") or []])
    errors += check_text(strict, loose, source_text)
    for i, q in enumerate(letter.get("quiz") or [], 1):
        opts = q.get("options") or []
        if len(opts) != 4 or len(set(opts)) != 4:
            errors.append(f"객관식 {i}번은 서로 다른 보기 4개가 있어야 해요")
        if not 0 <= int(q.get("answer_index", -1)) < 4:
            errors.append(f"객관식 {i}번 answer_index는 0~3이어야 해요")
        errors += [f"객관식 {i}번: {e}" for e in check_text(q.get("explanation", ""), q.get("question", ""), source_text)]
    if not (letter.get("quiz") and letter.get("follow_ups") and letter.get("concept")):
        errors.append("concept, follow_ups, quiz를 모두 채워야 해요")
    return errors


def write_letter(topic: str, docs: list[dict], notes: list[dict], api_key: str, models: list[str]) -> dict:
    source_text = "\n".join(d["text"] for d in docs) + "\n" + topic
    notes_text = "\n".join(f"- [{n['source_id']}] {n['problem']} → {n['correction']} (근거: {n['basis']})" for n in notes) or "(없음)"
    prompt = f"{PROMPT_LETTER}\n\n[주제] {topic}\n\n[검수 메모]\n{notes_text}\n\n{source_block(docs)}"
    feedback: list[str] = []
    for attempt in range(2):
        full = prompt + ("\n\n[이전 답변에서 어긴 규칙 — 이번에는 반드시 고친다]\n- " + "\n- ".join(feedback) if feedback else "")
        letter = gemini.call(full, LETTER_SCHEMA, api_key, models)
        feedback = check_letter(letter, source_text)
        if not feedback:
            return letter
        print(f"  검사 실패({attempt + 1}회): {' / '.join(feedback)}", file=sys.stderr)
    raise RuntimeError("레터가 원문 대조 검사를 두 번 통과하지 못했어요: " + " / ".join(feedback))


# ---------- 마크다운 ----------

def render_quiz(quiz: list[dict]) -> list[str]:
    lines = []
    for i, q in enumerate(quiz, 1):
        lines += [f"**{i}. {q['question'].strip()}**", ""]
        if (q.get("code") or "").strip():
            lines += ["```", q["code"].strip(), "```", ""]
        lines += [f"{'①②③④'[j]} {opt.strip()}" + "  " for j, opt in enumerate(q["options"])]
        lines += ["", f"> 정답: {'①②③④'[q['answer_index']]}. {q['explanation'].strip()}", ""]
    return lines


def render(now: datetime, area_name: str, topic: str, letter: dict, notes: list[dict], docs: list[dict]) -> tuple[str, str, str]:
    title = f"{area_name}: {topic}"
    summary = f"꼬리 질문 {len(letter['follow_ups'])}개, 객관식 {len(letter['quiz'])}문제" + (f", 검수 메모 {len(notes)}개" if notes else "")
    lines = ["---", f"title: {title}", f"summary: {summary}", f"topic: {topic}", f"area: {area_name}",
             f"generated_at: {now.isoformat(timespec='seconds')}", "---", "",
             "## 개념", "", letter["concept"].strip(), "",
             "**핵심 정리**", ""] + [f"- {p.strip()}" for p in letter["key_points"]] + [""]
    lines += ["## 면접 질문", "", f"**Q.** {letter['interview_question'].strip()}", "",
              "**모범 답변**", "", letter["model_answer"].strip(), ""]
    lines += ["## 꼬리 질문", ""]
    for f in letter["follow_ups"]:
        lines += [f"- **Q.** {f['question'].strip()}", f"  - {f['answer_hint'].strip()}"]
    lines += ["", "## 필기 대비 확인 문제", ""] + render_quiz(letter["quiz"])
    if notes:
        lines += ["## 검수 메모", "", "근거 자료에서 AI가 틀렸거나 오래됐다고 본 부분이에요. AI 판단도 틀릴 수 있으니 공식 문서로 한 번 더 확인해 보세요.", ""]
        for n in notes:
            label = docs[int(n["source_id"][1:]) - 1]["label"]
            lines.append(f"- **{label}**: {n['problem'].strip()} → {n['correction'].strip()} (근거: {n['basis'].strip()})")
        lines.append("")
    lines += ["## 근거 자료", ""] + [f"- [{d['label']}]({d['url']})" for d in docs] + [""]
    return "\n".join(lines), title, summary


def render_review(now: datetime, bank: list[dict]) -> tuple[str, str, str]:
    picks = random.sample(bank, min(REVIEW_COUNT, len(bank)))
    title, summary = "CS 복습: 지난 객관식 모음", f"객관식 {len(picks)}문제"
    lines = ["---", f"title: {title}", f"summary: {summary}", "topic: (복습)",
             f"generated_at: {now.isoformat(timespec='seconds')}", "---", "", "## 복습 문제", ""]
    for i, q in enumerate(picks, 1):
        lines += [f"`{q['topic']}`", "", f"**{i}. {q['question'].strip()}**", ""]
        if (q.get("code") or "").strip():
            lines += ["```", q["code"].strip(), "```", ""]
        lines += [f"{'①②③④'[j]} {o.strip()}  " for j, o in enumerate(q["options"])]
        lines += ["", f"> 정답: {'①②③④'[q['answer_index']]}. {q['explanation'].strip()}", ""]
    return "\n".join(lines), title, summary


def update_readme(date: str, area_name: str, topic: str) -> None:
    text = README.read_text(encoding="utf-8")
    marker = re.search(r"<!-- cs-topics.*?-->\n\|[^\n]*\|\n\|[-| ]+\|\n", text)
    if not marker:
        print("::warning::README에서 CS 표 위치를 찾지 못했어요", file=sys.stderr)
        return
    row = f"| {date} | {area_name} | {topic.replace('|', '/')} |\n"
    README.write_text(text[:marker.end()] + row + text[marker.end():], encoding="utf-8")


def write_output(**values: str) -> None:
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a", encoding="utf-8") as f:
            for k, v in values.items():
                f.write(f"{k}={v.replace(chr(10), ' ')}\n")


# ---------- main ----------

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", help="레포 파일 대신 이 경로에만 저장 (로컬 테스트용)")
    ap.add_argument("--topic", help="이 주제로 만들기 (테스트용)")
    ap.add_argument("--skip-if-exists", action="store_true", help="오늘 레터가 이미 있으면 아무것도 하지 않음 (재시도 예약용)")
    args = ap.parse_args()

    now = datetime.now(KST)
    date = now.strftime("%Y-%m-%d")
    if args.skip_if_exists and (LETTER_DIR / f"{date}.md").exists():
        print(f"오늘({date}) 레터가 이미 있어서 건너뛰어요.", file=sys.stderr)
        write_output(created="false")
        return 0

    picked = pick_topic(now, args.topic)
    bank = json.loads(QUIZ_BANK.read_text(encoding="utf-8")) if QUIZ_BANK.exists() else []

    if picked is None:  # 커리큘럼을 다 돌았으면 복습
        if not bank:
            print("복습할 문제가 없어요.", file=sys.stderr)
            return 1
        markdown, title, summary = render_review(now, bank)
        area_name = topic = None
    else:
        api_key = os.environ.get("GEMINI_API_KEY", "")
        if not api_key:
            print("GEMINI_API_KEY가 없어요.", file=sys.stderr)
            return 1
        models = gemini.candidate_models(os.environ.get("GEMINI_MODEL"))
        area_key, t = picked
        area_name, topic = CURRICULUM["areas"][area_key]["name"], t["title"]
        print(f"오늘 주제: [{area_name}] {topic}", file=sys.stderr)

        docs = [d for d in (fetch(s) for s in t["sources"]) if d and len(d["text"]) > 200]
        if not docs:
            print("::error::근거 자료를 하나도 가져오지 못했어요.", file=sys.stderr)
            return 1
        notes = review(topic, docs, api_key, models)
        letter = write_letter(topic, docs, notes, api_key, models)
        markdown, title, summary = render(now, area_name, topic, letter, notes, docs)

    if args.out:
        Path(args.out).write_text(markdown, encoding="utf-8")
        print(f"저장: {args.out} ({summary})", file=sys.stderr)
        return 0

    LETTER_DIR.mkdir(parents=True, exist_ok=True)
    (LETTER_DIR / f"{date}.md").write_text(markdown, encoding="utf-8")
    if picked is not None:
        update_readme(date, area_name, topic)
        bank += [{"date": date, "topic": topic, **q} for q in letter["quiz"]]
        QUIZ_BANK.write_text(json.dumps(bank, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    write_output(created="true", date=date, title=title, body=summary, url=f"{APP_URL}#/letters/cs/{date}")
    print(f"저장: public/letters/cs/{date}.md ({summary})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
