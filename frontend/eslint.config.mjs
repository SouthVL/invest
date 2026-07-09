import js from "@eslint/js";
import next from "eslint-config-next";
import tseslint from "typescript-eslint";

export default tseslint.config(
  js.configs.recommended,
  ...tseslint.configs.recommended,
  ...next,
  {
    ignores: [".next/**", "node_modules/**", "coverage/**"]
  }
);
