// 手动选种：番剧详情页标签。无需构建；宿主在包裹元素的 Shadow DOM 中注入
// --ab-* 主题变量，这里直接使用。
const TEXT = {
  'zh-CN': {
    empty: '这条规则还没有种子记录',
    pick: '选用',
    picked: '已选',
    failed: '保存选择失败',
  },
  'en-US': {
    empty: 'This rule has no torrent records yet',
    pick: 'Pick',
    picked: 'Picked',
    failed: 'Failed to save the pick',
  },
};

class ManualPick extends HTMLElement {
  async connectedCallback() {
    this.text = TEXT[this.host.i18n.locale] ?? TEXT['en-US'];
    this.bangumiId = this.context.bangumiId;
    const root = this.shadowRoot ?? this.attachShadow({ mode: 'open' });
    root.innerHTML = `
      <style>
        :host { display: block; }
        ul { margin: 0; padding: 0; list-style: none; display: flex; flex-direction: column; gap: 4px; }
        li {
          display: flex; align-items: center; gap: 12px; padding: 8px 12px;
          background: var(--ab-color-surface-2); border-radius: var(--ab-radius-sm);
        }
        .name { flex: 1; min-width: 0; overflow-wrap: anywhere; font-size: 13px; font-family: var(--ab-font-mono); }
        .mark { width: 8px; height: 8px; border-radius: 2px; background: var(--ab-color-primary); }
        button {
          padding: 4px 10px; border: 1px solid var(--ab-color-border); border-radius: var(--ab-radius-sm);
          background: var(--ab-color-surface); color: var(--ab-color-text); font: inherit; font-size: 12px; cursor: pointer;
        }
        button:focus-visible { outline: 2px solid var(--ab-color-primary); outline-offset: 2px; }
        p { margin: 0; font-size: 13px; color: var(--ab-color-text-secondary); }
      </style>
      <div></div>
    `;
    this.body = root.querySelector('div');
    // 别的会话或标签页选种后，打开着的详情页也会刷新
    this.unsubscribe = this.host.events.on('manual-pick.picked', (payload) => {
      if (payload?.bangumi_id === this.bangumiId) this.load();
    });
    await this.load();
  }

  disconnectedCallback() {
    this.unsubscribe?.();
  }

  async load() {
    const [torrents, pick] = await Promise.all([
      // 宿主的只读 API：以 /api/v1/ 开头的路径只允许 GET
      this.host.api.get(`/api/v1/bangumi/${this.bangumiId}/torrents`),
      this.host.api.get(`picks/${this.bangumiId}`),
    ]);
    this.render(torrents, pick.torrent_id);
  }

  render(torrents, pickedId) {
    this.body.replaceChildren();
    if (!torrents.length) {
      const empty = document.createElement('p');
      empty.textContent = this.text.empty;
      this.body.append(empty);
      return;
    }
    const list = document.createElement('ul');
    for (const torrent of torrents) {
      const item = document.createElement('li');
      const name = document.createElement('span');
      name.className = 'name';
      name.textContent = torrent.name;
      item.append(name);
      if (torrent.id === pickedId) {
        const mark = document.createElement('span');
        mark.className = 'mark';
        mark.title = this.text.picked;
        item.append(mark);
      } else {
        const button = document.createElement('button');
        button.type = 'button';
        button.textContent = this.text.pick;
        button.addEventListener('click', () => this.pick(torrent.id));
        item.append(button);
      }
      list.append(item);
    }
    this.body.append(list);
  }

  async pick(torrentId) {
    try {
      await this.host.api.put(`picks/${this.bangumiId}`, { torrent_id: torrentId });
    } catch {
      this.host.toast(this.text.failed, 'error');
    }
  }
}

if (!customElements.get('ab-plugin-manual-pick')) {
  customElements.define('ab-plugin-manual-pick', ManualPick);
}
