import { initializeApp } from 'firebase/app'
import { getMessaging, getToken, isSupported, onMessage } from 'firebase/messaging'
import { firebaseConfig, isFirebaseConfigured, vapidKey } from '../firebase-config'

export type PushStatus =
  | 'not-configured' // Firebase 설정값을 아직 안 넣음
  | 'unsupported' // 이 브라우저는 웹 푸시 불가 (아이폰은 홈 화면에 추가해야 가능)
  | 'denied' // 사용자가 알림 권한을 거부함
  | 'default' // 아직 안 물어봄
  | 'granted'

export async function getPushStatus(): Promise<PushStatus> {
  if (!isFirebaseConfigured) return 'not-configured'
  if (!('Notification' in window) || !(await isSupported())) return 'unsupported'
  return Notification.permission as PushStatus
}

/** 아이폰·아이패드에서 홈 화면 앱이 아닌 사파리 탭으로 열었는지 */
export function needsHomeScreenInstall(): boolean {
  const ios = /iPhone|iPad|iPod/.test(navigator.userAgent)
  const standalone = window.matchMedia('(display-mode: standalone)').matches
  return ios && !standalone
}

let messaging: ReturnType<typeof getMessaging> | null = null
function getClientMessaging() {
  messaging ??= getMessaging(initializeApp(firebaseConfig))
  return messaging
}

/** 알림 권한을 받고 FCM 토큰을 돌려준다. 토큰은 구독 워크플로에 넣어 토픽에 등록한다. */
export async function requestPushToken(): Promise<string> {
  const permission = await Notification.requestPermission()
  if (permission !== 'granted') throw new Error('알림 권한이 허용되지 않았어요. 브라우저 설정에서 알림을 허용해 주세요.')

  const registration = await navigator.serviceWorker.ready
  const token = await getToken(getClientMessaging(), { vapidKey, serviceWorkerRegistration: registration })
  if (!token) throw new Error('알림 토큰을 받지 못했어요. 잠시 뒤 다시 시도해 주세요.')
  return token
}

/** 앱을 보고 있을 때 온 알림은 브라우저가 띄우지 않으므로 직접 처리한다. */
export function listenForeground(handler: (title: string, body: string, url?: string) => void) {
  if (!isFirebaseConfigured) return
  isSupported().then((ok) => {
    if (!ok) return
    onMessage(getClientMessaging(), (payload) => {
      handler(payload.notification?.title ?? '새 레터', payload.notification?.body ?? '', payload.data?.url)
    })
  })
}
