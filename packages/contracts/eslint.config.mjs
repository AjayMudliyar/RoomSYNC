import { baseEslintConfig } from "@roomsync/config/eslint.base.mjs";

export default [
  ...baseEslintConfig,
  {
    files: ["scripts/**/*.mjs"],
    languageOptions: {
      globals: {
        console: "readonly",
        process: "readonly",
      },
    },
  },
];

