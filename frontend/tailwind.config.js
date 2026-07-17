/** @type {import('tailwindcss').Config} */
module.exports = {
    content: [
      // make sure these paths actually match where your .tsx live:
      "./app/**/*.{js,ts,jsx,tsx}",
      "./pages/**/*.{js,ts,jsx,tsx}",
      "./components/**/*.{js,ts,jsx,tsx}"
    ],
    theme: {
      extend: {},
    },
    plugins: [],
  };
  