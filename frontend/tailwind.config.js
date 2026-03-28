/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bashi: {
          bg: '#12151a',
          card: 'rgba(255, 255, 255, 0.03)',
          'card-hover': 'rgba(255, 255, 255, 0.06)',
          copper: '#d4a373',
          'copper-dark': '#854d27',
          accent: '#f4a261',
          'accent-warm': '#e76f51',
          border: 'rgba(255, 255, 255, 0.1)',
          'border-focus': 'rgba(212, 163, 115, 0.5)',
          text: '#ffffff',
          'text-secondary': 'rgba(255, 255, 255, 0.7)',
          'text-muted': 'rgba(255, 255, 255, 0.4)',
          success: '#a8c686',
        },
      },
    },
  },
  plugins: [],
}
