// src/index.ts
var e = {
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
}, t = class extends HTMLElement {
	text = e["en-US"];
	bangumiId = 0;
	body;
	unsubscribe;
	async connectedCallback() {
		this.text = e[this.host.i18n.locale] ?? e["en-US"], this.bangumiId = this.context.bangumiId;
		let t = this.shadowRoot ?? this.attachShadow({ mode: "open" });
		t.innerHTML = "\n      <style>\n        :host { display: block; }\n        ul { margin: 0; padding: 0; list-style: none; display: flex; flex-direction: column; gap: 4px; }\n        li {\n          display: flex; align-items: center; gap: 12px; padding: 8px 12px;\n          background: var(--ab-color-surface-2); border-radius: var(--ab-radius-sm);\n        }\n        .name { flex: 1; min-width: 0; overflow-wrap: anywhere; font-size: 13px; font-family: var(--ab-font-mono); }\n        .mark { width: 8px; height: 8px; border-radius: 2px; background: var(--ab-color-primary); }\n        button {\n          padding: 4px 10px; border: 1px solid var(--ab-color-border); border-radius: var(--ab-radius-sm);\n          background: var(--ab-color-surface); color: var(--ab-color-text); font: inherit; font-size: 12px; cursor: pointer;\n        }\n        button:focus-visible { outline: 2px solid var(--ab-color-primary); outline-offset: 2px; }\n        p { margin: 0; font-size: 13px; color: var(--ab-color-text-secondary); }\n      </style>\n      <div></div>\n    ", this.body = t.querySelector("div"), this.unsubscribe = this.host.events.on("manual-pick.picked", (e) => {
			e?.bangumi_id === this.bangumiId && this.load();
		}), await this.load();
	}
	disconnectedCallback() {
		this.unsubscribe?.();
	}
	async load() {
		let [e, t] = await Promise.all([this.host.api.get(`/api/v1/bangumi/${this.bangumiId}/torrents`), this.host.api.get(`picks/${this.bangumiId}`)]);
		this.render(e, t.torrent_id);
	}
	render(e, t) {
		if (this.body.replaceChildren(), !e.length) {
			let e = document.createElement("p");
			e.textContent = this.text.empty, this.body.append(e);
			return;
		}
		let n = document.createElement("ul");
		for (let r of e) {
			let e = document.createElement("li"), i = document.createElement("span");
			if (i.className = "name", i.textContent = r.name, e.append(i), r.id === t) {
				let t = document.createElement("span");
				t.className = "mark", t.title = this.text.picked, e.append(t);
			} else {
				let t = document.createElement("button");
				t.type = "button", t.textContent = this.text.pick, t.addEventListener("click", () => this.pick(r.id)), e.append(t);
			}
			n.append(e);
		}
		this.body.append(n);
	}
	async pick(e) {
		try {
			await this.host.api.put(`picks/${this.bangumiId}`, { torrent_id: e });
		} catch {
			this.host.toast(this.text.failed, "error");
		}
	}
};
customElements.get("ab-plugin-manual-pick") || customElements.define("ab-plugin-manual-pick", t);
