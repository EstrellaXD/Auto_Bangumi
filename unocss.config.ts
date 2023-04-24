import {
  defineConfig,
  presetAttributify,
  presetIcons,
  presetUno,
} from 'unocss';
import presetRemToPx from '@unocss/preset-rem-to-px';

export default defineConfig({
  presets: [
    presetUno(),
    presetRemToPx(),
    presetAttributify(),
    presetIcons({ autoInstall: true, cdn: 'https://esm.sh/' }),
  ],
  shortcuts: [[/^wh-(.*)$/, ([, t]) => `w-${t} h-${t}`]],
});
