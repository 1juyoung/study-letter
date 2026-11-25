<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import Postmark from '../components/Postmark.vue'
import { fetchLetter, formatDate, LETTER_LABEL, type LetterType } from '../lib/letters'
import { renderDiagrams, renderMarkdown } from '../lib/markdown'

const props = defineProps<{ type: LetterType; date: string }>()

const html = ref('')
const error = ref('')
const body = ref<HTMLElement | null>(null)

watch(
  () => [props.type, props.date],
  async () => {
    html.value = ''
    error.value = ''
    try {
      html.value = renderMarkdown(await fetchLetter(props.type, props.date))
      await nextTick()
      if (body.value) await renderDiagrams(body.value)
    } catch (e) {
      error.value = (e as Error).message
    }
  },
  { immediate: true },
)
</script>

<template>
  <article>
    <header class="flex items-start justify-between gap-4 pb-4">
      <div class="pt-1">
        <RouterLink to="/letters" class="block text-sm text-sub">‹ 지난 레터</RouterLink>
        <p class="mt-3"><span class="inline-block rounded-full px-2.5 py-0.5 text-xs font-semibold" :class="type === 'news' ? 'bg-news-soft text-news-ink' : 'bg-cs-soft text-cs-ink'">{{ LETTER_LABEL[type] }}</span></p>
        <p class="mt-1 text-lg font-bold">{{ formatDate(date) }}</p>
      </div>
      <Postmark :type="type" :date="date" />
    </header>

    <p v-if="error" class="rounded-xl border border-line bg-sheet p-4 text-sm text-sub">{{ error }}</p>
    <p v-else-if="!html" class="text-sm text-sub">불러오는 중…</p>
    <!-- markdown-it을 html: false로 렌더링해 원문 HTML은 이스케이프된다 -->
    <div v-else ref="body" class="letter rounded-xl border border-line bg-sheet px-4 py-5 sm:px-7" :data-type="type" v-html="html" />
  </article>
</template>
