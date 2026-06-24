module.exports = {
  content: [
    './index.html',
    './src/**/*.{vue,js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        bk: {
          /* backgrounds — Copilot warm-white */
          bg:       '#FAF9F8',
          surface:  '#FFFFFF',
          card:     '#FFFFFF',
          elevated: '#F5F5F5',
          /* borders */
          border:   '#E1DFDD',
          'border-2': '#C8C6C4',
          /* Microsoft blue accent */
          yellow:         '#0F6CBD',
          'yellow-hover': '#0D5CA6',
          'yellow-dim':   'rgba(15,108,189,0.08)',
          /* text */
          text:     '#201F1E',
          'text-2': '#605E5C',
          'text-3': '#A19F9D',
          /* event types */
          buy:       '#107C10',
          sell:      '#D13438',
          dividend:  '#0F6CBD',
          earnings:  '#CA5010',
          rebalance: '#5C2E91',
          watch:     '#008272',
          ipo:       '#C43E1C',
          macro:     '#038387',
          tax:       '#986F0B',
          rights:    '#004E8C',
          bond:      '#4B4B4B',
          fx:        '#7160E8',
        },
      },
      fontFamily: {
        sans: [
          '"Segoe UI Variable"',
          '"Segoe UI"',
          'Pretendard Variable',
          'Pretendard',
          '-apple-system',
          'BlinkMacSystemFont',
          'sans-serif',
        ],
        mono: ['Cascadia Code', 'JetBrains Mono', 'ui-monospace', 'monospace'],
      },
      fontSize: {
        xs:   ['12px', { lineHeight: '1.5' }],
        sm:   ['14px', { lineHeight: '1.5' }],
        base: ['16px', { lineHeight: '1.65' }],
        lg:   ['18px', { lineHeight: '1.5' }],
        xl:   ['20px', { lineHeight: '1.4' }],
        '2xl':['24px', { lineHeight: '1.3' }],
        '3xl':['32px', { lineHeight: '1.2' }],
      },
      borderRadius: {
        none: '0px',
        sm:   '4px',
        DEFAULT: '6px',
        md:   '8px',
        lg:   '12px',
        xl:   '16px',
        '2xl':'20px',
        full: '9999px',
      },
      boxShadow: {
        card:   '0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04)',
        lifted: '0 4px 12px rgba(0,0,0,0.08), 0 2px 4px rgba(0,0,0,0.04)',
        modal:  '0 20px 48px rgba(0,0,0,0.12), 0 4px 12px rgba(0,0,0,0.08)',
      },
    },
  },
  plugins: [],
};
