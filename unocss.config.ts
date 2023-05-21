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
      running: '#A3D491',
      stopped: '#DF7F91',
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
    [
      'poster-shandow',
      {
        filter: 'drop-shadow(2px 2px 2px rgba(0, 0, 0, 0.1))',
      },
    ],
    [
      'poster-pen-active',
      {
        background: '#B4ABC6',
        'box-shadow': '2px 2px 4px rgba(0, 0, 0, 0.25)',
      },
    ],
  ],
  shortcuts: [
    [/^wh-(.*)$/, ([, t]) => `w-${t} h-${t}`],

    [
      'layout-container',
      'wh-screen min-w-1024px min-h-768px p-16px space-y-12px flex flex-col bg-[#F0F0F0]',
    ],
    [
      'layout-main',
      'flex space-x-20px overflow-hidden h-[calc(100vh_-_2_*_16px_-_60px_-_12px)]',
    ],
    ['layout-content', 'overflow-hidden h-full flex flex-col flex-1'],

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
    ['input-reset', 'bg-transparent min-w-0 flex-1 outline-none'],
    ['btn-click', 'hover:scale-110 active:scale-100'],
    ['line', 'w-full h-2px bg-[#DFE1EF]'],
  ],
});
