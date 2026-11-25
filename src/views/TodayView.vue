<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { fetchLetterIndex, formatDate, LETTER_LABEL, todayKST, type LetterMeta, type LetterType } from '../lib/letters'

const today = todayKST()
const letters = ref<LetterMeta[]>([])
const error = ref('')
const loading = ref(true)

onMounted(async () => {
  try {
    letters.value = await fetchLetterIndex()
  } catch (e) {
    error.value = (e as Error).message
  } finally {
    loading.value = false
  }
})

const slots: { type: LetterType; time: string; color: string; pill: string }[] = [
  { type: 'news', time: '오전 9시', color: 'bg-news', pill: 'bg-news-soft text-news-ink' },
  { type: 'cs', time: '오후 3시', color: 'bg-cs', pill: 'bg-cs-soft text-cs-ink' },
]

const todays = computed(() =>
  Object.fromEntries(slots.map((s) => [s.type, letters.value.find((l) => l.type === s.type && l.date === today)])),
)
</script>

<template>
  <header class="pb-6">
    <p class="text-sm text-sub">오늘의 레터</p>
    <h1 class="mt-0.5 text-[1.375rem] font-bold tracking-tight">{{ formatDate(today) }}</h1>
  </header>

  <p v-if="error" class="rounded-lg border border-line bg-sheet p-4 text-sub">
    {{ error }} 인터넷 연결을 확인하고 다시 열어 주세요.
  </p>

  <ul v-else class="space-y-3">
    <li v-for="slot in slots" :key="slot.type">
      <RouterLink
        v-if="todays[slot.type]"
        :to="`/letters/${slot.type}/${today}`"
        class="relative block overflow-hidden rounded-xl border border-line bg-sheet py-4 pr-4 pl-5 transition-colors hover:border-sub"
      >
        <span class="absolute inset-y-0 left-0 w-1.5" :class="slot.color" aria-hidden="true" />
        <span class="block min-w-0">
          <span class="inline-block rounded-full px-2.5 py-0.5 text-xs font-semibold" :class="slot.pill">{{ LETTER_LABEL[slot.type] }}</span>
          <span class="mt-2 block text-base leading-snug font-bold">{{ todays[slot.type]!.title }}</span>
          <span v-if="todays[slot.type]!.summary" class="mt-1 block text-sm leading-relaxed text-sub">
            {{ todays[slot.type]!.summary }}
          </span>
        </span>
      </RouterLink>

      <div v-else class="rounded-xl border border-dashed border-line py-4 pr-4 pl-5">
        <span>
          <span class="inline-block rounded-full px-2.5 py-0.5 text-xs font-semibold" :class="slot.pill">{{ LETTER_LABEL[slot.type] }}</span>
          <span class="mt-2 block text-sm text-sub">
            {{ loading ? '불러오는 중…' : `${slot.time}에 도착해요.` }}
          </span>
        </span>
      </div>
    </li>
  </ul>

  <a
    href="https://1juyoung.github.io/algorithm/"
    target="_blank"
    rel="noopener"
    class="mt-6 block rounded-xl border border-line bg-sheet px-5 py-4 text-sm"
  >
    <span class="font-bold">코테 풀이 분석</span>
    <span class="mt-0.5 block text-sub">어제 푼 문제 분석은 매일 자정에 알고리즘 블로그에 올라와요.</span>
  </a>
</template>
