// Firebase 웹 앱 설정값. 브라우저에 그대로 내려가는 공개 값이라 코드에 둬도 된다.
// (비밀키인 서비스 계정 JSON은 GitHub Actions 시크릿에만 둔다)
export const firebaseConfig = {
  apiKey: 'AIzaSyD8tGnxv5I1pniA6luE-tSK6MF_oBWUm3Y',
  authDomain: 'study-letter.firebaseapp.com',
  projectId: 'study-letter',
  storageBucket: 'study-letter.firebasestorage.app',
  messagingSenderId: '496761617118',
  appId: '1:496761617118:web:bc12b59a89e6c66a69e04f',
}

// 웹 푸시 인증서(VAPID) 공개 키
export const vapidKey = 'BJDhvpijMBmQa7ngsU6_giy6OFRRuMl6cF1jNm_ADgFTg7nHpIzAypQ-9nD_SAX8OwlPU9xuYQ_R7OFJUG1IGDw'

export const isFirebaseConfigured = Boolean(firebaseConfig.apiKey && firebaseConfig.projectId && vapidKey)
