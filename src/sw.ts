/// <reference lib="webworker" />
import { initializeApp } from 'firebase/app'
import { getMessaging, onBackgroundMessage } from 'firebase/messaging/sw'
import { cleanupOutdatedCaches, precacheAndRoute } from 'workbox-precaching'
import { firebaseConfig, isFirebaseConfigured } from './firebase-config'

declare const self: ServiceWorkerGlobalScope

precacheAndRoute(self.__WB_MANIFEST)
cleanupOutdatedCaches()

self.addEventListener('message', (event) => {
  if (event.data?.type === 'SKIP_WAITING') self.skipWaiting()
})

if (isFirebaseConfigured) {
  const messaging = getMessaging(initializeApp(firebaseConfig))
  // notification 필드가 있는 메시지는 FCM SDK가 알림을 직접 띄우고,
  // 알림을 누르면 webpush.fcm_options.link 주소를 연다. 여기서는 기록만 남긴다.
  onBackgroundMessage(messaging, (payload) => {
    console.log('[sw] background message', payload.data)
  })
}
