<script setup lang="ts">
import { computed } from 'vue'
import type { LetterType } from '../lib/letters'

// 편지 봉투의 우체국 소인처럼 레터 종류와 날짜를 찍어 주는 도장
const props = defineProps<{ type: LetterType; date: string }>()

const label = computed(() => (props.type === 'news' ? '기술 뉴스' : 'CS 면접'))
const day = computed(() => props.date.replaceAll('-', '.'))
const color = computed(() => (props.type === 'news' ? '#f0670a' : 'var(--color-cs-ink)'))
</script>

<template>
  <svg
    viewBox="0 0 120 120"
    class="size-20 shrink-0 -rotate-12"
    :style="{ color }"
    role="img"
    :aria-label="`${label} 레터, ${day}`"
  >
    <circle cx="60" cy="60" r="56" fill="none" stroke="currentColor" stroke-width="2.5" />
    <circle cx="60" cy="60" r="47" fill="none" stroke="currentColor" stroke-width="1" stroke-dasharray="2 3" />
    <text x="60" y="44" text-anchor="middle" fill="currentColor" font-size="13" font-weight="600" font-family="IBM Plex Sans KR, sans-serif">
      {{ label }}
    </text>
    <line x1="18" y1="56" x2="102" y2="56" stroke="currentColor" stroke-width="1.2" />
    <text x="60" y="74" text-anchor="middle" fill="currentColor" font-size="14" font-family="ui-monospace, Menlo, monospace">
      {{ day }}
    </text>
    <line x1="18" y1="84" x2="102" y2="84" stroke="currentColor" stroke-width="1.2" />
  </svg>
</template>
