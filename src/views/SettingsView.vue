<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { getPushStatus, needsHomeScreenInstall, requestPushToken, type PushStatus } from '../lib/notifications'

const status = ref<PushStatus | 'loading'>('loading')
const token = ref('')
const error = ref('')
const busy = ref(false)
const copied = ref(false)
const iosBrowser = needsHomeScreenInstall()

const SUBSCRIBE_URL = 'https://github.com/1juyoung/study-letter/actions/workflows/subscribe.yml'

onMounted(async () => {
  status.value = await getPushStatus()
})

async function turnOn() {
  busy.value = true
  error.value = ''
  try {
    token.value = await requestPushToken()
    status.value = 'granted'
  } catch (e) {
    error.value = (e as Error).message
    status.value = await getPushStatus()
  } finally {
    busy.value = false
  }
}

async function copyToken() {
  await navigator.clipboard.writeText(token.value)
  copied.value = true
  setTimeout(() => (copied.value = false), 2000)
}

const schedule = [
  { time: '자정', name: '코테 풀이 분석', topic: 'algo' },
  { time: '오전 9시', name: '기술 뉴스 레터', topic: 'news' },
  { time: '오후 3시', name: 'CS 면접 레터', topic: 'cs' },
]
</script>

<template>
  <header class="pb-5">
    <h1 class="text-[1.375rem] font-bold tracking-tight">알림</h1>
  </header>

  <table class="w-full text-sm">
    <tbody>
      <tr v-for="s in schedule" :key="s.topic" class="border-b border-line">
        <td class="w-24 py-3 text-sub">{{ s.time }}</td>
        <td class="py-3">{{ s.name }}</td>
      </tr>
    </tbody>
  </table>

  <section class="mt-8">
    <p v-if="status === 'loading'" class="text-sub">확인하는 중…</p>

    <p v-else-if="status === 'not-configured'" class="rounded-lg border border-line bg-sheet p-4 text-sub">
      Firebase 설정값이 아직 없어요. <code>src/firebase-config.ts</code>를 채우면 알림을 켤 수 있어요.
    </p>

    <div v-else-if="iosBrowser" class="rounded-lg border border-line bg-sheet p-4 leading-relaxed">
      <p class="font-semibold">아이폰은 홈 화면에 추가해야 알림을 받을 수 있어요.</p>
      <p class="mt-1 text-sub">사파리 아래쪽 공유 버튼 → 홈 화면에 추가 → 홈 화면의 공부 레터 아이콘으로 다시 열어 주세요.</p>
    </div>

    <p v-else-if="status === 'unsupported'" class="rounded-lg border border-line bg-sheet p-4 text-sub">
      이 브라우저는 웹 푸시 알림을 지원하지 않아요. 크롬이나 사파리 최신 버전에서 열어 주세요.
    </p>

    <p v-else-if="status === 'denied'" class="rounded-lg border border-line bg-sheet p-4 text-sub">
      알림이 차단되어 있어요. 브라우저나 기기 설정에서 이 사이트의 알림을 허용한 뒤 다시 열어 주세요.
    </p>

    <template v-else>
      <button
        class="w-full rounded-xl bg-cs py-3.5 font-bold text-white disabled:opacity-60"
        :disabled="busy"
        @click="turnOn"
      >
        {{ busy ? '알림 켜는 중…' : status === 'granted' ? '알림 토큰 다시 받기' : '알림 켜기' }}
      </button>
      <p v-if="error" class="mt-3 text-sm text-[#b42318]">{{ error }}</p>
    </template>

    <div v-if="token" class="mt-6 rounded-lg border border-line bg-sheet p-4">
      <p class="font-semibold">마지막 단계: 이 기기를 알림 받을 곳으로 등록하기</p>
      <ol class="mt-2 list-decimal space-y-1 pl-5 text-sm leading-relaxed text-sub">
        <li>아래 토큰을 복사해요.</li>
        <li>
          <a :href="SUBSCRIBE_URL" target="_blank" rel="noopener" class="font-semibold text-cs-ink underline underline-offset-2">구독 워크플로</a>
          에서 Run workflow를 누르고 토큰을 붙여 넣어 실행해요.
        </li>
      </ol>
      <p class="mt-3 max-h-24 overflow-y-auto rounded-md bg-paper p-3 font-mono text-xs break-all">{{ token }}</p>
      <button class="mt-3 rounded-md border border-line px-3.5 py-2 text-sm" @click="copyToken">
        {{ copied ? '복사했어요' : '토큰 복사' }}
      </button>
    </div>
  </section>
</template>
