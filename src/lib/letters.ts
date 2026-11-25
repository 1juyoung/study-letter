export type LetterType = 'news' | 'cs'

export interface LetterMeta {
  type: LetterType
  date: string // YYYY-MM-DD (한국 날짜)
  title: string
  summary: string
}

export const LETTER_LABEL: Record<LetterType, string> = {
  news: '기술 뉴스',
  cs: 'CS 면접',
}

const base = import.meta.env.BASE_URL

// 레터는 매일 새로 커밋되므로 캐시를 쓰지 않고 항상 최신을 받는다
export async function fetchLetterIndex(): Promise<LetterMeta[]> {
  const res = await fetch(`${base}letters/index.json`, { cache: 'no-cache' })
  if (!res.ok) throw new Error('레터 목록을 불러오지 못했어요.')
  return res.json()
}

export async function fetchLetter(type: LetterType, date: string): Promise<string> {
  const res = await fetch(`${base}letters/${type}/${date}.md`, { cache: 'no-cache' })
  if (!res.ok) throw new Error(res.status === 404 ? '이 날짜의 레터가 없어요.' : '레터를 불러오지 못했어요.')
  return stripFrontMatter(await res.text())
}

function stripFrontMatter(text: string) {
  return text.replace(/^---\n[\s\S]*?\n---\n?/, '')
}

export function todayKST(): string {
  return new Intl.DateTimeFormat('sv-SE', { timeZone: 'Asia/Seoul' }).format(new Date())
}

export function formatDate(date: string): string {
  const [y, m, d] = date.split('-').map(Number)
  const weekday = '일월화수목금토'[new Date(y, m - 1, d).getDay()]
  return `${m}월 ${d}일 ${weekday}요일`
}
