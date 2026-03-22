/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/**/*.html",
    "./apps/**/*.html",
    "./apps/**/*.py",
    "./static/**/*.js",
  ],
  theme: {
    extend: {
      colors: {
        primary:  '#6366F1',
        accent:   '#22D3EE',
        dark:     '#0F172A',
        darker:   '#080D1A',
        surface:  '#1E2640',
        muted:    '#94A3B8',
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
      },
      backgroundImage: {
        'hero-gradient': 'linear-gradient(135deg, #0F172A 0%, #1a1040 50%, #0F172A 100%)',
      },
    },
  },
  plugins: [],
}
