import { createRequire } from "node:module";

const require = createRequire(import.meta.url);

const config = {
  endOfLine: "lf",
  tabWidth: 2,
  printWidth: 100,
  plugins: [
    require.resolve("prettier-plugin-embed"),
    require.resolve("prettier-plugin-packagejson"),
    require.resolve("prettier-plugin-sh"),
    require.resolve("prettier-plugin-sql"),
    require.resolve("prettier-plugin-tailwindcss"),
  ],

  // embed plugin
  embeddedSqlTags: ["sql"],

  // sql plugin
  language: "postgresql",
  keywordCase: "upper",
  dataTypeCase: "upper",
  functionCase: "upper",

  // tailwindcss plugin
  tailwindFunctions: ["cva", "clsx", "cn"],
};

export default config;
