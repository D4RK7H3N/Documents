/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        accent: "#a855f7",
        crimson: "#dc2626",
      },
    },
  },
  plugins: [],
};
