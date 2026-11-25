# 공부 레터

매일 정해진 시간에 오는 공부 레터를 모아 보는 PWA입니다.

| 시간 (KST) | 레터 | 알림 토픽 |
|---|---|---|
| 00:00 | 코테 풀이 분석 ([algorithm](https://github.com/1juyoung/algorithm) 레포, [블로그](https://1juyoung.github.io/algorithm/)) | `algo` |
| 09:00 | 기술 뉴스 레터 | `news` |
| 15:00 | CS 면접 레터 | `cs` |

앱 주소: https://1juyoung.github.io/study-letter/

## 구조

- Vue 3 + TypeScript + Tailwind CSS v4, vite-plugin-pwa
- 레터는 GitHub Actions가 마크다운으로 만들어 `public/letters/{news,cs}/YYYY-MM-DD.md`에 커밋하고, 빌드 때 `index.json` 목록을 만듭니다. DB는 쓰지 않습니다.
- 알림은 Firebase Cloud Messaging 토픽으로 보냅니다. 웹은 앱 안에서 토픽을 직접 구독할 수 없어서, 앱의 알림 화면에서 받은 토큰을 `Subscribe device` 워크플로에 넣어 서버 쪽에서 토픽에 등록합니다.
- 레터 마크다운은 표, 코드 하이라이트, Mermaid 도식을 지원합니다. HTML은 렌더링하지 않습니다.

## 처음 설정

1. `src/firebase-config.ts`에 Firebase 웹 앱 설정값과 웹 푸시 공개 키(VAPID)를 넣습니다.
2. 레포 Settings → Secrets and variables → Actions에 `FIREBASE_SERVICE_ACCOUNT`(서비스 계정 키 JSON 전체)를 넣습니다.
3. Settings → Pages → Source를 **GitHub Actions**로 바꿉니다.
4. 앱의 알림 화면에서 알림을 켜고, 나온 토큰으로 Actions → `Subscribe device` → Run workflow를 실행합니다.
   - 아이폰은 사파리에서 홈 화면에 추가한 앱으로 열어야 알림을 받을 수 있습니다.

## 개발

```bash
npm ci
npm run dev
```

레터 파일 앞부분에는 목록에 쓸 정보를 적습니다.

```markdown
---
title: HTTP와 HTTPS는 무엇이 다를까
summary: 주고받는 내용을 암호화하는지가 핵심 차이예요.
---
```
