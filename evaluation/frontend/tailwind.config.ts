import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{js,ts,jsx,tsx}", "./components/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#171717",
        paper: "#f7f4ee",
        line: "#d9d4cc",
        pine: "#183c3a",
        terracotta: "#bd6048",
        gold: "#b98735",
      },
      boxShadow: {
        panel: "0 16px 45px rgba(55, 49, 38, .07)",
      },
    },
  },
  plugins: [],
};

export default config;
