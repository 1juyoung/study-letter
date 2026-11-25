"""FCM 토큰을 토픽에 등록(또는 해제)한다. GitHub Actions의 Subscribe device 워크플로에서 실행.

환경 변수
    FIREBASE_SERVICE_ACCOUNT  서비스 계정 키 JSON 전체
    FCM_TOKEN                 앱에서 받은 토큰
    FCM_TOPICS                쉼표로 구분한 토픽 (기본값: algo,news,cs)
    FCM_ACTION                subscribe | unsubscribe
"""

from __future__ import annotations

import json
import os
import sys

import firebase_admin
from firebase_admin import credentials, messaging

ALLOWED_TOPICS = {"algo", "news", "cs"}


def main() -> int:
    raw = os.environ.get("FIREBASE_SERVICE_ACCOUNT", "").strip()
    token = os.environ.get("FCM_TOKEN", "").strip()
    if not raw:
        print("::error::FIREBASE_SERVICE_ACCOUNT 시크릿이 없어요.")
        return 1
    if not token:
        print("::error::토큰이 비어 있어요.")
        return 1
    print(f"::add-mask::{token}")  # 로그에 토큰이 그대로 찍히지 않게

    topics = [t.strip() for t in os.environ.get("FCM_TOPICS", "algo,news,cs").split(",") if t.strip()]
    unknown = [t for t in topics if t not in ALLOWED_TOPICS]
    if unknown:
        print(f"::error::모르는 토픽이에요: {', '.join(unknown)} (가능: {', '.join(sorted(ALLOWED_TOPICS))})")
        return 1

    action = os.environ.get("FCM_ACTION", "subscribe").strip()
    if action not in ("subscribe", "unsubscribe"):
        print("::error::action은 subscribe 또는 unsubscribe만 가능해요.")
        return 1

    firebase_admin.initialize_app(credentials.Certificate(json.loads(raw)))
    fn = messaging.subscribe_to_topic if action == "subscribe" else messaging.unsubscribe_from_topic

    failed = False
    for topic in topics:
        res = fn([token], topic)
        if res.failure_count:
            failed = True
            print(f"::error::{topic}: 실패 ({res.errors[0].reason})")
        else:
            print(f"{topic}: {'구독' if action == 'subscribe' else '해제'} 완료")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
