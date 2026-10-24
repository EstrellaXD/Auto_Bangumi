const s = {
  "zh-CN": {
    empty: "这条规则还没有种子记录",
    pick: "选用",
    picked: "已选",
    failed: "保存选择失败"
  },
  "en-US": {
    empty: "This rule has no torrent records yet",
    pick: "Pick",
    picked: "Picked",
    failed: "Failed to save the pick"
  }
};
class c extends HTMLElement {
  constructor() {
    super(...arguments), this.text = s["en-US"], this.bangumiId = 0;
  }
  async connectedCallback() {
    this.text = s[this.host.i18n.locale] ?? s["en-US"], this.bangumiId = this.context.bangumiId;
    const t = this.shadowRoot ?? this.attachShadow({ mode: "open" });
    t.innerHTML = `
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
    `, this.body = t.querySelector("div"), this.unsubscribe = this.host.events.on("manual-pick.picked", (i) => {
      (i == null ? void 0 : i.bangumi_id) === this.bangumiId && this.load();
    }), await this.load();
  }
  disconnectedCallback() {
    var t;
    (t = this.unsubscribe) == null || t.call(this);
  }
  async load() {
    const [t, i] = await Promise.all([
      // 宿主的只读 API：以 /api/v1/ 开头的路径只允许 GET
      this.host.api.get(`/api/v1/bangumi/${this.bangumiId}/torrents`),
      this.host.api.get(`picks/${this.bangumiId}`)
    ]);
    this.render(t, i.torrent_id);
  }
  render(t, i) {
    if (this.body.replaceChildren(), !t.length) {
      const n = document.createElement("p");
      n.textContent = this.text.empty, this.body.append(n);
      return;
    }
    const r = document.createElement("ul");
    for (const n of t) {
      const a = document.createElement("li"), o = document.createElement("span");
      if (o.className = "name", o.textContent = n.name, a.append(o), n.id === i) {
        const e = document.createElement("span");
        e.className = "mark", e.title = this.text.picked, a.append(e);
      } else {
        const e = document.createElement("button");
        e.type = "button", e.textContent = this.text.pick, e.addEventListener("click", () => this.pick(n.id)), a.append(e);
      }
      r.append(a);
    }
    this.body.append(r);
  }
  async pick(t) {
    try {
      await this.host.api.put(`picks/${this.bangumiId}`, { torrent_id: t });
    } catch {
      this.host.toast(this.text.failed, "error");
    }
  }
}
customElements.get("ab-plugin-manual-pick") || customElements.define("ab-plugin-manual-pick", c);
