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
    presetIcons({ cdn: 'https://esm.sh/' }),
  ],
  theme: {
    colors: {
      primary: '#493475',
    },
  },
  rules: [
    [
      'bg-theme-row',
      {
        background: 'linear-gradient(90.5deg, #372A87 1.53%, #9B4D9C 96.48%)',
      },
    ],
    [
      'bg-theme-col',
      {
        background: 'linear-gradient(180deg, #3C239F 0%, #793572 100%)',
      },
    ],
  ],
  shortcuts: [
    [/^wh-(.*)$/, ([, t]) => `w-${t} h-${t}`],
    ['rel', 'relative'],
    ['abs', 'absolute'],
    ['fx-cer', 'flex items-center'],
    ['f-cer', 'fx-cer justify-center'],
    ['text-h1', 'text-24px'],
    ['text-h2', 'text-20px'],
    ['text-h3', 'text-16px'],
    ['text-main', 'text-12px'],
    [
      'ab-input',
      'outline-none min-w-0 w-200px rounded-6px border-1 border-black shadow-inset hover:border-color-[#7A46AE]',
    ],
    ['input-error', 'border-color-[#CA0E0E]'],
    ['is-btn', 'cursor-pointer select-none'],
    ['is-disabled', 'cursor-not-allowed select-none'],
  ],
});
