/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
      },
      colors: {
        primary: {
          yellow: '#FFD60A',
          green: '#34C759',
          blue: '#007AFF',
        },
      },
      animation: {
        'float': 'float 3s ease-in-out infinite',
        'pulse': 'pulse 2s infinite',
        bubble: 'bubble 0.22s ease-out',
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-15px)' },
        },
        bubble: {
          '0%': {
            transform: 'scale(0.8) translateY(8px)',
            opacity: '0',
          },
          '60%': {
            transform: 'scale(1.03) translateY(0)',
            opacity: '1',
          },
          '100%': {
            transform: 'scale(1) translateY(0)',
            opacity: '1',
          },
        },
      },
    },
  },
  plugins: [],
}