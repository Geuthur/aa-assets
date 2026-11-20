import globals from 'globals';
import { defineConfig, globalIgnores } from 'eslint/config';
import js from '@eslint/js';

export default defineConfig([
    globalIgnores(['**/static/**/react/**', 'frontend/**']),
    {
        languageOptions: {
            globals: {
                ...globals.browser,
                ...globals.commonjs,
                ...globals.jquery,
            },
            parserOptions: {
                ...js.configs.recommended.parserOptions,
                ecmaVersion: 'latest',
                ecmaFeatures: {
                    impliedStrict: true,
                },
                sourceType: 'module',
            },
        },
        rules: {
            ...js.configs.recommended.rules,
            indent: ['error', 4],
            quotes: ['error', 'single', {
                avoidEscape: true,
                allowTemplateLiterals: true
            }],
            semi: [2, 'always'],
            'no-unused-vars': 'off',
        },
    }
]);
