/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        sidebar: 'var(--sidebar-bg)',
        'sidebar-hover': 'var(--sidebar-hover)',
        'sidebar-active': 'var(--sidebar-active)',
        topbar: 'var(--topbar-bg)',
        accent: 'var(--accent)',
        'accent-dark': 'var(--accent-dark)',
        content: 'var(--content-bg)',
        card: 'var(--card-bg)',
        'table-header': 'var(--table-header-bg)',
        line: 'var(--border)',
        muted: 'var(--text-muted)',
        danger: 'var(--danger)',
        warning: 'var(--warning)',
        info: 'var(--info)',
      },
      fontSize: {
        table: ['13px', '18px'],
      },
    },
  },
  plugins: [],
};
