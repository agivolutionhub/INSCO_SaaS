/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#9a7e5c',
          50: '#faf8f5',
          100: '#f3ece2',
          200: '#e6d9c6',
          300: '#d4c2a7',
          400: '#bfa584',
          500: '#9a7e5c',
          600: '#8c7154',
          700: '#735c45',
          800: '#5f4c3a',
          900: '#4f4031',
          950: '#2a221a',
        },
        orange: {
          DEFAULT: '#dd8d46',
          50: '#fdf7f2',
          100: '#fbeee3',
          200: '#f8dcc9',
          300: '#f3c49f',
          400: '#eba46e',
          500: '#dd8d46',
          600: '#ca7235',
          700: '#a85a2d',
          800: '#88492b',
          900: '#6f3d27',
          950: '#3c1e12',
        },
      },
      fontFamily: {
        sans: ['Poppins', 'sans-serif'],
      },
      animation: {
        'fadeIn': 'fadeIn 0.3s ease-out forwards',
        'shimmer': 'shimmer 1.5s infinite linear',
      },
      keyframes: {
        fadeIn: {
          'from': { opacity: '0', transform: 'translateY(10px)' },
          'to': { opacity: '1', transform: 'translateY(0)' },
        },
        shimmer: {
          '0%': { transform: 'translateX(-100%)' },
          '100%': { transform: 'translateX(200%)' },
        },
      },
      skew: {
        '30': '30deg',
      },
    },
  },
  plugins: [],
}