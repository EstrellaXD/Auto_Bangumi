import type { AbPluginElement } from '@autobangumi/plugin-ui';
import tokens from '@autobangumi/plugin-ui/tokens.css?inline';

// 元素名须与清单 [[plugin.ui]] 的 element 一致，并以 ab-plugin- 开头
const ELEMENT = 'ab-plugin-example';

class ExampleElement
  extends HTMLElement
  implements AbPluginElement<'settings.section'>
{
  // 宿主在插入文档前设置；用 declare 不生成类字段，否则构造时会被重置为 undefined
  declare host: AbPluginElement['host'];
  declare context: AbPluginElement<'settings.section'>['context'];

  connectedCallback() {
    const root = this.shadowRoot ?? this.attachShadow({ mode: 'open' });
    root.innerHTML = `
      <style>
        ${tokens}
        button {
          padding: 6px 12px;
          border: none;
          border-radius: var(--ab-radius-sm);
          background: var(--ab-color-primary);
          color: #fff;
          font: inherit;
          cursor: pointer;
        }
      </style>
      <button type="button"></button>
    `;
    const button = root.querySelector('button')!;
    button.textContent = this.host.i18n.locale.startsWith('zh')
      ? '调用插件路由'
      : 'Call plugin route';
    button.addEventListener('click', async () => {
      try {
        // 相对路径 → /api/v1/plugins/<plugin_id>/ping
        await this.host.api.get('ping');
        this.host.toast('OK');
      } catch (e) {
        this.host.toast(String(e), 'error');
      }
    });
  }
}

if (!customElements.get(ELEMENT))
  customElements.define(ELEMENT, ExampleElement);
