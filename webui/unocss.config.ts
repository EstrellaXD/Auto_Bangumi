import {
  defineConfig,
  presetAttributify,
  presetIcons,
  presetUno,
} from 'unocss';
import presetRemToPx from '@unocss/preset-rem-to-px';

export default defineConfig({
  presets: [
    presetUno({
      dark: 'class',
    }),
    presetRemToPx({
      baseFontSize: 4,
    }),
    presetAttributify(),
    presetIcons({ cdn: 'https://esm.sh/' }),
  ],
  preflights: [
    {
      getCSS: () => `
        :root {
          font-size: 4px;
        }
        body {
          font-size: 4rem;
        }
      `,
    },
  ],
  theme: {
    breakpoints: {
      sm: '640px',
      pc: '1024px',
    },
    colors: {
      // Semantic colors via CSS variables (support light/dark)
      primary: 'var(--color-primary)',
      'primary-hover': 'var(--color-primary-hover)',
      'primary-light': 'var(--color-primary-light)',
      accent: 'var(--color-accent)',
      success: 'var(--color-success)',
      danger: 'var(--color-danger)',
      warning: 'var(--color-warning)',
      surface: 'var(--color-surface)',
      'surface-hover': 'var(--color-surface-hover)',
      'text-primary': 'var(--color-text)',
      'text-secondary': 'var(--color-text-secondary)',
      'text-muted': 'var(--color-text-muted)',
      border: 'var(--color-border)',
      'border-hover': 'var(--color-border-hover)',
      page: 'var(--color-bg)',

      // Legacy aliases (for gradual migration)
      running: 'var(--color-success)',
      stopped: 'var(--color-danger)',
    },
  },
  rules: [
    [
      'bg-theme-row',
      {
        background: 'linear-gradient(90.5deg, var(--color-primary) 1.53%, var(--color-primary-hover) 96.48%)',
      },
    ],
    [
      'bg-theme-col',
      {
        background: 'linear-gradient(180deg, var(--color-primary) 0%, var(--color-primary-hover) 100%)',
      },
    ],
    [
      'poster-shandow',
      {
        filter: 'drop-shadow(2px 2px 2px var(--shadow-color, rgba(0, 0, 0, 0.1)))',
      },
    ],
    [
      'poster-pen-active',
      {
        background: 'var(--color-primary-light)',
        'box-shadow': '2px 2px 4px var(--shadow-color, rgba(0, 0, 0, 0.25))',
      },
    ],
    // Shadows
    ['shadow-sm', { 'box-shadow': 'var(--shadow-sm)' }],
    ['shadow-md', { 'box-shadow': 'var(--shadow-md)' }],
    ['shadow-lg', { 'box-shadow': 'var(--shadow-lg)' }],
  ],
  shortcuts: [
    [/^wh-(.*)$/, ([, t]) => `w-${t} h-${t}`],
    [/^text-limit-(\d{0,})$/, ([, n]) => `line-clamp-${n}`],

    // position
    {
      rel: 'relative',
      abs: 'absolute',
    },

    // flex
    {
      'fx-cer': 'flex items-center',
      'f-cer': 'flex items-center justify-center',
    },

    // font size
    {
      'text-h1': 'text-24',
      'text-h2': 'text-20',
      'text-h3': 'text-16',
      'text-main': 'text-12',
      'text-body': 'text-14',
      'text-sm': 'text-12',
      'text-xs': 'text-10',
    },

    // input
    {
      'ab-input': `outline-none min-w-0 w-full sm:w-200 h-36 sm:h-28
                     px-12 text-main text-right
                     rounded-6
                     border-1 border-border
                     bg-surface text-text-primary
                     hover:border-primary
                     focus:border-primary focus:ring-2 focus:ring-primary/20
                     transition-colors duration-150
                    `,

      'input-error': 'border-danger',
      'input-reset': 'bg-transparent min-w-0 flex-1 outline-none',
    },

    // status
    {
      'is-btn': 'cursor-pointer select-none',
      'btn-click': 'hover:scale-110 active:scale-100',
      'is-disabled': 'cursor-not-allowed select-none opacity-50',
    },

    // other
    {
      line: 'w-full h-1 bg-border',
    },
  ],
});
