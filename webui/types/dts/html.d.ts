/**
 * https://unocss.dev/presets/attributify#vue-3
 */

import type { AttributifyAttributes } from '@unocss/preset-attributify';

declare module '@vue/runtime-dom' {
  interface HTMLAttributes extends AttributifyAttributes {}
}
