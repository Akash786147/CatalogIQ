/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Base URL for the FastAPI backend. Empty in dev — Vite proxies /api. */
  readonly VITE_API_BASE?: string;
  /** Set to "false" to hit the real backend instead of src/lib/mockData.ts. */
  readonly VITE_USE_MOCK?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
