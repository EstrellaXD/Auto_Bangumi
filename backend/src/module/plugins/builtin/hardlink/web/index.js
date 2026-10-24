// 设置页分区：把下载根目录下已有的文件补链到媒体库（调用本插件的 POST /backfill）。
// 无需构建：宿主在包裹元素的 Shadow DOM 中注入 --ab-* 主题变量，这里直接使用。
const TEXT = {
  'zh-CN': {
    title: '链接已有文件',
    hint: '把下载根目录下已有的正片与字幕链接到媒体库。只在点击时运行；已链接的文件不会重复处理。',
    button: '链接已有文件',
    running: '链接中…',
    done: '已链接 {linked} · 已存在 {exists} · 冲突 {conflict} · 失败 {failed}',
    failed: '补链失败，详见日志',
  },
  'en-US': {
    title: 'Link existing files',
    hint: 'Link the videos and subtitles already in the download root into the library. Runs only when clicked; files that are already linked are skipped.',
    button: 'Link existing files',
    running: 'Linking…',
    done: 'linked {linked} · existing {exists} · conflict {conflict} · failed {failed}',
    failed: 'Backfill failed. See the log.',
  },
};

class HardlinkBackfill extends HTMLElement {
  connectedCallback() {
    const text = TEXT[this.host.i18n.locale] ?? TEXT['en-US'];
    const root = this.shadowRoot ?? this.attachShadow({ mode: 'open' });
    root.innerHTML = `
      <style>
        :host { display: block; }
        section {
          display: flex; flex-direction: column; align-items: flex-start; gap: 8px;
          padding: 16px; background: var(--ab-color-surface);
          border: 1px solid var(--ab-color-border); border-radius: var(--ab-radius-md);
        }
        h3 { margin: 0; font-size: 14px; font-weight: 600; }
        p { margin: 0; font-size: 12px; color: var(--ab-color-text-secondary); }
        button {
          padding: 6px 12px; border: none; border-radius: var(--ab-radius-sm);
          background: var(--ab-color-surface-2); color: var(--ab-color-text);
          font: inherit; font-size: 13px; cursor: pointer;
        }
        button:hover { background: var(--ab-color-surface-hover); }
        button:focus-visible { outline: 2px solid var(--ab-color-primary); outline-offset: 2px; }
        button:disabled { opacity: 0.5; cursor: default; }
        output { font-family: var(--ab-font-mono); font-size: 12px; font-variant-numeric: tabular-nums; }
      </style>
      <section>
        <h3></h3>
        <p></p>
        <button type="button"></button>
        <output aria-live="polite"></output>
      </section>
    `;
    const [title, hint] = [root.querySelector('h3'), root.querySelector('p')];
    const button = root.querySelector('button');
    const output = root.querySelector('output');
    title.textContent = text.title;
    hint.textContent = text.hint;
    button.textContent = text.button;
    button.addEventListener('click', async () => {
      button.disabled = true;
      button.textContent = text.running;
      output.textContent = '';
      try {
        const counts = await this.host.api.post('backfill');
        output.textContent = text.done.replace(/\{(\w+)\}/g, (_, key) => counts[key] ?? 0);
      } catch {
        this.host.toast(text.failed, 'error');
      } finally {
        button.disabled = false;
        button.textContent = text.button;
      }
    });
  }
}

if (!customElements.get('ab-plugin-hardlink-backfill')) {
  customElements.define('ab-plugin-hardlink-backfill', HardlinkBackfill);
}
