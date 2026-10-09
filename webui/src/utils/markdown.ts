/**
 * 插件 README 用的安全 Markdown 子集：先转义全部 HTML，再识别标题、段落、
 * 列表、代码块、行内代码、粗体/斜体与链接。链接只接受 http(s)，图片只保留
 * 替代文字，原始 HTML 一律按文本显示。输出可直接用于 v-html。
 */

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function emphasis(html: string): string {
  return html
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/(^|\W)__(.+?)__(?=\W|$)/g, '$1<strong>$2</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/(^|\W)_(.+?)_(?=\W|$)/g, '$1<em>$2</em>');
}

// 行内代码与链接先换成占位符，强调语法不会改到它们里面（如 URL 中的 _）
function inline(raw: string): string {
  const tokens: string[] = [];
  const hold = (html: string) => `\uE000${tokens.push(html) - 1}\uE000`;
  let html = escapeHtml(raw)
    .replace(/`([^`]+)`/g, (_, code: string) => hold(`<code>${code}</code>`))
    .replace(/!\[([^\]]*)\]\([^)]*\)/g, '$1')
    .replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, (_, text: string, url: string) =>
      /^https?:\/\//i.test(url)
        ? hold(
            `<a href="${url}" target="_blank" rel="noopener noreferrer">${emphasis(
              text
            )}</a>`
          )
        : text
    );
  html = emphasis(html);
  return html.replace(/\uE000(\d+)\uE000/g, (_, i: string) => tokens[+i]);
}

const LIST_ITEM = /^\s*(?:([-*+])|(\d+)[.)])\s+(.*)$/;

export function renderMarkdown(source: string): string {
  const lines = source
    .replace(/\uE000/g, '')
    .replace(/\r\n?/g, '\n')
    .split('\n');
  const out: string[] = [];
  let paragraph: string[] = [];
  let list: { ordered: boolean; items: string[] } | null = null;
  let code: string[] | null = null;

  const flush = () => {
    if (paragraph.length) out.push(`<p>${inline(paragraph.join(' '))}</p>`);
    paragraph = [];
    if (list) {
      const tag = list.ordered ? 'ol' : 'ul';
      const items = list.items.map((item) => `<li>${inline(item)}</li>`);
      out.push(`<${tag}>${items.join('')}</${tag}>`);
    }
    list = null;
  };

  for (const line of lines) {
    if (code) {
      if (/^\s*```/.test(line)) {
        out.push(`<pre><code>${escapeHtml(code.join('\n'))}</code></pre>`);
        code = null;
      } else code.push(line);
      continue;
    }
    if (/^\s*```/.test(line)) {
      flush();
      code = [];
      continue;
    }
    const heading = /^\s*(#{1,6})\s+(.*?)\s*#*\s*$/.exec(line);
    if (heading) {
      flush();
      // README 嵌在详情栏里，标题从 h3 起，不与页面标题争层级
      const level = Math.min(heading[1].length + 2, 6);
      out.push(`<h${level}>${inline(heading[2])}</h${level}>`);
      continue;
    }
    const item = LIST_ITEM.exec(line);
    if (item) {
      const ordered = item[2] !== undefined;
      if (paragraph.length || (list && list.ordered !== ordered)) flush();
      list ??= { ordered, items: [] };
      list.items.push(item[3]);
      continue;
    }
    if (!line.trim()) {
      flush();
      continue;
    }
    // 列表项的续行并入上一项
    if (list && /^\s+/.test(line)) {
      list.items[list.items.length - 1] += ` ${line.trim()}`;
      continue;
    }
    if (list) flush();
    paragraph.push(line.trim());
  }
  // 未闭合的代码块按代码块收尾
  if (code) out.push(`<pre><code>${escapeHtml(code.join('\n'))}</code></pre>`);
  flush();
  return out.join('');
}
