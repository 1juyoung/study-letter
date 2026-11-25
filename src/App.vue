<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink, RouterView, useRouter } from 'vue-router'
import { listenForeground } from './lib/notifications'

const tabs = [
  { to: '/', label: '오늘' },
  { to: '/letters', label: '지난 레터' },
  { to: '/settings', label: '알림' },
]

// 앱을 보고 있을 때 온 알림은 화면 위에 띠로 보여 준다
const toast = ref<{ title: string; body: string; url?: string } | null>(null)
const router = useRouter()
listenForeground((title, body, url) => {
  toast.value = { title, body, url }
})

function openToast() {
  const url = toast.value?.url
  toast.value = null
  if (!url) return
  const hash = url.split('#')[1]
  if (url.includes('/study-letter/') && hash) router.push(hash)
  else window.open(url, '_blank', 'noopener')
}
</script>

<template>
  <div class="mx-auto flex min-h-dvh max-w-2xl flex-col px-4 pt-[max(1.25rem,env(safe-area-inset-top))]">
    <div
      v-if="toast"
      class="fixed inset-x-4 top-[max(1rem,env(safe-area-inset-top))] z-20 mx-auto flex max-w-xl items-start gap-3 rounded-lg border border-line bg-sheet p-4 shadow-[0_6px_24px_rgba(30,39,64,0.12)]"
      role="status"
    >
      <button class="flex-1 text-left" @click="openToast">
        <p class="font-semibold">{{ toast.title }}</p>
        <p class="mt-0.5 text-sm text-sub">{{ toast.body }}</p>
      </button>
      <button class="text-sm text-sub" aria-label="알림 닫기" @click="toast = null">닫기</button>
    </div>

    <main class="flex-1 pb-24">
      <RouterView />
    </main>

    <nav
      class="fixed inset-x-0 bottom-0 z-10 border-t border-line bg-paper/95 pb-[env(safe-area-inset-bottom)] backdrop-blur"
      aria-label="주요 메뉴"
    >
      <ul class="mx-auto flex max-w-2xl">
        <li v-for="tab in tabs" :key="tab.to" class="flex-1">
          <RouterLink
            :to="tab.to"
            class="block py-3 text-center text-sm text-sub"
            exact-active-class="!text-cs-ink font-bold"
            :class="tab.to === '/letters' && $route.name === 'letter' ? '!text-cs-ink font-bold' : ''"
          >
            {{ tab.label }}
          </RouterLink>
        </li>
      </ul>
    </nav>
  </div>
</template>
