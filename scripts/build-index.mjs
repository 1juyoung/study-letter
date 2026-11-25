// public/letters/{news,cs}/YYYY-MM-DD.md 를 훑어서 public/letters/index.json 을 만든다.
// 레터 파일 맨 위 front matter(--- 사이)의 title, summary 를 목록에 쓴다.
import { readdirSync, readFileSync, writeFileSync, existsSync } from 'node:fs'
import { join } from 'node:path'

const root = join(import.meta.dirname, '..', 'public', 'letters')
const TYPES = ['news', 'cs']
const DATE_FILE = /^(\d{4}-\d{2}-\d{2})\.md$/

function readFrontMatter(text) {
  const match = text.match(/^---\n([\s\S]*?)\n---/)
  const meta = {}
  if (!match) return meta
  for (const line of match[1].split('\n')) {
    const i = line.indexOf(':')
    if (i > 0) meta[line.slice(0, i).trim()] = line.slice(i + 1).trim().replace(/^["']|["']$/g, '')
  }
  return meta
}

const letters = []
for (const type of TYPES) {
  const dir = join(root, type)
  if (!existsSync(dir)) continue
  for (const file of readdirSync(dir)) {
    const m = file.match(DATE_FILE)
    if (!m) continue
    const meta = readFrontMatter(readFileSync(join(dir, file), 'utf8'))
    letters.push({ type, date: m[1], title: meta.title ?? m[1], summary: meta.summary ?? '' })
  }
}
letters.sort((a, b) => (a.date === b.date ? a.type.localeCompare(b.type) : b.date.localeCompare(a.date)))

writeFileSync(join(root, 'index.json'), JSON.stringify(letters, null, 2) + '\n')
console.log(`letters/index.json: ${letters.length}개`)
