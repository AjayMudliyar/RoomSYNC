import { baseEslintConfig } from "@roomsync/config/eslint.base.mjs";

export default [
  ...baseEslintConfig,
  {
    files: ["metro.config.js"],
    languageOptions: {
      globals: {
        require: "readonly",
        module: "readonly",
        __dirname: "readonly",
      },
    },
    rules: {
      "@typescript-eslint/no-require-imports": "off",
    },
  },
];

