"""Gemini를 JSON 형식으로 호출한다. 모델이 바쁘면(429/503) 다음 무료 모델로 넘어간다."""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request

API_BASE = "https://generativelanguage.googleapis.com/v1beta"
# algorithm 레포의 코테 분석과 같은 무료 모델 목록. 레포 Variables의 GEMINI_MODEL이 있으면 맨 앞에 둔다.
FREE_MODELS = ["gemini-3.6-flash", "gemini-3.8-flash", "gemini-3.5-flash-lite", "gemini-3.1-flash-lite"]

CATEGORIES = ["프론트엔드", "백엔드", "AI", "인프라·보안", "CS 이론", "금융·핀테크", "커리어·기타"]

_STR = {"type": "STRING"}
_STR_LIST = {"type": "ARRAY", "items": _STR}

# 긱뉴스·블로그 요약
ITEMS_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "items": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "source_id": _STR,
                    "categories": {"type": "ARRAY", "items": {"type": "STRING", "enum": CATEGORIES}},
                    "one_line": _STR,
                    "insufficient": {"type": "BOOLEAN"},
                    "highlight": {"type": "BOOLEAN"},
                    "easy_summary": _STR,
                    "why_it_matters": _STR,
                    "interview_points": {
                        "type": "ARRAY",
                        "items": {
                            "type": "OBJECT",
                            "properties": {"question": _STR, "answer_hint": _STR},
                            "required": ["question", "answer_hint"],
                        },
                    },
                },
                "required": ["source_id", "categories", "one_line", "insufficient", "highlight",
                             "easy_summary", "why_it_matters", "interview_points"],
            },
        },
    },
    "required": ["items"],
}

# 한국경제 제목 고르기
HEADLINES_SCHEMA = {
    "type": "OBJECT",
    "properties": {"picks": _STR_LIST, "debate_pick": _STR},
    "required": ["picks", "debate_pick"],
}

# 오늘의 토론 주제
DEBATE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "insufficient": {"type": "BOOLEAN"},
        "background": _STR,
        "issue": _STR,
        "pros": _STR_LIST,
        "cons": _STR_LIST,
        "pt_angle": _STR,
        "counter_general": _STR_LIST,
    },
    "required": ["insufficient", "background", "issue", "pros", "cons", "pt_angle", "counter_general"],
}


def candidate_models(preferred: str | None) -> list[str]:
    if not preferred:
        return list(FREE_MODELS)
    return [preferred] + [m for m in FREE_MODELS if m != preferred]


def call(prompt: str, schema: dict, api_key: str, models: list[str]) -> dict:
    errors = []
    for model in list(models):
        try:
            result = _call_one(prompt, schema, api_key, model)
            if model != models[0]:  # 성공한 모델을 다음 호출부터 먼저 쓴다
                models.remove(model)
                models.insert(0, model)
            return result
        except RuntimeError as e:
            errors.append(f"{model}: {e}")
            print(f"  {model} 실패, 다음 모델 시도 → {str(e)[:120]}", file=sys.stderr)
    raise RuntimeError(" / ".join(errors)[:600])


def _call_one(prompt: str, schema: dict, api_key: str, model: str, retries: int = 2) -> dict:
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "responseMimeType": "application/json",
            "responseSchema": schema,
        },
    }
    data = json.dumps(payload).encode()
    last_error = None
    for attempt in range(retries):
        req = urllib.request.Request(
            f"{API_BASE}/models/{model}:generateContent", data=data, method="POST",
            headers={"Content-Type": "application/json", "x-goog-api-key": api_key})
        try:
            with urllib.request.urlopen(req, timeout=180) as res:
                body = json.loads(res.read())
            return json.loads(body["candidates"][0]["content"]["parts"][0]["text"])
        except urllib.error.HTTPError as e:
            last_error = f"HTTP {e.code}: {e.read()[:300]!r}"
            if e.code not in (429, 500, 502, 503, 504):
                break
        except (KeyError, IndexError, json.JSONDecodeError, urllib.error.URLError, TimeoutError) as e:
            last_error = repr(e)
        if attempt < retries - 1:
            time.sleep(10)
    raise RuntimeError(f"Gemini 호출 실패: {last_error}")
