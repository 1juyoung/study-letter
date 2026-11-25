"""FCM 토큰을 토픽에 등록한다. GitHub Actions의 Subscribe device 워크플로에서 실행.

firebase-admin의 subscribe_to_topic은 지원 종료 예정인 레거시 Instance ID 서비스를 써서
새 프로젝트에서 PERMISSION_DENIED가 나므로, FCM 토픽 구독 서버 API(v1)를 직접 호출한다.
POST https://fcm.googleapis.com/v1/projects/{project}/registrations/{token}/topicSubscriptions?topic_name={topic}

환경 변수
    FIREBASE_SERVICE_ACCOUNT  서비스 계정 키 JSON 전체
    FCM_TOKEN                 앱에서 받은 토큰
    FCM_TOPICS                쉼표로 구분한 토픽 (기본값: algo,news,cs)
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

from google.auth.transport.requests import Request
from google.oauth2 import service_account

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

    info = json.loads(raw)
    creds = service_account.Credentials.from_service_account_info(
        info, scopes=["https://www.googleapis.com/auth/firebase.messaging"])
    creds.refresh(Request())

    failed = False
    for topic in topics:
        url = (
            f"https://fcm.googleapis.com/v1/projects/{info['project_id']}"
            f"/registrations/{urllib.parse.quote(token, safe='')}/topicSubscriptions"
            f"?topic_name={urllib.parse.quote(topic)}"
        )
        req = urllib.request.Request(
            url,
            data=b"{}",
            headers={"Authorization": f"Bearer {creds.token}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30):
                print(f"{topic}: 구독 완료")
        except urllib.error.HTTPError as e:
            if e.code == 409:  # 이미 구독된 상태
                print(f"{topic}: 이미 구독돼 있어요")
                continue
            failed = True
            print(f"::error::{topic}: 실패 (HTTP {e.code}) {e.read().decode(errors='replace')[:500]}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
