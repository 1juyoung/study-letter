// Firebase 웹 앱 설정값. 브라우저에 그대로 내려가는 공개 값이라 코드에 둬도 된다.
// (비밀키인 서비스 계정 JSON은 GitHub Actions 시크릿에만 둔다)
// TODO: Firebase 콘솔 → 프로젝트 설정 → 일반 → 웹 앱의 firebaseConfig 값으로 채우기
export const firebaseConfig = {
  apiKey: '',
  authDomain: '',
  projectId: '',
  storageBucket: '',
  messagingSenderId: '',
  appId: '',
}

// TODO: 프로젝트 설정 → 클라우드 메시징 → 웹 푸시 인증서의 공개 키
export const vapidKey = ''

export const isFirebaseConfigured = Boolean(firebaseConfig.apiKey && firebaseConfig.projectId && vapidKey)
