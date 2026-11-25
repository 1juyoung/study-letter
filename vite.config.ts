import tailwindcss from '@tailwindcss/vite'
import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'
import { VitePWA } from 'vite-plugin-pwa'

// GitHub Pages 주소: https://1juyoung.github.io/study-letter/
const base = '/study-letter/'

export default defineConfig({
  base,
  plugins: [
    vue(),
    tailwindcss(),
    VitePWA({
      // 캐시(workbox)와 FCM 백그라운드 알림을 서비스 워커 하나에서 처리하려고 직접 작성한 sw.ts를 쓴다
      strategies: 'injectManifest',
      srcDir: 'src',
      filename: 'sw.ts',
      registerType: 'autoUpdate',
      injectRegister: false,
      injectManifest: {
        // 앱 화면에 필요한 파일만 미리 캐시한다.
        // mermaid 도식 관련 청크(수 MB)는 도식이 있는 레터를 열 때만 받고,
        // 레터 마크다운은 매일 바뀌므로 캐시하지 않는다.
        globPatterns: [
          'index.html',
          '*.png',
          'assets/*.css',
          'assets/{index,letters,TodayView,ArchiveView,LetterView,SettingsView,workbox-window}*.js',
        ],
      },
      manifest: {
        name: '공부 레터',
        short_name: '공부 레터',
        description: '매일 오는 기술 뉴스·CS 면접 레터',
        lang: 'ko',
        start_url: base,
        scope: base,
        display: 'standalone',
        background_color: '#FAFAFB',
        theme_color: '#FAFAFB',
        icons: [
          { src: 'icon-192.png', sizes: '192x192', type: 'image/png' },
          { src: 'icon-512.png', sizes: '512x512', type: 'image/png' },
          { src: 'icon-512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
        ],
      },
    }),
  ],
})
