import { defineConfig } from 'vite';

export default defineConfig({
  build: {
    rolldownOptions: {
      onwarn(warning, warn) {
        // Motion's React Server Component directives are inert in this browser bundle.
        if (warning.code === 'MODULE_LEVEL_DIRECTIVE' && /node_modules[\\/]+framer-motion[\\/]/.test(warning.id ?? '')) {
          return;
        }
        warn(warning);
      },
    },
  },
});
