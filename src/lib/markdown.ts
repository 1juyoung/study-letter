import hljs from 'highlight.js/lib/common'
import MarkdownIt from 'markdown-it'

const escapeHtml = (text: string) =>
  text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')

const md = new MarkdownIt({
  html: false, // AI가 쓴 글이라 HTML은 렌더링하지 않는다 (스크립트 삽입 방지)
  linkify: true,
  typographer: false,
  highlight(code, lang) {
    if (lang === 'mermaid') return `<pre class="mermaid">${escapeHtml(code)}</pre>`
    if (lang && hljs.getLanguage(lang)) {
      return `<pre class="hljs"><code>${hljs.highlight(code, { language: lang, ignoreIllegals: true }).value}</code></pre>`
    }
    return `<pre class="hljs"><code>${escapeHtml(code)}</code></pre>`
  },
})

// 외부 링크는 새 탭으로
const defaultLinkOpen = md.renderer.rules.link_open ?? ((tokens, idx, options, _env, self) => self.renderToken(tokens, idx, options))
md.renderer.rules.link_open = (tokens, idx, options, env, self) => {
  const href = String(tokens[idx].attrGet('href') ?? '')
  if (/^https?:\/\//.test(href)) {
    tokens[idx].attrSet('target', '_blank')
    tokens[idx].attrSet('rel', 'noopener noreferrer')
  }
  return defaultLinkOpen(tokens, idx, options, env, self)
}

export function renderMarkdown(source: string): string {
  return md.render(source)
}

/** 렌더링된 영역 안의 mermaid 블록을 도식으로 바꾼다. mermaid는 무거워서 도식이 있을 때만 불러온다. */
export async function renderDiagrams(container: HTMLElement) {
  const blocks = container.querySelectorAll<HTMLElement>('pre.mermaid')
  if (blocks.length === 0) return
  const { default: mermaid } = await import('mermaid')
  mermaid.initialize({
    startOnLoad: false,
    securityLevel: 'strict',
    theme: 'base',
    themeVariables: {
      fontFamily: '"IBM Plex Sans KR", sans-serif',
      primaryColor: '#FFF1F4',
      primaryBorderColor: '#F0386B',
      primaryTextColor: '#1F2330',
      lineColor: '#6A6F7D',
    },
  })
  await mermaid.run({ nodes: Array.from(blocks), suppressErrors: true })
}
