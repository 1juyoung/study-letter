<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { fetchLetterIndex, formatDate, LETTER_LABEL, type LetterMeta, type LetterType } from '../lib/letters'

const letters = ref<LetterMeta[]>([])
const error = ref('')
const loading = ref(true)
const filter = ref<LetterType | 'all'>('all')

onMounted(async () => {
  try {
    letters.value = await fetchLetterIndex()
  } catch (e) {
    error.value = (e as Error).message
  } finally {
    loading.value = false
  }
})

const filters: { value: LetterType | 'all'; label: string }[] = [
  { value: 'all', label: '전체' },
  { value: 'news', label: '기술 뉴스' },
  { value: 'cs', label: 'CS 면접' },
]

// 날짜별로 묶어서 최신순
const groups = computed(() => {
  const map = new Map<string, LetterMeta[]>()
  for (const l of letters.value) {
    if (filter.value !== 'all' && l.type !== filter.value) continue
    map.set(l.date, [...(map.get(l.date) ?? []), l])
  }
  return [...map.entries()]
})
</script>

<template>
  <header class="pb-5">
    <h1 class="text-[1.375rem] font-bold tracking-tight">지난 레터</h1>
  </header>

  <div class="mb-4 flex gap-2" role="radiogroup" aria-label="레터 종류">
    <button
      v-for="f in filters"
      :key="f.value"
      role="radio"
      :aria-checked="filter === f.value"
      class="rounded-full border px-3 py-1 text-sm"
      :class="filter === f.value ? 'border-cs bg-cs font-semibold text-white' : 'border-line text-sub'"
      @click="filter = f.value"
    >
      {{ f.label }}
    </button>
  </div>

  <p v-if="error" class="text-sm text-sub">{{ error }}</p>
  <p v-else-if="loading" class="text-sm text-sub">불러오는 중…</p>
  <p v-else-if="groups.length === 0" class="text-sm text-sub">아직 받은 레터가 없어요. 첫 레터는 내일 오전 9시에 와요.</p>

  <section v-for="[date, items] in groups" :key="date" class="border-t border-line py-4">
    <h2 class="text-xs text-sub">{{ formatDate(date) }}</h2>
    <ul class="mt-2 space-y-2">
      <li v-for="item in items" :key="item.type">
        <RouterLink :to="`/letters/${item.type}/${item.date}`" class="block py-1">
          <span class="inline-block rounded-full px-2 py-0.5 text-xs font-semibold" :class="item.type === 'news' ? 'bg-news-soft text-news-ink' : 'bg-cs-soft text-cs-ink'">{{ LETTER_LABEL[item.type] }}</span>
          <span class="mt-1 block text-[0.9375rem] leading-snug font-semibold">{{ item.title }}</span>
        </RouterLink>
      </li>
    </ul>
  </section>
</template>
