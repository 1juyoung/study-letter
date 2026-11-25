import { createRouter, createWebHashHistory } from 'vue-router'

// GitHub Pages는 없는 경로를 index.html로 돌려주지 않으므로 해시 주소(#/...)를 쓴다.
// 알림 링크 예: https://1juyoung.github.io/study-letter/#/letters/news/2026-11-26
export const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/', name: 'today', component: () => import('./views/TodayView.vue') },
    { path: '/letters', name: 'archive', component: () => import('./views/ArchiveView.vue') },
    {
      path: '/letters/:type(news|cs)/:date(\\d{4}-\\d{2}-\\d{2})',
      name: 'letter',
      component: () => import('./views/LetterView.vue'),
      props: true,
    },
    { path: '/settings', name: 'settings', component: () => import('./views/SettingsView.vue') },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
  scrollBehavior: () => ({ top: 0 }),
})
